import asyncio
from caproto.server import pvproperty, PVGroup, run
from SmaractStage import SmarAct

smaract_controller = SmarAct(MCS2="MCS2-00015447", axis=[3,4])
class Motor():
    def __init__(self, axis):
        self.axis = axis

    def waitdone(self):
        smaract_controller.waitdone(self.axis)

    def ismoving(self, wait=True):
        return smaract_controller.ismoving(self.axis)

    def onlimit(self):
        val = smaract_controller.limit_reached(self.axis)
        return val

    def get_pos(self):
        val = smaract_controller.get_pos(self.axis)
        return val

    def get_speed(self):
        val = smaract_controller.get_speed(self.axis)
        return val
    
    def set_pos(self, value):
        val = smaract_controller.set_pos(self.axis, value)
        return val
    
    def set_speed(self, value):
        val = smaract_controller.set_speed(self.axis, value)
        return val
    
    def mvr(self, val, wait=True):
        smaract_controller.mvr(self.axis, val, wait=wait)
    
    def mv(self, val, wait=True):
        smaract_controller.mv(self.axis, val, wait=wait)

class SmarActMotorRecord(PVGroup):
    """
    EPICS motor record for a SmarAct motor using caproto.

    This record is modeled after the EPICS motor record (see https://epics.anl.gov/bcda/synApps/motor/motorRecord.html).

    Record fields:
      - RBV (Readback): Motor's current position.
      - VAL (Target Position): Commanded motor position.
      - DMOV (Done Moving): Movement status (0: moving, 1: complete).
      - VBAS (Motor Speed): The speed at which the motor is operating.
      - TWR (Tweak Reverse): Adjust position in reverse direction.
      - TWF (Tweak Forward): Adjust position in forward direction.
      - TWV (Tweak Value): Adjustment value for tweaks.
      - HLM (High Limit): Maximum positional limit.
      - LLM (Low Limit): Minimum positional limit.
    """
    RBV = pvproperty(value=0.0, doc='(RVAL) Current motor position')
    VAL = pvproperty(value=0.0, doc='(VAL) Desired motor position')
    DMOV = pvproperty(value=1, doc='Done moving status: 0 = moving, 1 = done')
    VBAS = pvproperty(value=0.0, doc='(VBAS) Motor speed')
    TWR = pvproperty(value=0.0, doc='(TWR) Tweak reverse')
    TWF = pvproperty(value=0.0, doc='(TWF) Tweak forward')
    TWV = pvproperty(value=0.0, doc='(TWV) Tweak value')
    HLM = pvproperty(value=0.0, doc='(HLM) Higher Limit: 0 = not on limit, 1 = on limit')
    LLM = pvproperty(value=0.0, doc='(LLM) Lower Limite: 0 = not on limit, 1 = on limit')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Instantiate the motor device
        axis_number = kwargs['axis']
        self.motor = Motor(axis_number)
        # Optionally, perform any required initialization here:
        # self.motor.initialize() 

    @VAL.putter
    async def VAL(self, instance, value):
        """
        When a new target position is written, command the motor to move.
        This method runs the (possibly blocking) move() call in a thread.
        The dmov flag is updated to indicate motion is in progress and completion.
        """
        print(f"[SmarActMotorRecord] Received command to move motor to {value}")
        # Set dmov to 0 to indicate movement start.
        self.DMOV.put(0)
        # Move the motor asynchronously.
        await asyncio.to_thread(self.motor.mv, value)
        # After moving, update dmov to 1 to indicate motion complete.
        self.DMOV.put(1)
        return value

    @TWR.putter
    async def TWR(self, instance, value):
        """
        When a new target position is written, command the motor to move.
        This method runs the (possibly blocking) move() call in a thread.
        The dmov flag is updated to indicate motion is in progress and completion.
        """
        # Set dmov to 0 to indicate movement start.
        self.DMOV.put(0)
        # Move the motor asynchronously.
        await asyncio.to_thread(self.motor.mvr, -1*self.TWV.get())
        # After moving, update dmov to 1 to indicate motion complete.
        self.DMOV.put(1)
        return value

    @TWF.putter
    async def TWF(self, instance, value):
        """
        When a new target position is written, command the motor to move.
        This method runs the (possibly blocking) move() call in a thread.
        The dmov flag is updated to indicate motion is in progress and completion.
        """
        # Set dmov to 0 to indicate movement start.
        self.DMOV.put(0)
        # Move the motor asynchronously.
        await asyncio.to_thread(self.motor.mvr, self.TWV.get())
        # After moving, update dmov to 1 to indicate motion complete.
        self.DMOV.put(1)
        return value

    @RBV.getter
    async def RBV(self, instance):
        """
        Return the current motor position.
        Runs the get_position() method in a thread to avoid blocking the event loop.
        """
        pos = await asyncio.to_thread(self.motor.get_pos)
        return pos

    @VBAS.getter
    async def VBAS(self, instance):
        """
        Return the motor speed.
        Runs the get_speed() method in a thread to avoid blocking the event loop.
        """
        pos = await asyncio.to_thread(self.motor.get_speed)
        return pos

    @DMOV.getter
    async def DMOV(self, instance):
        """
        Return the current motor position.
        Runs the get_position() method in a thread to avoid blocking the event loop.
        """
        pos = await asyncio.to_thread(self.motor.ismoving)
        return pos

    @HLM.getter
    async def HLM(self, instance):
        """
        Return the current motor position.
        Runs the get_position() method in a thread to avoid blocking the event loop.
        """
        pos = await asyncio.to_thread(self.motor.onlimit)
        if pos == 2:
            pos = True
        else:
            pos = False
        return pos

    @LLM.getter
    async def LLM(self, instance):
        """
        Return the current motor position.
        Runs the get_position() method in a thread to avoid blocking the event loop.
        """
        pos = await asyncio.to_thread(self.motor.onlimit)
        if pos == 1:
            pos = True
        else:
            pos = False        
        return pos

if __name__ == '__main__':
    # Run the caproto server with our motor records.
    # These will start a PV server publishing the motor records.
    motor1 = SmarActMotorRecord(axis=3)
    motor2 = SmarActMotorRecord(axis=4)
    run((motor1, motor2), pv_cache=True)
