from instrument import Instrument
import visa
import types
import logging
import numpy
import time

class NewfocusVelocity(Instrument):
    '''
    This is the python driver for the Newfocus Velocity 6300

    Usage:
    Initialize with
    <name> = instruments.create('name', 'NewfocusVelocity', address='<GPIB address>')
    '''

    def __init__(self, name, address, reset=False):
        '''
        Initializes the Newfocus Laser.

        Input:
            name (string)    : name of the instrument
            address (string) : GPIB address

        Output:
            None
        '''
        logging.info(__name__ + ' : Initializing instrument')
        Instrument.__init__(self, name, tags=['physical'])

        self._address = address
        self._visainstrument = visa.instrument(self._address)

    def get_diode_temperature(self):
        logging.debug(__name__ + ' : reading diode temperature from instrument')
        return float(self._visainstrument.ask(':TEMP?'))

    def set_diode_temperature(self, temperature):
        logging.debug(__name__ + ' : setting diode temperature to %s C' % temperature)
        self._visainstrument.write(':TEMP %e' % temperature)

    def get_diode_current(self):
        logging.debug(__name__ + ' : reading diode current from instrument')
        return float(self._visainstrument.ask(':CURR?'))

    def set_diode_current(self, current):
        logging.debug(__name__ + ' : setting diode current to %s mA' % current)
        self._visainstrument.write(':CURR %e' % current)

    def get_piezo_voltage(self):
        logging.debug(__name__ + ' : reading piezo voltage from instrument')
        return float(self._visainstrument.ask(':VOLT?'))

    def set_piezo_voltage(self,voltage):
        logging.debug(__name__ + ' : setting piezo voltage to %s V' % voltage)
        self._visainstrument.write(':VOLT %e' % voltage)

    def get_wavelength(self):
        logging.debug(__name__ + ' : reading wavelength from instrument')
        return float(self._visainstrument.ask(':WAVE?'))

    def set_wavelength(self, wavelength):
        logging.debug(__name__ + ' : setting wavelength to %s nm' % wavelength)
        self._visainstrument.write(':WAVE %e' % wavelength)
        while self._visainstrument.ask('*OPC?') != '1':
            time.sleep(0.1)
        self._visainstrument.write(':OUTP:TRAC OFF')

    def set_power_level(self,power):
        logging.debug(__name__ + ' : setting power to %s mW' % power)
        self._visainstrument.write(':POW %e' % power)

    def get_power_level(self):
        logging.debug(__name__ + ' : reading power level from instrument')
        return float(self._visainstrument.ask(':SENS:POW:FRON ?'))

    def set_ready_mode(self):
        logging.debug(__name__ + ' : setting device to ready mode')
        self._visainstrument.write(':OUTP:TRAC OFF')

    def get_output(self):
        logging.debug(__name__ + ' : reading status from instrument')
        stat = self._visainstrument.ask(':OUTP ?')

        if stat == '1':
            return 'on'
        elif stat == '0':
            return 'off'
        else:
            raise ValueError('Output status not specified : %s' % stat)

    def set_output(self,status):
        logging.debug(__name__ + ' : setting output to "%s"' % status)
        if status.upper() in ('ON', 'OFF'):
            status = status.upper()
        else:
            raise ValueError('set_output(): can only set on or off')
        self._visainstrument.write(':OUTP %s' % status)

    def set_wavelength_input(self,status):
        logging.debug(__name__ + ' : setting wavelength input mode to "%s"' % status)
        if status.upper() in ('ON', 'OFF'):
            status = status.upper()
        else:
            raise ValueError('set_wavelength_input(): can only set on or off')
        self._visainstrument.write(':SYST:WINP %s' % status)

    def set_constant_power_mode(self,status):
        logging.debug(__name__ + ' : setting constant power mode to "%s"' % status)
        if status.upper() in ('ON', 'OFF'):
            status = status.upper()
        else:
            raise ValueError('set_constant_power_mode(): can only set on or off')
        self._visainstrument.write(':CPOW %s' % status)

