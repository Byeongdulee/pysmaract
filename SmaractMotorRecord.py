import asyncio
from caproto.server import pvproperty, PVGroup, run
from SmaractStage import SmarAct

class SmarActMotorRecord(PVGroup):
    """
    EPICS motor record for a SmarAct motor using caproto.
    
    This record is modeled after the EPICS motor record (see
    https://epics.anl.gov/bcda/synApps/motor/motorRecord.html).
    
    Record fields:
      - 'position' (RVAL): Readback of the current motor position.
      - 'target_position' (DVAL): Desired motor position command.
      - 'dmov': Done moving status (0 indicates moving; 1 indicates motion complete).
    
    Additional EPICS motor record fields can be added as needed.
    """
    position = pvproperty(value=0.0, doc='(RVAL) Current motor position')
    target_position = pvproperty(value=0.0, doc='(DVAL) Desired motor position')
    dmov = pvproperty(value=1, doc='Done moving status: 0 = moving, 1 = done')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Instantiate the motor device
        self.motor = SmarAct()
        # Optionally, perform any required initialization here:
        # self.motor.initialize() 

    @target_position.putter
    async def target_position(self, instance, value):
        """
        When a new target position is written, command the motor to move.
        This method runs the (possibly blocking) move() call in a thread.
        The dmov flag is updated to indicate motion is in progress and completion.
        """
        print(f"[SmarActMotorRecord] Received command to move motor to {value}")
        # Set dmov to 0 to indicate movement start.
        self.dmov.put(0)
        # Move the motor asynchronously.
        await asyncio.to_thread(self.motor.move, value)
        # After moving, update dmov to 1 to indicate motion complete.
        self.dmov.put(1)
        return value

    @position.getter
    async def position(self, instance):
        """
        Return the current motor position.
        Runs the get_position() method in a thread to avoid blocking the event loop.
        """
        pos = await asyncio.to_thread(self.motor.get_position)
        return pos

if __name__ == '__main__':
    # Run the caproto server with our motor record.
    # This will start a PV server publishing the motor record.
    run((SmarActMotorRecord,), pv_cache=True)
