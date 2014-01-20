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


class pid_controller(Instrument):

    _demo_mode = False

    def __init__(self, name, set_ctrl_func=None, get_val_func=None,
            get_ctrl_func=None, get_stabilizor_func=None, **kw):
        
        Instrument.__init__(self, name)

        self._set_ctrl = set_ctrl_func
        self._get_val = get_val_func
        self._get_ctrl = get_ctrl_func #neccecary for the Matisse pid
        self._get_stabilizor = get_stabilizor_func #neccecary for the HeNe true wavelength stabilisation
        
        if not(self._get_stabilizor == None): self._stabilizor_value = self._get_stabilizor()
        
        if self._demo_mode or self._set_ctrl == None or self._get_val == None:
            self._set_ctrl = self._set_demo_ctrl
            self._get_val = self._get_demo_val

            self._demo_ctrl = 1

            print self._name, 'in demo mode'

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
                
        self.add_parameter('use_stabilizor',
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

        self.add_parameter('max_value_deviation',
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

        self.add_parameter('integration_time',
                type=types.FloatType,
                unit='s',
                flags=Instrument.FLAG_GETSET)

        self.add_parameter('read_interval',
                type=types.FloatType,
                unit='s',
                flags=Instrument.FLAG_GETSET)

        self.add_parameter('PID_type',
                type=types.StringType,
                flags=Instrument.FLAG_GETSET)
        
        self.add_parameter('step_size',
                type=types.FloatType,
                flags=Instrument.FLAG_GETSET)

        self.add_function('start')
        self.add_function('stop')
        self.add_function('step_up')
        self.add_function('step_down')

        self.set_is_running(False)
        self.set_use_stabilizor(False)
        self._control_parameter=0
        self.set_max_value_deviation(10) #GHz
        self.set_max_control_deviation(6)
        self.set_setpoint(0)
        self.set_P(0)
        self.set_I(0)
        self.set_D(0)
        self.set_integration_time(10)
        self.set_read_interval(0.2)
        self._t0 = time.time() # for the demo case
        self.set_value_offset(470.4)
        self.set_value_factor(1e3)
        self.set_PID_type('')
        self.set_step_size(0.)
        #self.get_value()

        # override from config       
        cfg_fn = os.path.abspath(
                os.path.join(qt.config['ins_cfg_path'], name+'.cfg'))
        if not os.path.exists(cfg_fn):
            _f = open(cfg_fn, 'w')
            _f.write('')
            _f.close()
        
        self._parlist = ['P', 'I', 'D', 'integration_time', 
                'setpoint', 'value_factor', 'value_offset','max_value_deviation',
                'max_control_deviation','PID_type','use_stabilizor','step_size']
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
            if p=='control_parameter':
                self._control_parameter=self.ins_cfg.get(p)

    def save_cfg(self):
        for param in self._parlist:
            value = self.get(param)
            self.ins_cfg[param] = value
    
    
    ### set & get methods
    def do_set_control_parameter(self,val):
        self._set_ctrl(val)
        self._control_parameter = val

    def do_get_control_parameter(self):
        if not(self._get_ctrl == None):
            self._control_parameter = self._get_ctrl()
        return self._control_parameter

    def do_get_value(self):
        if self._use_stabilizor:
            if not(self._get_stabilizor == None):
                offset_from_stabilizor = self._stabilizor_value - self._get_stabilizor()
                return (self._get_val() + offset_from_stabilizor - self._value_offset)*self._value_factor
            else:
                print 'Cannot use stabilizor, no stabilizor set'
                self.set_use_stabilizor(False)
        return (self._get_val() - self._value_offset)*self._value_factor

    def do_get_value_offset(self):
        return self._value_offset

    def do_set_value_offset(self, val):
        self._value_offset = val

    def do_get_value_factor(self):
        return self._value_factor

    def do_set_value_factor(self, val):
        self._value_factor = val

    def do_get_max_value_deviation(self):
        return self._max_value_deviation

    def do_set_max_value_deviation(self, val):
        self._max_value_deviation = val

    def do_get_max_control_deviation(self):
        return self._max_control_deviation

    def do_set_max_control_deviation(self, val):
        self._max_control_deviation = val

    def do_get_is_running(self):
        return self._is_running

    def do_set_is_running(self, val):
        self._is_running = val
        
    def do_get_use_stabilizor(self):
        return self._use_stabilizor

    def do_set_use_stabilizor(self, val):
        self._use_stabilizor = val
        
    def do_get_setpoint(self):
        return self._setpoint

    def do_set_setpoint(self, val):
        self._setpoint = val

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

    def do_get_integration_time(self):
        return self._integration_time

    def do_set_integration_time(self, val):
        self._integration_time = val

    def do_get_read_interval(self):
        return self._read_interval

    def do_set_read_interval(self, val):
        self._read_interval = val

    def do_get_PID_type(self):
        return self._PID_type

    def do_set_PID_type(self, val):
        self._PID_type = val
    ### end set/get

    ### public methods
    def start(self):
        self._t0 = time.time()
        self.set_is_running(True)

        self._value = 0
        self._time = 0
        self._integral = 0
        self._prev_value = 0
        self._prev_prev_value = 0
        self._prev_time = 0

        self._dat = qt.Data(name=self._name)
        self._dat.add_coordinate('time')
        self._dat.add_value('frequency')
        self._dat.add_value('setpoint')
        self._dat.add_value('control parameter')
        self._dat.create_file()

        self._plt = qt.Plot2D(self._dat, 'r-', name=self._name, coorddim=0, 
                valdim=1, maxpoints=100, clear=True)
        self._plt.add(self._dat, 'b-', coorddim=0, valdim=2, maxpoints=100)
        
        if not(self._get_stabilizor == None): self._stabilizor_value = self._get_stabilizor()
        self.get_control_parameter()
        
        gobject.timeout_add(int(self._read_interval*1e3), self._update)

    def stop(self):
        self.set_is_running(False)

    def step_up(self):
        self.set_setpoint(self.get_setpoint() + self._step_size)

    def step_down(self):
        self.set_setpoint(self.get_setpoint() - self._step_size)

    def _new_control_parameter(self):

        if self._PID_type == 'A':
            print 'Type A PID not yet implemented'
            return 0
        elif self._PID_type == 'B':
            print 'Type B PID not yet implemented'
            return 0
        elif self._PID_type == 'C':
            pterm = -1.0 * self._P * (self._value - self._prev_value)

            iterm = self._I * self._read_interval * \
                    (self._value - self._setpoint)
            
            dterm = self._D / self._read_interval * \
                    (self._value - 2.0*self._prev_value + self._prev_prev_value)

            return self._control_parameter + pterm + iterm + dterm

        else:   #pid-type Wolfgang?

            pterm = self._P * (self._value - self._setpoint)
            
            if self._prev_time > 0:
                self._integral += (self._time - self._prev_time) * \
                        (self._value - self._setpoint)
                
                iterm = self._I * self._integral
            else:
                iterm = 0
            
            if self._prev_time < self._time:
                dterm = self._D * ((self._value - self._setpoint) - \
                        (self._prev_value - self._setpoint)) / \
                        (self._time - self._prev_time)
            else:
                dterm = 0

            return pterm + iterm + dterm

    def _update(self):
        if not self._is_running:
            return False
        
        self._prev_prev_value = self._prev_value
        self._prev_value = self._value
        raw_value = self.get_value()
        if (abs(raw_value - self._prev_value) > self._max_value_deviation) \
                and (self._prev_time != 0) :
            print 'Measured value', raw_value, 'exceeds max value deviation', \
                    self._max_value_deviation, 'ignoring value'
        else:
            self._value = raw_value   
        
        self._prev_time = self._time
        self._time = time.time() - self._t0

        self._dat.add_data_point(self._time, self._value,
                self._setpoint, self._control_parameter)

        new_control_parameter=self._new_control_parameter()

        if (abs(new_control_parameter-self._control_parameter) > \
                self._max_control_deviation) and (self._prev_time != 0) :
                new_control_parameter = self._control_parameter + \
                        numpy.copysign(self._max_control_deviation,new_control_parameter-self._control_parameter)
                #print 'Max control deviation'

        if not self.set_control_parameter(new_control_parameter):
            print 'Could not set control parameter, quit.'
            return False

        return True
    
    ### end public methods


    ### private methods    
    def _get_demo_val(self):
        # return self._control_parameter
        
        return (0.1 * (time.time()-self._t0)) + \
                (numpy.random.rand()-0.5)*10 + self._control_parameter*100

    def _set_demo_ctrl(self, val):
        return True

    ### end private methods

