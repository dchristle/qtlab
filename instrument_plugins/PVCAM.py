# PVCAM.py, instrument driver for PVCAM library
#


from lib.dll_support import pvcam_dev
reload(pvcam_dev)
from instrument import Instrument
import types
import logging
import time

class PVCAM(Instrument):
    '''
    This is the python driver for the PVCam library
    '''

    def __init__(self, name, reset=False):
        Instrument.__init__(self, name, tags=['physical'])

        self._create_dev()

        self.add_parameter('temperature', type=types.FloatType,
            flags=Instrument.FLAG_GET,
            units='K')
        self.add_parameter('setpoint', type=types.FloatType,
            flags=Instrument.FLAG_GETSET,
            units='K')
        self.add_parameter('gain', type=types.IntType,
            flags=Instrument.FLAG_GETSET)
        self.add_parameter('readout_rate', type=types.IntType,
            flags=Instrument.FLAG_GETSET, minval=0, maxval=(len(self.get_readout_rates())-1))
        self.add_parameter('exposure_time', type=types.FloatType,
            flags=Instrument.FLAG_GETSET)



        self.add_function('acquire_image')
        self.add_function('get_readout_rates')
        self.add_function('get_sensor_size')
        self.add_function('get_readout_ports')
        self.add_function('rem')
##        self.add_function('get_all')
##        self.add_function('open')
##        self.add_function('close')
##        self.add_function('start')
##        self.add_function('plot')

##        self.set_inttime(10)



    def _create_dev(self):
        self._dev = pvcam_dev.PVCAMDevice()

    def reset(self):
        #self.get_all()
        return

    def close(self):
        self._dev.close()
        return
    def uninit(self):
        self._dev.uninitialize()
        return
    def rem(self):
        self.close()
        self.uninit()
        return

    def do_get_setpoint(self):
        temperature = self._dev.get_temperature_setpoint()
        return temperature

    def do_get_temperature(self):

        return float(self._dev.get_temperature())

    def do_set_setpoint(self, temperature):
        self._dev.set_temperature_setpoint(temperature)
        return

    def do_set_gain(self, gain_index):
        self._dev.set_gain_index(gain_index)
        return

    def do_get_gain(self):
        return self._dev.get_gain_index()

    def acquire_image(self):
        # set up experimental parameters
        self._dev.exp_init_seq()
        self._dev.exp_setup_seq()
        self._dev.exp_start_seq()
        # convert the ctypes buffer to a numpy array
        image_array = self._dev.buffer_as_array()
        # finish the sequence
        self._dev.exp_finish_seq()
        # return the array
        return image_array

    def get_sensor_size(self):
        return self._dev.get_sensor_size()

    def get_readout_rates(self):
        return self._dev.get_readout_rates()

    def get_gains(self):
        return self._dev.get_gains()

    def get_readout_ports(self):
        return self._dev.get_readout_ports()
    def set_low_noise_readout(self):
        self._dev.set_low_noise_readout()
        return
    def do_get_readout_rate(self):
        return self._dev.get_readout_index()

    def do_set_readout_rate(self, ridx):
        self._dev.set_readout_index(ridx)
        return

    def do_get_exposure_time(self):
        return self._dev.get_exposure_time()

    def do_set_exposure_time(self, exp_time):
        self._dev.set_exposure_time(exp_time)
        return

##    def do_get_resolution(self):
##        if self._dev:
##            return self._dev.get_resolution()
##        return 0
##
##    def do_set_range(self, val):
##        if not self._dev:
##            return
##        self._dev.set_range(val)
##        self.get_resolution()
##
##    def do_get_counts(self, channel):
##        if self._dev:
##            return self._dev.get_count_rate(channel)
##
##    def do_set_inttime(self, time):
##        self._inttime = time
##
##    def start(self):
##        if not self._dev:
##            return
##        self._dev.clear_hist_mem()
##        self._dev.start(int(self._inttime * 1000))
##
##    def plot(self):
##        if not self._dev:
##            return
##        import qt
##        x, trace = self._dev.get_block()
##        qt.plot(trace, name='picoharp', clear=True)
##
##    def do_set_divider(self, value):
##        if not self._dev:
##            return
##        self._dev.set_sync_div(value)
##
##    def get_data(self):
##        '''
##        Returns histogram data (x,trace)
##        '''
##        if not self._dev:
##            return None
##        return self._dev.get_block()
##
##    def get_status(self):
##        '''
##        Returns acquisition status
##        0 : acquisition still running
##        >0: acquisition has ended
##        '''
##        if not self._dev:
##            return None
##        return self._dev.get_status()
##
##    def get_elepased_meas_time(self):
##        '''
##        Returns elapsed measurement time in ms
##        '''
##        if not self._dev:
##            return None
##        return self._dev.get_elepased_meas_time()
##
##    def set_offset(self,offset):
##        '''
##        Set the offset in ps
##        '''
##        if not self._dev:
##            return None
##        return self._dev.set_offset(offset)
##
##    def set_cfd_level(self, chan, val):
##        '''
##        Set CFD level (in mV) for channel chan.
##        '''
##        if not self._dev:
##            return None
##        return self._dev.set_cfd_level(chan, val)
##
##    def set_cfd_zero_cross(self, chan, val):
##        '''
##        Set CFD level 0 cross level (in mV) for channel chan.
##        '''
##        if not self._dev:
##            return None
##        return self._dev.set_cfd_zero_cross(chan, val)
##
