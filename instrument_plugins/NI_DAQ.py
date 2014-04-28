# NI_DAQ.py, National Instruments Data AcQuisition instrument driver
# Reinier Heeres <reinier@heeres.eu>, 2009
# David Christle <christle@uchicago.edu>, 2013
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

import types
from lib.dll_support import nidaq
from instrument import Instrument
import qt

def _get_channel(devchan):
    if not '/' in devchan:
        return devchan
    parts = devchan.split('/')
    if len(parts) != 2:
        return devchan
    return parts[1]

class NI_DAQ(Instrument):

    def __init__(self, name, id):
        Instrument.__init__(self, name, tags=['physical'])

        self._id = id

        for ch_in in self._get_input_channels():
            ch_in = _get_channel(ch_in)
            self.add_parameter(ch_in,
                flags=Instrument.FLAG_GET,
                type=types.FloatType,
                units='V',
                tags=['measure'],
                get_func=self.do_get_input,
                channel=ch_in)

        for ch_out in self._get_output_channels():
            ch_out = _get_channel(ch_out)
            self.add_parameter(ch_out,
                flags=Instrument.FLAG_SET,
                type=types.FloatType,
                units='V',
                tags=['sweep'],
                set_func=self.do_set_output,
                channel=ch_out)

        for ch_ctr in self._get_counter_channels():
            ch_ctr = _get_channel(ch_ctr)
            self.add_parameter(ch_ctr,
                flags=Instrument.FLAG_GET,
                type=types.IntType,
                units='#',
                tags=['measure'],
                get_func=self.do_get_counter,
                channel=ch_ctr)
            self.add_parameter(ch_ctr + "_src",
                flags=Instrument.FLAG_SET | Instrument.FLAG_SOFTGET,
                type=types.StringType,
                set_func=self.do_set_counter_src,
                channel=ch_ctr)

        self.add_parameter('chan_config',
            flags=Instrument.FLAG_SET|Instrument.FLAG_SOFTGET,
            type=types.StringType,
            option_list=('Default', 'RSE', 'NRSE', 'Diff', 'PseudoDiff'))

        self.add_parameter('count_time',
            flags=Instrument.FLAG_SET|Instrument.FLAG_SOFTGET,
            type=types.FloatType,
            units='s')


        self.add_function('reset')
        self.add_function('digital_out')
        self.add_function('write')
        self.add_function('write_and_count')
        #self.add_function('AOsweep_exportclk')
        #self.add_function('AOsweep_DAQcount')

        self.reset()
        self.set_chan_config('RSE')
        self.set_count_time(1)
        self.get_all()


    def get_all(self):
        ch_in = [_get_channel(ch) for ch in self._get_input_channels()]
        self.get(ch_in)

    def reset(self):
        '''Reset device.'''
        nidaq.reset_device(self._id)

    def _get_input_channels(self):
        return nidaq.get_physical_input_channels(self._id)

    def _get_output_channels(self):
        return nidaq.get_physical_output_channels(self._id)

    def _get_counter_channels(self):
        return nidaq.get_physical_counter_channels(self._id)

    def do_get_input(self, channel):
        devchan = '%s/%s' % (self._id, channel)
        return nidaq.read(devchan, config=self._chan_config)

    def do_set_output(self, val, channel):
        devchan = '%s/%s' % (self._id, channel)
        return nidaq.write(devchan, val)

    def do_set_chan_config(self, val):
        self._chan_config = val

    def do_set_count_time(self, val):
        self._count_time = val

    def do_get_counter(self, channel):
        devchan = '%s/%s' % (self._id, channel)
        src = self.get(channel + "_src")
        if src is not None and src != '':
            src = '/%s/%s' % (self._id, src)
        data = nidaq.read_counter(devchan, src=src, freq=1/self._count_time, samples=1)
        return data

    def read_counters(self, channels):
        chans = []
        srcs = []
        for chan in channels:
            chans.append('%s/%s' % (self._id, chan))
            srcs.append(self.get(chan + "_src"))
        return nidaq.read_counters(chans, src=srcs, freq=1.0/self._count_time)

    def write_and_count(self, vdata, devchan, ctrchan):
        # Format the various channels and terminals correctly for what the DAQ
        # routines expect.
        cchan = '/%s/%s' % (self._id, ctrchan)
        src = self.get(ctrchan + "_src")
        aochan = '/%s/%s' % (self._id, 'ao/SampleClock')
        aodevchan = '/%s/%s' % (self._id, devchan)

        return nidaq.write_and_count(aodevchan, cchan, src, aochan, vdata, 1.0/self._count_time, -10.0, 10.0,
                10.0)

    def write(self, data, freq, minv, maxv,
                timeout, channel):
        # This routine is a slightly more general version of the set output
        # routine already written. The purpose here is to allow the user direct
        # access to the lower nidaq.py module's "write" function that allows
        # setting of the frequency of the write, among other things.
        devchan = '%s/%s' % (self._id, channel)
        return nidaq.write(devchan, data, freq, minv, maxv,
                timeout)

    def writearray(self, data, freq, minv, maxv,
                timeout, channel):
        # This routine is a slightly more general version of the set output
        # routine already written. The purpose here is to allow the user direct
        # access to the lower nidaq.py module's "write" function that allows
        # setting of the frequency of the write, among other things.
        devchan = '%s/%s' % (self._id, channel)
        return nidaq.writearray(devchan, data, freq, minv, maxv,
                timeout)
    def readarray(self, samples, trigchan, freq, minv, maxv,
                timeout, channel):
        # This routine is a slightly more general version of the set output
        # routine already written. The purpose here is to allow the user direct
        # access to the lower nidaq.py module's "write" function that allows
        # setting of the frequency of the write, among other things.
        devchan = '%s/%s' % (self._id, channel)
        array_out = nidaq.readarray(devchan, trigchan, samples, freq, minv, maxv, timeout)

        return array_out

    # Dummy
    def do_set_counter_src(self, val, channel):

        return True

    def digital_out(self, lines, val):
        devchan = '%s/%s' % (self._id, lines)
        return nidaq.write_dig_port8(devchan, val)

def detect_instruments():
    '''Refresh NI DAQ instrument list.'''

    for name in nidaq.get_device_names():
        qt.instruments.create('NI%s' % name, 'NI_DAQ', id=name)

