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
            units = 'mA',
            minval=0.0,maxval=316.0)

        self.add_parameter('tec_current',
            flags = Instrument.FLAG_GETSET,
            type = types.FloatType,
            units = 'mA')

        self.add_parameter('t_loop',
            flags = Instrument.FLAG_GETSET,
            type = types.BooleanType)

        self.add_parameter('pgain',
            flags = Instrument.FLAG_GETSET,
            type = types.FloatType)

        self.add_parameter('igain',
            flags = Instrument.FLAG_GETSET,
            type = types.FloatType)

        self.add_parameter('dgain',
            flags = Instrument.FLAG_GETSET,
            type = types.FloatType)

        self.add_parameter('feedforward',
            flags = Instrument.FLAG_GETSET,
            type = types.BooleanType)

        self.add_parameter('feedforward_factor',
            flags = Instrument.FLAG_GETSET,
            type = types.FloatType,
            units = 'mA/V')

        self.add_parameter('display_auto_dark',
            flags = Instrument.FLAG_GETSET,
            type = types.BooleanType)

        self.add_parameter('piezo',
            flags = Instrument.FLAG_GETSET,
            type = types.BooleanType)

        self.add_parameter('piezo_voltage',
            flags = Instrument.FLAG_GETSET,
            type = types.FloatType,
            units = 'V',
            minval=0.0, maxval=99.0)

        self.add_parameter('idle_timeout',
            flags = Instrument.FLAG_GETSET,
            type = types.IntType,
            units = 's',
            minval = 0 )

        self.add_parameter('current',
            flags = Instrument.FLAG_GETSET,
            type = types.FloatType,
            units = 'mA',
            minval=0.0,maxval=316.0)

        self.add_parameter('temperature_setpoint',
            flags = Instrument.FLAG_GETSET,
            type = types.FloatType,
            units = 'C',
            minval=6.0,maxval=40.0)

        self.add_parameter('temperature',
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
        self.query('(exec \'buzzer:play \"ABCDEFG HIJKLMNO    EEEEEEEEEEEEEEEEEEEEEE  LLLLLLLLLLLLLLLLLLLLLLLL LLLLLL JJJJJJ HHHHHH GGGGGG GGGGGGGGGGGGGGGGGGGG HHHHHH EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE QQQQQQ OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO EEEEEE HHHHHH EEEEEEEEEEEEEEEEEEEEEE  LLLLLLLLLLLLLLLLLLLLLLLL LLLLLL JJJJJJ HHHHHH GGGGGG GGGGGGGGGGGGGGGGGGGG HHHHHH EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE\")')
        return
    def set_buzzer_welcome(self):
        self.query('(exec \'buzzer:welcome \"ABCDEFG HIJKLMNO    EEEEEEEEEEEEEEEEEEEEEE  LLLLLLLLLLLLLLLLLLLLLLLL LLLLLL JJJJJJ HHHHHH GGGGGG GGGGGGGGGGGGGGGGGGGG HHHHHH EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE QQQQQQ OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO\")')
        return
    def on(self):
        ret = self.query('(param-set! \'laser1:dl:cc:enabled #t)')
        if ret == '\n0\r':
            return True
        else:
            logging.error(__name__ + ': turn laser on returned string:%r' % ret)
            return False
    def off(self):
        ret = self.query('(param-set! \'laser1:dl:cc:enabled #f)')
        if ret == '\n0\r':
            return True
        else:
            logging.error(__name__ + ': turn laser off returned string:%r' % ret)
            return False
    def do_get_emission(self):
        ret = self.query('(param-ref \'laser1:dl:cc:enabled)')
        return ret

    def do_set_current(self, current):
        ret = self.query(('(param-set! \'laser1:dl:cc:current-set %.3f)' % current))
        if ret == '\n0\r':
            return True
        else:
            logging.error(__name__ + ': set current returned string:%r' % ret)
            return False
    def do_get_current(self):
        ret = self.query('(param-ref \'laser1:dl:cc:current-set)')
        return float(ret)

    def do_set_current_limit(self, current):
        ret = self.query(('(param-set! \'laser1:dl:cc:current-clip %.3f)' % current))
        if ret == '\n0\r':
            return True
        else:
            logging.error(__name__ + ': set current limit returned string:%r' % ret)
            return False
    def do_get_current_limit(self):
        ret = self.query('(param-ref \'laser1:dl:cc:current-clip)')
        return float(ret)

    def do_get_temperature_setpoint(self):
        ret = self.query('(param-ref \'laser1:dl:tc:temp-set)')
        return float(ret)

    def do_set_temperature_setpoint(self, temperature):
        ret = self.query(('(param-set! \'laser1:dl:tc:temp-set %.3f)' % temperature))
        if ret == '\n0\r':
            return True
        else:
            logging.error(__name__ + ': set temperature setpoint returned string:%r' % ret)
            return False

    def do_get_temperature(self):
        ret = self.query('(param-ref \'laser1:dl:tc:temp-act)')
        return float(ret)

    def do_set_display_auto_dark(self, setting):

        if setting == True:
            set_string = '#t'
        elif setting == False:
            set_string = '#f'
        else:
            logging.error(__name__ + ': received improper set string when trying to set auto-dark.')
            set_string = '#f'
        ret = self.query(('(param-set! \'display:auto-dark %s)' % set_string))
        if ret == '\n0\r':
            return True
        else:
            logging.error(__name__ + ': set display autodark returned string:%r' % ret)
            return False
    def do_get_display_auto_dark(self):

        ret = self.query(('(param-ref \'display:auto-dark)'))

        if ret == '\n#t\r':
            return True
        elif ret == '\n#f\r':
            return False
        else:
            logging.error(__name__ + (': received unknown reply %s from get_display_auto_dark' % ret))
            return
    def do_set_idle_timeout(self, setting):

        ret = self.query(('(param-set! \'display:idle-timeout %d)' % setting))
        if ret == '\n0\r':
            return True
        else:
            logging.error(__name__ + ': set idle timeout returned string:%r' % ret)
            return False
    def do_get_idle_timeout(self):

        ret = self.query(('(param-ref \'display:idle-timeout)'))
        return int(ret)

    def do_set_feedforward(self, setting):

        if setting == True:
            set_string = '#t'
        elif setting == False:
            set_string = '#f'
        else:
            logging.error(__name__ + ': received improper set string when trying to set feedforward enabled/disabled.')
            set_string = '#f'
        ret = self.query(('(param-set! \'laser1:dl:cc:feedforward-enabled %s)' % set_string))
        if ret == '\n0\r':
            return True
        else:
            logging.error(__name__ + ': set feedforward returned string:%r' % ret)
            return False
    def do_get_feedforward(self):

        ret = self.query(('(param-ref \'laser1:dl:cc:feedforward-enabled)'))

        if ret == '\n#t\r':
            return True
        elif ret == '\n#f\r':
            return False
        else:
            logging.error(__name__ + (': received unknown reply %s from get_feedforward' % ret))
            return

    def do_set_feedforward_factor(self, ff):
        ret = self.query(('(param-set! \'laser1:dl:cc:feedforward-factor %.3f)' % ff))
        if ret == '\n0\r':
            return True
        else:
            logging.error(__name__ + ': set feedforward factor string:%r' % ret)
            return False
    def do_get_feedforward_factor(self):
        ret = self.query('(param-ref \'laser1:dl:cc:feedforward-factor)')
        return float(ret)

    def do_set_t_loop(self, setting):

        if setting == True:
            set_string = '#t'
        elif setting == False:
            set_string = '#f'
        else:
            logging.error(__name__ + ': received improper set string when trying to set temperature PID loop enabled/disabled.')
            set_string = '#f'
        ret = self.query(('(param-set! \'laser1:dl:tc:enabled %s)' % set_string))
        if ret == '\n0\r':
            return True
        else:
            logging.error(__name__ + ': set temperature PID loop returned string:%r' % ret)
            return False
    def do_get_t_loop(self):

        ret = self.query(('(param-ref \'laser1:dl:tc:enabled)'))

        if ret == '\n#t\r':
            return True
        elif ret == '\n#f\r':
            return False
        else:
            logging.error(__name__ + (': received unknown reply %s from get_t_loop' % ret))
            return

    def do_set_pgain(self, current):
        ret = self.query(('(param-set! \'laser1:dl:tc:t-loop:p-gain %.3f)' % current))
        if ret == '\n0\r':
            return True
        else:
            logging.error(__name__ + ': set p gain returned string:%r' % ret)
            return False

    def do_get_pgain(self):
        ret = self.query('(param-ref \'laser1:dl:tc:t-loop:p-gain)')
        return float(ret)

    def do_set_igain(self, current):
        ret = self.query(('(param-set! \'laser1:dl:tc:t-loop:i-gain %.3f)' % current))
        if ret == '\n0\r':
            return True
        else:
            logging.error(__name__ + ': set i gain returned string:%r' % ret)
            return False
    def do_get_igain(self):
        ret = self.query('(param-ref \'laser1:dl:tc:t-loop:i-gain)')
        return float(ret)

    def do_set_dgain(self, current):
        ret = self.query(('(param-set! \'laser1:dl:tc:t-loop:d-gain %.3f)' % current))
        if ret == '\n0\r':
            return True
        else:
            logging.error(__name__ + ': set d gain returned string:%r' % ret)
            return False
    def do_get_dgain(self):
        ret = self.query('(param-ref \'laser1:dl:tc:t-loop:d-gain)')
        return float(ret)

    def do_set_tec_current(self, current):
        ret = self.query(('(param-set! \'laser1:dl:tc:current-set %.3f)' % current))
        if ret == '\n0\r':
            return True
        else:
            logging.error(__name__ + ': set TEC current returned string:%r' % ret)
            return False
    def do_get_tec_current(self):
        ret = self.query('(param-ref \'laser1:dl:tc:current-act)')
        return float(ret)

    def do_set_piezo(self, setting):

        if setting == True:
            set_string = '#t'
        elif setting == False:
            set_string = '#f'
        else:
            logging.error(__name__ + ': received improper set string when trying to set piezo enabled/disabled.')
            set_string = '#f'
        ret = self.query(('(param-set! \'laser1:dl:pc:enabled %s)' % set_string))
        if ret == '\n0\r':
            return True
        else:
            logging.error(__name__ + ': set feedforward returned string:%r' % ret)
            return False
    def do_get_piezo(self):

        ret = self.query(('(param-ref \'laser1:dl:pc:enabled)'))

        if ret == '\n#t\r':
            return True
        elif ret == '\n#f\r':
            return False
        else:
            logging.error(__name__ + (': received unknown reply %s from get_piezo' % ret))
            return

    def do_set_piezo_voltage(self, ff):
        ret = self.query(('(param-set! \'laser1:dl:pc:voltage-set %.3f)' % ff))
        if ret == '\n0\r':
            return True
        else:
            logging.error(__name__ + ': set piezo voltage string:%r' % ret)
            return False

    def do_get_piezo_voltage(self):
        ret = self.query('(param-ref \'laser1:dl:pc:voltage-set)')
        return float(ret)



    def get_all(self):
        return


