# Thorlabs_TSP01, Thorlabs TSP01 temperature monitor drive
# Wolfgang Pfaff <wolfgangpfff@gmail.com>, 2013
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

class Thorlabs_TSP01(Instrument):
    
    def __init__(self, name, address, reset=False):
        Instrument.__init__(self, name)

        self._address = address
        self._visa = visa.instrument(self._address)

        self.add_parameter('identification',
            flags=Instrument.FLAG_GET)

        self.add_parameter('internal_temperature',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            units='deg C')

        self.add_parameter('probe1_temperature',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            units='deg C')

        self.add_parameter('probe2_temperature',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            units='deg C')     
        
        self.add_parameter('humidity',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            units='percent')

        if reset:
            self.reset()
        else:
            self.get_all()

    def reset(self):
        self._visa.write('*RST')

    def get_all(self):
        self.get_internal_temperature()
        self.get_probe1_temperature()
        self.get_probe2_temperature()
        self.get_humidity()

    def do_get_identification(self):
        return self._visa.ask('*IDN?')

    def do_get_internal_temperature(self):
        ans = self._visa.ask('MEAS:TEMP?')
        return float(ans)

    def do_get_probe1_temperature(self):
        ans = self._visa.ask('MEAS:TEMP2?')
        return float(ans)

    def do_get_probe2_temperature(self):
        ans = self._visa.ask('MEAS:TEMP3?')
        return float(ans)

    def do_get_humidity(self):
        ans = self._visa.ask('MEAS:HUM?')
        return float(ans)



