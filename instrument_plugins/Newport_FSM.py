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
import logging
import time
import qt
import math
import numpy as np



class Newport_FSM(Instrument):

    def __init__(self, name, channels=2):
        Instrument.__init__(self, name, tags=['positioner'])
        # Import the DAQ as an instrument object to write to.
        self._ni63 = qt.instruments['NIDAQ6363']
        # Store related constants for the FSM here; the only important
        # ones are the micron_per_volt conversion, which is calibrated somewhat
        # infrequently, and the min_v and max_v. These min/max voltages should
        # be hardcoded to +-10 V, since (c.f. the manual) these limits are the
        # full-scale movement of the device on its command inputs.

        self.fsm_dimensions = {
                'X' : {
                    'micron_per_volt' : 9.324,
                    'min_v' : -10.,
                    'max_v' : 10,
                    'default' : 0.,
                    'origin' : 0.,
                    'ao_function' : 'set_ao0',
                    'ao_read_function' : 'get_ao0',
                    'ao_channel' : 'ao0'
                    },
                'Y' : {
                    'micron_per_volt' : 9.3,
                    'min_v' : -10.,
                    'max_v' : 10,
                    'default' : 0.,
                    'origin' : 0.,
                    'ao_function' : 'set_ao1',
                    'ao_read_function' : 'get_ao1',
                    'ao_channel' : 'ao1'
                    },
                }
        # Instrument parameters
        self.add_parameter('abs_position',
            type=types.FloatType,
            channels=('X', 'Y'),
            flags=Instrument.FLAG_SET|Instrument.FLAG_SOFTGET,
            units='um',
            format='%.04f')
        self.add_parameter('speed',
            type=types.TupleType,
            units='V/s',
            flags=Instrument.FLAG_SET|Instrument.FLAG_SOFTGET,
            format='%.1f, %.01f')

        # Instrument functions
        self.add_function('zero')





    def do_set_speed(self, val):
        print 'Setting speed to %r' % (val, )

    def start(self):
        print 'Starting'

    def stop(self):
        print 'Stopping'

    def step(self, chan, nsteps):
        print 'Stepping channel %d by %d' % (chan, nsteps)

    def convert_um_to_V(self, x_um, channel):
        # Just do the micron-to-volt conversion using the hardcoded constants
        x_volts = (x_um-self.fsm_dimensions[channel]['origin']) *(
        1/self.fsm_dimensions[channel]['micron_per_volt'])
        return x_volts

    def convert_V_to_um(self, x_V, channel):
        # Just do the micron-to-volt conversion using the hardcoded constants
        x_um = x_V*self.fsm_dimensions[channel]['micron_per_volt']+self.fsm_dimensions[channel]['origin']
        return x_um

    def do_get_abs_position(self, channel):
        # This function is only a *soft* get, meaning using the FSM in LabView,
        # for example with the 2D scanner, will not properly update the value
        # read by this function.
        #
        # For now, translating between LabView and QtLab will involve just taking
        # the absolute position from LabView and setting the FSM to this position
        # using the set_abs_position function.
        getao_func = getattr(self._ni63, self.fsm_dimensions[channel]['ao_read_function'])
        current_V = getao_func()
        return convert_V_to_um(current_V, channel)

    def do_set_abs_position(self, x_um, channel):
        # Convert to volts first
        x_volts = self.convert_um_to_V(x_um, channel)
        # Check if voltage is in bounds, then set

        if (x_volts >= self.fsm_dimensions[channel]['min_v'] and
            x_volts <= self.fsm_dimensions[channel]['max_v']):

            local_AO_function = getattr(self._ni63, self.fsm_dimensions[channel]['ao_function'])
            result = local_AO_function(x_volts)
            #print 'Moving to %r at %s V' % (x_um, x_volts)
            return 0
        else:
            print 'Could not set position -- voltage bounds exceeded -- V was: %s' % x_volts
            logging.debug(__name__ + 'voltage bounds exceeded')
            return -1

    def simple_sweep_um(self, x_um_array, rate, channel):
        # This is a crude sweep that just uses repeated software calls. This is
        # in contrast to a hardware-controlled sweep that loads the points and
        # then writes them using hardware timing.
        for x_c in x_um_array:
            self.do_set_abs_position(x_c, channel)
            time.sleep(1.0/float(rate))
        return

    def simple_sweep_V(self, x_V_array, rate, channel):
        # This is a crude sweep that just uses repeated software calls. This is
        # in contrast to a hardware-controlled sweep that loads the points and
        # then writes them using hardware timing.
        for x_V in x_V_array:
            x_c = self.convert_V_to_um(x_V, channel)
            self.do_set_abs_position(x_c, channel)
            time.sleep(1.0/float(rate))
        return

    def sweep_and_count(self, x_um_array, rate, ctr, term, channel):
        # Set the terminal of the corresponding counter to the desired terminal
        funcname = ('set_' + ctr + '_src')
        getattr(self._ni63, funcname)(term)
        prev_count_time = self._ni63.get_count_time()
        self._ni63.set_count_time(1.0/rate)
        # Create voltage array by doing the conversion
        x_V_array = self.convert_um_to_V(x_um_array, channel)
        # Execute write and count function with raw voltage values

        carray = self._ni63.write_and_count(x_V_array,
            self.fsm_dimensions[channel]['ao_channel'],ctr)
        self._ni63.set_count_time(prev_count_time)
        return carray

    def AO_smooth(self, x_init, x_final, channel):
        # Use a cosine function to interpolate between two positions
        ao_smooth_rate = 50000.0 # Hz
        ao_smooth_steps_per_volt = 1000.0 # 1000 steps per Volt of movement
        # Convert initial and final positions to volts
        v_init = self.convert_um_to_V(x_init, channel)
        v_final = self.convert_um_to_V(x_final, channel)
        # Compute the number of steps we're going to use
        n_steps = math.ceil(np.abs((v_final-v_init))*ao_smooth_steps_per_volt)
        # Create the array of voltage points
        v_array = v_init*np.ones(n_steps) + (v_final-v_init)*(1.0-np.cos(np.linspace(0.0,np.pi,n_steps)))/2.0
        # Now write the array to the appropriate DAQ channel
        return self._ni63.writearray(v_array, ao_smooth_rate, -10.0, 10.0,
                10.0, self.fsm_dimensions[channel]['ao_channel'])


    def zero(self):
        # Zero out both FSM voltages.
        self.set_abs_positionX(self.convert_V_to_um(0, 'X'))
        self.set_abs_positionY(self.convert_V_to_um(0, 'Y'))

        return

