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
        self._channels = self._get_number_of_channels()
        Instrument.__init__(self, name, tags=['measure', 'example'])

         # Add some global constants
        self._address = address
        self._visainstrument = visa.instrument(self._address)

        self.add_parameter('current',
            flags=Instrument.FLAG_GETSET, units='dBm', minval=-135, maxval=16, type=types.FloatType)
        self.add_parameter('temperature',
            flags=Instrument.FLAG_GETSET, units='rad', minval=-numpy.pi, maxval=numpy.pi, type=types.FloatType)
        self.add_parameter('status',
            flags=Instrument.FLAG_GETSET, type=types.StringType)

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
        self.get_status()

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
    def do_get_value1(self):
        return self._dummy_value1

    def do_get_value2(self):
        return self._dummy_value2

    def do_set_output1(self, val):
        self._dummy_output1 = val

    def do_get_status(self):
        return self._dummy_status

    def do_set_status(self, val):
        self._dummy_status = val

    def do_get_speed(self):
        return self._dummy_speed

    def do_set_speed(self, val):
        self._dummy_speed = val

    def do_get_input(self, channel):
        return self._dummy_input[channel-1]

    def do_get_output(self, channel):
        return self._dummy_output[channel]

    def do_set_output(self, val, channel, times2=False):
        if times2:
            val *= 2
        self._dummy_output[channel] = val

    def do_set_gain(self, val):
        self._dummy_gain = val

    def step(self, channel, stepsize=0.1):
        '''Step channel <channel>'''
        print 'Stepping channel %s by %f' % (channel, stepsize)
        cur = self.get('ch%s_output' % channel, query=False)
        self.set('ch%s_output' % channel, cur + stepsize)

