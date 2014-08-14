# sacher_epos.py, python wrapper for sacher epos motor
# David Christle <christle@uchicago.edu>, 2014
#


import ctypes
import numpy as np
import logging
from instrument import Instrument
from ctypes.wintypes import DWORD
from ctypes.wintypes import WORD
import ctypes.wintypes

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

        #try:
        self.open()
        self.initialize()
        #except:
        #    logging.error('Error loading Sacher EPOS motor. In use?')

    def __del__(self):
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

    def close(self):
        self._is_open = False
        #ret = phlib.PH_CloseDevice(self._devid)
        return True

    def is_open(self):
        return self._is_open

    def initialize(self):
        '''
        Initialize picoharp.
        Modes:
            0: histogramming
            2: T2
            3: T3
        '''
        print 'trying protocol stack'
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
            ret = eposlib.VCS_SetDisabledState(self._keyhandle,nodeID,ctypes.byref(buf))
            if int(ret.value) != 0:
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
        print 'about to call getpost'
        ret = eposlib.VCS_GetPositionProfile(self._keyhandle, nodeID, pProfileVelocity, pProfileAcceleration, pProfileDeceleration,ctypes.byref(buf))
        print 'getposprofile done'
        print 'operation mode buf %s' % (buf.value)
        print 'pvel is %s' % (pProfileVelocity.contents.value)
        print 'acc is %s' % (pProfileAcceleration.contents.value)
        print 'dec is %s' % (pProfileDeceleration.contents.value)
        print 'ret is %s' % (ret)
        print 'type is %s' % type(pProfileVelocity.contents.value)
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

        # These are hardcoded values I got from the LabVIEW program -- I don't think
        # any documentation exists on particular object indices
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
        print 'coefficients are %s %s %s %s' % (self._coefA, self._coefB, self._coefC, self._coefD)
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
