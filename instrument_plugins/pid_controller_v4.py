import os
import types
import gobject
import time
#import threading

import numpy

import qt
from instrument import Instrument
from data import Data
from lib import config

import instrument_helper


class pid_controller_v4(Instrument):

    def __init__(self, name, set_ctrl_func=None, get_val_func=None, 
                 set_ctrl_func_coarse=None,get_ctrl_func_coarse=None, get_ctrl_func=None, 
                 get_stabilizor_func=None, **kw):
        
        Instrument.__init__(self, name)

        self._set_ctrl = set_ctrl_func
        self._get_val = get_val_func
        self._get_ctrl = get_ctrl_func #neccecary for the Matisse pid
        self._get_stabilizor = get_stabilizor_func #neccecary for the HeNe true wavelength stabilisation
        self._set_ctrl_coarse = set_ctrl_func_coarse
        self._get_ctrl_coarse = get_ctrl_func_coarse

        if not(self._get_stabilizor == None): self._stabilizor_value = self._get_stabilizor()

        self.add_parameter('control_parameter',
                type=types.FloatType,
                minval=kw.get('ctrl_minval', -10.),
                maxval=kw.get('ctrl_maxval', +10.),
                flags=Instrument.FLAG_GETSET)
                
        self.add_parameter('control_parameter_coarse',
                type=types.FloatType,
                minval=kw.get('ctrl_minval_coarse', -10.),
                maxval=kw.get('ctrl_maxval_coarse', +10.),
                flags=Instrument.FLAG_GETSET)
        
        self.add_parameter('value',
                type=types.FloatType,
                flags=Instrument.FLAG_GET)

        self.add_parameter('setpoint',
                type=types.FloatType,
                flags=Instrument.FLAG_GETSET)
        
        ins_pars  = {'is_running'               :   {'type':types.BooleanType,'val':False,'flags':Instrument.FLAG_GETSET},
                    'use_stabilizor'            :   {'type':types.BooleanType,'val':False,'flags':Instrument.FLAG_GETSET},
                    'max_value'                 :   {'type':types.FloatType,  'val':100.0,'flags':Instrument.FLAG_GETSET},
                    'min_value'                 :   {'type':types.FloatType,  'val':0.0,  'flags':Instrument.FLAG_GETSET},
                    'P'                         :   {'type':types.FloatType,  'val':0.,   'flags':Instrument.FLAG_GETSET},
                    'I'                         :   {'type':types.FloatType,  'val':0.,   'flags':Instrument.FLAG_GETSET}, #s
                    'D'                         :   {'type':types.FloatType,  'val':0.,   'flags':Instrument.FLAG_GETSET}, #s
                    'read_interval'             :   {'type':types.FloatType,  'val':0.2,  'units':'s','flags':Instrument.FLAG_GETSET},
                    'write_interval'            :   {'type':types.IntType,    'val':1,    'maxval':100,'minval':1,'flags':Instrument.FLAG_GETSET},
                    'value_offset'              :   {'type':types.FloatType,  'val':470.4,'flags':Instrument.FLAG_GETSET},
                    'value_factor'              :   {'type':types.FloatType,  'val':1e3,  'flags':Instrument.FLAG_GETSET},
                    'step_size'                 :   {'type':types.FloatType,  'val':0.01, 'flags':Instrument.FLAG_GETSET},
                    'floating_avg_pts'          :   {'type':types.IntType,    'val':1.,   'maxval':100,'minval':1, 'flags':Instrument.FLAG_GETSET},
                    'max_control_deviation'     :   {'type':types.FloatType,  'val':1.0,  'flags':Instrument.FLAG_GETSET},
                    'control_coarse_step':{'type':types.FloatType, 'val':0.05,'flags':Instrument.FLAG_GETSET},
                    }
        instrument_helper.create_get_set(self,ins_pars)
        self.add_function('start')
        self.add_function('stop')
        self.add_function('step_up')
        self.add_function('step_down')
       
        self.set_setpoint(0)
        self._control_parameter=0
        self._control_parameter_coarse=0

        # override from config       
        cfg_fn = os.path.abspath(
                os.path.join(qt.config['ins_cfg_path'], name+'.cfg'))
        if not os.path.exists(cfg_fn):
            _f = open(cfg_fn, 'w')
            _f.write('')
            _f.close()
        
        self._parlist = ['P', 'I', 'D',
                'setpoint', 'value_factor', 'value_offset','max_value',
                'min_value', 'max_control_deviation','use_stabilizor', 'step_size',
                'control_coarse_step']
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
            if p=='control_parameter_coarse':
                self._control_parameter_coarse=self.ins_cfg.get(p)

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
        
    def do_set_control_parameter_coarse(self,val):
        if self._set_ctrl_coarse == None:
            return False
        self._set_ctrl_coarse(val)
        self._control_parameter_coarse = val

    def do_get_control_parameter_coarse(self):
        if not(self._get_ctrl_coarse == None):
            self._control_parameter_coarse = self._get_ctrl_coarse()
        return self._control_parameter_coarse

    def do_get_value(self):
        if self._use_stabilizor:
            if not(self._get_stabilizor == None):
                offset_from_stabilizor = self._stabilizor_value - self._get_stabilizor()
                return (self._get_val() + offset_from_stabilizor - self._value_offset)*self._value_factor
            else:
                print 'Cannot use stabilizor, no stabilizor set'
                self.set_use_stabilizor(False)
        return (self._get_val() - self._value_offset)*self._value_factor
    
    def do_get_setpoint(self):
        return self._setpoint
   
    def do_set_setpoint(self, val):
        self._setpoint = val
        # self._values = []
        self._integrator = 0.
        #self._derivator = 0.
    
    ### end set/get

    ### public methods
    def start(self):
        self.set_is_running(True)

        self._error = 0.
        self._derivator = 0.
        self._integrator = 0.
        self._values = []
        self._read_counter=-1
        
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
        if not(self._get_stabilizor == None): self._stabilizor_value = self._get_stabilizor()
        self.get_control_parameter()
        self.get_control_parameter_coarse()             
        gobject.timeout_add(int(self._read_interval*1e3), self._update)

    def stop(self):
        self.set_is_running(False)

    def step_up(self):
        self.set_setpoint(self.get_setpoint() + self._step_size)

    def step_down(self):
        self.set_setpoint(self.get_setpoint() - self._step_size)
        
    ### end public methods    
    def _update(self):
        if not self._is_running:
            return False
        
        new_raw_value = self.get_value()
        if new_raw_value > self._max_value or new_raw_value < self._min_value:
            return True     
        
        self._values.append(new_raw_value)
        while len(self._values) > self._floating_avg_pts:
            self._values = self._values[1:]
        
        self._read_counter=self._read_counter+1
        
        current_avg_value = numpy.mean(self._values)
        self._error = self._setpoint - current_avg_value

        pval = self._P * self._error

        dval = self._D * (current_avg_value - self._derivator)
        self._derivator = current_avg_value
        
        ival = self._I * self._integrator
        self._integrator = self._integrator + self._error
        
        self._time = time.time() - self._t0
        self._dat.add_data_point(self._time, new_raw_value, current_avg_value,
                self._setpoint, self._control_parameter)

        new_control_parameter = self._control_parameter + pval + dval + ival

        if not self._try_set_control_parameter(new_control_parameter):
            print 'Could not set control parameter, quit.'
            return False

        return True
    
   
    
    def _try_set_control_parameter(self,new_control_parameter):
        
        if self._read_counter < self._write_interval:
            return True
        
        self._read_counter=0
    
        if (abs(new_control_parameter-self._control_parameter) > \
                self._max_control_deviation) and (self._time > self.get_read_interval()) :
                new_control_parameter = self._control_parameter + \
                        numpy.copysign(self._max_control_deviation,new_control_parameter-self._control_parameter)
                        
        if not(self.set_control_parameter(new_control_parameter)):
            if self.set_control_parameter_coarse(self.get_control_parameter_coarse()+ \
                    numpy.copysign(self.get_control_coarse_step(),new_control_parameter-self._control_parameter)):
                self.set_control_parameter(0)
            else:
                return False
        return True

