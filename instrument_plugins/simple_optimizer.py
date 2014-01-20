import qt
import numpy as np
from instrument import Instrument
import plot as plt
import types
import os
from lib import config
import instrument_helper

class simple_optimizer(Instrument):

    def __init__(self, name, get_control_f=None, set_control_f=None, get_value_f=None, get_norm_f=None, plot_name=''):
        Instrument.__init__(self, name)        
        if plot_name=='': 
            plot_name='optimizer_'+name            
               
        self._get_control_f=get_control_f
        self._set_control_f=set_control_f
        self._get_value_f=get_value_f
        self._get_norm_f=get_norm_f
        
        ins_pars  = {'max_control'      :   {'type':types.FloatType,'val':0.0,'flags':Instrument.FLAG_GETSET},
                    'min_control'       :   {'type':types.FloatType,'val':0.0,'flags':Instrument.FLAG_GETSET},
                    'scan_range'        :   {'type':types.FloatType,'val':0.0,'flags':Instrument.FLAG_GETSET},
                    'control_step_size' :   {'type':types.FloatType,'val':0.0,'flags':Instrument.FLAG_GETSET},
                    'min_value'         :   {'type':types.IntType, 'val':2,'flags':Instrument.FLAG_GETSET},
                    'dwell_time'        :   {'type':types.FloatType,'val':0.1,'flags':Instrument.FLAG_GETSET}, #s
                    'wait_time'         :   {'type':types.FloatType,'val':10,'flags':Instrument.FLAG_GETSET}, #s
                    'order_index'       :   {'type':types.IntType,  'val':1,'flags':Instrument.FLAG_GETSET},
                    'do_plot'           :   {'type':types.BooleanType,'val':True,'flags':Instrument.FLAG_GETSET},
                    'plot_name'         :   {'type':types.StringType,'val':plot_name,'flags':Instrument.FLAG_GETSET},
                    'variance'          :   {'type':types.FloatType,'val':0.,'flags':Instrument.FLAG_GETSET},
                    'last_max'          :   {'type':types.FloatType,'val':0.,'flags':Instrument.FLAG_GETSET},
                    }
        
        instrument_helper.create_get_set(self,ins_pars)
                    
        self.add_function('scan')
        self.add_function('optimize')
        self.add_function('get_value')
        
    # override from config       
        cfg_fn = os.path.join(qt.config['ins_cfg_path'], name+'.cfg')
        if not os.path.exists(cfg_fn):
            _f = open(cfg_fn, 'w')
            _f.write('')
            _f.close()
        
        self.ins_cfg = config.Config(cfg_fn)
        self.load_cfg()
        self.save_cfg()
        
    def get_all_cfg(self):
        for n in self._parlist:
            self.get(n)
        
    def load_cfg(self):
        params_from_cfg = self.ins_cfg.get_all()
        for p in params_from_cfg:
                self.set(p, value=self.ins_cfg.get(p))

    def save_cfg(self):
        for param in self.get_parameter_names():
            value = self.get(param)
            self.ins_cfg[param] = value
            
    def scan(self):
          
        initial_setpoint = self._get_control_f()
        scan_min = max(self._min_control,initial_setpoint - self._scan_range/2.)
        scan_max = min(self._max_control,initial_setpoint + self._scan_range/2.)
        steps=int((scan_max - scan_min) / self._control_step_size)
        print initial_setpoint,scan_min,scan_max, steps
        udrange=np.append(np.linspace(initial_setpoint,scan_min,int(steps/2.)),
                np.linspace(scan_min, scan_max, steps))
        udrange=np.append(udrange,np.linspace(scan_max,initial_setpoint,int(steps/2.)))
        values=np.zeros(len(udrange))
        true_udrange=np.zeros(len(udrange))
        for i,sp in enumerate(udrange):
            #print 'sp',sp
            self._set_control_f(sp)
            qt.msleep(self._dwell_time)
            true_udrange[i]=self._get_control_f()
            values[i]=self.get_value()
            
        valid_i=np.where(values>self._min_value)
        
        if self.get_do_plot():
            p=plt.plot(name=self._plot_name)
            p.clear()
            plt.plot(true_udrange[valid_i],values[valid_i],'O',name=self._plot_name)
        
        return (true_udrange[valid_i],values[valid_i])
    
    def optimize(self):
        value_before=self.get_value()
        x,y=self.scan()
        if len(y)>0:
            maxx=x[np.argmax(y)]
            variance=np.sum(np.abs(np.ediff1d(y)))
            self.set_variance(variance)
            print 'variance: ', variance
            maxy=np.max(y)
            self.set_last_max(maxy)
            print 'before', value_before,'after:', maxy
            if maxy>value_before:
                print self.get_name(),'setting new control (old,new,delta): {:.2f},{:.2f},{:.2f}'.format(self._get_control_f(),maxx,self._get_control_f()-maxx)
                self._set_control_f(maxx)
            
    def get_value(self):
        v1,n1=self._get_value_f(),self._get_norm_f()
        qt.msleep(self._dwell_time)
        v2,n2=self._get_value_f(),self._get_norm_f()
        if (n2-n1)!=0:
            return float((v2-v1))/(n2-n1)
        else:
            return 0.