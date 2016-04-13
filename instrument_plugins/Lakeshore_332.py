# Lakeshore 332, Lakeshore 332 temperature controller driver
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
import time

class Lakeshore_332(Instrument):

    def __init__(self, name, address, reset=False):
        Instrument.__init__(self, name)

        self._address = address
        self._visa = visa.instrument(self._address)
        self._channels = ('A', 'B')

        self.add_parameter('identification',
            flags=Instrument.FLAG_GET)

        self.add_parameter('kelvin',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            channels=self._channels,
            units='K')
        self.add_parameter('heater_status',
            flags=Instrument.FLAG_GET,
            type=types.IntType)

        self.add_parameter('sensor',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            channels=self._channels,
            units='')

        self.add_parameter('heater_range',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType,
            format_map={
                0: 'off',
                1: 'low',
                2: 'med',
                3: 'high'
                })

        self.add_parameter('heater_output',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            units='%')

        self.add_parameter('mode',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType,
            format_map={0: 'Local', 1: 'Remote', 2: 'Remote, local lock'})

        self.add_parameter('pid',
            flags=Instrument.FLAG_GETSET,
            type=types.TupleType,
            channels=(1,2))

        self.add_parameter('setpoint',
            flags=Instrument.FLAG_GETSET,
            type=types.FloatType,
            channels=(1,2))
        # Manual output
        self.add_parameter('mout',
            flags=Instrument.FLAG_GETSET,
            type=types.FloatType,
            channels=(1,2))
        # Control mode
        # : 1 = Manual PID, 2 = Zone,
        #3 = Open Loop, 4 = AutoTune PID, 5 = AutoTune PI, 6 = AutoTune P.
        self.add_parameter('cmode',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType,
            channels=(1,2))

        self.add_function('local')
        self.add_function('remote')
        self.add_function('check_heater')

        if reset:
            self.reset()
        else:
            self.get_all()

    def reset(self):
        self._visa.write('*RST')

    def get_all(self):
        self.get_identification()
        self.get_mode()

    def do_get_identification(self):
        return self._visa.ask('*IDN?')

    def do_get_kelvin(self, channel):
        ans = self._visa.ask('KRDG? %s' % channel)
        return float(ans)

    def do_get_sensor(self, channel):
        ans = self._visa.ask('SRDG? %s' % channel)
        return float(ans)

    def do_get_heater_status(self):
        ans = self._visa.ask('HTRST?')
        return int(ans)

    def do_get_heater_range(self):
        ans = self._visa.ask('RANGE?')
        # if ans == '0':
        #     return 'OFF'
        # elif ans == '1':
        #     return 'LOW'
        # elif ans == '2':
        #     return 'MED'
        # elif ans == '3':
        #     return 'HIGH'
        # else:
        #     print 'HEATER NOT RESPONDING CORRECTLY'
        return int(ans)

    def do_set_heater_range(self, val):
        self._visa.write('RANGE %d' % val)

    def do_get_heater_output(self):
        ans = self._visa.ask('HTR?')
        return ans

    def do_get_mode(self):
        ans = self._visa.ask('MODE?')
        return int(ans)

    def do_set_mode(self, mode):
        self._visa.write('MODE %d' % mode)

    def local(self):
        self.set_mode(1)

    def remote(self):
        self.set_mode(2)

    def do_get_pid(self, channel):
        ans = self._visa.ask('PID? %d' % channel)
        fields = ans.split(',')
        if len(fields) != 3:
            return None
        fields = [float(f) for f in fields]
        return fields

    def do_set_pid(self, val, channel):
        pid_f = [float(f) for f in val]
        ans = self._visa.write('PID %d, %.1f, %.1f, %.1f' % (channel, pid_f[0], pid_f[1], pid_f[2]))
        return

    def do_get_setpoint(self, channel):
        ans = self._visa.ask('SETP? %s' % channel)
        return float(ans)

    def do_set_setpoint(self, val, channel):
        self._visa.write('SETP %s, %f' % (channel, val))

    def do_get_mout(self, channel):
        ans = self._visa.ask('MOUT? %s' % channel)
        return float(ans)

    def do_set_mout(self, val, channel):
        self._visa.write('MOUT %s,%f' % (channel, val))

    def do_get_cmode(self, channel):
        ans = self._visa.ask('CMODE? %s' % channel)
        return float(ans)

    def do_set_cmode(self, val, channel):
        self._visa.write('CMODE %s,%f' % (channel, val))

    def check_heater(self):
        chp = self.get_heater_output()
        if chp > 0.0:
            return
        ctmp = self.get_kelvinA()
        cstp = self.get_setpoint1()
        crng = self.get_heater_range()
        if (ctmp < cstp):
            self.set_heater_range('off')
            time.sleep(0.25)
            self.set_heater_range(crng)
            logging.warning(__name__ + ': reset heater after output was zero.')
        return