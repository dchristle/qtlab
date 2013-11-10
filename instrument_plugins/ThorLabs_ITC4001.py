# ThorLabs_ITC4001.py class, to perform the communication between the Wrapper and the device
# David Christle, University of Chicago -- November, 2013

from instrument import Instrument
import visa
import types
import logging
import numpy
import qt

class ThorLabs_ITC4001(Instrument):

    def __init__(self, name, address='USB0::0x1313::0x804A::M00277475::INSTR', reset=False):

        '''
        Initializes the ThorLabs_ITC4001, and communicates with the wrapper.

        Input:
            name (string)    : name of the instrument
            address (string) : USB address
            reset (bool)     : resets to default values, default=false

        Output:
            None
        '''

        Instrument.__init__(self, name, tags=['physical'])

        logging.info(__name__ + ' : Initializing instrument ThorLabs_ITC4001')

        self._address = address
        self._visainstrument = visa.instrument(self._address)
        Instrument.__init__(self, name, tags=['physical'])


        self.add_parameter('current',
            flags=Instrument.FLAG_GETSET,
            units='A',
            minval=0, maxval=0.672,
            type=types.FloatType)
        self.add_parameter('temperatureSP',
            flags=Instrument.FLAG_GETSET,
            units='C',
            minval=15, maxval=32,
            type=types.FloatType)
        self.add_parameter('source_status',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType)
        self.add_parameter('TEC_status',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType)
        self.add_parameter('temperature',
            units='C',format='%.2f',
            flags=Instrument.FLAG_GET,
            type=types.FloatType)

        self.add_function('reset')
        self.add_function('get_all')



        if address == None:
            raise ValueError('ThorLabs ITC4001 requires an address parameter')
        else:
            print 'ThorLabs_ITC4001 address %s' % address

        if reset:
            self.reset()
        else:
            self.get_all()

    def reset(self):
        '''
        Resets the instrument to default values

        Input:
            None

        Output:
            None
        '''
        logging.info(__name__ + ' : resetting instrument')
        self._visainstrument.write('*RST')
        self.get_all()

    def get_all(self):
        '''
        Reads all implemented parameters from the instrument,
        and updates the wrapper.

        Input:
            None

        Output:
            None
        '''
        logging.info(__name__ + ' : get all')
        self.get_current()
        self.get_source_status()
        self.get_TEC_status()
        self.get_temperature()
        self.get_temperatureSP()

    def do_get_current(self):
        '''
        Reads the current from the instrument

        Input:
            None

        Output:
            cur (float) : current set point
        '''
        logging.debug(__name__ + ' : get laser diode current setpoint')
        return float(self._visainstrument.ask('SOUR:CURR:AMPL?'))

    def do_set_current(self, cur):
        '''
        Set the current to the laser diode

        Input:
            cur (float) : current setpoint

        Output:
            None
        '''
        logging.debug(__name__ + ' : set laser diode current to to %f amps' % cur)
        self._visainstrument.write('SOUR:CURR:AMPL %s' % cur)

    def do_get_source_status(self):
        '''
        Reads status of current source ON/OFF from the driver

        Input:
            None

        Output:
            status (integer) : 0 or 1
        '''
        logging.debug(__name__ + ' : get source status')
        return int(self._visainstrument.ask('OUTP1:STATE?'))

    def do_set_source_status(self, source_status):
        '''
        Sets status of current source ON/OFF from the driver

        Input:
            source_status (integer) : 0 or 1

        Output:
            None
        '''
        # Check if TEC is on before enabling laser
        current_TEC_status = self.do_get_TEC_status()
        if current_TEC_status == 0:
            logging.error(__name__ + 'current source could not be set -- TEC is off. TEC status: %s' % current_TEC_status)
            return -1
        elif current_TEC_status == 1:
            logging.debug(__name__ + ' : set laser diode current source to status %d' % source_status)
            self._visainstrument.write('OUTP1:STATE %d' % source_status)
            return 0
        else:
            logging.error(__name__ + 'unknown TEC status!')
            return -2
    def do_set_TEC_status(self, TEC_status):
        '''
        Sets status of current source ON/OFF from the driver

        Input:
            TEC_status (integer) : 0 or 1

        Output:
            None
        '''

        logging.debug(__name__ + ' : set laser diode TEC to status %d' % TEC_status)
        self._visainstrument.write('OUTP2:STATE %d' % TEC_status)
    def do_get_TEC_status(self):
        '''
        Reads status of current source ON/OFF from the driver

        Input:
            None

        Output:
            TEC_status (integer) : 0 or 1
        '''
        logging.debug(__name__ + ' : get laser diode TEC status')
        return int(self._visainstrument.ask('OUTP2:STATE?'))

    def do_set_temperatureSP(self, temperature):
        '''
        Sets temperature setpoint of the TEC

        Input:
            temperature (float) : setpoint temperature in C

        Output:
            None
        '''

        logging.debug(__name__ + ' : set laser diode TEC to temperature setpoint %d' % temperature)
        self._visainstrument.write('SOUR2:TEMP:SPO %d' % temperature)
    def do_get_temperatureSP(self):
        '''
        Gets temperature setpoint of the TEC

        Input:
            None

        Output:
            temperature (float) : setpoint temperature in C
        '''

        logging.debug(__name__ + ' : getting laser TEC setpoint')
        return float(self._visainstrument.ask('SOUR2:TEMP:SPO?'))
    def do_get_temperature(self):
        '''
        Reads actual temperature of the laser diode

        Input:
            None

        Output:
            temperature (float) : actual temperature in C
        '''
        logging.debug(__name__ + ' : get actual temperature of laser diode')
        return float(self._visainstrument.ask('MEAS:TEMP?'))

    # Now add some shortcut functions

    def on(self):
        tol = 0.15 # This is the tolerance in C we wait to achieve
        logging.debug(__name__ + 'turning laser on using shortcut on function')
        self.set_TEC_status(1)
        tempSP = self.do_get_temperatureSP()
        qt.msleep(1)
        total_time = 0
        within = 0
        while within < 3: # Achieve tolerance for three seconds
            current_temp = self.do_get_temperature()
            ## print 'Current temp %s' % current_temp
            if abs(current_temp-tempSP) < tol:
                within = within + 1
            else:
                within = 0
            qt.msleep(1)
            total_time = total_time + 1
            if total_time > 20:
                logging.error(__name__ + 'did not achieve setpoint within 20 s, breaking')
                break

        # now set the laser on

        if total_time < 20:
            self.set_source_status(1)
            total_time = 0
            within = 0
            while within < 5: # Achieve tolerance for 5 seconds
                current_temp = self.do_get_temperature()
                ## print 'Current temp %s' % current_temp
                if abs(current_temp-tempSP) < tol:
                  within = within + 1
                else:
                 within = 0
                qt.msleep(1)
                total_time = total_time + 1
                if total_time > 20:
                  logging.error(__name__ + 'did not achieve setpoint within 20 s, breaking')
                  self.set_source_status(0)
                  qt.msleep(5)
                  self.set_TEC_status(0)
                  break

        return

    def off(self):
        logging.debug(__name__ + 'turning laser off using shortcut off function')
        self.set_source_status(0)
        qt.msleep(5)
        self.set_TEC_status(0)
        return


