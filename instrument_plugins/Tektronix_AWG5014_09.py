# Tektronix_AWG5014.py class, to perform the communication between the Wrapper and the device
# Pieter de Groot <pieterdegroot@gmail.com>, 2008
# Martijn Schaafsma <mcschaafsma@gmail.com>, 2008
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
import struct
from time import sleep, localtime
from cStringIO import StringIO
import numpy as np
import measurement.instruments.Tektronix_AWG5014 as awg_ins
reload(awg_ins)


class Tektronix_AWG5014_09(awg_ins.Tektronix_AWG5014):
    '''
        This extention adds the dynamic jump functionality for the 09 option
    '''

    def __init__(self, name, address, reset=False, clock=1e9, numpoints=1000):
        awg_ins.Tektronix_AWG5014.__init__(self, name, address, reset=reset, clock=clock, numpoints=numpoints)

        awg_ins.Tektronix_AWG5014.AWG_FILE_FORMAT_HEAD.update({
                'EVENT_JUMP_MODE'           :   'h',#EVENT JUMP | DYNAMIC JUMP
                'TABLE_JUMP_STROBE'         :   'h',#On | off
                'TABLE_JUMP_DEFINITION'     :   'l'*16 #
        })
        self.add_function('set_sequence_jump_mode')
        self.add_function('get_sequence_jump_mode')
        self.add_function('set_djump_def')
        self.add_function('get_djump_def')
        self.add_function('set_event_jump_mode')
        self.add_function('get_event_jump_mode')

    def set_sequence_jump_mode(self, mode):
       self._visainstrument.write('AWGC:ENH:SEQ:JMOD %s' %(mode))

    def get_sequence_jump_mode(self):
        return self._visainstrument.ask('AWGC:ENH:SEQ:JMOD?')

    def set_djump_def(self, pattern, target):
       self._visainstrument.write('AWGC:EVEN:DJUM:DEF %s, %s' %(pattern, target))

    def get_djump_def(self, pattern):
        return self._visainstrument.ask('AWGC:EVEN:DJUM:DEF? %s' %(pattern))

    def set_event_jump_mode(self, mode):
       self._visainstrument.write('AWGC:EVEN:JMOD %s' %(mode))

    def get_event_jump_mode(self):
        return self._visainstrument.ask('AWGC:EVEN:JMOD?')


