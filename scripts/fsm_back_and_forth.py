# FSM Sweep back and forth script
# David Christle <christle@uchicago.edu>, 2013
#
# This script just sweeps the FSM back and forth. The FSM should already be
# intialized as a Qt instrument.
#

import time
import logging
import qt
import numpy
import msvcrt

def main():
    channel = 'X' # This can be 'X' or 'Y' channels
    min_position = -10 # Volts
    max_position = 10 # Volts
    rate = 100 # number of points written per second to DAQ
    density = 100 # number of points across the full scale range
    wait = 1 # Wait time before sweeping back in seconds

    x_V_array_f = numpy.linspace(min_position,max_position,density)
    x_V_array_b = numpy.linspace(max_position,min_position,density)
    fsm = qt.instruments['fsm']

    while 1:
        if (msvcrt.kbhit() and (msvcrt.getch() == 'q')): break
        print 'Sweeping %s forward...' % channel
        fsm.simple_sweep_V(x_V_array_f,rate,channel)
        time.sleep(wait)
        if (msvcrt.kbhit() and (msvcrt.getch() == 'q')): break
        print 'Sweeping %s backward...' % channel
        fsm.simple_sweep_V(x_V_array_b,rate,channel)
        time.sleep(wait)


    f_string = 'set_abs_position' + channel
    # Create function that corresponds to the abs_position set function of
    # the correct channel, then call it to reset the voltage to 0.
    reset_channel = getattr(fsm, f_string)
    reset_channel(0.0)
    return

if __name__ == '__main__':
    main()
