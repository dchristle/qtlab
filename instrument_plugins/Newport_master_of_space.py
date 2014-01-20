# Newport FSM Master of Space
# Modified from the original qtlab master_of_space.py file from Delft.
#
#
# Controls a single Newport FSM positioner that is set via an
# NI DAQ voltage
#
import os
from instrument import Instrument
from cyclopean_instrument import CyclopeanInstrument
import qt
import time
import types
import gobject
import numpy as np
from lib import config

# constants
LINESCAN_CHECK_INTERVAL = 50 # [ms]

# FIXME origin, markers, not fully consistent and probably not working at the
# moment! fix that! (origin not taken into account)

class master_of_space(CyclopeanInstrument):
    def __init__(self, name, adwin):
        """
        Parameters:
            adwin : string
                qtlab-name of the adwin instrument to be used
        """
        CyclopeanInstrument.__init__(self, name, tags=['positioner'])
        self._adwin = qt.instruments[adwin]

        #print 'init'
        # should not change often, hardcode is fine for now
        self.rt_dimensions = {
                'x' : {
                    'dac' : 'atto_x',
                    'micron_per_volt' : 9.324,
                    'max_v' : 4.29,
                    'min_v' : 0.,
                    'default' : 0.,
                    'origin' : 0.,
                    },
                'y' : {
                    'dac' : 'atto_y',
                    'micron_per_volt' : 5.59,
                    'min_v' : 0.,
                    'max_v' : 4.29,
                    'default' : 0.,
                    'origin' : 0.,
                    },
                'z' : {
                    'dac' : 'atto_z',
                    'micron_per_volt' : 9.324,
                    'max_v' : 4.29,
                    'min_v' : 0.,
                    'default' : 0.,
                    'origin' : 0.,
                    },
                }

        self.lt_dimensions = {
                'x' : {
                    'dac' : 'atto_x',
                    'micron_per_volt' : 2.8,
                    'max_v' : 10,
                    'min_v' : 0.,
                    'default' : 0.,
                    'origin' : 0.,
                    },
                'y' : {
                    'dac' : 'atto_y',
                    'micron_per_volt' : 1.40,
                    'min_v' : 0.,
                    'max_v' : 10,
                    'default' : 0.,
                    'origin' : 0.,
                    },
                'z' : {
                    'dac' : 'atto_z',
                    'micron_per_volt' : 2.8,
                    'max_v' : 10,
                    'min_v' : 0.,
                    'default' : 0.,
                    'origin' : 0.,
                    },
                }

        self.dimensions = self.rt_dimensions

        # auto generate parameters incl set and get for all dimensions
        for d in self.dimensions:
            dim = self.dimensions[d]

            # make set and get
            self._make_get(d)
            self._make_set(d)

            # make stepping function
            self._make_stepfunc(d)

            # register parameter (set and get need to exist already)
            self.add_parameter(d,
                    type=types.FloatType,
                    flags=Instrument.FLAG_GETSET,
                    units='um',
                    minval=dim['min_v']*dim['micron_per_volt'],
                    maxval=dim['max_v']*dim['micron_per_volt'], )

            # register the step function
            self.add_function('step_'+d)

        # scan control
        self._linescan_running = False
        self._linescan_px_clock = 0

        self.add_parameter('linescan_running',
                type=types.BooleanType,
                flags=Instrument.FLAG_GET)
        self.add_parameter('linescan_px_clock',
                type=types.IntType,
                flags=Instrument.FLAG_GET)

        self.add_function('linescan_start')

        # for positioning with attocubes
        self.add_parameter('lt_settings',
                type=types.BooleanType,
                flags=Instrument.FLAG_GETSET)
        self._lt_settings = False

        # managing the coordinate system
        self.add_function('set_origin')
        self.add_function('get_origin')
        self.add_function('from_relative')
        self.add_function('to_relative')
        self.add_function('set_relative_position')
        self.add_function('get_relative_position')
        self.add_function('move_to_xyz_pos')

        # markers
        self._markers = {}
        self.add_function('set_marker')
        self.add_function('get_marker')
        self.add_function('get_markers')
        self.add_function('goto_marker')
        self.add_function('push_position')
        self.add_function('pop_position')

        # set up config file
        cfg_fn = os.path.join(qt.config['ins_cfg_path'], name+'.cfg')
        if not os.path.exists(cfg_fn):
            _f = open(cfg_fn, 'w')
            _f.write('')
            _f.close()

        self.ins_cfg = config.Config(cfg_fn)
        self.load_cfg()
        self.save_cfg()

        # set initial position values (need to know whether LT or RT settings)
        for d in self.dimensions:
            dim = self.dimensions[d]
            voltage = self._adwin.get_dac_voltage(dim['dac'])
            position = voltage * dim['micron_per_volt']
            setattr(self, '_'+d, position)


    ### config management
    def load_cfg(self):
        params = self.ins_cfg.get_all()
        if 'lt_settings' in params:
            if params['lt_settings']:
                self.set_lt_settings(True)

    def save_cfg(self):
        self.ins_cfg['lt_settings'] = self._lt_settings

    # Line scan control
    def linescan_start(self, dimensions, starts, stops, steps, px_time,
            relative=False, value='counts'):
        #print 'linescan_start'

        # for now, user has to wait until scan is finished
        if self.get_linescan_running() or self._adwin.is_linescan_running():
            return False

        self._linescan_running = True
        self.get_linescan_running()

        # if we get relative coordinates, convert to absolutes first
        if relative:
            for i, dimname in enumerate(dimensions):
                starts[i] = from_relative(dimname, starts[i])
                stops[i] = from_relative(dimname, stops[i])

        # calculate the stepping in voltages and move to the start position
        # (Only move if v start and v stop are within allowed values)
        dacs = []
        starts_v = []
        stops_v = []
        for i, dimname in enumerate(dimensions):
            dim = self.dimensions[dimname]
            dacs.append(dim['dac'])
            if self.dimensions[dimname]['min_v'] <= (starts[i]/dim['micron_per_volt']) <= self.dimensions[dimname]['max_v']:
                starts_v.append(starts[i] / dim['micron_per_volt'])
            else:
                starts_v.append(self.dimensions[dimname]['min_v'])
                print "Error in master_of_space.linescan_start: Exceeding max/min voltage "
                print starts[i] / dim['micron_per_volt']
            if self.dimensions[dimname]['min_v'] <= (stops[i]/dim['micron_per_volt']) <= self.dimensions[dimname]['max_v']:
                stops_v.append(stops[i] / dim['micron_per_volt'])
            else:
                stops_v.append(self.dimensions[dimname]['max_v'])
                print "Error in master_of_space.linescan_start: Exceeding max.min voltage"
                print stops[i] / dim['micron_per_volt']

        self._adwin.linescan(dacs, np.array(starts_v), np.array(stops_v),
                steps, px_time, value=value, scan_to_start=True)

        # start monitoring the status
        gobject.timeout_add(LINESCAN_CHECK_INTERVAL, self._linescan_check)

        return True

    def do_get_linescan_running(self):
        return self._linescan_running

    def do_get_linescan_px_clock(self):
        return self._linescan_px_clock

    def do_get_lt_settings(self):
        return self._lt_settings

    # FIXME should first move to save location if necessary!
    def do_set_lt_settings(self, val):
        if val:
            # self._adwin.set_LT(1)
            self.dimensions = self.lt_dimensions
            self._lt_settings = True
        else:
            # self._adwin.set_LT(0)
            self.dimensions = self.rt_dimensions
            self._lt_settings = False
        self.save_cfg()

    # monitor the status of the linescan
    def _linescan_check(self):
        #print 'linescan_check'

        # first update the px clock, call get to make connects easy
        if self._adwin.get_linescan_px_clock() > self._linescan_px_clock:
            self._linescan_px_clock = self._adwin.get_linescan_px_clock()
            self.get_linescan_px_clock()

        # debug output
        # print 'px clock: ', self._linescan_px_clock

        if self._adwin.is_linescan_running():
            return True
        else:
            self._linescan_running = False
            self.get_linescan_running()

            # debug output
            # print 'scan finished'

            return False


    ### managing the coordinate system
    def set_origin(self, relative=False, **kw):
        for d in kw:
            if d in self.dimensions:
                origin = kw.pop(d)
                if origin == 'here':
                    self.dimensions[d]['origin'] = getattr(self, 'get_'+d)()
                else:
                    self.dimensions[d]['origin'] = float(origin)

    def get_origin(self, dim):
        if dim in self.dimensions:
            return self.dimensions[dim]['origin']
        else:
            return False

    def to_relative(self, dim, val):
        if dim in self.dimensions:
            return val-self.dimensions[dim]['origin']
        else:
            return False

    def from_relative(self, dim, val):
        if dim in self.dimensions:
            return val+self.dimensions[dim]['origin']
        else:
            return False

    def set_relative_position(self, dim, val):
        if dim in self.dimensions:
            return getattr(self, 'set_'+dim)(self.from_relative(dim, val))
        else:
            return False

    def get_relative_position(self, dim):
        if dim in self.dimensions:
            return self.to_relative(getattr(self, 'get_'+dim)())


    ### managing markers
    def set_marker(self, name, **kw):
        self._markers[name] = {}
        for d in kw:
            if d in self.dimensions:
                pt = kw.pop(d)
                if pt == 'here':
                    self._markers[name][d] = getattr(self, 'get_'+d)()
                else:
                    self._markers[name][d] = float(pt)

    def get_markers(self):
        return self._markers

    def get_marker(self, name):
        return self._markers[name]

    def goto_marker(self, name):
        for d in self._markers[name]:
            print name
            getattr(self, 'set_'+d)(self._markers[name][d])

    def push_position(self, dims=[]):
        self._markers['push'] = {}
        for d in dims:
            if d in self.dimensions:
                self._markers['push'][d] = getattr(self, 'get_'+d)()

    def pop_position(self):
        if 'push' not in self._markers:
            print 'no position pushed, cannot pop'
            return False
        else:
            self.goto_marker('push')


    ### internals
    # creation of get and set functions, stepfunction
    def _make_get(self, dimname):
        def getfunc():
            return getattr(self, '_' + dimname)
        getfunc.__name__ = 'do_get_'+dimname
        setattr(self, 'do_get_'+dimname, getfunc)
        return

    def _make_set(self, dimname):
        def setfunc(val):
            self._set_dim(dimname, val)
            setattr(self, '_'+dimname, val)
            return
        setfunc.__name__ = 'do_set_'+dimname
        setattr(self, 'do_set_'+dimname, setfunc)
        return

    def _make_stepfunc(self, dimname):
        def stepfunc(delta):
            self._step_dim(dimname, delta)
            return
        stepfunc.__name__ = 'step_'+dimname
        setattr(self, 'step_'+dimname, stepfunc)

    # functions that do the actual work :)
    # FIXME This might be a little specific.
    def _set_dim(self, dimname, val):
        dim = self.dimensions[dimname]
        self.move_to_xyz_pos([dimname], [val])

    def _step_dim(self, dimname, delta):
        current = getattr(self, 'get_'+dimname)()
        getattr(self, 'set_'+dimname)(current+delta)

    def U_to_pos(self,dimname,val):
        pos=[]
        for dim in dimname:
            pos.append(self.dimensions[dim]['micron_per_volt']*val[dimname.index(dim)])
        return pos

    def pos_to_U(self,dimname,val):
        U = []
        for dim in dimname:
            U.append(val[dimname.index(dim)]/self.dimensions[dim]['micron_per_volt'])
        return U

    #Convenient extra functions
    def move_to_pos(self, dim_name, val, speed=5000, blocking=False):
        # print dim_name, val
        #print 'move_to_pos'

        dim = self.dimensions[dim_name]
        dac_name = dim['dac']
        target_voltage = val/dim['micron_per_volt']
        if not dim['min_v'] <= target_voltage <= dim['max_v']:
            print 'Error in mos: exceeding max/min voltage'
            return

        self._adwin.move_to_dac_voltage(dac_name, target_voltage, speed=speed,
                blocking=blocking)
        setattr(self, '_'+dim_name, val)
        self.get(dim_name)

    def move_to_xyz_pos(self, dim_names, vals, speed=5000, blocking=False):

        #print 'move_to_xyz_pos'
        target_voltages = []
        for d in ['x','y','z']:
            dim = self.dimensions[d]
            try:
                tvalt = self.get(d)/dim['micron_per_volt']
            except:
                tvalt = 0.

            tv = vals[dim_names.index(d)]/dim['micron_per_volt'] if d in dim_names else \
                        tvalt

            if not dim['min_v'] <= tv <= dim['max_v']:
                print 'Error in mos: exceeding max/min voltage'
                return

            target_voltages.append(tv)

        #print '*'
        self._adwin.move_to_xyz_U(target_voltages, speed=speed,
                blocking=blocking)
        #print '**'

        for i,d in enumerate(dim_names):
            setattr(self, '_'+d, vals[i])
            try:
                self.get(d)
            except:
                pass


