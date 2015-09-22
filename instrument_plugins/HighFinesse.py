# HighFinesse.py - Instrument plugin to communicate with a High Finesse 
# wavelengthmeter
# Gabriele de Boo <g.deboo@student.unsw.edu.au>
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
import types
import logging
from ctypes import *

wlmData = windll.wlmData

GetWvl = wlmData.GetWavelength
GetWvl.restype = c_double
GetFrq = wlmData.GetFrequency
GetFrq.restype = c_double
GetLw = wlmData.GetLinewidth
GetLw.restype = c_double
GetPwr = wlmData.GetPowerNum
GetPwr.restype = c_double
GetExposure = wlmData.GetExposure
GetExposure.restype = c_ushort
GetTemperature = wlmData.GetTemperature
GetTemperature.restype = c_double
GetPressure = wlmData.GetPressure
GetPressure.restype = c_double
GetInterval = wlmData.GetInterval
GetInterval.restype = c_long
ConvertUnit = wlmData.ConvertUnit
ConvertUnit.restype = c_double

cReturnWavelengthVac    = c_ushort(0)
cReturnWavelengthAir    = c_ushort(1)
cReturnFrequency        = c_ushort(2)
cReturnWavenumber       = c_ushort(3)
cReturnPhotonEnergy     = c_ushort(4)

class HighFinesse(Instrument):
    '''High Finesse Wavelength meter'''

    def __init__(self, name, reset=False):
        Instrument.__init__(self, name, tags=['physical'])

        self.add_parameter('wavelength',
                type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units='nm')
        self.add_parameter('frequency',
                type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units='THz')
        self.add_parameter('energy',
                type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units='eV')
        self.add_parameter('linewidth',
                type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units='THz')
        self.add_parameter('power',
                type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units='microW')
        self.add_parameter('exposure',
                type=types.IntType,
                flags=Instrument.FLAG_GET,
                units='ms')
        self.add_parameter('temperature',
                type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units='C')
        self.add_parameter('pressure',
                type=types.FloatType,
                flags=Instrument.FLAG_GET,
                units='mbar')
        self.add_parameter('interval',
                type=types.IntType,
                flags=Instrument.FLAG_GET,
                units='ms')

        if reset:
            self.reset()
        else:
            self.get_all()

#### initialization related

    def reset(self):
        print __name__ + ' : resetting instrument'

    def get_all(self):
        print __name__ + ' : reading all settings from instrument'
        self.get_wavelength()
        self.get_frequency()
        self.get_energy()
        self.get_power()
        self.get_temperature()
        self.get_pressure()

#### communication with machine

    def do_get_wavelength(self):
        '''Get the measured wavelength in nm'''
        Wavelength = GetWvl(c_double(0))
        return Wavelength

    def do_get_power(self):
        '''Get the measured optical power'''
        return GetPwr(c_long(1), c_double(0))

    def do_get_frequency(self):
        '''Get the measured frequency in THz'''
        return GetFrq(c_double(0))

    def do_get_energy(self):
        '''Get the measured energy in eV'''
        frequency = GetFrq(c_double(0))
        energy = ConvertUnit(c_double(frequency),
                             cReturnFrequency,
                             cReturnPhotonEnergy)
        return energy

    def do_get_linewidth(self):
        '''Get the measured linewidth'''
        linewidth = GetLw(cReturnFrequency,c_double(0))
        if linewidth == -6:
            logging.warning('Linewidth measurement is not available.')
        else:
            return linewidth

    def do_get_exposure(self):
        '''Get the exposure in ms'''
        return GetExposure(c_ushort(0))

    def do_get_temperature(self):
        '''Get the temperature in C'''
        return GetTemperature(c_double(0))

    def do_get_pressure(self):
        '''Get the pressure in mbar'''
        return GetPressure(c_double(0))

    def do_get_interval(self):
        '''Get the measurement interfal in ms'''
        return GetInterval(c_long(0))
