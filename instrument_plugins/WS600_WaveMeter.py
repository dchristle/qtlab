from ctypes import *
import os
from instrument_plugins._Spectrum_M2i2030.errors import errors as _spcm_errors
from instrument_plugins._Spectrum_M2i2030.regs import regs as _spcm_regs
from instrument import Instrument
import pickle
from time import sleep, time
import types
import logging
import numpy
import qt
from qt import *
from numpy import *
from data import Data



class WS600_WaveMeter(Instrument): #1
    '''
    This is the driver for the WS600 HighFinesse wavemeter

    Usage:
    Initialize with
    <name> = qt.instruments.create('name', 'WS600_WaveMeter')
    
    status:
     1) create this driver!=> is never finished
    TODO:
    '''

    def __init__(self, name): #2
         # Initialize wrapper
        logging.info(__name__ + ' : Initializing instrument WS600')
        Instrument.__init__(self, name, tags=['physical'])

        # Load dll and open connection
        self._load_dll()
        sleep(0.01)

        self.add_parameter('wavelength', flags = Instrument.FLAG_GET, type=types.FloatType,units='nm',format = '%.6f')
        self.add_parameter('temperature', flags = Instrument.FLAG_GET, type=types.FloatType,units='C',format = '%.2f')
        self.add_parameter('frequency', flags = Instrument.FLAG_GET, type=types.FloatType,units='THz',format = '%.6f')
        self.add_parameter('integration_time', flags = Instrument.FLAG_GETSET, type=types.IntType, minval = 0, maxval = 9999, units = 'ms')
        self.add_parameter('active_channel', flags = Instrument.FLAG_GETSET, type=types.IntType)
        
        
        self.add_function('get_channel_frequency')
        self.add_function('get_channel_wavelength')        
        
        
        self._ref_freq = 470.400
        self._last_valid = [self._ref_freq, self._ref_freq, self._ref_freq, self._ref_freq]
        self.set_active_channel(1)
        self.get_integration_time()
        self.get_temperature()

    def _load_dll(self): #3
        print __name__ +' : Loading wlmData.dll'
        WINDIR=os.environ['WINDIR']
        self._wlmData = windll.LoadLibrary(WINDIR+'\\System32\\wlmData')
        self._wlmData.GetWavelengthNum.restype = c_double
        self._wlmData.GetFrequencyNum.restype = c_double
        self._wlmData.GetTemperature.restype = c_double
        sleep(0.02)

    def Get_Wavelength(self,channel):
        Wavelength = self._wlmData.GetWavelengthNum(channel, c_double(0))
        return Wavelength

    def do_get_wavelength(self):
        return self.Get_Wavelength(self.active_channel)

    def Get_Frequency(self,channel):
        Frequency = self._wlmData.GetFrequencyNum(channel,c_double(0))
        if Frequency != 0:
            self._last_valid[channel-1] = Frequency
        else:
            Frequency = self._last_valid[channel-1]
        return Frequency

    def do_get_frequency(self):
        return self.Get_Frequency(self.active_channel)

    def Get_Exposure(self,channel):
        Exposure = self._wlmData.GetExposureNum(channel,1,0)
        return Exposure

    def Set_Exposure(self,channel,exposure):
        self._wlmData.SetExposureNum(channel,1,exposure)

    def do_get_integration_time(self):
        return self.Get_Exposure(self.active_channel)

    def do_set_integration_time(self,integration_time):
        self.Set_Exposure(self.active_channel,integration_time)

    def do_set_active_channel(self,channel):
        self.active_channel = channel

    def do_get_active_channel(self):
        return self.active_channel

    def Set_SwitcherMode(self,mode):
        self._wlmData.SetSwitcherMode(mode)

    def Get_SwitcherMode(self):
        mode = self._wlmData.GetSwitcherMode(0)
        return mode

    def Get_SwitcherChannel(self):
        channel = self._wlmData.GetSwitcherChannel(0)
        return channel

    def Set_SwitcherSignalStates(self,signal,use):
        self._wlmData.SetSwitcherSignalStates(signal,use,use)

    def Set_ExposureMode(self,mode):
        self._wlmData.SetExposureMode(mode)

    def Get_Temperature(self):
        Temperature = self._wlmData.GetTemperature(c_double(0))
        return Temperature

    def do_get_temperature(self):
        return self.Get_Temperature()

    def get_channel_frequency(self, channel):
        Frequency = self._wlmData.GetFrequencyNum(channel,c_double(0))
        if Frequency != 0:
            self._last_valid[channel-1] = Frequency
        else:
            Frequency = self._last_valid[channel-1]
        return Frequency

    def get_channel_wavelength(self, channel):
        Wavelength = self._wlmData.GetWavelengthNum(channel, c_double(0))
        return Wavelength

