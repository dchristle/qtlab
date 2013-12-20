# Lakeshore 221 Temperature Monitor
# David Christle <christle@uchicago.edu>, December 2013


from instrument import Instrument
import visa
import types
import logging
import math
import time
import pyvisa

class Lakeshore_221(Instrument):


    def __init__(self, name, address, reset=False):
        Instrument.__init__(self, name, tags=['physical'])

        self._address = address
        # Device identification
        self.add_parameter('identification',
        flags=Instrument.FLAG_GET)
        # Get temperature in Kelvin
        self.add_parameter('temperature',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            units='K')
        # Input type is the type of temperator sensor in the device
        self.add_parameter('intype',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType)
        # Controls whether display is on or off on the module
        self.add_parameter('dispon',
            flags=Instrument.FLAG_GETSET,
            type=types.BooleanType)

        self._open_serial_connection()
        if reset:
            self.reset()
        else:
            self.get_all()


    # Open serial connection
    def _open_serial_connection(self):
        logging.debug(__name__ + ' : Opening serial connection')

        self._visa = pyvisa.visa.SerialInstrument(self._address,
                baud_rate=9600, data_bits=7, stop_bits=1,
                parity=pyvisa.visa.odd_parity, term_chars=pyvisa.visa.CR+pyvisa.visa.LF,
                send_end=False,timeout=2)
        # The purpose of the short timeout is so that the buffer_clear()
        # operation that takes place with every command to ensure the proper
        # output doesn't take too long. Each buffer_clear() usually takes one
        # entire timeout period, since most of the time, the buffer is in fact
        # clear.

    # Close serial connection
    def _close_serial_connection(self):
        '''
        Closes the serial connection
        '''
        logging.debug(__name__ + ' : Closing serial connection')
        self._visa.close()

    def buffer_clear(self): # Got this from Zaber code
        navail = pyvisa.vpp43.get_attribute(self._visa.vi, pyvisa.vpp43.VI_ATTR_ASRL_AVAIL_NUM)
        if navail > 0:
            reply = pyvisa.vpp43.read(self._visa.vi, navail)

    def reset(self):
        self._visa.write('*rst')
        time.sleep(3) # Sleep to avoid trying to talk to the device too quickly

    def get_all(self):
        self.get_identification()
        self.get_intype()
        self.get_temperature()
        self.get_dispon()

    def do_get_identification(self):
        self.buffer_clear()
        return self._visa.ask('*ind')

    def do_get_dispon(self):
        logging.debug(__name__ + 'reading temperature')
        self.buffer_clear()
        return self._visa.ask('DISPON?')

    def do_set_dispon(self, dispon):
        logging.debug(__name__ + 'setting input type')
        self.buffer_clear()
        if dispon == True:
            self._visa.write('DISPON 1')
        elif dispon == False:
            self._visa.write('DISPON 0')
        else:
            logging.error(__name__ + 'dispon value received was not a Boolean!')
            return False
        return True

    def do_get_temperature(self):
        logging.debug(__name__ + 'reading temperature')
        self.buffer_clear()
        return self._visa.ask('KRDG?')

    def do_get_intype(self):
        logging.debug(__name__ + 'reading input type')
        self.buffer_clear()
        return float(self._visa.ask('INTYPE?'))

    def do_set_intype(self, intype):
        logging.debug(__name__ + 'setting input type')
        self.buffer_clear()
        self._visa.write('INTYPE %d' % intype)