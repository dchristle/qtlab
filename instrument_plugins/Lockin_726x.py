# Lockin_726x.py driver for EG&G/Signal Recovery 726x Lock-in Amplifier
# F. J. Heremans <jhereman@gmail.com>
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
import visa
import types
import logging
import numpy

import qt



def bool_to_str(val):
    '''
    Function to convert boolean to 'ON' or 'OFF'
    '''
    if val == True:
        return "ON"
    else:
        return "OFF"

class Lockin_726x(Instrument):
    '''
    This is the driver for the EG&G/Signal Recovery 726x class of Lock-in Amplifiers

    Usage:
    Initialize with
    <name> = instruments.create('<name>', 'LOCKIN_7265',
        address='<GBIP address>',
        reset=<bool>)
    '''

    def __init__(self, name, address, reset=False):
        '''
        Initializes the EG&G/Signal Recovery 726x class of Lock-in Amplifiers, and communicates with the wrapper.

        Input:
            name (string)           : name of the instrument
            address (string)        : GPIB address
            reset (bool)            : resets to default values
        Output:
            None
        '''
        # Initialize wrapper functions
        logging.info('Initializing instrument Lockin_726x')
        Instrument.__init__(self, name, tags=['physical'])

        # Add some global constants
        self._address = address
        self._visa = visa.instrument(self._address)
        self._modes = ['IMODE_HB','IMODE_LN','VMODE_A','VMODE_-B','VMODE_A-B']

        # Add parameters to wrapper
        self.add_parameter('X',
            flags=Instrument.FLAG_GET,
            units='V', minval=0, maxval=10, type=types.FloatType)
        self.add_parameter('Y',
            flags=Instrument.FLAG_GET,
            units='V', minval=0, maxval=10, type=types.FloatType)
##        self.add_parameter('XY',
##            flags=Instrument.FLAG_GET,
##            units='V', minval=0, maxval=10, type=types.FloatType)
        self.add_parameter('frequency',
            flags=Instrument.FLAG_GET,
            units='Hz', minval=0, maxval=10, type=types.FloatType)
        self.add_parameter('gain',
            flags=Instrument.FLAG_SET,
            units='dB', minval=0, maxval=9, type=types.FloatType,
            format_map={
               0: '0dB',
               1: '10dB',
               2: '20dB',
               3: '30dB',
               4: '40dB',
               5: '50dB',
               6: '60dB',
               7: '70dB',
               8: '80dB',
               9: '90dB',
            })
        self.add_parameter('TC',
            flags=Instrument.FLAG_GETSET,
            units='s', minval=0, maxval=29, type=types.FloatType,
            format_map={
               0: '10e-6s',
               1: '20e-6s',
               2: '40e-6s',
               3: '80e-6s',
               4: '160e-6s',
               5: '320e-6s',
               6: '640e-6s',
               7: '5e-3s',
               8: '10e-3s',
               9: '20e-3s',
               10: '50e-3s',
               11: '100e-3s',
               12: '200e-3s',
               13: '500e-3s',
               14: '1s',
               15: '2s',
               16: '5s',
               17: '10s',
               18: '20s',
               19: '50s',
               20: '100s',
               21: '200s',
               22: '500s',
               23: '1e3s',
               24: '2e3s',
               25: '5e3s',
               26: '10e3s',
               27: '20e3s',
               28: '50e3s',
               29: '100e3s',
           })


        # Add functions to wrapper
##        self.add_function('get_XY')
        self.add_function('autophase')
        self.add_function('get_all')

        if reset:
            self.reset()
        else:
            self.get_all()
            self.set_defaults()

# --------------------------------------
#           functions
# --------------------------------------

    def reset(self):
        '''
        Resets instrument to default values

        Input:
            None

        Output:
            None
        '''
        logging.debug('Resetting instrument')
        self._visa.write('*RST')
        self.get_all()

    def set_defaults(self):
        '''
        Set to driver defaults:
        '''
        return

    def get_all(self):
        '''
        Reads all relevant parameters from instrument

        Input:
            None

        Output:
            None
        '''
        logging.info('Get all relevant data from device')
        self.get_X()
        self.get_Y()
        self.get_TC()
        self.get_frequency()

    def reset_trigger(self):
        '''
        Reset trigger status

        Input:
            None

        Output:
            None
        '''
        logging.debug('Resetting trigger')
        self._visa.write(':ABOR')

    def autophase(self):
        '''
        Run an autophase
        '''
        logging.debug('Run Autophase (Auto Quadrature Null)')
        self._visa.write('AQN')


# --------------------------------------
#           parameters
# --------------------------------------
    def do_get_X(self):
        '''
        Read X value
        '''
        ans = self._visa.ask('X.')
        return float(ans)

    def do_get_Y(self):
        '''
        Read Y value
        '''
        ans = self._visa.ask('Y.')
        return float(ans)

    def get_XY(self):
        '''
        Read X& Y values simultaneously
        '''
        ans = self._visa.ask('XY.')
        # replace usage here necessary to get rid of \x00 that is attached to
        # the string when the lockin returns 0E+00.
        XYvals = [float(x) for x in ans.replace('\x00','').split(',')]
        return XYvals

    def do_set_TC(self,TCval):
        '''
        Write Time Constant (TC) value
        '''
        self._visa.write('TC%d' % TCval)

    def do_get_TC(self):
        '''
        Read Time Constant (TC) value
        '''
        ans = self._visa.ask('TC.')
        return float(ans)

    def do_get_frequency(self):
        '''
        Read frequency value (Hz)
        '''
        ans = self._visa.ask('FRQ.')
        return float(ans)

    def do_set_gain(self,Gain):
        '''
        Set gain (dB)
        '''
        ans = self._visa.write('AUTOMATIC0')
        ans = self._visa.write('ACGAIN %d' % Gain)

##    def do_set_Gain(self,Gain):
##        '''
##        Write Gain value
##        '''
##        ans = self._visa.write('ACGAIN%d' % Gain)
##        return float(ans)
##
##    def do_get_Gain(self)
##        '''
##        Read Gain value
##        '''
##        ans = self.visa.ask(ACGAIN.)