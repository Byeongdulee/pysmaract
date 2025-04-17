import sys
import smaract.ctl as ctl
import time
# installation: 
# 1. download SDK
# 2. Look for python package folder (C:\SmarAct\MCS2\SDK\Python\packages\)
#    There, you will see a zip file, for example, smaract.ctl-1.3.36.zip
# 3. python -m pip install smaract.<productname>-<version.zip

class SmarAct():
    
    base_units = []
    units = []
    channel_names = []

    def __init__(self, smaractstage = 'MCS2-00015447', channels = [0, 1, 2, 3]):
        self.channels = channels
        print("")
        buffer = ctl.FindDevices()
        print(buffer)
        if len(buffer)==0:
            print("no MCS2 device is found.")
            return
        buff = buffer.split("\n")
        print("")
        if not (smaractstage in buffer):
            print(f"{smaractstage} is not found.")
            return
        print("")
        for stage in buff:
            if smaractstage in stage:
                self.smaractstage = stage
        #try:
            # Open the first MCS2 device from the list
        try:
            smaract = ctl.Open(self.smaractstage)
            print("MCS2 opened {}.".format(self.smaractstage))
            self.smaract = smaract
        except:
            print(f"Error in loading {self.smaractstage}")
            return
        trnum=0
        tinum=0
        for ch in channels:
            ctl.SetProperty_i32(self.smaract, ch, ctl.Property.MAX_CL_FREQUENCY, 6000)
            ctl.SetProperty_i32(self.smaract, ch, ctl.Property.HOLD_TIME, 1000)
            self.set_speed(ch)  # return the speed and acc to defaults (1mm/s, 10mm/s2)
            un, base_unit = self.get_unit(ch)
            self.base_units.append(base_unit)
            self.units.append(un)
            if un == 'mm':
                name0 = 'trans'
                trnum += 1
                n = trnum
            elif un == "deg":
                name0 = 'tilt'
                tinum += 1
                n = tinum
            else:
                name0 = 'None'
                k = k+1
                n = k
            self.channel_names.append("%s%i"%(name0, n))
        self.version = ctl.GetFullVersionString()
        #print("SmarActCTL library version: '{}'.".format(version))


    def calibrate(self, channel):
        print("MCS2 start calibration on channel: {}.".format(channel))
        # Set calibration options (start direction: forward)
        ctl.SetProperty_i32(self.smaract, channel, ctl.Property.CALIBRATION_OPTIONS, 0)
        # Start calibration sequence
        ctl.Calibrate(self.smaract, channel)
        # Note that the function call returns immediately, without waiting for the movement to complete.
        # The "ChannelState.CALIBRATING" flag in the channel state can be monitored to determine
        # the end of the calibration sequence.
        while True:
            state = ctl.GetProperty_i32(self.smaract, channel, ctl.Property.CHANNEL_STATE)
            if bool(state & ctl.ChannelState.CALIBRATING):
                time.sleep(0.1)
            else:
                break
    # FIND REFERENCE
    # Since the position sensors work on an incremental base, the referencing sequence is used to
    # establish an absolute positioner reference for the positioner after system startup.
    # Note: the "ChannelState.IS_REFERENCED" in the channel state can be used to to decide
    # whether it is necessary to perform the referencing sequence.
    def findReference(self, channel):
        print("MCS2 find reference on channel: {}.".format(channel))
        # Set find reference options.
        # The reference options specify the behavior of the find reference sequence.
        # The reference flags can be ORed to build the reference options.
        # By default (options = 0) the positioner returns to the position of the reference mark.
        # Note: In contrast to previous controller systems this is not mandatory.
        # The MCS2 controller is able to find the reference position "on-the-fly".
        # See the MCS2 Programmer Guide for a description of the different modes.
        ctl.SetProperty_i32(self.smaract, channel, ctl.Property.REFERENCING_OPTIONS, 0)
        # Set velocity to 1mm/s
        ctl.SetProperty_i64(self.smaract, channel, ctl.Property.MOVE_VELOCITY, 1000000000)
        # Set acceleration to 10mm/s2.
        ctl.SetProperty_i64(self.smaract, channel, ctl.Property.MOVE_ACCELERATION, 10000000000)
        # Start referencing sequence
        ctl.Reference(self.smaract, channel)
        # Note that the function call returns immediately, without waiting for the movement to complete.
        # The "ChannelState.REFERENCING" flag in the channel state can be monitored to determine
        # the end of the referencing sequence.
        while True:
            state = ctl.GetProperty_i32(self.smaract, channel, ctl.Property.CHANNEL_STATE)
            if bool(state & ctl.ChannelState.REFERENCING):
                time.sleep(0.1)
            else:
                break
    def mv(self, ax, target, wait=True):
        if type(ax) == str:
            ax = self.channels[self.channel_names.index(ax)]
        #ax = channels[chname]
        self.move(ax, target=target, absolute=True, wait=wait)
        
    def mvr(self, ax, target, wait=True):
        if type(ax) == str:
            ax = self.channels[self.channel_names.index(ax)]
        #ax = channels[chname]
        self.move(ax, target=target, absolute=False, wait=wait)

    def set_speed(self, channel, vel=5, acc=10):
        if type(channel) == str:
            channel = self.channels[self.channel_names.index(channel)]

        # input vel and acc should be in mm/s and mm/s^2
        vel = int(vel*1E9)
        acc = int(acc*1E9)
        # velocity 1000000000 equals 1mm/s
        # acceler  10000000000 equals 10mm/s2.
        ctl.SetProperty_i64(self.smaract, channel, ctl.Property.MOVE_VELOCITY, vel)
        ctl.SetProperty_i64(self.smaract, channel, ctl.Property.MOVE_ACCELERATION, acc)

    def get_speed(self, channel):
        if type(channel) == str:
            channel = self.channels[self.channel_names.index(channel)]
        vel = ctl.GetProperty_i64(self.smaract, channel, ctl.Property.MOVE_VELOCITY)
        acc = ctl.GetProperty_i64(self.smaract, channel, ctl.Property.MOVE_ACCELERATION)
        return (vel/1E9, acc/1E9)

    # MOVE
    # The move command instructs a positioner to perform a movement.
    # The given "move_value" parameter is interpreted according to the previously configured move mode.
    # It can be a position value (in case of closed loop movement mode), a scan value (in case of scan move mode)
    # or a number of steps (in case of step move mode).
    def move(self, channel, target=0.001, absolute=True, wait=True):
        # input target is in mm or deg.
        target = int(target*1E9)
        # Set move mode depending properties for the next movement.
        if absolute:
            move_mode = ctl.MoveMode.CL_ABSOLUTE
            # Set move velocity [in pm/s].
    #        ctl.SetProperty_i64(self.smaract, channel, ctl.Property.MOVE_VELOCITY, 1000000000)
            # Set move acceleration [in pm/s2].
    #        ctl.SetProperty_i64(self.smaract, channel, ctl.Property.MOVE_ACCELERATION, 1000000000)
            # Specify absolute position [in pm].
            # (For Piezo Scanner channels adjust to valid value within move range, e.g. +-10000000.)

    #        print("MCS2 move channel {} to absolute position: {} pm.".format(channel, target))
        else:
            move_mode = ctl.MoveMode.CL_RELATIVE
            # Set move velocity [in pm/s].
    #        ctl.SetProperty_i64(self.smaract, channel, ctl.Property.MOVE_VELOCITY, 500000000)
            # Set move acceleration [in pm/s2].
    #        ctl.SetProperty_i64(self.smaract, channel, ctl.Property.MOVE_ACCELERATION, 10000000000)
            # Specify relative position distance [in pm] and direction.
            # (For Piezo Scanner channels adjust to valid value within move range, e.g. 10000000.)
    #        print("MCS2 move channel {} relative: {} pm.".format(channel, target))

        # Start actual movement.
        ctl.SetProperty_i32(self.smaract, channel, ctl.Property.MOVE_MODE, move_mode)
        ctl.Move(self.smaract, channel, target, 0)
        # Note that the function call returns immediately, without waiting for the movement to complete.
        if wait:
            while self.ismoving(channel):
                time.sleep(0.01)
        # The "ChannelState.ACTIVELY_MOVING" (and "ChannelState.CLOSED_LOOP_ACTIVE") flag in the channel state
        # can be monitored to determine the end of the movement.
    def waitdone(self, channel):
        while self.ismoving(channel):
            time.sleep(0.01)
    # STOP
    # This command stops any ongoing movement. It also stops the hold position feature of a closed loop command.
    # Note for closed loop movements with acceleration control enabled:
    # The first "stop" command sent while moving triggers the positioner to come to a halt by decelerating to zero.
    # A second "stop" command triggers a hard stop ("emergency stop").
    def stop(self, channel):
        if type(channel) == str:
            self.channels[self.channel_names.index(channel)]
        print("MCS2 stop channel: {}.".format(channel))
        ctl.Stop(self.smaract, channel)


    def _get_unit(self, channel):
        base_unit = ctl.GetProperty_i32(self.smaract, channel, ctl.Property.POS_BASE_UNIT)
        return base_unit

    def get_unit(self, channel):
        base_unit = self._get_unit(channel)
        if base_unit == ctl.BaseUnit.METER:
            return "mm", base_unit
        else: 
            return "deg", base_unit


        # The move mode states the type of movement performed when sending the "Move" command.
    #move_mode = ctl.MoveMode.CL_ABSOLUTE

    def isconnected(self, ax=-1):
        # Now we read the state for all available channels.
        # The passed "idx" parameter (the channel index in this case) is zero-based.
        if ax>-1:
            state = ctl.GetProperty_i32(self.smaract, ax, ctl.Property.CHANNEL_STATE)
            if bool(state & ctl.ChannelState.SENSOR_PRESENT):
                return True
            else:
                return False
        status = []
        for channel in self.channels:
            state = ctl.GetProperty_i32(self.smaract, channel, ctl.Property.CHANNEL_STATE)
            # The returned channel state holds a bit field of several state flags.
            # See the MCS2 Programmers Guide for the meaning of all state flags.
            # We pick the "sensorPresent" flag to check if there is a positioner connected
            # which has an integrated sensor.
            # Note that in contrast to previous controller systems the controller supports
            # hotplugging of the sensor module and the actuators.
            if bool(state & ctl.ChannelState.SENSOR_PRESENT):
                status.append(True)
                print("MCS2 channel {} has a sensor.".format(channel))
            else:
                status.append(False)
                print("MCS2 channel {} has no sensor.".format(channel))
        return status

    def get_pos(self, ax):
        # return position in deg or mm
        if type(ax) == str:
            ax = self.channels[self.channel_names.index(ax)]
        try:
            r_id1 = ctl.RequestReadProperty(self.smaract, ax, ctl.Property.POSITION, 0)
            position = ctl.ReadProperty_i64(self.smaract, r_id1)

            # Print the results
            #print("MCS2 current position of channel {}: {}".format(ax, position), end='')
            #print("pm.") if base_units[ax] == ctl.BaseUnit.METER else print("ndeg.")
            return position/1E9
        except ctl.Error as e:
            # Catching the "ctl.Error" exceptions may be used to handle errors of SmarActCTL function calls.
            # The "e.func" element holds the name of the function that caused the error and
            # the "e.code" element holds the error code.
            # Passing an error code to "GetResultInfo" returns a human readable string specifying the error.
            print("MCS2 {}: {}, error: {} (0x{:04X}) in line: {}."
                .format(e.func, ctl.GetResultInfo(e.code), ctl.ErrorCode(e.code).name, e.code, (sys.exc_info()[-1].tb_lineno)))

        except Exception as ex:
            print("Unexpected error: {}, {} in line: {}".format(ex, type(ex), (sys.exc_info()[-1].tb_lineno)))
            raise

    def set_pos(self, ax, position=0):
        if type(ax) == str:
            ax = self.channels[self.channel_names.index(ax)]

        pos=position*1E9
        # For the sake of completeness, finally we use the asynchronous (non-blocking) write function to
        # set the position to -0.1 mm respectively -100 degree.
    #    position = -100000000
        print("MCS2 set position of channel {} to {}".format(ax, pos), end='')
        print("pm.") if self.base_units[ax] == ctl.BaseUnit.METER else print("ndeg.")
        r_id = ctl.RequestWriteProperty_i64(self.smaract, ax, ctl.Property.POSITION, pos)
        # The function call returns immediately, without waiting for the reply from the controller.
        # ...process other tasks...

        # Wait for the result to arrive.
        ctl.WaitForWrite(self.smaract, r_id)
        return self.get_pos(ax)

        # Alternatively, the "call-and-forget" mechanism for asynchronous (non-blocking) write functions
        # may be used:
        # For property writes the result is only used to report errors. With the call-and-forget mechanism
        # the device does not generate a result for writes and the application can continue processing other
        # tasks immediately. Compared to asynchronous accesses, the application doesn’t need to keep
        # track of open requests and collect the results at some point. This mode should be used with care
        # so that written values are within the valid range.
        # The call-and-forget mechanism is activated by passing "False" to the optional pass_rID parameter of the
        # RequestWriteProperty_x functions.
    #    ctl.RequestWriteProperty_i64(d_handle, channel, ctl.Property.POSITION, position, pass_rID = False)
        # No result must be requested with the WaitForWrite function in this case.

    def ismoving(self, ax):
        if type(ax) == str:
            ax = self.channels[self.channel_names.index(ax)]
        r_id2 = ctl.RequestReadProperty(self.smaract, ax, ctl.Property.CHANNEL_STATE, 0)
        state = ctl.ReadProperty_i32(self.smaract, r_id2)
        if bool(state & ctl.ChannelState.END_STOP_REACHED):
            print("End Stop reached.")
            return False
        return bool(state & ctl.ChannelState.ACTIVELY_MOVING)
    
    
    def get_numberofchannels(self):
        return ctl.GetProperty_i32(self.smaract, 0, ctl.Property.NUMBER_OF_CHANNELS)
    
    def get_channel_state(self, axis):
        sr = ctl.GetProperty_i32(self.smaract, axis, ctl.Property.CHANNEL_STATE)
        print(f"Return code: {sr}")
        for state in ctl.ChannelState:
            res = bool(sr & state)
            print(state, res)

    def get_broadcaststop_options(self, axis):
        sr = ctl.GetProperty_i32(self.smaract, axis, ctl.Property.BROADCAST_STOP_OPTIONS)
        print(f"Return code: {sr}")
        for state in ctl.BroadcastStopOption:
            res = bool(sr & state)
            print(state, res)

    def get_channel_error(self, axis):
        sr = ctl.GetProperty_i32(self.smaract, axis, ctl.Property.CHANNEL_ERROR)
        print(f"Return code: {sr}")
        for state in ctl.ErrorCode:
            res = bool(sr & state)
            print(state, res)
    
    def limit_reached(self, axis):
        state = ctl.GetProperty_i32(self.smaract, axis, ctl.Property.CHANNEL_STATE)
        if bool(state & ctl.ChannelState.END_STOP_REACHED):
            if self.get_pos(axis)>0:
                return 2
            else:
                return 1
        else:
            return 0
def assert_lib_compatibility():
    """
    Checks that the major version numbers of the Python API and the
    loaded shared library are the same to avoid errors due to 
    incompatibilities.
    Raises a RuntimeError if the major version numbers are different.
    """
    vapi = ctl.api_version
    vlib = [int(i) for i in ctl.GetFullVersionString().split('.')]
    if vapi[0] != vlib[0]:
        raise RuntimeError("Incompatible SmarActCTL python api and library version.")

def printMenu():
    print("*******************************************************")
    print("WARNING: make sure the positioner can move freely\n \
            without damaging other equipment!")
    print("*******************************************************")
    print("Enter command and return:")
    print("[?] print this menu")
    print("[c] calibrate")
    print("[f] find reference")
    print("[+] perform movement in positive direction")
    print("[-] perform movement in negative direction")
    print("[s] stop")
    print("[p] get current position")
    print("[0] set move mode: closed loop absolute move")
    print("[1] set move mode: closed loop relative move")
    print("[2] set move mode: open loop scan absolute*")
    print("[3] set move mode: open loop scan relative*")
    print("[4] set move mode: open loop step*")
    print("[5] set control mode: standard mode*")
    print("[6] set control mode: quiet mode*")
    print("  * not available for E-Magnetic Driver channels")
    print("[q] quit")

# CALIBRATION
# The calibration sequence is used to increase the precision of the position calculation. This function
# should be called once for each channel if the mechanical setup changes.
# (e.g. a different positioner was connected to the channel, the positioner type was set to a different type)
# The calibration data will be saved to non-volatile memory, thus it is not necessary to perform the calibration sequence
# on each initialization.
# Note: the "ChannelState.IS_CALIBRATED" in the channel state can be used to determine
# if valid calibration data is stored for the specific channel.

# During the calibration sequence the positioner performs a movement of up to several mm, make sure to not start
# the calibration near a mechanical endstop in order to ensure proper operation.
# See the MCS2 Programmers Guide for more information on the calibration.
