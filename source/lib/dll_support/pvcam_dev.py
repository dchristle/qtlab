# pvcam_dev.py -- the low-level library that interacts directly with pvcam's dll
# David Christle - <christle@uchicago.edu> 2015
# Alex Crook - <acrook@uchicago.edu> 2015
#
# several parts of this code are adapted from the odemis library

import ctypes
import numpy as np
import logging
import math
import time

pvlib = ctypes.windll.pvcam32

PARAM_TEMP = 16908813
PARAM_TEMP_SETPOINT = 16908814
PARAM_PREEXP_CLEANS = 184680802
PARAM_GAIN_INDEX = 16908800
PARAM_EXP_TIME = 100859905
ATTR_CURRENT = 0
ATTR_AVAIL = 8
ATTR_DEFAULT = 5
ATTR_MIN = 3
ATTR_MAX = 4
ATTR_INCREMENT = 6
ATTR_TYPE = 2
ATTR_COUNT = 1
OPEN_EXCLUSIVE = 0

# readout port options
PARAM_READOUT_PORT = 151126263
READOUT_PORT_LOW_NOISE = 2
READOUT_PORT_HIGH_CAP = 3
READOUT_PORT1 = 0
READOUT_PORT_MULT_GAIN = 0
READOUT_PORT_NORMAL = 1

# acquisition mode
PARAM_PMODE = 151126540
PMODE_NORMAL = 0

# gain index parameter
PARAM_GAIN_INDEX = 16908800

# sensor size parameters
PARAM_SER_SIZE = 100794426
PARAM_PAR_SIZE = 100794425

# readout rate
PARAM_SPDTAB_INDEX = 16908801
PARAM_PIX_TIME = 100794884

# PVCAM library types - used for when asking what type a parameter is
TYPE_CHAR_PTR = 13
TYPE_INT8 = 12
TYPE_INT16 = 1
TYPE_INT32 = 2
TYPE_UNS32 = 7
TYPE_UNS8 = 5
TYPE_UNS16 = 6
TYPE_UNS32 = 7
TYPE_UNS64 = 8
TYPE_ENUM = 9 # Variable c_int '9'
TYPE_FLT64 = 4
TYPE_BOOLEAN = 11
TYPE_VOID_PTR_PTR = 15
TYPE_VOID_PTR = 14

# dictionary to convert PVCAM type to ctypes type
pv_type_to_ctype = {
         TYPE_INT8: ctypes.c_int8,
         TYPE_INT16: ctypes.c_int16,
         TYPE_INT32: ctypes.c_int32,
         TYPE_UNS8: ctypes.c_uint8,
         TYPE_UNS16: ctypes.c_uint16,
         TYPE_UNS32: ctypes.c_uint32,
         TYPE_UNS64: ctypes.c_uint64,
         TYPE_FLT64: ctypes.c_double,
         TYPE_BOOLEAN: ctypes.c_byte,
         TYPE_ENUM: ctypes.c_uint32,
         }

# TIMED_MODE = 0 is the integer corresponding to the exposure mode where
# we let the camera just expose for a fixed duration, software timed, and stop
TIMED_MODE = 0
PARAM_READOUT_TIME = 67240115

READOUT_COMPLETE = 3
ACQUISITION_IN_PROGRESS = 5
READOUT_IN_PROGRESS = 2
EXPOSURE_IN_PROGRESS = 1
# make a tuple out of these, to search through later.
STATUS_IN_PROGRESS = (ACQUISITION_IN_PROGRESS, EXPOSURE_IN_PROGRESS,
                      READOUT_IN_PROGRESS)



uns16 = ctypes.c_ushort

class rgn_type(ctypes.Structure):
    _fields_ = [
        ('s1', uns16),
        ('s2', uns16),
        ('sbin', uns16),
        ('p1', uns16),
        ('p2', uns16),
        ('pbin', uns16),
        ]



class PVCAMDevice():

    def __init__(self):

        self._is_open = False


        self.initialize()
        self.get_version()
        self.get_cam_total()
        self._camname = self.get_cam_name(0)
        self.open()

        # Get the size of the entire sensor
        self._resolution = self.get_sensor_size()
        # Set the image rectangle to be the size of the entire sensor
        self._image_rect = (0, self._resolution[0] - 1, 0, self._resolution[1] - 1)
        self._binning = (1, 1)
        # Set to simple acquisition mode
        self.set_param(PARAM_PMODE, PMODE_NORMAL)
        # Set a default exposure time
        self.set_exposure_time(1.0)


        return

    def __del__(self):
        print 'removing routine running...'
        self.close()
        self.uninitialize()
        return

    def pv_check(self):
        error_code_string = ctypes.create_string_buffer(256)
        rs_bool = pvlib.pl_error_message(pvlib.pl_error_code(), error_code_string)
        if error_code_string.value != 'No error':
            print 'Error: %s' % error_code_string.value
        return error_code_string.value

    def open(self):
        camera_handle = ctypes.c_int16()
        ret = pvlib.pl_cam_open(self._camname, ctypes.byref(camera_handle), OPEN_EXCLUSIVE)
        if ret == 0:
            'Camera %s successfully opened.' % self._camname
        else:
            'Could not open camera %s!' % self._camname
        self._handle = camera_handle
        self.get_cam_diags()
        if ret == 0:
            self._is_open = True
        return self.pv_check()

    def close(self):
        self._is_open = False
        ret = pvlib.pl_cam_close(self._handle)
        return self.pv_check()

    def is_open(self):
        return self._is_open

    def initialize(self):
        '''
        Initialize PVCam library
        '''
        ret = pvlib.pl_pvcam_init()
        if ret != 0:
            print 'Return code from PVCAM library initialization is %d' % ret
        return self.pv_check()

    def uninitialize(self):
        '''
        Uninitialize PVCam library
        '''
        rs_bool = pvlib.pl_pvcam_uninit()

        return rs_bool


    def get_version(self):
        versionptr = ctypes.c_ushort()
        rs_bool = pvlib.pl_pvcam_get_ver(ctypes.byref(versionptr))
        self._version = versionptr.value
        print 'Successfully loaded PVCAM version %s' % hex(self._version)
        return self.pv_check()

    def get_cam_total(self):
        total_cams = ctypes.c_short(0)
        rs_bool = pvlib.pl_cam_get_total(ctypes.byref(total_cams))
        return self.pv_check()

    def get_cam_name(self, cam_number):
        assert(cam_number >= 0)
        camname = ctypes.create_string_buffer(32)
        rs_bool = pvlib.pl_cam_get_name(cam_number,camname)
        return camname.value

    def get_cam_diags(self):
        rs_bool = pvlib.pl_cam_get_diags(self._handle)
        self.pv_check()
        return

    def get_temperature_setpoint(self):
        current_temperature = ctypes.c_int16()
        rs_bool = pvlib.pl_get_param(self._handle, ctypes.c_int(PARAM_TEMP_SETPOINT), ctypes.c_int(ATTR_CURRENT), ctypes.byref(current_temperature))
        self.pv_check()
        return float(current_temperature.value*1.0/100.0)

    def get_temperature(self):
        current_temperature = ctypes.c_int16()
        rs_bool = pvlib.pl_get_param(self._handle, ctypes.c_int(PARAM_TEMP), ctypes.c_int(ATTR_CURRENT), ctypes.byref(current_temperature))
        self.pv_check()
        return float(current_temperature.value*1.0/100.0)

    def set_temperature_setpoint(self, temperature):
        new_setpoint = ctypes.c_short(int(temperature*100.0))
        rs_bool = pvlib.pl_set_param(self._handle, ctypes.c_int(PARAM_TEMP_SETPOINT), ctypes.byref(new_setpoint))
        return self.pv_check()

    def get_gain_index(self):
        current_gain_index = ctypes.c_int16()
        rs_bool = pvlib.pl_get_param(self._handle, ctypes.c_int(PARAM_GAIN_INDEX), ctypes.c_int(ATTR_CURRENT), ctypes.byref(current_gain_index))
        self.pv_check()
        return current_gain_index.value

    def set_gain_index(self, gainindex):
        new_gain_index = ctypes.c_int16(int(gainindex))
        rs_bool = pvlib.pl_set_param(self._handle, ctypes.c_int(PARAM_GAIN_INDEX), ctypes.byref(new_gain_index))
        return self.pv_check()

    def set_exposure_time(self, exp_time):
        if float(exp_time) > 0.0:
            self._exp_time = float(exp_time)
        else:
            self._exp_time = 0.01
            print 'Exposure time was <= 0, set to 0.01 s'
        return

    def get_exposure_time(self):
        return self._exp_time

    def exp_init_seq(self):
        rs_bool = pvlib.pl_exp_init_seq()
        print 'Initializing the sequence now...'
        return self.pv_check()

    def exp_setup_seq(self):
        exposure = self._exp_time
        # instantiate a 'rgn_type' struct, defined above
        region = rgn_type()
        # region is 0 indexed
        region.s1, region.s2, region.p1, region.p2 = self._image_rect
        # set binning, also hardcoded for now
        region.sbin, region.pbin = self._binning

        self._size = ((self._image_rect[1] - self._image_rect[0] + 1) // self._binning[0],
                (self._image_rect[3] - self._image_rect[2] + 1) // self._binning[1])
        print 'size is %s %s' % (self._size[0], self._size[1])
        print 'region is %s %s %s %s' % (region.s1, region.s2, region.p1, region.p2)
        # initialize a blank uint32 so pvcam can tell us the byte stream size
        blength = ctypes.c_uint32()
        # convert the exposure time into milliseconds, which pvcam wants
        exp_ms = int(math.ceil(exposure * 1e3)) # ms
        print 'exp in ms is %s' % exp_ms
        # 1 image, with 1 region
        rs_bool = pvlib.pl_exp_setup_seq(self._handle, 1, 1, ctypes.byref(region), TIMED_MODE, exp_ms, ctypes.byref(blength))

        print 'acquisition setup report buffer size of %d' % blength.value
        # allocate a buffer of blength.value bytes
        self._cbuffer = self.allocate_buffer(blength.value)
        # get the actual readout time
        current_readout_time = ctypes.c_int16()
        self._readout = self.get_param(PARAM_READOUT_TIME) * 1e-3
        print 'Exposure of %s s, readout %s s' % (exp_ms * 1e-3, self._readout)
        return

    def allocate_buffer(self, length):
        cbuffer = (ctypes.c_uint16 * (length // 2))() # empty array
        return cbuffer

    def exp_start_seq(self):
        start = time.time()

        expected_end = start + self._exp_time + self._readout
        timeout = expected_end + 2.0 # add a 2.0 second timeout
        pvlib.pl_exp_start_seq(self._handle, self._cbuffer)
        time.sleep(0.5)
        # now check status
        status = self.exp_check_status()

        while status in STATUS_IN_PROGRESS:
            now = time.time()
            ##print 'now is %s and %s' % (now, now-start)
            if now > timeout:
                raise IOError("Timeout after %g s" % (now - start))
            # check if we should stop (sleeping less and less)
            left = expected_end - now
            ##print 'status is %s' % status
            status = self.exp_check_status()
            ##print 'status is %s' % status
            time.sleep(0.1)


        if status != READOUT_COMPLETE:
            raise IOError("Acquisition status is unexpected %d" % status)
        # set this internal variable to cbuf if everything went OK so far
        logging.debug('image acquired successfully after %g s' % (time.time() - start))
        print 'image acquired successfully after %g s' % (time.time() - start)

        return

    def exp_check_status(self):
        status = ctypes.c_int16()
        byte_cnt = ctypes.c_uint32()
        pvlib.pl_exp_check_status(self._handle, ctypes.byref(status), ctypes.byref(byte_cnt))
        return status.value
    def exp_finish_seq(self):
        pvlib.pl_exp_finish_seq(self._handle, self._cbuffer, None)
        pvlib.pl_exp_uninit_seq()

    def buffer_as_array(self):
        """
        Converts the buffer allocated for the image as an ndarray. zero-copy
        size (2-tuple of int): width, height
        return an ndarray
        """
        p = ctypes.cast(self._cbuffer, ctypes.POINTER(ctypes.c_uint16))
        ndbuffer = np.ctypeslib.as_array(p, (self._size[1], self._size[0])) # numpy shape is H, W
        return ndbuffer
    def get_sensor_size(self):
        """
        return 2-tuple (int, int): width, height of the detector in pixel
        """
        width = self.get_param(PARAM_SER_SIZE, ATTR_DEFAULT)
        height = self.get_param(PARAM_PAR_SIZE, ATTR_DEFAULT)
        return width, height

    def get_param(self, param, value=ATTR_CURRENT):
        """
        Read the current (or other) value of a parameter.
        Note: for the enumerated parameters, this it the actual value, not the
        index.
        param (int): parameter ID (cf pv.PARAM_*)
        value (int from pv.ATTR_*): which value to read (current, default, min, max, increment)
        return (value): the value of the parameter, whose type depend on the parameter
        """
        assert(value in (ATTR_DEFAULT, ATTR_CURRENT, ATTR_MIN,
                         ATTR_MAX, ATTR_INCREMENT))

        # find out the type of the parameter
        tp = ctypes.c_uint16()
        pvlib.pl_get_param(self._handle, param, ATTR_TYPE, ctypes.byref(tp))
        if tp.value == TYPE_CHAR_PTR:
            # a string => need to find out the length
            count = ctypes.c_uint32()
            pvlib.pl_get_param(self._handle, param, ATTR_COUNT, ctypes.byref(count))
            content = ctypes.create_string_buffer(count.value)
        elif tp.value in pv_type_to_ctype:
            content = pv_type_to_ctype[tp.value]()
        elif tp.value in (TYPE_VOID_PTR, TYPE_VOID_PTR_PTR):
            raise ValueError("Cannot handle arguments of type pointer")
        else:
            raise NotImplementedError("Argument of unknown type %d" % tp.value)

        # read the parameter
        pvlib.pl_get_param(self._handle, param, value, ctypes.byref(content))
        return content.value
    def set_param(self, param, value):
        """
        Write the current value of a parameter.
        Note: for the enumerated parameter, this is the actual value to set, not
        the index.
        param (int): parameter ID (cf pv.PARAM_*)
        value (should be of the right type): value to write
        Warning: it seems to not always complain if the value written is incorrect,
        just using default instead.
        """
        # find out the type of the parameter
        tp = ctypes.c_uint16()
        pvlib.pl_get_param(self._handle, param, ATTR_TYPE, ctypes.byref(tp))
        if tp.value == TYPE_CHAR_PTR:
            content = str(value)
        elif tp.value in pv_type_to_ctype:
            content = pv_type_to_ctype[tp.value](value)
        elif tp.value in (TYPE_VOID_PTR, TYPE_VOID_PTR_PTR):
            raise ValueError("Cannot handle arguments of type pointer")
        else:
            raise NotImplementedError("Argument of unknown type %d" % tp.value)

        pvlib.pl_set_param(self._handle, param, ctypes.byref(content))
        return

    def get_readout_index(self):
        return self.get_param(PARAM_SPDTAB_INDEX)

    def set_readout_index(self, ridx):
        self.set_param(PARAM_SPDTAB_INDEX, ridx)
        self.pv_check()
        return

    def get_readout_rates(self):
        # It depends on the port (output amplifier), bit depth, which we
        # consider both fixed.
        # PARAM_PIX_TIME (ns): the time per pixel
        # PARAM_SPDTAB_INDEX: the speed index
        # The only way to find out the rate of a speed, is to set the speed, and
        # see the new time per pixel.
        # Note: setting the spdtab idx resets the gain

        mins = self.get_param(PARAM_SPDTAB_INDEX, ATTR_MIN)
        maxs = self.get_param(PARAM_SPDTAB_INDEX, ATTR_MAX)
        # save the current value
        current_spdtab = self.get_param(PARAM_SPDTAB_INDEX)
        current_gain = self.get_param(PARAM_GAIN_INDEX)

        rates = {}
        for i in range(mins, maxs + 1):
            # Try with this given speed tab
            self.set_param(PARAM_SPDTAB_INDEX, i)
            pixel_time = self.get_param(PARAM_PIX_TIME) # ns
            if pixel_time == 0:
                logging.warning("Camera reporting pixel readout time of 0 ns!")
                pixel_time = 1
            rates[i] = 1 / (pixel_time * 1e-9)

        # restore the current values
        self.set_param(PARAM_SPDTAB_INDEX, current_spdtab)
        self.set_param(PARAM_GAIN_INDEX, current_gain)
        return rates
    def get_readout_ports(self):
        tp = ctypes.c_uint16()
        n_ports = pvlib.pl_get_param(self._handle, PARAM_READOUT_PORT, ATTR_COUNT, ctypes.byref(tp))
        self.pv_check()
        aos = self.get_enum_available(PARAM_READOUT_PORT)
        return aos
    def get_gains(self):
        ming = self.get_param(PARAM_GAIN_INDEX, ATTR_MIN)
        maxg = self.get_param(PARAM_GAIN_INDEX, ATTR_MAX)
        gains = {}
        for i in range(ming, maxg + 1):
            # seems to be correct for PIXIS and ST133
            gains[i] = 2 ** (i - 1)
        return gains
    def set_low_noise_readout(self):
        aos = self.get_enum_available(PARAM_READOUT_PORT)
        if READOUT_PORT_LOW_NOISE in aos:
            print 'Found low noise readout option, setting it.'
            self.set_param(PARAM_READOUT_PORT, READOUT_PORT_LOW_NOISE)
        else:
            print 'Did not find low noise readout option, setting port to default.'
            ao = self.get_param(PARAM_READOUT_PORT, ATTR_DEFAULT)
            self.set_param(PARAM_READOUT_PORT, ao)
        self._output_amp = self.get_param(PARAM_READOUT_PORT)
        return

    def get_enum_available(self, param):
        """
        Get all the available values for a given enumerated parameter.
        param (int): parameter ID (cf pv.PARAM_*), it must be an enumerated one
        return (dict (int -> string)): value to description
        """
        count = ctypes.c_uint32()
        pvlib.pl_get_param(self._handle, param, ATTR_COUNT, ctypes.byref(count))

        ret = {} # int -> str
        for i in range(count.value):
            length = ctypes.c_uint32()
            content = ctypes.c_uint32()
            pvlib.pl_enum_str_length(self._handle, param, i, ctypes.byref(length))
            desc = ctypes.create_string_buffer(length.value)
            pvlib.pl_get_enum_param(self._handle, param, i, ctypes.byref(content),
                                         desc, length)
            ret[content.value] = desc.value
        return ret
