import qt
import msvcrt
import numpy
import math
##import analysis.lib.fitting.fit as fit
##import analysis.lib.fitting.common

def fit_knife_simple(g_a, g_x0, g_w, g_b, *arg):
    """
    fits a knife edge function,
        y(x) = a/2 * (1-erf(sqrt(2)*(x-x0)/w)) + b

    Initial guesses, in this order:
        g_a : amplitude
        g_x0 : center position
        g_w : beam waist
        g_b : background


    """
    fitfunc_str = "a/2 * (1-erf(sqrt(2)*(x-x0)/w)) + b"

    a = fit.Parameter(g_a, 'a')
    x0 = fit.Parameter(g_x0, 'x0')
    w = fit.Parameter(g_w, 'w')
    b = fit.Parameter(g_b, 'b')
    # tau = fit.Parameter(g_tau, 'tau')
    p0 = [a, x0, w, b]

    def fitfunc(x) :
        return a()/2 * (1 - math.erf(math.sqrt(2)*(x()-x0())/w())) + b()
    return p0, fitfunc, fitfunc_str
# end damped rabi

def meas_BW(min_pos, max_pos, steps):


#generate list of steps
    x_list = numpy.linspace(min_pos, max_pos, steps)

    ins_xps = qt.instruments['xps']
    ins_fm = qt.instruments['fm']


    # create data object
    qt.mstart()

    qt.msleep(0.2)


    d = qt.Data(name='BeamWaist')
    d.add_coordinate('displacement (mm)')
    d.add_value('power')
    d.create_file()
    filename=d.get_filepath()[:-4]

    plot2d = qt.Plot2D(d, name='beammeasure')
    stop_scan = False
    for i,cur_x in enumerate(x_list):

        if (msvcrt.kbhit() and (msvcrt.getch() == 'q')): stop_scan=True
        ins_xps.set_abs_positionZ(float(-1*cur_x))

        qt.msleep(0.05)
        result = ins_fm.get_power()
        d.add_data_point(cur_x, result)

        if stop_scan: break


    ins_xps.set_abs_positionZ(-1*min_pos)
##    knife_fit = fit.fit1d(x_list, result,fit_knife_simple, 3.3e-3,
##                    0, p[i], sigma, do_print=False,ret=True)
    d.close_file()
    plot2d.save_png(filename+'.png')

    qt.mend()

##    fit_result = fit.fit1d(p, cr,common.fit_gauss, array(cr).min(),
##                    array(cr).max(), 1, 0.1, do_print=False,ret=True)
##    return fit_result
