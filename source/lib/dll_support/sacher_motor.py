# sacher_epos.py, python wrapper for sacher epos motor
# David Christle <christle@uchicago.edu>, 2014
#


import ctypes
import numpy as np
import logging
from ctypes.wintypes import DWORD
eposlib = ctypes.windll.eposcmd

DeviceName = 'EPOS'
ProtocolStackName = 'MAXON_RS232'
InterfaceName = 'RS232'
BaudRate = DWORD(38400)
Timeout = DWORD(100)

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

def get_version():
    buf = ctypes.create_string_buffer(16)
    phlib.PH_GetLibraryVersion(buf)
    return buf.value

def get_error_string(errcode):
    buf = ctypes.create_string_buffer(64)
    phlib.PH_GetErrorString(buf, errcode)
    return buf.value



class Sacher_EPOS():

    def __init__(self, port_name):
        self._port_name = port_name
        self._is_open = False

        try:
            self.open()
            self.initialize(mode)
        except:
            logging.error('Error loading Sacher EPOS motor. In use?')

    def __del__(self):
        self.close()

    def open(self):
        buf = ctypes.wintypes.DWORD(0)
        ret = eposlib.VCS_OpenDevice(DeviceName,ProtocolStackName,InterfaceName,str(self._port_name),buf)
        self._keyhandle = ret
        print 'open device ret %s' % buf
        print buf
        if buf >= 0:
            self._is_open = True
            self._keyhandle = ret
        return

    def close(self):
        self._is_open = False
        ret = phlib.PH_CloseDevice(self._devid)
        return ph_check(ret)

    def is_open(self):
        return self._is_open

    def initialize(self, mode):
        '''
        Initialize picoharp.
        Modes:
            0: histogramming
            2: T2
            3: T3
        '''
        buf = ctypes.wintypes.DWORD(0)
        ret = eposlib.VCS_SetProtocolStackSettings(self._keyhandle,BaudRate,Timeout,str(self._port_name),buf)
        print 'set protocol ret %s' % buf
        buf = ctypes.wintypes.DWORD(0)
        ret = eposlib.VCS_ClearFault(DeviceName,ProtocolStackName,InterfaceName,str(self._port_name),buf)
        print 'clear fault ret %s' % buf
        return ph_check(ret)

    def get_hardware_version(self):
        model = ctypes.create_string_buffer(32)
        version = ctypes.create_string_buffer(16)
        ret = phlib.PH_GetHardwareVersion(model, version)
        ph_check(ret)
        return (model.value, version.value)