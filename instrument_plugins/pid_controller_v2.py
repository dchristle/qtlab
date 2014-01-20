import os
import types
import gobject
import time
#import threading

import numpy
from scipy import integrate

import qt
from instrument import Instrument
from data import Data
from lib import config


class pid_controller_v2(Instrument):

    def __init__(self, name, set_ctrl_func=None, get_val_func=None,
            get_ctrl_func=None, get_stabilizor_func=None, **kw):
        
        Instrument.__init__(self, name)

        self._set_ctrl = set_ctrl_func
        self._get_val = get_val_func

        self.add_parameter('control_parameter',
                type=types.FloatType,
                minval=kw.get('ctrl_minval', -3.),
                maxval=kw.get('ctrl_maxval', +3.),
                flags=Instrument.FLAG_GETSET)
        
        self.add_parameter('value',
                type=types.FloatType,
                flags=Instrument.FLAG_GET)

        self.add_parameter('is_running',
                type=types.BooleanType,
                flags=Instrument.FLAG_GETSET)
                
        self.add_parameter('setpoint',
                type=types.FloatType,
                flags=Instrument.FLAG_GETSET)

        self.add_parameter('value_offset',
                type=types.FloatType,
                flags=Instrument.FLAG_GETSET)

        self.add_parameter('value_factor',
                type=types.FloatType,
                flags=Instrument.FLAG_GETSET)

        self.add_parameter('max_control_deviation',
                type=types.FloatType,
                flags=Instrument.FLAG_GETSET)

        self.add_parameter('max_value',
                type=types.FloatType,
                flags=Instrument.FLAG_GETSET)

        self.add_parameter('min_value',
                type=types.FloatType,
                flags=Instrument.FLAG_GETSET)

        self.add_parameter('P',
                type=types.FloatType,
                flags=Instrument.FLAG_GETSET)

        self.add_parameter('I',
                type=types.FloatType,
                flags=Instrument.FLAG_GETSET)

        self.add_parameter('D',
                type=types.FloatType,
                flags=Instrument.FLAG_GETSET)

        self.add_parameter('read_interval',
                type=types.FloatType,
                unit='s',
                flags=Instrument.FLAG_GETSET)

        self.add_parameter('step_size',
                type=types.FloatType,
                flags=Instrument.FLAG_GETSET)

        self.add_parameter('floating_avg_pts',
                type=types.IntType,
                flags=Instrument.FLAG_GETSET,
                maxval=100,
                minval=1)

        self.add_function('start')
        self.add_function('stop')
        self.add_function('step_up')
        self.add_function('step_down')

        self.set_is_running(False)
        self.set_control_parameter(0)
        self.set_max_value(100) #GHz
        self.set_min_value(0)
        self.set_max_control_deviation(6)
        self.set_setpoint(0)
        self.set_P(0)
        self.set_I(0)
        self.set_D(0)
        self.set_read_interval(0.2)
        self.set_value_offset(470.4)
        self.set_value_factor(1e3)
        self.set_step_size(0.01)
        self.set_floating_avg_pts(1)

        self._error = 0.
        self._derivator = 0.
        self._integrator = 0.
        self._values = []

        # override from config       
        cfg_fn = os.path.abspath(
                os.path.join(qt.config['ins_cfg_path'], name+'.cfg'))
        if not os.path.exists(cfg_fn):
            _f = open(cfg_fn, 'w')
            _f.write('')
            _f.close()
        
        self._parlist = ['P', 'I', 'D', 'control_parameter', 
                'setpoint', 'value_factor', 'value_offset','max_value',
                'min_value', 'max_control_deviation']
        self.ins_cfg = config.Config(cfg_fn)
        self.load_cfg()
        self.save_cfg()

    def get_all(self):
        for n in self._parlist:
            self.get(n)
        
    def load_cfg(self):
        params_from_cfg = self.ins_cfg.get_all()
        for p in params_from_cfg:
            if p in self._parlist:
                self.set(p, value=self.ins_cfg.get(p))

    def save_cfg(self):
        for param in self._parlist:
            value = self.get(param)
            self.ins_cfg[param] = value    
    
    ### set & get methods
    def do_set_control_parameter(self,val):
        self._set_ctrl(val)
        self._control_parameter = val

    def do_get_control_parameter(self):
        return self._control_parameter

    def do_get_value(self):
        return (self._get_val() - self._value_offset)*self._value_factor

    def do_get_value_offset(self):
        return self._value_offset

    def do_set_value_offset(self, val):
        self._value_offset = val

    def do_get_value_factor(self):
        return self._value_factor

    def do_set_value_factor(self, val):
        self._value_factor = val

    def do_get_max_value(self):
        return self._max_value

    def do_set_max_value(self, val):
        self._max_value = val

    def do_get_min_value(self):
        return self._min_value

    def do_set_min_value(self, val):
        self._min_value = val

    def do_get_max_control_deviation(self):
        return self._max_control_deviation

    def do_set_max_control_deviation(self, val):
        self._max_control_deviation = val

    def do_get_is_running(self):
        return self._is_running

    def do_set_is_running(self, val):
        self._is_running = val
               
    def do_get_setpoint(self):
        return self._setpoint

    def do_set_setpoint(self, val):
        self._setpoint = val
        # self._values = []
        self._integrator = 0.
        self._derivator = 0.

    def do_get_P(self):
        return self._P

    def do_set_P(self, val):
        self._P = val

    def do_get_step_size(self):
        return self._step_size

    def do_set_step_size(self, val):
        self._step_size = val

    def do_get_I(self):
        return self._I

    def do_set_I(self, val):
        self._I = val

    def do_get_D(self):
        return self._D

    def do_set_D(self, val):
        self._D = val

    def do_get_read_interval(self):
        return self._read_interval

    def do_set_read_interval(self, val):
        self._read_interval = val
    
    def do_get_floating_avg_pts(self):
        return self._floating_avg_pts

    def do_set_floating_avg_pts(self, val):
        self._floating_avg_pts = val
    
    ### end set/get

    ### public methods
    def start(self):
        self.set_is_running(True)

        self._error = 0.
        self._derivator = 0.
        self._integrator = 0.
        self._t0 = time.time()

        self._dat = qt.Data(name=self._name)
        self._dat.add_coordinate('time')
        self._dat.add_value('raw frequency')
        self._dat.add_value('avg frequency')
        self._dat.add_value('setpoint')
        self._dat.add_value('control parameter')
        self._dat.create_file()

        self._plt = qt.Plot2D(self._dat, 'r-', name=self._name, coorddim=0, 
                valdim=1, maxpoints=100, clear=True)
        self._plt.add(self._dat, 'b-', coorddim=0, valdim=2, maxpoints=100)
        self._plt.add(self._dat, 'k-', coorddim=0, valdim=3, maxpoints=100)

        self.get_control_parameter()       
        gobject.timeout_add(int(self._read_interval*1e3), self._update)

    def stop(self):
        self.set_is_running(False)

    def step_up(self):
        self.set_setpoint(self.get_setpoint() + self._step_size)

    def step_down(self):
        self.set_setpoint(self.get_setpoint() - self._step_size)
        
    def _update(self):
        if not self._is_running:
            return False
        
        new_raw_value = self.get_value()
        if new_raw_value > self._max_value or new_raw_value < self._min_value:
            return True     
        
        self._values.append(new_raw_value)
        while len(self._values) > self._floating_avg_pts:
            self._values = self._values[1:]

        current_avg_value = numpy.mean(self._values)
        self._error = self._setpoint - current_avg_value

        pval = self._P * self._error

        dval = self._D * (self._error - self._derivator)
        self._derivator = self._error
        
        self._integrator = self._integrator + self._error
        ival = self._I * self._integrator

        self._time = time.time() - self._t0
        self._dat.add_data_point(self._time, new_raw_value, current_avg_value,
                self._setpoint, self._control_parameter)

        new_control_parameter = self._control_parameter + pval + dval + ival

        if not self.set_control_parameter(new_control_parameter):
            print 'Could not set control parameter, quit.'
            return False

        return True
    
    ### end public methods

