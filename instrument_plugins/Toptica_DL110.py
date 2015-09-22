# Toptica_DL110 driver
# 
# Gabriele de Boo <g.deboo@student.unsw.edu.au>
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
import types
import logging
import numpy
import socket
from time import sleep

class Toptica_DL110(Instrument):
    '''
    This is the driver for the Toptica DigiLock 110

    Usage:
    Initialize with
    <name> = instruments.create('<name>', 'Toptica_DL110', 
                                ipaddress='<IP address>',
                                port='<TCP port>')
    '''

    def __init__(self, name, ipaddress, port=60001, reset=False):
        '''
        Input:
          name (string)    : name of the instrument
          ipaddress (string) : IP address
          port  (integer)    : TCP port
        '''
        logging.info(__name__ + ' : Initializing instrument Toptica_DL110')
        Instrument.__init__(self, name, tags=['physical'])

        # Add some global constants
        self._HOST = ipaddress
        self._PORT = port
        
        self.add_parameter('piezo_offset',
                        flags=Instrument.FLAG_GETSET, 
                        units='V', 
                        minval=0, maxval=70, 
                        type=types.FloatType,
                        maxstep=1.0, stepdelay=50)
        self.add_parameter('pid1_gain',
                        flags=Instrument.FLAG_GET,
                        type=types.FloatType,
                        )
        self.add_parameter('pid1_differential_gain',
                        flags=Instrument.FLAG_GET,
                        type=types.FloatType,
                        )
        self.add_parameter('pid1_input',
                        flags=Instrument.FLAG_GET,
                        type=types.StringType,
                        )
        self.add_parameter('pid1_integral',
                        flags=Instrument.FLAG_GET,
                        type=types.FloatType,
                        )
        self.add_parameter('pid1_differential',
                        flags=Instrument.FLAG_GET,
                        type=types.FloatType,
                        )
        # scan block
        self.add_parameter('scan_enabled',
                        flags=Instrument.FLAG_GETSET,
                        type=types.BooleanType,
                        )
        self.add_parameter('scan_amplitude',
                        flags=Instrument.FLAG_GETSET,
                        type=types.FloatType,
                        )
        self.add_parameter('scan_frequency',
                        flags=Instrument.FLAG_GETSET,
                        type=types.FloatType,
                        )
        self.add_parameter('scan_output',
                        flags=Instrument.FLAG_GET,
                        type=types.StringType,
                        )
        self.add_parameter('scan_signal_type',
                        flags=Instrument.FLAG_GETSET,
                        type=types.StringType,
                        option_list=('triangle',
                                    'square',
                                    'sine',
                                    'sawtooth')
                        )

        self.add_function ('get_all')
        self.get_all()

#    def reset(self):
#        '''
#        Resets the instrument to default values
#
#        Input:
#            None
#
#        Output:
#            None
#        '''
#        logging.info(__name__ + ' : resetting instrument')
#        self.get_all()

    def get_all(self):
        '''
        Reads all implemented parameters from the instrument,
        and updates the wrapper.

        Input:
            None

        Output:
            None
        '''
        self.get_piezo_offset()
        self.get_pid1_gain()
        self.get_pid1_differential_gain()
        self.get_pid1_input()
        self.get_pid1_integral()
        self.get_pid1_differential()
        self.get_scan_enabled()
        self.get_scan_amplitude()
        self.get_scan_frequency()
        self.get_scan_output()
        self.get_scan_signal_type()
        logging.info(__name__ + ' : get all')

    def do_get_piezo_offset(self):
        '''Get the piezo voltage'''
        logging.debug(__name__ + ' Getting the piezo voltage.')
        response = self.query('offset:value?')
        return float(response.lstrip('offset:value='))

    def do_set_piezo_offset(self, voltage):
        '''Set the piezo voltage'''
        logging.debug(__name__ + ' Setting the piezo voltage to %.3f' 
                        % voltage)
        response = self.query('offset:value=%.3f' % voltage)

    def do_get_pid1_gain(self):
        '''Get the gain of PID1'''
        logging.debug(__name__ + ' Getting the gain of PID1')
        response = self.query('pid1:gain?')
        return float(response.lstrip('pid1:gain='))

    def do_get_pid1_differential_gain(self):
        '''Get the gain of PID1'''
        logging.debug(__name__ + ' Getting the differential gain of PID1')
        response = self.query('pid1:differential?')
        return float(response.lstrip('pid1:differential='))

    def do_get_pid1_input(self):
        '''Get the input of PID1'''
        logging.debug(__name__ + ' Getting the input of PID1')
        response = self.query('pid1:input?')
        return response.lstrip('pid1:input=')

    def do_get_pid1_integral(self):
        '''Get the integral term of PID1'''
        logging.debug(__name__ + ' Getting the integral term of PID1')
        response = self.query('pid1:integral?')
        return float(response.lstrip('pid1:integral='))

    def do_get_pid1_differential(self):
        '''Get the differential term of PID1'''
        logging.debug(__name__ + ' Getting the differential term of PID1')
        response = self.query('pid1:differential?')
        return float(response.lstrip('pid1:differential='))

    def do_get_scan_enabled(self):
        '''Get whether the scan is enabled or not'''
        logging.debug(__name__ + ' Getting scan enabled')
        response = self.query('scan:enable?').lstrip('scan:enable=')
        if response == 'false':
            return False
        elif response == 'true':
            return True
        else:
            logging.warning('Unexpected response to scan:enable? : %s' % response)

    def do_set_scan_enabled(self, enabled):
        '''Set the scan enabled to True or False'''
        if enabled:
            response = self.query('scan:enable=true')
        else:
            response = self.query('scan:enable=false')

    def do_get_scan_amplitude(self):
        '''Get the scan amplitude'''
        logging.debug(__name__ + ' Getting the scan amplitude')
        response = self.query('scan:amplitude?').lstrip('scan:amplitude=')
        return float(response)

    def do_set_scan_amplitude(self, amplitude):
        '''Set the scan amplitude'''
        logging.debug(__name__ + ' Setting the scan amplitude to %.3f V' %
                        amplitude)
        response = self.query('scan:amplitude=%.3f' % amplitude)

    def do_get_scan_frequency(self):
        '''Get the scan frequency'''
        logging.debug(__name__ + ' Getting the scan frequency')
        response = self.query('scan:frequency?').lstrip('scan:frequency=')
        return float(response)

    def do_set_scan_frequency(self, frequency):
        '''Set the scan frequency'''
        logging.debug(__name__ + ' Setting the scan frequency to %.1f Hz'
                        % frequency)
        response = self.query('scan:frequency=%.3f' % frequency)

    def do_get_scan_output(self):
        '''Get the scan output destination'''
        logging.debug(__name__ + ' Getting the scan output destination')
        response = self.query('scan:output?').lstrip('scan:output=')
        return response

    def do_get_scan_signal_type(self):
        '''Get the scan signal type'''
        logging.debug(__name__ + ' Getting the scan signal type')
        response = self.query('scan:signal type?').lstrip('scan:signal type')
        return response[1:]

    def do_set_scan_signal_type(self, signal_type):
        '''Set the scan signal type'''
        logging.debug(__name__ + ' Setting the scan signal type to %s' %
                                signal_type)
        response = self.query('scan:signal type=%s' % signal_type)

    def query(self, command):
        '''
        Query the controller
        '''
        termination = '\r\n> '
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Connect to server
            self.sock.connect((self._HOST, self._PORT))
            # send data to the server
            welcome_message = self.sock.recv(1024)

            self.sock.sendall(command + "\r\n")
            # Receive data from the server and shut down
            echo = self.sock.recv(1024)
            received = self.sock.recv(1024)
        finally:
            self.sock.close()
        return received.rstrip(termination)

        
