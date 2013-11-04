# ThorLabs_ITC4001.py class, to perform the communication between the Wrapper and the device
# David Christle, University of Chicago -- November, 2013

from instrument import Instrument
import visa
import types
import logging
import numpy

class ThorLabs_ITC4001(Instrument):

    def __init__(self, name, address=None, reset=False):
        
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
        self.add_parameter('temperature',
            flags=Instrument.FLAG_GETSET,
            units='C',
            minval=15, maxval=32,
            format='%.02f',
            type=types.FloatType)
        self.add_parameter('source_status',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType)
        self.add_parameter('TEC_status',
            flags=Instrument.FLAG_GETSET,
            type=types.IntType)

        self.add_function('reset')
        self.add_function ('get_all')



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
        self.get_temperature()
        self.get_source_status()
        self.get_TEC_status()

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
            amp (float) : power in ??

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

        logging.debug(__name__ + ' : set laser diode current source to status %d' % source_status)
        self._visainstrument.write('OUTP1:STATE %d' % source_status)
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
        return int(self._visainstrument.ask('OUTP1:STATE?'))

