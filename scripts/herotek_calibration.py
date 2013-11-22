# Herotek Diode Calibration
# David Christle <christle@uchicago.edu>, 2013
#
#

import numpy
from time import time,sleep
import os
import qt
import logging
import msvcrt


def ht_calibrate(f_vec, p_vec):
    '''
    this example is based on 'measure_module.py'
    you will need to set up a vector of frequencies and then call the
    measurment script.

    To run the function type in the terminal:

    fv = numpy.arange(1e9,2e9,50e6)
    esr_meas.simple(fv,power,TC)
    '''


    n63 = qt.instruments['NIDAQ6363']
    pxi = qt.instruments['pxi']

    qt.mstart()

    data = qt.Data(name='herotek_calibration')
    data.add_coordinate('Frequency, NI_RFSG [GHz]')
    data.add_coordinate('Power, NI_RFSG [dBm]')
    data.add_value('Analog Input (V)')
    data.create_file()

    p2d = qt.Plot2D(data, 'bO',
    name = 'Herotek',
    clear = True,
    coorddim = 1,
    valdim = 2,
    maxtraces = 1)

    p3d = qt.Plot3D(data, name='measure3D', coorddims=(0,1), valdim=2, style='image')

    pxi.set_power(-50)
    pxi.set_frequency(1e9)
    pxi.set_status('on')
    for f in f_vec:
        pxi.set_frequency(f)
        logging.debug('frequency set: %s GHz' % (f*1e-9))
        if (msvcrt.kbhit() and (msvcrt.getch() == 'q')): break
        for p in p_vec:
            pxi.set_power(p)
            qt.msleep(0.1)
            logging.debug(__name__ + 'power set to: %s dBm' % (p))
            tot = 0
            Navg = 128
            for i in numpy.arange(0,Navg):
                tot = tot + n63.get_ai0()
                qt.msleep(0.01)
            meas_v = tot/Navg
            data.add_data_point(f,p,meas_v)
        data.new_block()
        p3d.update()



    pxi.set_status('off')
    data.close_file()
    qt.mend()
