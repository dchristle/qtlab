# Keithley_2700.py driver for Keithley 2700 DMM
# Pieter de Groot <pieterdegroot@gmail.com>, 2008
# Martijn Schaafsma <qtlab@mcschaafsma.nl>, 2008
# Reinier Heeres <reinier@heeres.eu>, 2008
#
# Update december 2009:
# Michiel Jol <jelle@michieljol.nl>
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


TC_array =[
    (10e-6, 0),
    (20e-6, 1),
    (40e-6, 2),
    (80e-6, 3),
    (160e-6, 4),
    (320e-6, 5),
    (640e-6, 6),
    (5e-3, 7),
    (10e-3, 8),
    (20e-3, 9),
    (50e-3, 10),
    (100e-3, 11),
    (200e-3, 12),
    (500e-3, 13),
    (1, 14),
    (2, 15),
    (5, 16),
    (10, 17),
    (20, 18),
    (50, 19),
    (100, 20),
    (200, 21),
    (500, 22),
    (1e3, 23),
    (2e3, 24),
    (5e3, 25),
    (10e3, 26),
    (20e3, 27),
    (50e3, 28),
    (100e3, 29),
]


def bool_to_str(val):
    '''
    Function to convert boolean to 'ON' or 'OFF'
    '''
    if val == True:
        return "ON"
    else:
        return "OFF"

class LOCKIN_7265(Instrument):
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
            units='', minval=0, maxval=10, type=types.FloatType)
        self.add_parameter('Y',
            flags=Instrument.FLAG_GET,
            units='', minval=0, maxval=10, type=types.FloatType)
        self.add_parameter('XY',
            flags=Instrument.FLAG_GET,
            units='', minval=0, maxval=10, type=types.FloatType)
        self.add_parameter('Gain',
            flags=Instrument.FLAG_GETSET,
            units='', minval=0, maxval=10, type=types.FloatType)
        self.add_parameter('TC',
            flags=Instrument.FLAG_GETSET,
            units='', minval=0, maxval=10, type=types.FloatType)


        # Add functions to wrapper
        self.add_function('get_XY')
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
        self._visainstrument.write('*RST')
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
        self.get_Gain()



    def reset_trigger(self):
        '''
        Reset trigger status

        Input:
            None

        Output:
            None
        '''
        logging.debug('Resetting trigger')
        self._visainstrument.write(':ABOR')


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
        Read X value
        '''
        ans = self._visa.ask('Y.')
        return float(ans)

     def do_get_XY(self):
        '''
        Read X& Y values simultaneously
        '''
        ans = self._visa.ask('XY.')
        XYvals = [int(x) for x in ans.split(";")]
        return float(XYvals)

     def do_set_TC(self,TCval):
        '''
        Write Time Constant (TC) value
        '''


        pos = bisect.bisect_right(TC_array[:,1], (TCval,))
        setTCnum = TC_array[pos]
        print '%s -> %s' % (TCval, setTCnum)

        ans = self._visa.write('TC%d' % setTCnum)
        return float(ans)

     def do_get_TC(self):
        '''
        Read Time Constant (TC) value
        '''
        ans = self._visa.ask('TC.')
        return float(ans)

    def do_set_Gain(self,Gain):
        '''
        Write Gain value
        '''
        ans = self._visa.write('ACGAIN%d' % Gain)
        return float(ans)

    def do_get_Gain(self)
        '''
        Read Gain value
        '''
        ans = self.visa.ask(ACGAIN.)