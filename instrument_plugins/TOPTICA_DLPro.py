# Laser driver for Toptica DL Pro
# David Christle, September 2015 <christle@uchicago.edu>
#
# This is a driver for TOPTICA's DL Pro laser control module. It uses a Scheme-like
# syntax for sending commands and retrieving data. One curiosity about the interface
# is that it always echoes the command sent back before sending the respond. To
# handle this, I wrote a 'query' method that reads/discards the echo and then
# returns the next chunk of data read from the serial buffer.
from instrument import Instrument
import visa
import types
import logging
import numpy
import time
import qt
import pyvisa

class TOPTICA_DLPro(Instrument):

#----------------------------------------------
# Initialization
#----------------------------------------------

    def __init__(self, name, address, reset = False):

        Instrument.__init__(self, name, tags = ['physical'])

        self._address = address
        self._visa = visa.instrument(self._address)


        # Add functions

        self.add_function('get_all')

        self.add_parameter('current_limit',
            flags = Instrument.FLAG_GETSET,
            type = types.FloatType,
            units = 'A',
            minval=0.0,maxval=0.6)

        self.add_parameter('current',
            flags = Instrument.FLAG_GETSET,
            type = types.FloatType,
            units = 'A',
            minval=0.0,maxval=312.0)

        self.add_parameter('temperature_setpoint',
            flags = Instrument.FLAG_GETSET,
            type = types.FloatType,
            units = 'C',
            minval=6.0,maxval=40.0)

        self.add_parameter('temperature_actual',
            flags = Instrument.FLAG_GET,
            type = types.FloatType,
            units = 'C')

        self.add_parameter('emission',
            flags = Instrument.FLAG_GET,
            type = types.StringType)

        self.add_function('on')
        self.add_function('off')
        self.add_function('test_buzzer')
        self.add_function('set_buzzer_welcome')
    # Open serial connection
    def _open_serial_connection(self):
        logging.debug(__name__ + ' : Opening serial connection')

        self._visa = pyvisa.visa.SerialInstrument(self._address,
                baud_rate=115200, data_bits=8, stop_bits=1,
                parity=pyvisa.visa.no_parity, term_chars=pyvisa.visa.CR+pyvisa.visa.LF,
                send_end=True,timeout=2)


    # Close serial connection
    def _close_serial_connection(self):
        '''
        Closes the serial connection
        '''
        logging.debug(__name__ + ' : Closing serial connection')
        self._visa.close()

    def buffer_clear(self): # Got this from Zaber code
        navail = pyvisa.vpp43.get_attribute(self._visa.vi, pyvisa.vpp43.VI_ATTR_ASRL_AVAIL_NUM)
        print '%d bytes available, reading...' % navail
        its = 0
        while (navail > 0 and its < 200):
            navail = pyvisa.vpp43.get_attribute(self._visa.vi, pyvisa.vpp43.VI_ATTR_ASRL_AVAIL_NUM)
            reply = pyvisa.vpp43.read(self._visa.vi, navail)
            its += 1
    def query(self, string):
        self._visa.write(string)
        echo = pyvisa.vpp43.read(self._visa.vi, 1024)
        reply = pyvisa.vpp43.read(self._visa.vi, 1024)
        return reply

    def reset(self):
        self._visa.write('*rst')
        time.sleep(3) # Sleep to avoid trying to talk to the device too quickly

    def test_buzzer(self):
        #self._visa.write('(exec \'buzzer:play \"A A A A A A E E H E H E AAAA\")')
        self.query('(exec \'buzzer:play \"ABCDEFG HIJKLMNO    EEEEEEEEEEEEEEEEEEEEEE  LLLLLLLLLLLLLLLLLLLLLLLL LLLLLL JJJJJJ HHHHHH GGGGGG GGGGGGGGGGGGGGGGGGGG HHHHHH EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE QQQQQQ OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO EEEEEE HHHHHH EEEEEEEEEEEEEEEEEEEEEE  LLLLLLLLLLLLLLLLLLLLLLLL LLLLLL JJJJJJ HHHHHH GGGGGG GGGGGGGGGGGGGGGGGGGG HHHHHH EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE\")')
        return
    def set_buzzer_welcome(self):
        self.query('(exec \'buzzer:play \"ABCDEFG HIJKLMNO    EEEEEEEEEEEEEEEEEEEEEE  LLLLLLLLLLLLLLLLLLLLLLLL LLLLLL JJJJJJ HHHHHH GGGGGG GGGGGGGGGGGGGGGGGGGG HHHHHH EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE QQQQQQ OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO\")')
        return
    def on(self):
        self.query('(param-set! \'laser1:dl:cc:enabled #t)')
        if ret == '()':
            return True
        else:
            print ('%s' % ret)
            return False
    def off(self):
        self.query('(param-set! \'laser1:dl:cc:enabled #f)')
        if ret == '()':
            return True
        else:
            print ('%s' % ret)
            return False
    def do_get_emission(self):
        ret = self.query('(param-ref \'laser1:dl:cc:enabled)')
        return ret
    def do_set_current(self,current):
        self.query(('(param-set! \'laser1:dl:cc:current-set %.3f)' % current))
        if ret == '()':
            return True
        else:
            print ('%s' % ret)
            return False
    def do_get_current(self):
        ret = self.query('(param-ref \'laser1:dl:cc:current-set)')
        return float(ret)
    def do_get_temperature_setpoint(self):
        ret = self.query('(param-ref \'laser1:dl:tc:temp-set)')
        return float(ret)
    def do_set_temperature_setpoint(self, temperature):
        ret = self.query(('(param-set! \'laser1:dl:tc:temp-set %.3f)' % temperature))
        if ret == '()':
            return True
        else:
            print ('%s' % ret)
            return False
    def do_get_temperature_actual(self):
        ret = self.query('(param-ref \'laser1:dl:tc:temp-act)')
        return float(ret)

    def get_all(self):
        return


