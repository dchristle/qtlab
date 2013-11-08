# SRS_DG645.py driver for SRS DG645 Digital Delay Generator
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

class SRS_DG645(Instrument):
    '''
    This is the driver for the SRS DG645 Digital Delay Generator

    Usage:
    Initialize with
    <name> = instruments.create('<name>', 'SRS_DG645',
        address='<GBIP address>',
        reset=<bool>)
    '''

    def __init__(self, name, address, reset=False):
        '''
        Initializes the SRS DG645 class of Digital Delay Generator, and communicates with the wrapper.

        Input:
            name (string)           : name of the instrument
            address (string)        : GPIB address
            reset (bool)            : resets to default values
        Output:
            None
        '''
        # Initialize wrapper functions
        logging.info('Initializing instrument SRS DG645')
        Instrument.__init__(self, name, tags=['physical'])

        # Add some global constants
        self._address = address
        self._visa = visa.instrument(self._address)
        self._modes = ['BURST','DELAY']

        self.add_parameter('delay',
            flags=Instrument.FLAG_GETSET,
            type=types.FloatType,
            channels=('T0','T1','A','B','C','D','E','F','G'),
            minval=0, maxval=2000,units = 's',
            format_map = {
                0: 'T0',
                1: 'T1',
                2: 'A',
                3: 'B',
                4: 'C',
                5: 'D',
                6: 'E',
                7: 'F',
                8: 'G',
                9: 'H',
            })

        self.add_parameter('amplitude',
            flags=Instrument.FLAG_GETSET,
            type=types.FloatType,
            channels=('AB', 'CD','EF','GH'),
            minval=0, maxval=5,units = 'V',
            format_map = {
                0: 'T1',
                1: 'AB',
                2: 'CD',
                3: 'EF',
                4: 'GH',
            })

        self.add_parameter('offset',
            flags=Instrument.FLAG_GETSET,
            type=types.FloatType,
            channels=('AB', 'CD','EF','GH'),
            minval=-2, maxval=2,units = 'V',
            format_map = {
                0: 'T1',
                1: 'AB',
                2: 'CD',
                3: 'EF',
                4: 'GH',
            })

        self.add_parameter('polarity',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType,
            channels=('AB', 'CD','EF','GH'),
            minval=0, maxval=1,units = 'V',
            format_map = {
                0: 'neg',
                1: 'pos',
            })


        self.add_parameter('trig_source',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType,
            minval=0, maxval=6,units = '',
            format_map = {
                0: 'internal',
                1: 'external_rising_edge',
                2: 'external_falling_edge',
                3: 'single_shot_external_rising_edge',
                4: 'single_shot_external_falling_edge',
                5: 'single_shot',
                6: 'line'
            })

        self.add_parameter('trig_rate',
            flags=Instrument.FLAG_GETSET,
            type=types.FloatType,
            minval=100e-6, maxval=10e6,units = 'Hz',
            )

        self.add_parameter('trig_level',
            flags=Instrument.FLAG_GETSET,
            type=types.FloatType,
            minval=0, maxval=3.5,units = 'V',
            )

        # Add functions to wrapper
        self.add_function('set_z_high')
        self.add_function('set_z_50')
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
        for chan in 'T0','T1','A', 'B', 'C', 'D', 'E', 'F', 'G', 'H':
            self.get('delay%s' % chan)
        for chan in 'T0', 'AB', 'CD', 'EF', 'GH':
            self.get('level%s' % chan)
            self.get('offset%s' % chan)
            self.get('polarity%s' % chan)

    def set_z_high(self):
        '''
        Set output impedance to High-Z
        '''

    def set_z_50(self):
        '''
        Set output impedance to 50 Ohm
        '''

# --------------------------------------
#           parameters
# --------------------------------------
    def do_set_delay(self,channel,ref,delay_time):
        '''
        Write delay for given channel
        '''
        self._visa.ask('DLAY %d,%d,%f' % (channel,ref,delay_time))

    def do_get_delay(self,channel):
        '''
        Read delay for given channel
        '''
        ans = self._visa.ask('DLAY?%d' % channel)
        return float(ans)

    def do_set_amplitude(self,channel,ampl):
        '''
        Write level amplitude for given channel
         - may want to add some error checkign to make sure
         amplitude + offset does not exceed 6V
        '''
        self._visa.ask('LAMP %d,%f' % (channel,ampl))


    def do_get_amplitude(self,channel):
        '''
        Read level amplitude for given channel
        '''
        ans = self._visa.ask('LAMP?%d' % channel)
        return float(ans)

    def do_set_offset(self,channel,offs):
        '''
        Write level offset for given channel
        - may want to add some error checkign to make sure
         amplitude + offset does not exceed 6V
        '''
        self._visa.ask('LOFF %d,%f' % (channel,offs))

    def do_get_offset(self,channel):
        '''
        Read level offset for given channel
        '''
        ans = self._visa.ask('LOFF?%d' % channel)
        return float(ans)

    def do_set_polarity(self,channel,pol):
        '''
        Write level polarity for given channel
        '''
        self._visa.ask('LPOL %d,%f' % (channel,pol))

    def do_get_polarity(self,channel):
        '''
        Read level polarity for given channel
        '''
        ans = self._visa.ask('LPOL?%d' % channel)
        return float(ans)

    def do_set_trig_source(self,source):
        '''
        Write trigger source
        '''
        self._visa.ask('TSRC %d' % source)

    def do_get_trig_source(self):
        '''
        Read trigger source
        '''
        ans = self._visa.ask('LTSRC?')
        return float(ans)

    def do_set_trig_rate(self,rate):
        '''
        Write internal trigger rate
        '''
        self._visa.ask('TRAT %d' % rate)

    def do_get_trig_rate(self):
        '''
        Read internal trigger rate
        '''
        ans = self._visa.ask('TRAT?')
        return float(ans)

    def do_set_trig_level(self,source):
        '''
        Write trigger level
        '''
        self._visa.ask('TLVL %d' % source)

    def do_get_trig_level(self):
        '''
        Read trigger level
        '''
        ans = self._visa.ask('TLVL?')
        return float(ans)

