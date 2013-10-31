# Keithley_2700.py driver for Keithley 2700 DMM
#
# Update October 2013:
# F.J. Heremans <jhereman@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

import ctypes
import numpy
import logging


# Declare variables
#ResourceName = "RFSG5622"
pxilib = ctypes.windll.LoadLibrary("C:\\Python Scripts\\FJH Test\\niRFSG_64.dll")

# Remark: The pointer and probably also the array variants are of no
# significance in Python because there is no native call-by-reference.
# However, as long as I'm not fully sure about this, they won't hurt.
def _type_dublet(ctypes_type):
    return (ctypes_type, _ctypes.POINTER(ctypes_type))

def _type_triplet(ctypes_type):
    return _type_dublet(ctypes_type) + (_ctypes.POINTER(ctypes_type),)

ViUInt32, ViPUInt32, ViAUInt32    = _type_triplet(_ctypes.c_ulong)
ViInt32, ViPInt32, ViAInt32       = _type_triplet(_ctypes.c_long)
ViUInt16, ViPUInt16, ViAUInt16    = _type_triplet(_ctypes.c_ushort)
ViInt16, ViPInt16, ViAInt16       = _type_triplet(_ctypes.c_short)
ViUInt8, ViPUInt8, ViAUInt8       = _type_triplet(_ctypes.c_ubyte)
ViInt8, ViPInt8, ViAInt8          = _type_triplet(_ctypes.c_byte)
ViAddr, ViPAddr, ViAAddr          = _type_triplet(_ctypes.c_void_p)
ViChar, ViPChar, ViAChar          = _type_triplet(_ctypes.c_char)
ViByte, ViPByte, ViAByte          = _type_triplet(_ctypes.c_ubyte)
ViBoolean, ViPBoolean, ViABoolean = _type_triplet(ViUInt16)
ViReal32, ViPReal32, ViAReal32    = _type_triplet(_ctypes.c_float)
ViReal64, ViPReal64, ViAReal64    = _type_triplet(_ctypes.c_double)

# Declare variables
viSession = ctypes.c_long() 
VI_True =ViBoolean(1)
VI_False = ViBoolean(0)
genStatus = ViBoolean(0)
errorCode = ViInt32()
selfTestResult = ViInt16()
maxWaitTime = ViInt32(10000) # ms


# Declare Char Array for messages
errorMessage = (ViChar * 256)("0")
instrumentDriverRevision = (ViChar * 256)("0")
firmwareRevision = (ViChar * 256)("0")
selfTestMessage = (ViChar * 256)("0")




def get_version():
    buf = pxilib.niRFSG_revision_query (viSession, instrumentDriverRevision, firmwareRevision);
    return (instrumentDriverRevision,firmwareRevision)
    

def get_error_query(viSession):
    buf = pxilib.niRFSG_error_query (viSession, ctypes.byref(errorCode),errorMessage);
    return (errorCode,errorMessage)
    
def pxi_check(val,viSession):
    if val == 0:
        return val
    else:
        raise get_error_query(viSession)    


class PXIDevice():

    def __init__(self, resourceName):
        self._viSession = viSession
        self._is_open = False
        self._resourceName = resourceName

        try:
            self.open()
        except:
            logging.error('Error loading NI-PXI. Da Fuh?')

    def __del__(self):
        self.close()

    def open(self):
        ret = pxilib.niRFSG_init(self._resourceName,VI_True,VI_True,ctypes.byref(viSession))
        self._viSession = viSession
        if ret >= 0:
            self._is_open = True
        return pxi_check(ret,self._viSession)

    def close(self):
        self._is_open = False
        ret = phlib.PH_CloseDevice(self._viSession)
        return pxi_check(ret,self._viSession)

    def is_open(self):
        return self._is_open

    #def init(self):
    #    '''
    #    Initialize PXI.
    #    '''
    #    ret = pxilib.niRFSG_init(self._resourceName,VI_True,VI_True,ctypes.byref(self._viSession))
    #    return pxi_check(ret,self._viSession)

    def get_hardware_version(self):
        ret = pxilib.niRFSG_revision_query (self._viSession, instrumentDriverRevision, firmwareRevision);
        #pxi_check(ret,self._viSession)
        return (instrumentDriverRevision.value, firmwareRevision.value)

    def self_test(self):
        ret = pxilib.niRFSG_self_test (self._viSession, ctypes.byref(selfTestResult), selfTestMessage);
        #pxi_check(ret,self._viSession)
        return (instrumentDriverRevision.value, firmwareRevision.value)

    def configure_RF(self,RF_freq,RF_power):
        virFreq = ViReal64(RF_freq)
        virPower = ViReal64(RF_power)
        ret = pxilib.niRFSG_ConfigureRF(self._viSession,virFreq,virPower)
        return pxi_check(ret,self._viSession)

    def generate_RF(self):
        ret = pxilib.niRFSG_Initiate(self._viSession)
        return pxi_check(ret,self._viSession)
        
    def check_generation_status(self):
        ret = pxilib.niRFSG_CheckGenerationStatus(self._viSession,ctypes.byref(genStatus));
        return genStatus
        
    def wait_for_settle(self):
        ret = pxilib.niRFSG_WaitUntilSettled (self._viSession, maxWaitTime);
        return pxi_check(ret,self._viSession)
        
    def abort_RF(self):
        ret = pxilib.niRFSG_Abort(self._viSession)
        return pxi_check(ret,self._viSession)
        
    def disable(self):
        ret = pxilib.niRFSG_Disable (self._viSession)
        return pxi_check(ret,self._viSession)
    
    def close_RF(self):
        ret = pxilib.niRFSG_close(self._viSession)
        return pxi_check(ret,self._viSession)
        
    def reset(self):
        ret = pxilib.niRFSG_reset (self._viSession)
        return pxi_check(ret,self._viSession)

    def reset_device(self):
        ret = pxilib.niRFSG_ResetDevice(self._viSession)
        return pxi_check(ret,self._viSession)
        
        