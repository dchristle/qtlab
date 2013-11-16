# Newport Fast Steering Mirror via DAQ instrument driver
#
# David Christle <christle@uchicago.edu>, Nov. 2013
# The purpose of this code is to provide an interface between the Qtlab and
# the voltages written to the FSM-300 controller via the NI DAQ analog out.
# What occurs here is that one can specify an X,Y position pair, and the code
# will output a sequence of voltages to the FSM to bring the FSM to that position
# on the sample, after using a calibration that relates the output voltage to
# the position on the surface of the sample.
#
# The reason this isn't just done by directly writing the desired voltage is
# because the FSM will change too quickly and backlash because of the momentum.
# By writing this code, it will step in a particular pattern.

from instrument import Instrument
import types

class dummy_positioner(Instrument):

    def __init__(self, name, channels=3):
        Instrument.__init__(self, name, tags=['positioner'])

        # Instrument parameters
        self.add_parameter('position',
            type=types.TupleType,
            flags=Instrument.FLAG_GET,
            format='%.03f, %.03f, %.03f')
        self.add_parameter('speed',
            type=types.TupleType,
            flags=Instrument.FLAG_SET|Instrument.FLAG_SOFTGET,
            format='%.1f, %.01f, %.01f')
        self.add_parameter('channels',
            type=types.IntType,
            flags=Instrument.FLAG_SET|Instrument.FLAG_SOFTGET)

        self.set_channels(channels)

        # Instrument functions
        self.add_function('start')
        self.add_function('stop')
        self.add_function('move_abs')

    def do_get_position(self, query=True):
        return [0, 0, 0]

    def do_set_channels(self, val):
        return True

    def do_set_speed(self, val):
        print 'Setting speed to %r' % (val, )

    def start(self):
        print 'Starting'

    def stop(self):
        print 'Stopping'

    def step(self, chan, nsteps):
        print 'Stepping channel %d by %d' % (chan, nsteps)

    def move_abs(self, pos, **kwargs):
        print 'Moving to %r' % (pos, )
