# AMS CMAX 410 driver
# David Christle <christle@uchicago.edu>, August 2014


from instrument import Instrument
import visa
import types
import logging
import math
import time
import pyvisa
import re

class AMS_CMAX410(Instrument):


    def __init__(self, name, address, reset=False):
        Instrument.__init__(self, name, tags=['physical'])

        self._address = address



        self.add_parameter('position',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType,
            units='step')
        self.add_parameter('encoder',
            flags=Instrument.FLAG_SET|Instrument.FLAG_SOFTGET,
            type=types.IntType,
            units='step')
        self.add_parameter('initial_velocity',
            flags=Instrument.FLAG_SET|Instrument.FLAG_SOFTGET,
            type=types.IntType,
            units='step')
        self.add_parameter('slew_velocity',
            flags=Instrument.FLAG_SET|Instrument.FLAG_SOFTGET,
            type=types.IntType,
            units='step')
        self.add_parameter('actual_position',
            flags=Instrument.FLAG_GET,
            type=types.IntType,
            units='step')
        self.add_parameter('deadband',
            flags=Instrument.FLAG_SET|Instrument.FLAG_SOFTGET,
            type=types.IntType,
            units='step')

##        self.add_parameter('actual_position',
##            flags=Instrument.FLAG_GET,
##            type=types.IntType,
##            units='step')


##        self.add_function('origin')
##        self.add_function('encoder')

        self.add_function('buffer_clear')




        self._open_serial_connection()
        self.initialize()
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
    def initialize(self):
        # Need to read the CMAX info upon connection.
        time.sleep(1.0)
        self._visa.write(' ')
        time.sleep(1.0)
        navail = pyvisa.vpp43.get_attribute(self._visa.vi, pyvisa.vpp43.VI_ATTR_ASRL_AVAIL_NUM)
        if navail > 0:

            reply = pyvisa.vpp43.read(self._visa.vi, navail)
            self._cmaxinfo = reply
            print 'cmax info: %s' % reply

        # search for multiple axis (need to implement still)
        return


    def reset(self):
        #self._visa.write('*rst')
        time.sleep(3) # Sleep to avoid trying to talk to the device too quickly
        return

    def get_all(self):
##        self.get_detectortype()
##        self.get_offsetval()
##        self.get_attenuation()
##        self.get_numavgs()
##        self.get_wavelength()
##        self.get_power()
##        self.get_identification()
        return




    def do_get_actual_position(self):
        logging.debug(__name__ + ' getting actual position')
        reply = self._visa.ask('z')
        regex_match = re.search(r'\d+',reply)
        print 'reply is %r' % reply
        return int(regex_match.group())
    def set_and_wait(self, position):
        # set position and wait for movement to stop before releasing
        self.do_set_position(position)
        time.sleep(1)
        finished_move = False
        t0 = time.time()
        while finished_move == False and time.time() - t0 < 120.0:
            move_status = self.get_moving_status()
            if move_status == 0:
                finished_move = True
                break
        return

    def do_set_position(self, position):
        logging.debug(__name__ + ' setting position')
        self.buffer_clear()
        self._visa.write('R %d' % position)
        print 'reply is %s' % self._visa.read()
        return
    def do_get_position(self):
        logging.debug(__name__ + ' setting position')
        self.buffer_clear()
        reply = self._visa.ask('Z')
        regex_match = re.search(r'\d+',reply)
        print 'reply is %r' % reply
        return int(regex_match.group())

    def do_set_encoder(self, encoder):
        logging.debug(__name__ + ' setting encoder')
        self.buffer_clear()
        self._visa.write('e %d' % encoder)
        print 'reply is %s' % self._visa.read()
        return
    def do_set_initial_velocity(self, velocity):
        logging.debug(__name__ + ' setting initial velocity')
        self.buffer_clear()
        self._visa.write('I %d' % velocity)
        print 'reply is %s' % self._visa.read()
        return
    def do_set_slew_velocity(self, velocity):
        logging.debug(__name__ + ' setting slew velocity')
        self.buffer_clear()
        self._visa.write('V %d' % velocity)
        print 'reply is %s' % self._visa.read()
        return
    def save(self):
        logging.debug(__name__ + ' saving settings to nonvolatile memory')
        self.buffer_clear()
        reply = self._visa.ask('S')
        if reply == 'S':
            return
        else:
            raise ValueError('Did not return correct echo from save settings command')
        return
    def get_moving_status(self):
        logging.debug(__name__ + ' getting moving status')
        self.buffer_clear()

        reply = self._visa.ask('^')
        regex_match = re.search(r'\d+',reply)
        msint = int(regex_match.group())
        if msint == 1:
            return True
        elif msint == 0:
            return False
        else:
            raise ValueError('Unknown response from get CMAX moving status command')
        return
    def do_set_deadband(self, deadband):
        logging.debug(__name__ + ' setting deadband')
        self.buffer_clear()
        self._visa.write('d %d' % deadband)
        print 'reply is %s' % self._visa.read()
        return


