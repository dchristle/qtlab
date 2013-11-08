# Coherent_FieldMasterGS, FieldMaster GS laser power meter driver
# David Christle <christle@uchicago.edu>, November 2013


from instrument import Instrument
import visa
import types
import logging
import math
import time
import pyvisa

class Coherent_FieldMasterGS(Instrument):


    def __init__(self, name, address, reset=False):
        Instrument.__init__(self, name, tags=['physical'])

        self._address = address

        self.add_parameter('identification',
        flags=Instrument.FLAG_GET)

        self.add_parameter('power',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            units='W')

        self.add_parameter('detectortype',
            flags=Instrument.FLAG_GET,
            type=types.StringType)

        self.add_parameter('offsetval',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            units='W',docstring='Get actual offset value in Watts')


        self.add_parameter('wavelength',
            flags=Instrument.FLAG_GETSET,
            type=types.FloatType,
            units='m')

        self.add_parameter('attenuation',
            flags=Instrument.FLAG_GETSET,
            type=types.FloatType,
            minval=1)

        self.add_parameter('numavgs',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType,
            minval=1)

        self.add_parameter('offset',
            flags=Instrument.FLAG_SET,
            type=types.StringType,
            doc='''Offset on or off?''')




        self._open_serial_connection()
        if reset:
            self.reset()
        else:
            self.get_all()


    # Open serial connection
    def _open_serial_connection(self):
        logging.debug(__name__ + ' : Opening serial connection')

        self._visa = pyvisa.visa.SerialInstrument(self._address,
                baud_rate=9600, data_bits=8, stop_bits=1,
                parity=pyvisa.visa.no_parity, term_chars=pyvisa.visa.CR+pyvisa.visa.LF,
                send_end=False)

    # Close serial connection
    def _close_serial_connection(self):
        '''
        Closes the serial connection
        '''
        logging.debug(__name__ + ' : Closing serial connection')
        self._visa.close()
    def buffer_clear(self): #in case of buffer jamming
        while True:
            try:
                self._visa.read_raw()

            except(pyvisa.vpp43.visa_exceptions.VisaIOError):
                break

    def reset(self):
        self._visa.write('*rst')

    def get_all(self):
        self.get_detectortype()
        self.get_offsetval()
        self.get_attenuation()
        self.get_numavgs()
        self.get_wavelength()
        self.get_power()
        self.get_identification()

    def do_get_identification(self):
        self.buffer_clear()
        return self._visa.ask('*ind')


    def do_get_power(self):
        logging.debug(__name__ + 'reading power')
        self.buffer_clear()
        return self._visa.ask('pw?')

    def do_get_wavelength(self):
        logging.debug(__name__ + 'reading wavelength')
        self.buffer_clear()
        return float(self._visa.ask('wv?'))

    def do_set_wavelength(self, wavelength):
        logging.debug(__name__ + 'setting wavelength')
        self.buffer_clear()
        self._visa.write('wv %6e' % wavelength)

    def do_set_attenuation(self, at):
        logging.debug(__name__ + 'setting attenuation')
        self.buffer_clear()
        self._visa.write('at %d' % at)
        return
    def do_get_attenuation(self):
        self.buffer_clear()
        logging.debug(__name__ + 'getting attenuation')
        return float(self._visa.ask('at?'))

    def do_set_offset(self, offset):
        self.buffer_clear()
        if offset == 'on':
            self._visa.write('of on')
            logging.debug(__name__ + 'fieldmaster offset set to on')
            return
        elif offset == 'off':
            self._visa.write('of of')
            logging.debug(__name__ + 'fieldmaster offset set to off')
            return
        else:
            logging.error(__name__ + 'offset given not on or of/off')
            return -1

    def do_get_offsetval(self):
        self.buffer_clear()
        logging.debug(__name__+ 'getting offset value')
        return float(self._visa.ask('of?'))

    def do_set_numavgs(self, pa):
        self.buffer_clear()
        logging.debug(__name__+ 'setting number of averages')
        self._visa.write('pa %d' % pa)
        return
    def do_get_numavgs(self):
        self.buffer_clear()
        logging.debug(__name__ + 'getting number of averages')
        return int(self._visa.ask('pa?'))
    def do_get_detectortype(self):
        self.buffer_clear()
        logging.debug(__name__ + 'getting detector type')
        return self._visa.ask('dt?')