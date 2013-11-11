# SRS_DG645.py driver for SRS DG645 Digital Delay Generator
# F. J. Heremans <jhereman@gmail.com>
# David Christle <christle@uchicago.edu>
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

class SR_DG645(Instrument):
    '''
    This is the driver for the SR DG645 Digital Delay Generator

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
            channels=('T0','T1','A','B','C','D','E','F','G','H'),
            minval=0, maxval=2000,units = 's')

        self.add_parameter('reference',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType,
            channels=('T0','T1','A','B','C','D','E','F','G'),
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
            channels=('T0', 'AB', 'CD','EF', 'GH'),
            minval=0, maxval=5,units = 'V')

        self.add_parameter('offset',
            flags=Instrument.FLAG_GETSET,
            type=types.FloatType,
            channels=('T0', 'AB', 'CD', 'EF', 'GH'),
            minval=-2, maxval=2,units = 'V')

        self.add_parameter('polarity',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType,
            channels=('T0', 'AB', 'CD','EF','GH'),
            minval=0, maxval=1,
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
        for output in 'T0', 'AB', 'CD', 'EF', 'GH':
            self.get('amplitude%s' % output)
            self.get('offset%s' % output)
            self.get('polarity%s' % output)

    def set_z_high(self):
        '''
        Set output impedance to High-Z
        '''

    def set_z_50(self):
        '''
        Set output impedance to 50 Ohm
        '''

    # This function converts a string channel to a number
    def _channel_num(self, channel):
        if type(channel) == types.IntType:
            return channel
        elif type(channel) == types.StringType:
            nummap = {'T0': 0,
                'T1': 1,
                'A': 2,
                'B': 3,
                'C': 4,
                'D': 5,
                'E': 6,
                'F': 7,
                'G': 8,
                'H': 9 }
            return nummap.get(channel.upper(), None)
        else:
            return None
    # This function converts a string output to a number
    def _output_num(self, output):
        if type(output) == types.IntType:
            return output
        elif type(output) == types.StringType:
            nummap = {
            'T0': 0,
            'AB': 1,
            'CD': 2,
            'EF': 3,
            'GH': 4}
            return nummap.get(output.upper(), None)
        else:
            return None
# --------------------------------------
#           parameters
# --------------------------------------
    def do_set_delay(self, delay_time, channel):
        '''
        Write delay for given channel
        '''
        # Get reference, use it to write delay
        ref = self.do_get_reference(channel)
        self._visa.write('DLAY %d,%d,%.12e' % (self._channel_num(channel),self._channel_num(ref),delay_time))
        return

    def do_get_delay(self, channel):
        '''
        Read delay for given channel
        '''
        ans = self._visa.ask('DLAY?%d' % self._channel_num(channel))
        lhs, delay = ans.split(",", 1)
        return float(delay)

    def do_get_reference(self, channel):
        '''
        Read delay reference for given channel
        '''
        ans = self._visa.ask('DLAY?%d' % self._channel_num(channel))
        ref, rhs = ans.split(",", 1)
        return int(ref)

    def do_set_reference(self, ref, channel):
        '''
        Set delay reference for given channel
        '''
        # First, get the existing delay time
        ans = self.do_get_delay(channel)
        # Split the response to get just the delay time
        lhs, delay_time = ans.split(",", 1)
        # Now set the reference with the same delay time
        self._visa.write('DLAY %d,%d,%.12e' % (self._channel_num(channel),self._channel_num(ref),delay_time))
        return

    def do_set_amplitude(self, ampl, channel):
        '''
        Write level amplitude for given channel
         - may want to add some error checkign to make sure
         amplitude + offset does not exceed 6V
        '''
        self._visa.write('LAMP %d,%f' % (self._output_num(channel),ampl))
        return


    def do_get_amplitude(self, channel):
        '''
        Read level amplitude for given channel
        '''
        ans = self._visa.ask('LAMP?%d' % self._output_num(channel))

        return float(ans)

    def do_set_offset(self, offs, channel):
        '''
        Write level offset for given channel
        - may want to add some error checkign to make sure
         amplitude + offset does not exceed 6V
        '''
        self._visa.write('LOFF %d,%f' % (self._output_num(channel),offs))
        return

    def do_get_offset(self, channel):
        '''
        Read level offset for given channel
        '''
        ans = self._visa.ask('LOFF?%d' % self._output_num(channel))
        return float(ans)

    def do_set_polarity(self, pol, channel):
        '''
        Write level polarity for given channel
        '''
        self._visa.write('LPOL %d,%f' % (self._output_num(channel),pol))
        return

    def do_get_polarity(self, channel):
        '''
        Read level polarity for given channel
        '''
        ans = self._visa.ask('LPOL?%d' % self._output_num(channel))
        return float(ans)

    def do_set_trig_source(self, source):
        '''
        Write trigger source
        '''
        self._visa.write('TSRC %d' % source)
        return

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
        self._visa.write('TRAT %d' % rate)
        return

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
        self._visa.write('TLVL %d' % source)
        return

    def do_get_trig_level(self):
        '''
        Read trigger level
        '''
        ans = self._visa.ask('TLVL?')
        return float(ans)

