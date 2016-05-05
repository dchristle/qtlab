# Laser driver for Toptica MOT/DL Pro option
# David Christle, September 2015 <christle@uchicago.edu>
#
# This is a driver for TOPTICA's DL Pro motorized control option. It relies on
# controlling a TMCL stepper motor inside that uses its own byte-packing-based
# communication protocol. Each command sent to the motor contains the motor
# address, the actual command, and a checksum. I took the code that does the
# encoding/decoding of these commands from Andreas Pohlmann's pyStepRocker
# module, since this will do the compacting and checksum verification. The rest
# of the methods I had to port over from the LabView code the best I could.
# In particular, I set the upper/lower wavelength range and other calibration
# parameters manually here for our laser, so these need to be changed if this driver
# is used for another laser. The read/calculate procedure is a little complicated
# for those parameters, so I chose to skip it.
#
# IMPORTANT: TO BE COMPATIBLE WITH TOPTICA'S CODE, IF YOU LOOK IN THE
# GENERATE/SEND COMMAND VI, FOR SOME REASON THE AUTHOR TAKES THE INTEGER
# 2 AND SUBTRACTS THE MOTOR NUMBER FROM IT. SO MOTOR 0 IN THE TOPTICA
# VI IS ACTUALLY MOTOR 2 IN THE TMCL CODE.

from instrument import Instrument
#import visa
import types
import logging
import numpy
import time
import qt
import numpy as np
import pyvisa
import struct
import serial

TMCL_OK_STATUS = {100, # successfully executed
                  101, # commanded loaded in memory
}
class Toptica_MOTDLPro(Instrument):

#----------------------------------------------
# Initialization
#----------------------------------------------

    def __init__(self, name, address, reset = False):

        Instrument.__init__(self, name, tags = ['physical'])

        self._address = address
        #self._visa = visa.instrument(self._address)

        self._STATUSCODES = { 100 : "Succesfully executed, no error",
                    101 : "Command loaded into TMCL program EEPROM",
                      1 : "Wrong Checksum",
                      2 : "Invalid command",
                      3 : "Wrong type",
                      4 : "Invalid value",
                      5 : "Configuration EEPROM locked",
                      6 : "Command not available" }

        self._STAT_OK = 100

        self._COMMAND_NUMBERS = {  1 : "ROR",    2 : "ROL",    3 : "MST",
                             4 : "MVP",    5 : "SAP",    6 : "GAP",
                             7 : "STAP",   8 : "RSAP",   9 : "SGP",
                            10 : "GGP",   11 : "STGP",  12 : "RSGP",
                            13 : "RFS",   14 : "SIO",   15 : "GIO",
                            19 : "CALC",  20 : "COMP",  21 : "JC",
                            22 : "JA",    23 : "CSUB",  24 : "RSUB",
                            25 : "EI",    26 : "DI",    27 : "WAIT",
                            28 : "STOP",  30 : "SCO",   31 : "GCO",
                            32 : "CCO",   33 : "CALCX", 34 : "AAP",
                            35 : "AGP",   37 : "VECT",  38 : "RETI",
                            39 : "ACO"
                          }

        self._NUMBER_COMMANDS = dict([(v, k) for k, v in self._COMMAND_NUMBERS.iteritems()])

        self.INTERRUPT_VECTORS = {  0 : "Timer 0",
                               1 : "Timer 1",
                               2 : "Timer 2",
                               3 : "Target position reached",
                              15 : "stallGuard",
                              21 : "Deviation",
                              27 : "Left stop switch",
                              28 : "Right stop switch",
                              39 : "Input change 0",
                              40 : "Input change 1",
                             255 : "Global interrupts" }

        self._CMD_MVP_TYPES = { 'ABS' : 0,
                          'REL' : 1,
                          'COORDS' : 2 }
        CMD_RFS_TYPES = { 'START' : 0,
                          'STOP' : 1,
                          'STATUS' : 2 }


        def apard(name, prange, acc):
            return { "name": name,
                     "range" : prange,
                     "access" : acc }

        TR_24s = [(-2**23+1, 2**23)]
        TR_32u = [(0, 2**32)]
        TR_32s = [(-2**31, 2**31)]
        TR_16u = [(0, 2**16)]
        TR_12s = [(-2**11+1, 2**11)]
        TR_12u = [(0, 2**12)]
        TR_11u = [(0, 2**11)]
        TR_10u = [(0, 2**10)]
        TR_8u = [(0, 2**8)]
        TR_7s = [(-2**6, 2**6)]
        TR_5u = [(0, 2**5)]
        TR_1u = [(0, 2**1)]
        TR_m3 = [(0, 3)]
        TR_m4 = [(0, 4)]
        TR_m9 = [(0, 9)]
        TR_m12 = [(0, 14)]
        TR_m14 = [(0, 14)]
        TR_m16 = [(0, 16)]

        TR_xCHP0 = [(-3, 13)]
        TR_xCHP1 = [(0, 1), (2, 16)]
        TR_xSE0 = [(1, 4)]
        TR_xRFS0 = [(1, 9)]
        TR_xRFS1 = [(0, 8388307)]
        TR_xPWR0 = [(1, 2**16)]
        TR_xRND0 = [(0, 2**31)]

        T_R = 4
        T_W = 2
        T_E = 1
        T_RW = T_R+T_W
        T_RWE = T_RW + T_E


        self._AXIS_PARAMETER = {   0 : ("target position", TR_24s, T_RW),
                             1 : ("actual position", TR_24s, T_RW),
                             2 : ("target speed", TR_12s, T_RW),
                             3 : ("actual speed", TR_12s, T_RW),
                             4 : ("max positioning speed", TR_11u, T_RWE),
                             5 : ("max acceleration", TR_11u, T_RWE),
                             6 : ("abs max current", TR_8u, T_RWE),
                             7 : ("standby current", TR_8u, T_RWE),
                             8 : ("target pos reached", TR_1u, T_R),
                             9 : ("ref switch status", TR_1u, T_R),
                            10 : ("right limit switch status", TR_1u, T_R),
                            11 : ("left limit switch status", TR_1u, T_R),
                            12 : ("right limit switch disable", TR_1u, T_RWE),
                            13 : ("left limit switch disable", TR_1u, T_RWE),
                           130 : ("minimum speed", TR_11u, T_RWE),
                           135 : ("actual acceleration", TR_11u, T_R),
                           138 : ("ramp mode", TR_m3, T_RWE),
                           140 : ("microstep resolution", TR_m9, T_RWE),
                           141 : ("ref switch tolerance", TR_12u, T_RW),
                           149 : ("soft stop flag", TR_1u, T_RWE),
                           153 : ("ramp divisor", TR_m14, T_RWE),
                           154 : ("pulse divisor", TR_m14, T_RWE),
                           160 : ("step interpolation enable", TR_1u, T_RW),
                           161 : ("double step enable", TR_1u, T_RW),
                           162 : ("chopper blank time", TR_m4, T_RW),
                           163 : ("chopper mode", TR_1u, T_RW),
                           164 : ("chopper hysteresis dec", TR_m4, T_RW),
                           165 : ("chopper hysteresis end", TR_xCHP0, T_RW),
                           166 : ("chopper hysteresis start", TR_m9, T_RW),
                           167 : ("chopper off time", TR_xCHP1, T_RW),
                           168 : ("smartEnergy min current", TR_1u, T_RW),
                           169 : ("smartEnergy current downstep", TR_m4, T_RW),
                           170 : ("smartEnergy hysteresis", TR_m16, T_RW),
                           171 : ("smartEnergy current upstep", TR_xSE0, T_RW),
                           172 : ("smartEnergy hysteresis start", TR_m16, T_RW),
                           173 : ("stallGuard2 filter enable", TR_1u, T_RW),
                           174 : ("stallGuard2 threshold", TR_7s, T_RW),
                           175 : ("slope control high side", TR_m4, T_RW),
                           176 : ("slope control low side", TR_m4, T_RW),
                           177 : ("short protection disable", TR_1u, T_RW),
                           178 : ("short detection timer", TR_m4, T_RW),
                           179 : ("Vsense", TR_1u, T_RW),
                           180 : ("smartEnergy actual current", TR_5u, T_RW),
                           181 : ("stop on stall", TR_11u, T_RW),
                           182 : ("smartEnergy threshold speed", TR_11u, T_RW),
                           183 : ("smartEnergy slow run current", TR_8u, T_RW),
                           193 : ("ref. search mode", TR_xRFS0, T_RWE),
                           194 : ("ref. search speed", TR_11u, T_RWE),
                           195 : ("ref. switch speed", TR_11u, T_RWE),
                           196 : ("distance end switches", TR_xRFS1, T_R),
                           204 : ("freewheeling", TR_16u, T_RWE),
                           206 : ("actual load value", TR_10u, T_R),
                           208 : ("TMC262 errorflags", TR_8u, T_R),
                           209 : ("encoder pos", TR_24s, T_RW),
                           210 : ("encoder prescaler", TR_16u, T_RWE), # that one isnt really correct
                           212 : ("encoder max deviation", TR_16u, T_RWE),
                           214 : ("power down delay", TR_xPWR0, T_RWE)
                        }

        self._SINGLE_AXIS_PARAMETERS = [140]+range(160, 184)



        self._GLOBAL_PARAMETER = { (0, 64) : ("EEPROM magic", TR_8u, T_RWE),
                             (0, 65) : ("RS485 baud rate", TR_m12, T_RWE),
                             (0, 66) : ("serial address", TR_8u, T_RWE),
                             (0, 73) : ("EEPROM lock flag", TR_1u, T_RWE),
                             (0, 75) : ("telegram pause time", TR_8u, T_RWE),
                             (0, 76) : ("serial host adress", TR_8u, T_RWE),
                             (0, 77) : ("auto start mode", TR_1u, T_RWE),
                             (0, 81) : ("TMCL code protect", TR_m4, T_RWE),
              #Wrong type?? #(0, 84) : ("coordinate storage", TR_1u, T_RWE),
                             (0, 128) : ("TMCL application status", TR_m3, T_R),
                             (0, 129) : ("download mode", TR_1u, T_R),
                             (0, 130) : ("TMCL program counter", TR_32u, T_R),
                             (0, 132) : ("tick timer", TR_32u, T_RW),
              #Wrong type?? #(0, 133) : ("random number", TR_xRND0, T_R),
                             (3, 0) : ("Timer0 period", TR_32u, T_RWE),
                             (3, 1) : ("Timer1 period", TR_32u, T_RWE),
                             (3, 2) : ("Timer2 period", TR_32u, T_RWE),
                             (3, 39) : ("Input0 edge type", TR_m4, T_RWE),
                             (3, 40) : ("Input0 edge type", TR_m4, T_RWE)
                           }
        # set the parameters exposed to the user
        self.add_parameter('wavelength',
            flags = Instrument.FLAG_GETSET,
            type = types.FloatType,
            units = 'nm',
            minval=1064.86, maxval=1144.51)
        self.add_parameter('position',
            flags = Instrument.FLAG_GETSET,
            type = types.IntType,
            units = 'step',
            minval=0, maxval=182215)
        self._target = 1
        self.add_function('reference_search')
        self.add_function('close_device')
        self.add_function('open_device')
        self.open_device()


    def open_device(self):
        # start the initialization of the TOPTICA MOT/DLPro.
        self._open_serial_connection()
        logging.debug(__name__ + ': Toptica Motor device opened.')
        self._tmcl_stop_application()
        self._init_dl_pro_parameters()
        self._dl_get_cal_data()
        self.reference_search() # for some reason, the reference search does not finish here in Python but it does in LabView, even for what I think are nominally the same command sequences.
        self.set_wavelength(1105.0)
        return



    def _instr_to_str(self, instr):
        """
        instr (buffer of 9 bytes)
        """
        target, n, typ, mot, val, chk = struct.unpack('>BBBBiB', instr)
        s = "%d, %d, %d, %d, %d (%d)" % (target, n, typ, mot, val, chk)
        return s


    def _reply_to_str(self, rep):
        """
        rep (buffer of 9 bytes)
        """
        ra, rt, status, rn, rval, chk = struct.unpack('>BBBBiB', rep)
        s = "%d, %d, %d, %d, %d (%d)" % (ra, rt, status, rn, rval, chk)
        return s
     # Open serial connection
    def _open_serial_connection(self):
        logging.debug(__name__ + ' : Opening serial connection')

        self._serial = serial.Serial(
                port=self._address,
                baudrate=9600,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1 )




    # Close serial connection
    def _close_serial_connection(self):
        '''
        Closes the serial connection
        '''
        logging.debug(__name__ + ' : Closing serial connection')

        self._serial.close()
        return

    def __del__(self):
        self.close_device()
        return

    def close_device(self):
        self._close_serial_connection()
        return

    def _tmcl_stop_application(self):
        #self.tmcl_w_crc(self.encodeRequestCommand(1, 128, 0, 0, 0, debug = False))    # stop any running TMCL application
        ret = self.SendInstruction(128,0,0,0)
        return ret

    def _init_dl_pro_parameters(self):
        self.set_sap_for_all_motors(4, 1000)    # set speed to 1000
        self.set_sap_for_all_motors(5, 100)     # set max accel to 100
        self.set_sap_for_all_motors(6, 42)      # set maxcurrentl to 250 - this is in units of 255 = 100%; I think the max current is 1.5 A so this is ~250 mA.
        self.set_sap_for_all_motors(7, 0)       # set standby current to 0
        self.set_sap_for_all_motors(12, 1)      # disable right limit switch
        self.set_sap_for_all_motors(13, 0)      # enable left limit switch
        self.set_sap_for_all_motors(140, 4)     # set microstep resolution to 16 microsteps (parameter value = 4)
        #self.set_sap_for_all_motors(143, 2)     # set rest current to approximately 12%
        self.set_sap_for_all_motors(153, 7)     # set ramp to 7
        self.set_sap_for_all_motors(154, 3)     # set pulse to 3
        self.set_sap_for_all_motors(194, 1000)  # set reference speed to 1000
        self.set_sap_for_all_motors(203, 100)   # set the mixed decay threshold to 100
        self.set_sap_for_all_motors(204, 30)    # set FreeWheelTime to 10

        for i in range(6):
            self.SendInstruction(14,i,0,0) # do an SIO command for type = 0 to 5 for motor 0, setting some digital output lines to 0
        return

    def _dl_get_cal_data(self):
        # this function could be expanded to actually read the calibration data from the module, but
        # it's quicker for me to hardcode in the retrieved values instead from the LabVIEW VI.
        self._restore_global_parameters()
        self._upper_wavelength_limit = 1144.51
        self._lower_wavelength_limit = 1064.86
        # p0, p1, and p2 are polynomial coefficients that convert wavelength in nm to motor step position
        self._p0 = -1.15278e6
        self._p1 = 64.5135
        self._p2 = 0.962788
        self._backlash = 5035
        return

    def convert_step_to_wavelength(self, step):
        # here we just use the correct root of the quadratic formula to invert the calibration relation
        wavelength = (-self._p1 + np.sqrt((self._p1*self._p1) - 4.0*self._p2*(self._p0 - float(step))))/(2*self._p2)
        if wavelength > self._upper_wavelength_limit or wavelength < self._lower_wavelength_limit:
            logging.error(__name__ + ': step conversion indicates that our step is outside the allowed wavelength range!')
        return wavelength

    def convert_wavelength_to_step(self, wavelength):
        step = self._p0 + self._p1*wavelength + self._p2*wavelength*wavelength
        if wavelength > self._upper_wavelength_limit or wavelength < self._lower_wavelength_limit:
            logging.error(__name__ + ': wavelength conversion indicates that our wavelength is outside the allowed wavelength range!')
        return int(step)
    def _restore_global_parameters(self):
        for i in range(34):
            ret = self.SendInstruction(12,20+i,0,0)
            ret = self.SendInstruction(10,20+i,0,0)

        return
    def reference_search(self):

        self.SendInstruction(13,0,0,0) # starts the reference search
        time_start = time.time()

        while (time.time()-time_start < 45.0):
            time.sleep(1)
            ret = self.SendInstruction(13,2,0,0)
            if ret == 0:
                # a return value of 0 indicates the reference search has completed
                logging.debug(__name__ + ': reference search completed successfully.')
                break



            # if the reference search status returns a value other than 0, the search is still ongoing
        if time.time()-time_start >= 45.0:
            logging.warning(__name__ +': reference search on initialization did not finish before timeout.')
            # this condition indicates that we probably stopped the while loop, so we abort the reference search
            ret = self.SendInstruction(13,2,0,0) # aborts the reference search

        return
    def do_set_position(self,step):
        self.move_and_wait(step)
        return

    def do_get_position(self):
        return self.get_current_position()

    def do_set_wavelength(self, wavelength):
        # first calculate the step position we want to get to
        desired_step = self.convert_wavelength_to_step(wavelength)
        # now retrieve the current step position
        current_step = self.get_current_position()
        if current_step > desired_step:
            # if we make a movement to the left, set the desired step
            # to beyond by the "backlash" calibration parameter
            desired_step = desired_step - self._backlash
        self.move_and_wait(desired_step)
        return

    def do_get_wavelength(self):
        # retrieve the current step position
        current_step = self.get_current_position()
        # convert it to wavelength
        current_wavelength = self.convert_step_to_wavelength(current_step)
        return current_wavelength

    def get_current_position(self):
        ret = self.SendInstruction(6,1,0,0)
        return ret
    def high_precision_move(self, step, direction = 1):
        if direction == 1:
            if step > 10000:
                self.set_position(step-10000)
            else:
                self.set_position(0)

            self.set_position(step)
        elif direction == 0:
            if step < 172000:
                self.set_position(step+10000)
            else:
                self.set_position(182000)

            self.set_position(step)
        else:
            logging.warning(__name__ + ': improper direction argument to high_precision_move function of the MOTDL. Doing standard move to position.')
            self.set_position(step)
        return

    def move_and_wait(self,step):
        self.move_to_position(step)
        self.wait_for_position(step)
        return

    def move_to_position(self, step):
        if step > 800000:
            step = 800000
            logging.error(__name__ + ': step had to be coerced to 800000.')
        if step < 0:
            step = 0
            logging.error(__name__ + ': step had to be coerced to 0.')

        ret = self.SendInstruction(4,0,0,int(step))
        time.sleep(0.005)
        return
    def wait_for_position(self, step):
        if step > 800000:
            step = 800000
            logging.error(__name__ + ': step had to be coerced to 800000.')
        if step < 0:
            step = 0
            logging.error(__name__ + ': step had to be coerced to 0.')
        time_start = time.time()
        while (time.time() - time_start < 120.0):
            ret = self.SendInstruction(6,1,0,step)
            if ret == step:
                break
            time.sleep(2.0)
        if (time.time() - time_start > 120.0):
            logging.error(__name__ + ': timed out while waiting for position move.')
            return False
        return

    def set_sap_for_all_motors(self, sap_type, sap_value):
        for i in range(3):
            self.SendInstruction(5,sap_type,int(i),sap_value)



    def SendInstruction(self, n, typ=0, mot=0, val=0):
            """
            Sends one instruction, and return the reply.
            n (0<=int<=255): instruction ID
            typ (0<=int<=255): instruction type
            mot (0<=int<=255): motor/bank number
            val (0<=int<2**32): value to send
            return (0<=int<2**32): value of the reply (if status is good)
            raises:
                IOError: if problem with sending/receiving data over the serial port
                TMCLError: if status if bad
            """
            # IMPORTANT: TO BE COMPATIBLE WITH TOPTICA'S CODE, IF YOU LOOK IN THE
            # GENERATE/SEND COMMAND VI, FOR SOME REASON THE AUTHOR TAKES THE INTEGER
            # 2 AND SUBTRACTS THE MOTOR NUMBER FROM IT. SO MOTOR 0 IN THE TOPTICA
            # VI IS ACTUALLY MOTOR 2 IN THE TMCL CODE.
            mot = 2-mot
            # REMOVE THE ABOVE LINE TO MAKE IT COMPATIBLE WITH OTHER TMCL SYSTEMS
            msg = numpy.empty(9, dtype=numpy.uint8)
            struct.pack_into('>BBBBiB', msg, 0, self._target, n, typ, mot, val, 0)
            # compute the checksum (just the sum of all the bytes)
            msg[-1] = numpy.sum(msg[:-1], dtype=numpy.uint8)

            self._serial.write(msg)
            self._serial.flush()

            while True:
                res = self._serial.read(9)
                if len(res) < 9: # TODO: TimeoutError?
                    logging.warning("Received only %d bytes after %s, will fail the instruction",
                                    len(res), self._instr_to_str(msg))
                    raise IOError("Received only %d bytes after %s" %
                                  (len(res), self._instr_to_str(msg)))
                logging.debug("Received %s", self._reply_to_str(res))
                ra, rt, status, rn, rval, chk = struct.unpack('>BBBBiB', res)

                # Check it's a valid message
                npres = numpy.frombuffer(res, dtype=numpy.uint8)
                good_chk = numpy.sum(npres[:-1], dtype=numpy.uint8)
                if chk == good_chk:
                    if self._target != 0 and self._target != rt:  # 0 means 'any device'
                        logging.warning("Received a message from %d while expected %d",
                                        rt, self._target)
                    if rn != n:
                        logging.info("Skipping a message about instruction %d (waiting for %d)",
                                     rn, n)
                        continue
                    if status not in TMCL_OK_STATUS:
                        raise TMCLError(status, rval, self._instr_to_str(msg))
                else:
                    # TODO: investigate more why once in a while (~1/1000 msg)
                    # the message is garbled
                    logging.warning("Message checksum incorrect (%d), will assume it's all fine", chk)

                return rval

    def encodeRequestCommand(self, m_address, n_command, n_type, n_motor, value, debug=False):
        # convert to bytes
        m_address = int(m_address) % (1<<8)
        n_command = int(n_command) % (1<<8)
        n_type = int(n_type) % (1<<8)
        n_motor = int(n_motor) % (1<<8)
        value = [(int(value) >> i*8) % (1<<8) for i in range(3,-1,-1)]
        # generate command
        checksum = (m_address + n_command + n_type + n_motor + sum(value)) % (1<<8)
        tmcl_bytes = [m_address, n_command, n_type, n_motor] + value + [checksum]
        tmcl_cmd = sum(b << (8-i)*8 for i,b in enumerate(tmcl_bytes))
        if debug:
            print "{0:0>18X}".format(tmcl_cmd), "".join([chr(b) for b in tmcl_bytes])
        return "".join([chr(b) for b in tmcl_bytes])

    def encodeReplyCommand(self, r_address, m_address, status, n_command, value, debug=False):
        # convert to bytes
        r_address = int(r_address) % (1<<8)
        m_address = int(m_address) % (1<<8)
        status = int(status) % (1<<8)
        n_command = int(n_command) % (1<<8)
        value = [(int(value) >> i*8) % (1<<8) for i in range(3,-1,-1)]
        # generate command
        checksum = (r_address + m_address + status + n_command + sum(value)) % (1<<8)
        tmcl_bytes = [r_address, m_address, status, n_command] + value + [checksum]
        tmcl_cmd = sum(b << (8-i)*8 for i,b in enumerate(tmcl_bytes))
        if debug:
            print "{0:0>18X}".format(tmcl_cmd), "".join([chr(b) for b in tmcl_bytes])
        return "".join([chr(b) for b in tmcl_bytes])

    def decodeRequestCommand(self, cmd_string):
        byte_array = bytearray(cmd_string)
        if len(byte_array) != 9:
            print 'Length of byte array received is %d' % len(byte_array)
            raise TMCLError("Command string shorter than 9 bytes")
            ret = {}
            ret['value'] = -1
            #self.buffer_clear()
            return ret
        if byte_array[8] != sum(byte_array[:8]) % (1<<8):
            print 'checksum error'
            raise TMCLError("Checksum error in command %s" % cmd_string)
        ret = {}
        ret['module-address'] = byte_array[0]
        ret['command-number'] = byte_array[1]
        ret['type-number'] = byte_array[2]
        ret['motor-number'] = byte_array[3]
        ret['value'] = sum(b << (3-i)*8 for i,b in enumerate(byte_array[4:8]))
        ret['checksum'] = byte_array[8]


        return ret

    def decodeReplyCommand(self, cmd_string):
        byte_array = bytearray(cmd_string)
        if len(byte_array) != 9:
            print 'Length of byte array received is %d' % len(byte_array)
            raise TMCLError("Commandstring shorter than 9 bytes")
        if byte_array[8] != sum(byte_array[:8]) % (1<<8):
            raise TMCLError("Checksum error in command %s" % cmd_string)
        ret = {}
        ret['reply-address'] = byte_array[0]
        ret['module-address'] = byte_array[1]
        ret['status'] = byte_array[2]
        ret['command-number'] = byte_array[3]
        ret['value'] = sum(b << (3-i)*8 for i,b in enumerate(byte_array[4:8]))
        ret['checksum'] = byte_array[8]
        return ret

class TMCLError(Exception):
    pass


