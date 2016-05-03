# Thorlabs_PM100D, Thorlabs PM100D power meter driver
# Reinier Heeres <reinier@heeres.eu>, 2010
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
import re
import math

class Thorlabs_PM100D(Instrument):

    def __init__(self, name, address, reset=False):
        Instrument.__init__(self, name)

        self._address = address
        self._visa = visa.instrument(self._address)

        self.add_parameter('identification',
            flags=Instrument.FLAG_GET,
            type=types.StringType)

        self.add_parameter('power',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            units='W')

        self.add_parameter('num_avgs',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType)

        self.add_parameter('head_info',
            flags=Instrument.FLAG_GET,
            type=types.StringType)

        self.add_parameter('wavelength',
            flags=Instrument.FLAG_GETSET,
            type=types.FloatType,
            units='nm')

        if reset:
            self.reset()
        else:
            self.get_all()

    def reset(self):
        self._visa.write('*RST')

    def get_all(self):
        self.get_power()
        self.get_head_info()
        self.get_wavelength()

    def do_get_identification(self):
        return self._visa.ask('*IDN?')

    def do_get_power(self):
        ans = self._visa.ask('MEAS:POW?')
        return float(ans)

    def do_get_head_info(self):
        ans = self._visa.ask('SYST:SENS:IDN?')
        return ans

    def do_get_wavelength(self):
        ans = self._visa.ask('CORR:WAV?')
        return float(ans)*1e-9

    def do_set_wavelength(self, val):
        valnm=val*1e9
        self._visa.write('CORR:WAV %e' % valnm)
    def do_get_num_avgs(self):
        return self._visa.ask('SENS:AVER?')
    def do_set_num_avgs(self, navgs):
        self._visa.write(('SENS:AVER %d' % navgs))
        return

