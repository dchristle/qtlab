# sacher_epos.py, python wrapper for sacher epos motor
# David Christle <christle@uchicago.edu>, August 2014
#


import ctypes
import numpy as np
import logging
from instrument import Instrument
from ctypes.wintypes import DWORD
from ctypes.wintypes import WORD
import ctypes.wintypes
import time

#eposlib = ctypes.windll.eposcmd
eposlib = ctypes.windll.LoadLibrary('C:\\measuring\\measurement\\lib\\dll_support\\EPOS\\EposCmd2.dll')
DeviceName = 'EPOS'
ProtocolStackName = 'MAXON_RS232'
InterfaceName = 'RS232'


HISTCHAN = 65536
TTREADMAX = 131072
RANGES = 8

MODE_HIST = 0
MODE_T2 = 2
MODE_T3 = 3

FLAG_OVERFLOW = 0x0040
FLAG_FIFOFULL = 0x0003

# in mV
ZCMIN = 0
ZCMAX = 20
DISCRMIN = 0
DISCRMAX = 800

# in ps
OFFSETMIN = 0
OFFSETMAX = 1000000000

# in ms
ACQTMIN = 1
ACQTMAX = 10*60*60*1000

# in mV
PHR800LVMIN = -1600
PHR800LVMAX = 2400



class Sacher_EPOS(Instrument):

    def __init__(self, name, port_name, reset=False):
        Instrument.__init__(self, name, tags=['physical'])
        self._port_name = str(port_name)
        self._is_open = False
        self._HPM = True

        #try:
        self.open()
        self.initialize()
        #except:
        #    logging.error('Error loading Sacher EPOS motor. In use?')

    def __del__(self):
        # execute disconnect
        return
    def get_bit(self, byteval,idx):
        return ((byteval&(1<< idx ))!=0)
    def _u32todouble(self, uinput):
        # this function implements the really weird/non-standard U32 to
        # floating point conversion in the sacher VIs

        # get sign of number
        sign = self.get_bit(uinput,31)
        if sign == False:
            mantissa_sign = 1
        elif sign == True:
            mantissa_sign = -1
        exp_mask =  0b111111
        #print 'uin u is %d' % uinput
        #print 'type uin %s' % type(uinput)
        #print 'binary input is %s' % bin(long(uinput))
        # get sign of exponent
        if self.get_bit(uinput,7) == False:
            exp_sign = 1
        elif self.get_bit(uinput,7) == True:
            exp_sign = -1

        #print 'exp extract %s' % bin(int(uinput & exp_mask))
        #print 'exp conv %s' % (exp_sign*int(uinput & exp_mask))
        #print 'sign of exponent %s' % self.get_bit(uinput,7)
        #print 'binary constant is %s' % bin(int(0b10000000000000000000000000000000))
        mantissa_mask = 0b01111111111111111111111100000000
        #print 'mantissa extract is %s' % bin((uinput & mantissa_mask) >> 8)
        mantissa = 1.0/1000000.0*float(mantissa_sign)*float((uinput & mantissa_mask) >> 8)
        #print 'mantissa is %.12f' % mantissa
        output = mantissa*2.0**(float(exp_sign)*float(int(uinput & exp_mask)))
        #print 'output is %s' % output

        return output

    def open(self):
        print 'yes'

        eposlib.VCS_OpenDevice.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.POINTER(DWORD)]
        eposlib.VCS_OpenDevice.restype = ctypes.wintypes.HANDLE
        buf = ctypes.pointer(DWORD(0))
        ret = ctypes.wintypes.HANDLE()

        print 'types are all %s %s %s %s %s' % (type(DeviceName), type(ProtocolStackName), type(InterfaceName), type(self._port_name), type(buf))
        ret = eposlib.VCS_OpenDevice(DeviceName, ProtocolStackName, InterfaceName, self._port_name, buf)
        self._keyhandle = ret
        print 'keyhandle is %s' % self._keyhandle
        print 'open device ret %s' % buf
        print 'printing'
        print buf.contents.value
        print 'done printer'
        if int(buf.contents.value) >= 0:
            self._is_open = True
            self._keyhandle = ret
        return
    def get_offset(self):
        nodeID = ctypes.wintypes.WORD(0)
        buf = ctypes.wintypes.DWORD(0)
        eposlib.VCS_GetObject.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.WORD, ctypes.wintypes.WORD, ctypes.c_uint8, ctypes.c_void_p, ctypes.wintypes.DWORD, ctypes.POINTER(ctypes.wintypes.DWORD), ctypes.POINTER(ctypes.wintypes.DWORD)]
        eposlib.VCS_GetObject.restype = ctypes.wintypes.BOOL
        print 'setting objs'
        # These are hardcoded values I got from the LabVIEW program -- I don't think
        # any documentation exists on particular object indices
        StoredPositionObject = ctypes.wintypes.WORD(8321)
        StoredPositionObjectSubindex = ctypes.c_uint8(0)
        StoredPositionNbBytesToRead = ctypes.wintypes.DWORD(4)
        ObjectData = ctypes.c_void_p()
        ObjectDataArray = (ctypes.c_uint32*1)()
        ObjectData = ctypes.cast(ObjectDataArray, ctypes.POINTER(ctypes.c_uint32))
        StoredPositionNbBytesRead = ctypes.pointer(ctypes.wintypes.DWORD(0))
        ret = eposlib.VCS_GetObject(self._keyhandle, nodeID, StoredPositionObject, StoredPositionObjectSubindex, ObjectData, StoredPositionNbBytesToRead, StoredPositionNbBytesRead, ctypes.byref(buf))

        # Cast the object data to uint32
        CastedObjectData = ctypes.cast(ObjectData, ctypes.POINTER(ctypes.c_uint32))
        if ret == 0:
            logging.error(__name__ + ' Could not read stored position from Sacher EPOS motor')
        print 'data is %s' % (CastedObjectData[0])
        return CastedObjectData[0]
    def set_new_offset(self, new_offset):
        nodeID = ctypes.wintypes.WORD(0)
        buf = ctypes.wintypes.DWORD(0)
        eposlib.VCS_SetObject.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.WORD, ctypes.wintypes.WORD, ctypes.c_uint8, ctypes.POINTER(ctypes.wintypes.DWORD), ctypes.wintypes.DWORD, ctypes.POINTER(ctypes.wintypes.DWORD), ctypes.POINTER(ctypes.wintypes.DWORD)]
        eposlib.VCS_SetObject.restype = ctypes.wintypes.BOOL
        print 'setting new offset'

        StoredPositionObject = ctypes.wintypes.WORD(8321)
        StoredPositionObjectSubindex = ctypes.c_uint8(0)
        StoredPositionNbBytesToWrite = ctypes.wintypes.DWORD(4)


        ObjectDataArray = (ctypes.c_uint32*1)(new_offset)
        ObjectData = ctypes.cast(ObjectDataArray, ctypes.POINTER(ctypes.c_uint32))
        StoredPositionNbBytesWritten = ctypes.pointer(ctypes.wintypes.DWORD(0))
        ret = eposlib.VCS_SetObject(self._keyhandle, nodeID, StoredPositionObject, StoredPositionObjectSubindex, ObjectData, StoredPositionNbBytesToWrite, StoredPositionNbBytesWritten, ctypes.byref(buf))


        if ret == 0:
            logging.error(__name__ + ' Could not write stored position from Sacher EPOS motor')
        return

    def get_motor_position(self):
        nodeID = ctypes.wintypes.WORD(0)
        buf = ctypes.wintypes.DWORD(0)
        pPosition = ctypes.pointer(ctypes.c_long())
        eposlib.VCS_GetPositionIs.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.WORD, ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.wintypes.DWORD)]
        eposlib.VCS_GetPositionIs.restype = ctypes.wintypes.BOOL
        ret = eposlib.VCS_GetPositionIs(self._keyhandle, nodeID, pPosition, ctypes.byref(buf))
        print 'get motor position ret %s' % ret
        print 'get motor position buf %s' % buf.value
        print 'get motor position value %s' % pPosition.contents.value
        return pPosition.contents.value

    def set_target_position(self, target, absolute, immediately):
        nodeID = ctypes.wintypes.WORD(0)
        buf = ctypes.wintypes.DWORD(0)
        # First, set enabled state
        ret = eposlib.VCS_SetEnableState(self._keyhandle,nodeID,ctypes.byref(buf))
        print 'Enable state ret %s buf %s' % (ret, buf.value)
        pTarget = ctypes.c_long(target)
        pAbsolute = ctypes.wintypes.BOOL(absolute)
        pImmediately = ctypes.wintypes.BOOL(immediately)
        eposlib.VCS_MoveToPosition.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.WORD, ctypes.c_long, ctypes.wintypes.BOOL, ctypes.wintypes.BOOL, ctypes.POINTER(ctypes.wintypes.DWORD)]
        eposlib.VCS_MoveToPosition.restype = ctypes.wintypes.BOOL
        print 'About to set motor position'
        ret = eposlib.VCS_MoveToPosition(self._keyhandle, nodeID, pTarget, pAbsolute, pImmediately, ctypes.byref(buf))
        print 'set motor position ret %s' % ret
        print 'set motor position buf %s' % buf.value
        # Now get movement state
        nchecks = 0
        while nchecks < 15:
            pMovementState = ctypes.pointer(ctypes.wintypes.BOOL())
            eposlib.VCS_GetMovementState.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.WORD, ctypes.POINTER(ctypes.wintypes.BOOL), ctypes.POINTER(ctypes.wintypes.DWORD)]
            eposlib.VCS_GetMovementState.restype = ctypes.wintypes.BOOL
            print 'Getting movement state'
            ret = eposlib.VCS_GetMovementState(self._keyhandle, nodeID, pMovementState, ctypes.byref(buf))
            print 'set motor position ret %s' % ret
            print 'set motor position buf %s' % buf.value
            print 'Movement state is %s' % pMovementState.contents.value
            if pMovementState.contents.value == 1:
                break
            nchecks = nchecks + 1
            time.sleep(5.0)
        # Now set disabled state
        ret = eposlib.VCS_SetDisableState(self._keyhandle,nodeID,ctypes.byref(buf))
        print 'Disable state ret %s buf %s' % (ret, buf.value)
        return ret
    def get_wavelength(self):
        nodeID = ctypes.wintypes.WORD(0)
        buf = ctypes.wintypes.DWORD(0)
        eposlib.VCS_GetObject.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.WORD, ctypes.wintypes.WORD, ctypes.c_uint8, ctypes.c_void_p, ctypes.wintypes.DWORD, ctypes.POINTER(ctypes.wintypes.DWORD), ctypes.POINTER(ctypes.wintypes.DWORD)]
        eposlib.VCS_GetObject.restype = ctypes.wintypes.BOOL
        print 'setting objs'
        # These are hardcoded values I got from the LabVIEW program -- I don't think
        # any documentation exists on particular object indices
        StoredPositionObject = ctypes.wintypes.WORD(8321)
        StoredPositionObjectSubindex = ctypes.c_uint8(0)
        StoredPositionNbBytesToRead = ctypes.wintypes.DWORD(4)
        ObjectData = ctypes.c_void_p()
        ObjectDataArray = (ctypes.c_uint32*1)()
        ObjectData = ctypes.cast(ObjectDataArray, ctypes.POINTER(ctypes.c_uint32))
        StoredPositionNbBytesRead = ctypes.pointer(ctypes.wintypes.DWORD(0))
        ret = eposlib.VCS_GetObject(self._keyhandle, nodeID, StoredPositionObject, StoredPositionObjectSubindex, ObjectData, StoredPositionNbBytesToRead, StoredPositionNbBytesRead, ctypes.byref(buf))

        # Cast the object data to uint32
        CastedObjectData = ctypes.cast(ObjectData, ctypes.POINTER(ctypes.c_uint32))
        if ret == 0:
            logging.error(__name__ + ' Could not read stored position from Sacher EPOS motor')
        print 'data is %s' % (CastedObjectData[0])
        self._offset = CastedObjectData[0]
        self._currentwl = self._doubleA*(self._offset)**2.0 + self._doubleB*self._offset + self._doubleC
        return self._currentwl

    def set_wavelength(self, wavelength):
        print 'Coefficients are %s %s %s' % (self._doubleA, self._doubleB, self._doubleC)
        nodeID = ctypes.wintypes.WORD(0)
        buf = ctypes.wintypes.DWORD(0)
        # Step 1: Get the actual motor position
        print 'Getting motor position'
        current_motor_pos = self.get_motor_position()
        # Step 2: Get the motor offset
        self._offset = self.get_offset()
        print 'Motor offset is %s' % self._offset
        # Step 3: Convert the desired wavelength into a position
        # Check sign of position-to-wavelength
        pos0 = self._doubleA*(0.0)**2.0 + self._doubleB*0.0 + self._doubleC
        pos5000 = self._doubleA*(5000.0)**2.0 + self._doubleB*5000.0 + self._doubleC

        #    logging.error(__name__ + ' Sacher wavelength calibration polynomials indicated a wrong wavelength direction')
        # If that's OK, use the quadratic formula to calculate the roots
        b2a = -1.0*self._doubleB/(2.0*self._doubleA)
        sqrtarg = self._doubleB**2.0/(4.0*self._doubleA**2.0) - (self._doubleC - wavelength)/self._doubleA
        if sqrtarg < 0.0:
            logging.error(__name__ + ' Negative value under square root sign -- something is wrong')
        if pos0 > pos5000:
            # Take the + square root solution
            x = b2a + np.sqrt(sqrtarg)
        elif pos0 < pos5000:
            x = b2a - np.sqrt(sqrtarg)
        #print 'Position is %s' % x
        wavelength_to_pos = int(round(x))
        # Step 4: Calculate difference between the output position and the stored offset
        print 'Step 4...'
        diff_wavelength_offset = wavelength_to_pos - int(self._offset)
        print 'Diff wavelength offset %s' % diff_wavelength_offset
        # Step 5: If HPM is activated and the wavelength position is lower, overshoot
        # the movement by 10,000 steps
        print 'Step 5...'
        if self._HPM and diff_wavelength_offset < 0:
            print 'Overshooting by 10000'
            self.set_target_position(diff_wavelength_offset - 10000, False, True)
        # Step 6: Set the real target position
        print 'Step 6... diff wavelength'
        self.set_target_position(diff_wavelength_offset, False, True)
        # Step 7: Get the actual motor position
        new_motor_pos = self.get_motor_position()
        print 'New motor position is %s' % new_motor_pos
        print 'new offset is %s' % (new_motor_pos-current_motor_pos+self._offset)
        self.set_new_offset(new_motor_pos-current_motor_pos+self._offset)



        return

    def close(self):
        self._is_open = False
        #ret = phlib.PH_CloseDevice(self._devid)
        return True

    def is_open(self):
        return self._is_open

    def initialize(self):

        nodeID = ctypes.wintypes.WORD(0)
        buf = ctypes.wintypes.DWORD(0)
        BaudRate = DWORD(38400)
        Timeout = DWORD(100)
        ret = eposlib.VCS_SetProtocolStackSettings(self._keyhandle,BaudRate,Timeout,ctypes.byref(buf))
        print 'set protocol buf %s ret %s' % (buf, ret)
        if ret == 0:
            errbuf = ctypes.create_string_buffer(64)
            eposlib.VCS_GetErrorInfo(buf, errbuf, WORD(64))
            raise ValueError(errbuf.value)


        buf = ctypes.wintypes.DWORD(0)
        ret = eposlib.VCS_ClearFault(self._keyhandle,nodeID,ctypes.byref(buf))
        print 'clear fault buf %s, ret %s' % (buf, ret)
        if ret == 0:
            errbuf = ctypes.create_string_buffer(64)
            eposlib.VCS_GetErrorInfo(buf, errbuf, WORD(64))
            raise ValueError(errbuf.value)
        buf = ctypes.wintypes.DWORD(0)
        plsenabled = ctypes.wintypes.DWORD(0)
        ret = eposlib.VCS_GetEnableState(self._keyhandle,nodeID,ctypes.byref(plsenabled),ctypes.byref(buf))
        print 'get enable state buf %s ret %s and en %s' % (buf, ret, plsenabled)
        if ret == 0:
            errbuf = ctypes.create_string_buffer(64)
            eposlib.VCS_GetErrorInfo(buf, errbuf, WORD(64))
            raise ValueError(errbuf.value)

        if int(plsenabled.value) != 0:
            logging.warning(__name__ + ' EPOS motor enabled, disabling before proceeding.')
            ret = eposlib.VCS_SetDisableState(self._keyhandle,nodeID,ctypes.byref(buf))
            if int(ret) != 0:
                logging.warning(__name__ + ' EPOS motor successfully disabled, proceeding')
            else:
                logging.error(__name__ + ' EPOS motor was not successfully disabled!')
        buf = ctypes.wintypes.DWORD(0)
        Counts = WORD(512) # incremental encoder counts in pulses per turn
        PositionSensorType = WORD(4)
        ret = eposlib.VCS_SetEncoderParameter(self._keyhandle,nodeID,Counts,PositionSensorType,ctypes.byref(buf))
        print 'encoder parameter set buf %s, ret %s' % (buf, ret)
        print 'type is %s' % type(ret)
##        if ret == int(0):
##            print 'errr'
##            errbuf = ctypes.create_string_buffer(64)
##            print 'sending'
##            eposlib.VCS_GetErrorInfo.restype = ctypes.wintypes.BOOL
##            print 'boolerrorinfo'
##            eposlib.VCS_GetErrorInfo.argtypes = [ctypes.wintypes.DWORD, ctypes.c_char_p, ctypes.wintypes.WORD]
##            print 'arg'
##
##            ret = eposlib.VCS_GetErrorInfo(buf, ctypes.byref(errbuf), WORD(64))
##            print 'err'
##            raise ValueError(errbuf.value)
        # For some reason, it appears normal in the LabVIEW code that this
        # function actually returns an error, i.e. the return value is zero
        # and the buffer has a non-zero error code in it; the LabVIEW code
        # doesn't check it.
        # Also, it appears that in the 2005 version of this DLL, the function
        # VCS_GetErrorInfo doesn't exist!
        print 'getting operation'
        # Get operation mode, check if it's 1
        buf = ctypes.wintypes.DWORD(0)
        pMode = ctypes.pointer(ctypes.c_int8())
        eposlib.VCS_GetOperationMode.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.WORD, ctypes.POINTER(ctypes.c_int8), ctypes.POINTER(ctypes.wintypes.DWORD)]
        eposlib.VCS_GetOperationMode.restype = ctypes.wintypes.BOOL
        ret = eposlib.VCS_GetOperationMode(self._keyhandle, nodeID, pMode, ctypes.byref(buf))
        # if mode is not 1, make it 1
        if pMode.contents.value != 1:
            eposlib.VCS_SetOperationMode.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.WORD, ctypes.c_int8, ctypes.POINTER(ctypes.wintypes.DWORD)]
            eposlib.VCS_SetOperationMode.restype = ctypes.wintypes.BOOL
            pMode_setting = ctypes.c_int8(1)
            ret = eposlib.VCS_SetOperationMode(self._keyhandle, nodeID, pMode_setting, ctypes.byref(buf))
        eposlib.VCS_GetPositionProfile.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.WORD, ctypes.POINTER(ctypes.wintypes.DWORD), ctypes.POINTER(ctypes.wintypes.DWORD), ctypes.POINTER(ctypes.wintypes.DWORD), ctypes.POINTER(ctypes.wintypes.DWORD)]
        eposlib.VCS_GetPositionProfile.restype = ctypes.wintypes.BOOL
        pProfileVelocity = ctypes.pointer(ctypes.wintypes.DWORD())
        pProfileAcceleration = ctypes.pointer(ctypes.wintypes.DWORD())
        pProfileDeceleration = ctypes.pointer(ctypes.wintypes.DWORD())

        ret = eposlib.VCS_GetPositionProfile(self._keyhandle, nodeID, pProfileVelocity, pProfileAcceleration, pProfileDeceleration,ctypes.byref(buf))

        if (long(pProfileVelocity.contents.value) > long(11400) or long(pProfileAcceleration.contents.value) > long(60000) or long(pProfileDeceleration.contents.value) > long(60000)):
            eposlib.VCS_GetPositionProfile.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.WORD, ctypes.wintypes.DWORD, ctypes.wintypes.DWORD, ctypes.wintypes.DWORD, ctypes.POINTER(ctypes.wintypes.DWORD)]
            eposlib.VCS_GetPositionProfile.restype = ctypes.wintypes.BOOL
            pProfileVelocity = ctypes.wintypes.DWORD(429)
            pProfileAcceleration = ctypes.wintypes.DWORD(429)
            pProfileDeceleration = ctypes.wintypes.DWORD(429)
            logging.warning(__name__ + ' GetPositionProfile out of bounds, resetting...')
            ret = eposlib.VCS_SetPositionProfile(self._keyhandle, nodeID, pProfileVelocity, pProfileAcceleration, pProfileDeceleration,ctypes.byref(buf))
        print 'setting args'
        # Now get the motor position (stored position offset)
        # from the device's "homposition" object
        eposlib.VCS_GetObject.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.WORD, ctypes.wintypes.WORD, ctypes.c_uint8, ctypes.c_void_p, ctypes.wintypes.DWORD, ctypes.POINTER(ctypes.wintypes.DWORD), ctypes.POINTER(ctypes.wintypes.DWORD)]
        eposlib.VCS_GetObject.restype = ctypes.wintypes.BOOL
        print 'setting objs'
        # These are hardcoded values I got from the LabVIEW program -- I don't think
        # any documentation exists on particular object indices
        StoredPositionObject = ctypes.wintypes.WORD(8321)
        StoredPositionObjectSubindex = ctypes.c_uint8(0)
        StoredPositionNbBytesToRead = ctypes.wintypes.DWORD(4)
        ObjectData = ctypes.c_void_p()
        ObjectDataArray = (ctypes.c_uint32*1)()
        ObjectData = ctypes.cast(ObjectDataArray, ctypes.POINTER(ctypes.c_uint32))
        StoredPositionNbBytesRead = ctypes.pointer(ctypes.wintypes.DWORD(0))
        ret = eposlib.VCS_GetObject(self._keyhandle, nodeID, StoredPositionObject, StoredPositionObjectSubindex, ObjectData, StoredPositionNbBytesToRead, StoredPositionNbBytesRead, ctypes.byref(buf))

        # Cast the object data to uint32
        CastedObjectData = ctypes.cast(ObjectData, ctypes.POINTER(ctypes.c_uint32))
        if ret == 0:
            logging.error(__name__ + ' Could not read stored position from Sacher EPOS motor')
        print 'data is %s' % (CastedObjectData[0])
        self._offset = CastedObjectData[0]

        # Now read the stored 'calculation parameters'
        eposlib.VCS_GetObject.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.WORD, ctypes.wintypes.WORD, ctypes.c_uint8, ctypes.c_void_p, ctypes.wintypes.DWORD, ctypes.POINTER(ctypes.wintypes.DWORD), ctypes.POINTER(ctypes.wintypes.DWORD)]
        eposlib.VCS_GetObject.restype = ctypes.wintypes.BOOL

        # More hardcoded values
        StoredPositionObject = ctypes.wintypes.WORD(8204)
        StoredPositionObjectSubindex = ctypes.c_uint8(1)
        StoredPositionNbBytesToRead = ctypes.wintypes.DWORD(4)
        ObjectData = ctypes.c_void_p()
        ObjectDataArray = (ctypes.c_uint32*1)()
        ObjectData = ctypes.cast(ObjectDataArray, ctypes.POINTER(ctypes.c_uint32))
        StoredPositionNbBytesRead = ctypes.pointer(ctypes.wintypes.DWORD(0))
        ret = eposlib.VCS_GetObject(self._keyhandle, nodeID, StoredPositionObject, StoredPositionObjectSubindex, ObjectData, StoredPositionNbBytesToRead, StoredPositionNbBytesRead, ctypes.byref(buf))
        # Cast the object data to uint32
        CastedObjectData = ctypes.cast(ObjectData, ctypes.POINTER(ctypes.c_uint32))

        self._coefA = CastedObjectData[0]
        eposlib.VCS_GetObject.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.WORD, ctypes.wintypes.WORD, ctypes.c_uint8, ctypes.c_void_p, ctypes.wintypes.DWORD, ctypes.POINTER(ctypes.wintypes.DWORD), ctypes.POINTER(ctypes.wintypes.DWORD)]
        eposlib.VCS_GetObject.restype = ctypes.wintypes.BOOL

        # Get coefficient B
        StoredPositionObject = ctypes.wintypes.WORD(8204)
        StoredPositionObjectSubindex = ctypes.c_uint8(2)
        StoredPositionNbBytesToRead = ctypes.wintypes.DWORD(4)
        ObjectData = ctypes.c_void_p()
        ObjectDataArray = (ctypes.c_uint32*1)()
        ObjectData = ctypes.cast(ObjectDataArray, ctypes.POINTER(ctypes.c_uint32))
        StoredPositionNbBytesRead = ctypes.pointer(ctypes.wintypes.DWORD(0))
        ret = eposlib.VCS_GetObject(self._keyhandle, nodeID, StoredPositionObject, StoredPositionObjectSubindex, ObjectData, StoredPositionNbBytesToRead, StoredPositionNbBytesRead, ctypes.byref(buf))
        # Cast the object data to uint32
        CastedObjectData = ctypes.cast(ObjectData, ctypes.POINTER(ctypes.c_uint32))

        self._coefB = CastedObjectData[0]
        eposlib.VCS_GetObject.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.WORD, ctypes.wintypes.WORD, ctypes.c_uint8, ctypes.c_void_p, ctypes.wintypes.DWORD, ctypes.POINTER(ctypes.wintypes.DWORD), ctypes.POINTER(ctypes.wintypes.DWORD)]
        eposlib.VCS_GetObject.restype = ctypes.wintypes.BOOL

        # These are hardcoded values I got from the LabVIEW program -- I don't think
        # any documentation exists on particular object indices
        StoredPositionObject = ctypes.wintypes.WORD(8204)
        StoredPositionObjectSubindex = ctypes.c_uint8(3)
        StoredPositionNbBytesToRead = ctypes.wintypes.DWORD(4)
        ObjectData = ctypes.c_void_p()
        ObjectDataArray = (ctypes.c_uint32*1)()
        ObjectData = ctypes.cast(ObjectDataArray, ctypes.POINTER(ctypes.c_uint32))
        StoredPositionNbBytesRead = ctypes.pointer(ctypes.wintypes.DWORD(0))
        ret = eposlib.VCS_GetObject(self._keyhandle, nodeID, StoredPositionObject, StoredPositionObjectSubindex, ObjectData, StoredPositionNbBytesToRead, StoredPositionNbBytesRead, ctypes.byref(buf))
        # Cast the object data to uint32
        CastedObjectData = ctypes.cast(ObjectData, ctypes.POINTER(ctypes.c_uint32))

        self._coefC = CastedObjectData[0]

        # Get coefficient D
        eposlib.VCS_GetObject.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.WORD, ctypes.wintypes.WORD, ctypes.c_uint8, ctypes.c_void_p, ctypes.wintypes.DWORD, ctypes.POINTER(ctypes.wintypes.DWORD), ctypes.POINTER(ctypes.wintypes.DWORD)]
        eposlib.VCS_GetObject.restype = ctypes.wintypes.BOOL

        # These are hardcoded values I got from the LabVIEW program -- I don't think
        # any documentation exists on particular object indices
        StoredPositionObject = ctypes.wintypes.WORD(8204)
        StoredPositionObjectSubindex = ctypes.c_uint8(4)
        StoredPositionNbBytesToRead = ctypes.wintypes.DWORD(4)
        ObjectData = ctypes.c_void_p()
        ObjectDataArray = (ctypes.c_uint32*1)()
        ObjectData = ctypes.cast(ObjectDataArray, ctypes.POINTER(ctypes.c_uint32))
        StoredPositionNbBytesRead = ctypes.pointer(ctypes.wintypes.DWORD(0))
        ret = eposlib.VCS_GetObject(self._keyhandle, nodeID, StoredPositionObject, StoredPositionObjectSubindex, ObjectData, StoredPositionNbBytesToRead, StoredPositionNbBytesRead, ctypes.byref(buf))
        # Cast the object data to uint32
        CastedObjectData = ctypes.cast(ObjectData, ctypes.POINTER(ctypes.c_uint32))

        self._coefD = CastedObjectData[0]
        #print 'coefficients are %s %s %s %s' % (self._coefA, self._coefB, self._coefC, self._coefD)
        self._doubleA = self._u32todouble(self._coefA)
        self._doubleB = self._u32todouble(self._coefB)
        self._doubleC = self._u32todouble(self._coefC)
        firstHalf = np.int16(self._coefD >> 16)
        secondHalf = np.int16(self._coefD & 0xffff)
        # Set the minimum and maximum wavelengths for the motor
        self._minwl = float(firstHalf)/10.0
        self._maxwl = float(secondHalf)/10.0
        # print 'first %s second %s' % (firstHalf, secondHalf)
        # This returns '10871' and '11859' for the Sacher, which are the correct
        # wavelength ranges in Angstroms
        print 'Now calculate the current wavelength position'
        self._currentwl = self._doubleA*(self._offset)**2.0 + self._doubleB*self._offset + self._doubleC
        print 'Current wl %f' % self._currentwl
        return True
