# Coherent_FieldMasterGS, FieldMaster GS laser power meter driver
# David Christle <christle@uchicago.edu>, November 2013


from instrument import Instrument
import qt
import visa
import types
import logging
import math
import time
import pyvisa

class Pololu_MicroMaestro(Instrument):


    def __init__(self, name, address, reset=False):
        Instrument.__init__(self, name, tags=['physical'])

        self._address = address
        self._channels = (0, 1, 2, 3, 4, 5)


        self.add_parameter('target',
            flags=Instrument.FLAG_SET | Instrument.FLAG_SOFTGET,
            type=types.FloatType,
            units='us',
            channels = self._channels)

        self.add_parameter('speed',
            flags=Instrument.FLAG_SET | Instrument.FLAG_SOFTGET,
            type=types.FloatType,
            units='0.25us/10ms',
            channels = self._channels)

        self.add_parameter('acceleration',
            flags=Instrument.FLAG_SET | Instrument.FLAG_SOFTGET,
            type=types.FloatType,
            units='(0.25 us)/(10 ms)/(80 ms)',
            channels = self._channels)

        self.add_parameter('position',
            flags=Instrument.FLAG_GET,
            type=types.FloatType,
            units='us',
            channels = self._channels)

        self.add_parameter('crc',
            flags=Instrument.FLAG_GET,
            type=types.BooleanType)


        self.add_function('crc7')
        self.add_function('byte_crc7')
        self.add_function('home')

        self.add_function('buffer_clear')


        self.CRC7_POLY = 0x91
        self._crcon = False

        self._open_serial_connection()
##        if reset:
##            self.reset()
##        else:
##            self.get_all()


    # Open serial connection
    def _open_serial_connection(self):
        logging.debug(__name__ + ' : Opening serial connection')
        
        qt.rm.open_resource(self._address)
        self._visa =  qt.rm.get_instrument(self._address)
        self._visa.baud_rate = long(19200)
        self._visa.data_bits = 8
        self._visa.stop_bits = 1
        self._visa.read_termination = '\r\n'
        self._visa.write_termination = '\r\n'
#        self._visa = pyvisa.visa.SerialInstrument(self._address,
#                baud_rate=19200, data_bits=8, stop_bits=1,
#                parity=pyvisa.visa.no_parity,term_chars=pyvisa.visa.CR+pyvisa.visa.LF,
#                timeout=2)


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




    def byte_crc7(self, v):
        # from the Charon project
        for i in range(8):
            if v & 1:
                v ^= self.CRC7_POLY
            v >>= 1
        return v

    def crc7(self, data):
        # from the Charon project
        self.CRC7_TABLE = tuple( self.byte_crc7(i) for i in range(256) )
        if isinstance(data, basestring):
            data = ( ord(c) for c in data )
        crc = 0
        for c in data:
            crc = self.CRC7_TABLE[crc ^ c]
        return crc

    def do_set_crc(self, crcon):
        self._crcon = crcon
        return
    def do_get_crc(self):
        return self._crcon

    def get_all(self):
        return

    def home(self):
        logging.debug(__name__ + ' re-homing all servos')
        thestring = "\xAA\x0C\x22"
        if self._crcon:
            thestring = thestring + chr(self.crc7(thestring))
        self._visa.write(bytes(thestring,encoding='ascii'))

    def do_set_speed(self, speed, channel):
        logging.debug(__name__ + ' setting speed')
        byte1_string = int(hex(int(speed)),16) & 0x7F
        byte2_string = (int(hex(int(speed)),16) >> 7) & 0x7F
        thestring = "\xAA\x0C\x07" + chr(int(channel)) + chr(byte1_string) + chr(byte2_string)
        if self._crcon:
            thestring = thestring + chr(self.crc7(thestring))
        self._visa.write(bytes(thestring),encoding='ascii')

    def do_set_acceleration(self, accel, channel):
        logging.debug(__name__ + ' setting acceleration')
        byte1_string = int(hex(int(accel)),16) & 0x7F
        byte2_string = (int(hex(int(accel)),16) >> 7) & 0x7F
        thestring = "\xAA\x0C\x09" + chr(int(channel)) + chr(byte1_string) + chr(byte2_string)
        if self._crcon:
            thestring = thestring + chr(self.crc7(thestring))
        self._visa.write(bytes(thestring),encoding='ascii')


    def do_set_target(self, target, channel):
        overshoot_pos = target - 16
        logging.debug(__name__ + ' setting target position')
        byte1_string = int(hex(int(4*overshoot_pos)),16) & 0x7F
        byte2_string = (int(hex(int(4*overshoot_pos)),16) >> 7) & 0x7F
        thestring = "\xAA\x0C\x04" + chr(int(channel)) + chr(byte1_string) + chr(byte2_string)
        if self._crcon:
            thestring = thestring + chr(self.crc7(thestring))
        self._visa.write(bytes(thestring),encoding='ascii')
        time.sleep(1.0)
        byte1_string = int(hex(int(4*target)),16) & 0x7F
        byte2_string = (int(hex(int(4*target)),16) >> 7) & 0x7F
        thestring = "\xAA\x0C\x04" + chr(int(channel)) + chr(byte1_string) + chr(byte2_string)
        if self._crcon:
            thestring = thestring + chr(self.crc7(thestring))
        self._visa.write(thestring)

    def do_get_position(self, channel):
        logging.debug(__name__ + ' getting position')

        thestring = chr(0xaa) + chr(0xc) + chr(0x10) + chr(int(channel))
        print 'send %r' % thestring
        self._visa.write(thestring)
        time.sleep(0.1)
        return self._visa.read()

