# Thorlabs_TSP01, Thorlabs SC10 optical shutter
# David Christle <christle@uchicago.edu>, August 2014
#

from instrument import Instrument
import visa
import types
import logging
import re
import math
import pyvisa
import time
import qt

CR = '\r'
LF = '\n'


class Thorlabs_SC10(Instrument):

    def __init__(self, name, address, reset=False):
        Instrument.__init__(self, name)

        self._address = address


        self.add_parameter('identification',
            flags=Instrument.FLAG_GET)

        self.add_parameter('toggle_enable',
            flags=Instrument.FLAG_GETSET,
            type=types.BooleanType)

        self.add_parameter('mode',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType,
            format_map={
               1: 'Manual',
               2: 'Auto',
               3: 'Single',
               4: 'Repeat',
               5: 'External'
            })




        self.add_parameter('closed',
            flags=Instrument.FLAG_GET,
            type=types.BooleanType)

        self.add_function('buffer_clear')

        self._open_serial_connection()
        self.buffer_clear()

        self.get_all()
    # Open serial connection
    def _open_serial_connection(self):
        logging.debug(__name__ + ' : Opening serial connection')
        qt.rm.open_resource(self._address)
        self._visa =  qt.rm.get_instrument(self._address)
        self._visa.baud_rate = long(9600)
        self._visa.data_bits = 8
        self._visa.stop_bits = 1
        self._visa.read_termination = '\r'
        self._visa.write_termination = '\r'
#        self._visa = pyvisa.visa.SerialInstrument(self._address,
#                baud_rate=9600, data_bits=8, stop_bits=1,
#                parity=pyvisa.visa.no_parity, term_chars=pyvisa.visa.CR,
#                send_end=False,timeout=2)
        # The purpose of the short timeout is so that the buffer_clear()
        # operation that takes place with every command to ensure the proper
        # output doesn't take too long. Each buffer_clear() usually takes one
        # entire timeout period, since most of the time, the buffer is in fact
        # clear.
        return

    # Close serial connection
    def _close_serial_connection(self):
        '''
        Closes the serial connection
        '''
        logging.debug(__name__ + ' : Closing serial connection')
        self._visa.close()

    def buffer_clear(self): # updated to work with recent PyVISA
        navail = self._visa.get_visa_attribute(pyvisa.VI_ATTR_ASRL_AVAIL_NUM)
        if navail > 0:
            #reply = pyvisa.vpp43.read(self._visa.vi, navail)
            reply = self._visa.read(


    def get_all(self):
        self.get_mode()
        return
        

    def do_get_identification(self):
        self.buffer_clear()
        ans = self._visa.ask('*IDN?')
        self.buffer_clear()
        return

    def do_get_mode(self):
        self.buffer_clear()
        print 'cleared buffer, getting mode'
        outp = self._visa.ask('mode?')
        self.buffer_clear()
        print 'output is %s' % outp
        return outp
        
    def do_set_mode(self, newmode):
        self.buffer_clear()
        self._visa.write('mode=%d' % newmode)
        self.buffer_clear()
        return

    def do_get_toggle_enable(self):
        self.buffer_clear()
        ans = self._visa.ask('ens?')
        print 'toggle enable state is %s' % ans
        self.buffer_clear()
        return ans

    def do_set_toggle_enable(self, toggle):
        self.buffer_clear()
        cur_state = self.get_toggle_enable()
        print 'Current state is %s' % cur_state
        if cur_state == toggle:
            return
        else:
            self._visa.write('ens')
        self.buffer_clear()
        cur_state = self.get_toggle_enable()
        if cur_state == toggle:
            return
        else:
            logging.error(__name__ + ': failed to change toggle state properly')
        self.buffer_clear()
        return

    def do_get_closed(self):
        self.buffer_clear()
        self.buffer_clear()
        ans = self._visa.ask('closed?')
        print 'closed state is %s' % ans
        self.buffer_clear()
        return ans
