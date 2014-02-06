# ni_rfsg.py class, to perform the communication between the Wrapper and the device
# David Christle <christle@uchicago.edu> - 2013
# F. J. Heremans <heremans@gmail.com> - 2013
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

from instrument import Instrument
import qt
import visa
import types
import logging
import numpy
import ctypes as _ctypes
import ctypes


def _type_dublet(ctypes_type):
    return (ctypes_type, _ctypes.POINTER(ctypes_type))

def _type_triplet(ctypes_type):
    return _type_dublet(ctypes_type) + (_ctypes.POINTER(ctypes_type),)


# Define some types to use later
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
isDone = ViBoolean()


# Declare Char Array for messages
errorMessage = (ViChar * 256)("0")
instrumentDriverRevision = (ViChar * 256)("0")
firmwareRevision = (ViChar * 256)("0")
selfTestMessage = (ViChar * 256)("0")

# Bring in the NI RFSG DLL using ctypes.

nfsglib = ctypes.windll.LoadLibrary("C:\\Python Scripts\\FJH Test\\niRFSG_64.dll")


class NI_RFSG(Instrument):
    '''
    This is the driver for the Agilent E8257D Signal Genarator

    Usage:
    Initialize with
    <name> = instruments.create('<name>', 'NI_RFSG', resource_name='<string>', reset=<bool>')
    '''

    def __init__(self, name, resource_name, reset=False):
        '''
        Initializes the NI_RFSG, and communicates with the wrapper.

        Input:
          name (string)    : name of the instrument
          resource_name (string) : resource name from NI MAX (IQ5611 is typical)
          reset (bool)     : resets to default values, default=False
        '''

        # initialize the NI-RFSG port
        nfsglib.niRFSG_init(resource_name,VI_True,VI_True,ctypes.byref(viSession))

        self._viSession = viSession
        logging.info(__name__ + ' : Initializing instrument NI_RFSG')
        Instrument.__init__(self, name, tags=['physical'])


        self.add_parameter('power',
            flags=Instrument.FLAG_SET, units='dBm', minval=-135, maxval=8, type=types.FloatType, tags=['sweep'])
        self.add_parameter('frequency',
            flags=Instrument.FLAG_SET, units='Hz', minval=1e5, maxval=6e9, type=types.FloatType, format='%.04e', tags=['sweep'])
        self.add_parameter('status',
            flags=Instrument.FLAG_GETSET, type=types.StringType)

        # Add other functions
        self.add_function('reset')
        self.add_function ('get_all')
        self.add_function('on')
        self.add_function('off')

        # Define default values of frequency and power. These are internal
        # properties that are kept track of in self._freq and self._power.
        # The reason for this is that the ConfigureRF routine requires both
        # power and frequency to be input, but in QtLab, we want to just change
        # each of these individually. Thus, we need to keep track of the
        # last frequency/power we set it to, and pass this to ConfigureRF when
        # we are trying to change the power/frequency, respectively.

        self._freq = 1e9
        self._power = -90


        if (reset):
            self._viSession = viSession
            self.reset_device()
        else:
            self.get_all()



    def reset(self):
        '''
        Soft reset of the RF to configuration state

        Input:
            None

        Output:
            None
        '''
        retVal = nfsglib.niRFSG_reset (self._viSession)
        return retVal

    def reset_device(self):
        '''
        Resets the instrument to default values

        Input:
            None

        Output:
            None
        '''
        retVal = nfsglib.niRFSG_ResetDevice(self._viSession)
        return retVal

    def close(self):
        retVal = nfsglib.niRFSG_close (self._viSession)
        return retVal

    def get_all(self):
        '''
        Reads all implemented parameters from the instrument,
        and updates the wrapper.

        Input:
            None

        Output:
            None
        '''
        logging.info(__name__ + ' : get all')
        self.get_status()
        return 0

    def do_set_frequency(self, freq):
        '''
        Set the frequency of the instrument

        Input:
            freq (float) : Frequency in Hz

        Output:
            None
        '''
        logging.debug(__name__ + ' : set frequency to %f' % freq)

        power = self._power
        virFreq = ViReal64(freq)
        virPower = ViReal64(power)
        retVal = nfsglib.niRFSG_ConfigureRF(self._viSession,virFreq,virPower)
        if retVal == 0:
            self._freq = freq
        else:
            logging.error(__name__ + ' returned value of %s in error' % retVal)
        return retVal

    def do_set_power(self, power):
        '''
        Set the power of the signal

        Input:
            power (float) : power in dBm

        Output:
            None
        '''
        logging.debug(__name__ + ' : set power to %f' % power)

        freq = self._freq
        virFreq = ViReal64(freq)
        virPower = ViReal64(power)
        retVal = nfsglib.niRFSG_ConfigureRF(self._viSession,virFreq,virPower)
        if retVal == 0:
            self._power = power
        return retVal

    def do_set_status(self, status):
        '''
        Set the output status of the instrument

        Input:
            status (string) : 'on' or 'off'

        Output:
            None
        '''

        logging.debug(__name__ + ' : set status to %s' % status)

        if (status == 'on'):
            retVal = nfsglib.niRFSG_Initiate(self._viSession)
            return retVal
        elif (status == 'off'):
            disVal = nfsglib.niRFSG_Disable(self._viSession)
            abVal = nfsglib.niRFSG_Abort(self._viSession)
            return ((disVal == 0) and (abVal == 0))
        else:
            logging.error('Set status error: %s' % status)
        return

    def do_get_status(self):
        '''
        Reads the output status from the instrument

        Input:
            None

        Output:
            status (string) : 'On' or 'Off'
        '''
        logging.debug(__name__ + ' : get status')

        retVal = nfsglib.niRFSG_CheckGenerationStatus(self._viSession, ctypes.byref(isDone))
##        print 'isdone is: %s' % isDone.value
        if (isDone.value == 0):
            return 'on'
        elif (isDone.value == 1):
            return 'off'
        else:
            logging.error('Check Generation Status Error: %s' % retVal)
        return -1

    # shortcuts
    def off(self):
        '''
        Set status to 'off'

        Input:
            None

        Output:
            None
        '''
        self.set_status('off')

    def on(self):
        '''
        Set status to 'on'

        Input:
            None

        Output:
            None
        '''
        self.set_status('on')


