# scontel_dev.py -- the low-level library that interacts with SCONTEL DLL
# David Christle - <christle@uchicago.edu> 2015
#


import ctypes
import numpy as np
import logging
import math
import time


from instrument import Instrument
import pickle
from time import sleep, time
import types

import qt
from data import Data


# This is a MEASDATA structure that the SCONTEL biasbox expects to be passed via
# a pointer to the function. I got this information from the Preferences_RUS.pdf
# manual, which is in Russian, after I put it through Google Translate.

class MEASDATA(ctypes.Structure):
    _fields_ = [
        ('I1', ctypes.c_float),
        ('U1', ctypes.c_float),
        ('I2', ctypes.c_float),
        ('U2', ctypes.c_float),
        ('P', ctypes.c_float),
        ('T', ctypes.c_float),
        ('R', ctypes.c_float),
        ('BATP', ctypes.c_ushort),
        ('BATN', ctypes.c_ushort),
        ('HEATER', ctypes.c_float),
        ('STATUS', ctypes.c_char),
        ('BBERROR', ctypes.c_char)
        ]

class CONFIGDATA(ctypes.Structure):
    _fields_ = [
        ('I1', ctypes.c_float),
        ('U1', ctypes.c_float),
        ('I2', ctypes.c_float),
        ('U2', ctypes.c_float),
        ('HEATER', ctypes.c_float),
        ('STATUS', ctypes.c_ubyte)
        ]

class SCONTEL_BiasBox(Instrument):

    def __init__(self, name):
        logging.info(__name__ + ' : Initializing SCONTEL SNSPD instrument')
        Instrument.__init__(self, name, tags=['physical'])
        self._bl = ctypes.windll.LoadLibrary('C:\\measuring\\qtlab\\instrument_plugins\\_Scontel\\biasbox.dll')
        self._bl.bb_Open.restype = ctypes.c_char
        self._bl.bb_Close.restype = ctypes.c_char
        self._bl.bb_LVGetData.restype = ctypes.c_uint
        self._bl.bb_LVGetData.argtypes = [ctypes.POINTER(MEASDATA)]
        self._bl.bb_GetData.restype = ctypes.c_char
        self._bl.bb_GetData.argtypes = [ctypes.POINTER(MEASDATA)]
        self._bl.bb_PutData.restype = ctypes.c_char
        self._bl.bb_Short.restype = ctypes.c_char
        self._bl.bb_Mode.restype = ctypes.c_char
        self._bl.bb_Value.restype = ctypes.c_char


        self.add_function('bb_Open')
        self.add_function('bb_SetZero')
        self.add_function('bb_GetData')
        self.add_function('bb_Close')
        return


    def bb_Open(self):

        ret = self._bl.bb_Open()
        print 'ret is %s' % ord(ret)
        return

    def bb_Close(self):

        dev_id = self._bl.bb_Close()
        print 'dev_id is %s' % ord(dev_id)
        self._dev = dev_id
        return dev_id
    def bb_SetZero(self, channel, state):
        # int8_t bb_Short(uint8_t num, uint8_t st);
        ret = self._bl.bb_Short(ctypes.c_ubyte(channel), ctypes.c_ubyte(state))
        print 'ret is %s' % ord(ret)
        return
    def bb_GetData(self):
        # int16_t bb_LVGetData(int8_t *arg1);
        output_md = MEASDATA()
        self._gdcallback = self._bl.bb_GetData(output_md)
        print 'ret is: %s' % self._gdcallback
        print 'I1 %.1f U1 %.1f I2 %.1f U2 %.1f P %.1f T %.1f R %.1f BATP %d BATN %d' % (output_md.I1, output_md.U1, output_md.I2, output_md.U2, output_md.P, output_md.T, output_md.R, output_md.BATP, output_md.BATN)
        return
    def GetData(self):
        self.bb_Open()
        self.bb_GetData()
        self.bb_Close()
        return

    def __del__(self):
        print 'removing routine running...'

        return


    def open(self):
        return



    def is_open(self):
        return self._is_open




