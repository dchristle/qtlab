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
        self.add_parameter('XY',
            flags=Instrument.FLAG_GET,
            units='V', minval=0, maxval=10, type=types.FloatType)
        self.add_parameter('frequency',
            flags=Instrument.FLAG_GET,
            units='Hz', minval=0, maxval=10, type=types.FloatType)
        self.add_parameter('gain',
            flags=Instrument.FLAG_SET,
            units='dB', minval=0, maxval=9, type=types.FloatType,
            format_map={
               0: 0,
               1: 10,
               2: 20,
               3: 30,
               4: 40,
               5: 50,
               6: 60,
               7: 70,
               8: 80,
               9: 90,
            })
        self.add_parameter('TC',
            flags=Instrument.FLAG_GETSET,
            units='s', minval=0, maxval=10, type=types.FloatType,
            format_map={
               0: 10e-6,
               1: 20e-6,
               2: 40e-6,
               3: 80e-6,
               4: 160e-6,
               5: 320e-6,
               6: 640e-6,
               7: 5e-3,
               8: 10e-3,
               9: 20e-3,
               10: 50e-3,
               11: 100e-3,
               12: 200e-3,
               13: 500e-3,
               14: 1,
               15: 2,
               16: 5,
               17: 10,
               18: 20,
               19: 50,
               20: 100,
               21: 200,
               22: 500,
               23: 1e3,
               24: 2e3,
               25: 5e3,
               26: 10e3,
               27: 20e3,
               28: 50e3,
               29: 100e3,
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

    def do_get_XY(self):
        '''
        Read X& Y values simultaneously
        '''
        ans = self._visa.ask('XY.')
        XYvals = [int(x) for x in ans.split(",")]
        return float(XYvals)

    def do_set_TC(self,TCval):
        '''
        Write Time Constant (TC) value
        '''
        ans = self._visa.write('TC%d' % setTCnum)
        return float(ans)

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
        ans = self._visa.write('AUTOMATIC')
        ans = self._visa.write('ACGAIN%d' % Gain)


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