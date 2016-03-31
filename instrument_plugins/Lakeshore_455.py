# Lakeshore 455, Lakeshore 455 DSP Gaussmeter
# David J. Christle <christle@uchicago.edu>, 2015
#


from instrument import Instrument
import visa
import types
import logging
import re
import math
import time

class Lakeshore_455(Instrument):

    def __init__(self, name, address, reset=False):
        Instrument.__init__(self, name)

        self._address = address
        self._visa = visa.instrument(self._address)

        self.add_parameter('identification',
            flags=Instrument.FLAG_GET)

        self.add_parameter('field',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            units='G')
##
##        self.add_parameter('sensor',
##            flags=Instrument.FLAG_GET,
##            type=types.FloatType,
##            channels=self._channels,
##            units='')
##
##        self.add_parameter('heater_range',
##            flags=Instrument.FLAG_GETSET,
##            type=types.IntType,
##            format_map={
##                1: '25 W',
##                2: '2.5 W',
##                3: '250 mW',
##                4: '25 mW',
##                5: '2.5 mW',
##                })
##
##        self.add_parameter('heater_output',
##            flags=Instrument.FLAG_GET,
##            type=types.FloatType,
##            units='%')
##
        self.add_parameter('mode',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType,
            format_map={1: 'Local', 2: 'Remote', 3: 'Remote, local lock'})
##
##        self.add_parameter('pid',
##            flags=Instrument.FLAG_GETSET,
##            type=types.TupleType,
##            channels=(1,4))

##        self.add_parameter('auto',
##            flags=Instrument.FLAG_GETSET,
##            type=types.FloatType,
##            channels=(1,4))

        self.add_function('local')
        self.add_function('remote')

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



    def do_get_mode(self):
        ans = self._visa.ask('MODE?')
        return int(ans)

    def do_set_mode(self, mode):
        self._visa.write('MODE %d' % mode)

    def local(self):
        self.set_mode(1)

    def remote(self):
        self.set_mode(2)

    def do_get_field(self):
        ans = self._visa.ask('RDGFIELD?')
        return float(ans)
