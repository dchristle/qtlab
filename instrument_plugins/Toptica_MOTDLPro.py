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

from instrument import Instrument
import visa
import types
import logging
import numpy
import time
import qt
import pyvisa

class TMCLError(Exception):
    pass


class TOPTICA_MOTDLPro(Instrument):

#----------------------------------------------
# Initialization
#----------------------------------------------

    def __init__(self, name, address, reset = False):

        Instrument.__init__(self, name, tags = ['physical'])

        self._address = address
        self._visa = visa.instrument(self._address)

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
##        # add general purpose registers
##        for b, p, a in zip([2]*256, range(256), ([T_RWE]*56)+([T_RW]*200)):
##            GLOBAL_PARAMETER[(2, p)] = ("general purpose reg#{0:0>3d}".format(p), TR_32s, a)


     # Open serial connection
    def _open_serial_connection(self):
        logging.debug(__name__ + ' : Opening serial connection')

        self._visa = pyvisa.visa.SerialInstrument(self._address,
                baud_rate=9600, data_bits=8, stop_bits=1,
                parity=pyvisa.visa.no_parity, term_chars=pyvisa.visa.LF,
                send_end=True,timeout=10)


    # Close serial connection
    def _close_serial_connection(self):
        '''
        Closes the serial connection
        '''
        logging.debug(__name__ + ' : Closing serial connection')
        self._visa.close()
    def init_dl_pro_parameters(self):
        self.set_sap_for_all_motors(4, 1000)    # set speed to 1000
        self.set_sap_for_all_motors(5, 100)     # set max accel to 100
        self.set_sap_for_all_motors(6, 42)      # set maxcurrentl to 250 - this is in units of 255 = 100%; I think the max current is 1.5 A so this is ~250 mA.
        self.set_sap_for_all_motors(7, 0)       # set standby current to 0
        self.set_sap_for_all_motors(12, 1)      # disable right limit switch
        self.set_sap_for_all_motors(13, 0)      # enable left limit switch
        self.set_sap_for_all_motors(140, 4)     # set microstep resolution to 16 microsteps (parameter value = 4)
        self.set_sap_for_all_motors(143, 1)     # set rest current to approximately 12%
        return
    def set_sap_for_all_motors(self, sap_type, sap_value):
        # this method sets the axis parameter for motors 0, 1, and 2, although it
        # seems like only motor 0 is used later by the MOT/DL.
        for i in range(3):
            self.tmcl_w_crc(self.encodeRequestCommand(1, 5, sap_type, int(i), sap_value, debug = False))

    def tmcl_w_crc(self,command):
        self._visa.write(command)
        ret = pyvisa.vpp43.read(self._visa.vi, 9)
        ret_decode = self.decodeReplyCommand(ret)
        return


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
            raise TMCLError("Commandstring shorter than 9 bytes")
        if byte_array[8] != sum(byte_array[:8]) % (1<<8):
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



