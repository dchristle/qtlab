# Coherent Verdi G - USB control
# David Christle <christle@uchicago.edu>, 2013
#
#
# This file allows us to control the Verdi G series pump laser over USB. The
# class uses ctypes to interface with the CohrHOPS.dll file, available with
# Coherent's OPSL software that comes on CD with the laser.


from instrument import Instrument
import types
import ctypes
import logging
import time

# hardcoded DLL file, works for now.
cohr = ctypes.windll.LoadLibrary('C:\measuring\measurement\lib\dll_support\CohrHOPS.dll')


class Coherent_VerdiG_USB(Instrument):

    def __init__(self, name, reset=False):
        Instrument.__init__(self, name, tags=['physical'])

        # Run get devices & set handle to first device handle
        self.get_devices()


        # Add functions
        self.add_function('reset')
        self.add_function('get_all')
#        self.add_function('optimize_LBO')
#        self.add_function('optimize_diodes')

        self.add_parameter('tgt_power',
            type=types.FloatType, units='W', format='%.04f',
            flags=Instrument.FLAG_GETSET, minval=0, maxval=7.05,
            maxstep=0.25, stepdelay=5000)
        self.add_parameter('output_power',
            type=types.FloatType, units='W', format='%.03f',
            flags=Instrument.FLAG_GET)
        self.add_parameter('cmode',
            type=types.IntType, format_map={1: 'Current', 0: 'Light'},
            flags=Instrument.FLAG_GET)
        self.add_parameter('REM',
            type=types.IntType, format_map={1: 'Remote', 0: 'Local'},
            flags=Instrument.FLAG_GETSET)
        self.add_parameter('current',
            type=types.FloatType, units='A', format='%.01f',
            flags=Instrument.FLAG_GET)
        self.add_parameter('Tmain',
            type=types.FloatType, units='C', format='%.02f',
            flags=Instrument.FLAG_GET)
        self.add_parameter('Tetalon',
            type=types.FloatType, units='C', format='%.02f',
            flags=Instrument.FLAG_GET)
        self.add_parameter('TSHG',
            type=types.FloatType, units='C', format='%.02f',
            flags=Instrument.FLAG_GET)
        self.add_parameter('TBRF',
            type=types.FloatType, units='C', format='%.02f',
            flags=Instrument.FLAG_GET)
        self.add_parameter('headhours',
            type=types.FloatType, units='h', format='%.02f',
            flags=Instrument.FLAG_GET)
        self.add_parameter('kswcmd',
            type=types.IntType, format_map={1: 'On', 0: 'Off'},
            flags=Instrument.FLAG_GETSET)
        self.add_parameter('faultcode',
            type=types.IntType,
            flags=Instrument.FLAG_GET)



        if reset:
            self.reset()
        else:
            self.get_all()

    def reset(self):
        self.get_all()

    def get_all(self):
        self.get_Tmain()
        self.get_TSHG()
        self.get_TBRF()
        self.get_Tetalon()
        self.get_headhours()
        self.get_cmode()
        self.get_output_power()
        self.get_tgt_power()
        self.get_REM()
        self.get_kswcmd()
        self.get_faultcode()
        self.get_current()

    def CHK(self, err):
        if err != 0:
            logging.error(__name__ +'Coherent DLL call failed with error code %s' % err)
    def get_devices(self):

        # This was somewhat complicated to figure out & prevented me from
        # getting this to work for quite a while. I believe what happens here
        # is that we create a set of Python arrays of ctypes c_ulong types.
        # Then we use the cast function on these arrays with a pointer to the
        # ctypes.c_ulong type, which casts the array into a C array that the
        # function requires. Without this extra cast step, the behavior was that
        # the entire Python interpreter would crash.

        LPDWORDPTR = ctypes.POINTER(ctypes.c_ulong)
        vgDevCon = (ctypes.c_ulong*20)()
        vgNDevCon = ctypes.c_ulong()
        vgDevAdded = (ctypes.c_ulong*20)()
        vgNDevAdded = ctypes.c_ulong()
        vgDevRemoved = (ctypes.c_ulong*20)()
        vgNDevRemoved = ctypes.c_ulong()

        vgDevCon_arr = ctypes.cast(vgDevCon, LPDWORDPTR)
        vgDevAdded_arr = ctypes.cast(vgDevAdded, LPDWORDPTR)
        vgDevRemoved_arr = ctypes.cast(vgDevCon, LPDWORDPTR)
        # For some reason, it seems like we must do the get DLL... not sure.
        dllversionstring = ctypes.create_string_buffer(128)
        self.CHK(cohr.CohrHOPS_GetDLLVersion(dllversionstring))

        self.CHK(cohr.CohrHOPS_CheckForDevices(vgDevCon_arr, ctypes.byref(vgNDevCon),
             vgDevAdded_arr, ctypes.byref(vgNDevAdded), vgDevRemoved_arr,
             ctypes.byref(vgNDevRemoved)))
        print 'Checked for Verdi devices.'
        self.Ndev = vgNDevCon.value
        print 'Found %s device(s).' % self.Ndev
        logging.debug(__name__ + 'Got the data out. Number of devices connected: %s' % vgNDevCon.value)
        # Here we just get the first device and use that handle - this is hard
        # coding in something that might be variable in the future.
        self.handle = vgDevCon[0]
        # Now initialize the handle for use
        headtype = ctypes.create_string_buffer(100)
        self.CHK(cohr.CohrHOPS_InitializeHandle(vgDevCon_arr[0],headtype))
        logging.info(__name__ + 'Verdi G handle initialized, headtype: %s, DLL version: %s' % (headtype.value, dllversionstring.value))
        return

    def _query(self, cmd):
        # Create string buffers for command and response
        cmd_buf = ctypes.c_char_p(cmd)
        rsp_buf = ctypes.create_string_buffer(100)
        logging.debug(__name__ + ': Now sending command %s to Verdi...' % cmd)
        self.CHK(cohr.CohrHOPS_SendCommand(self.handle,cmd_buf,rsp_buf))
        logging.debug(__name__ + ': Response is: %s' % rsp_buf.value)
        return rsp_buf.value

    def do_get_output_power(self):
        s = self._query('?P')
        return float(s)

    def do_get_cmode(self):
        s = self._query('?CMODE')
        return int(s)

    def do_get_REM(self):
        s = self._query('?REM')
        return int(s)

    def do_set_REM(self, rem):
        s = self._query('REM=%d' % rem)
        return True

    def do_get_kswcmd(self):
        s = self._query('?KSWCMD')
        return int(s)

    def do_set_kswcmd(self, ksw):
        if ksw == 1:
            self.set_tgt_power(0.0)
            # Wait and allow Verdi to cool a bit
            time.sleep(5)
            s = self._query('KSWCMD=%d' % ksw)
            # Wait again to allow Verdi to wake up
            time.sleep(8)
        elif ksw == 0:
            # Ensure the target power is zero
            self.set_tgt_power(0.0)
            # Wait and allow Verdi to cool a bit
            time.sleep(8)
            s = self._query('KSWCMD=%d' % ksw)

        return True

    def do_get_tgt_power(self):
        s = self._query('?PCMD')
        return float(s)

    def do_set_tgt_power(self, p):
        # Power is in Watts here
        self._query('PCMD=%.04f' % p)
        return True

    def do_get_Tmain(self):
        s = self._query('?TMAIN')
        return float(s)

    def do_get_Tetalon(self):
        s = self._query('?TETA')
        return float(s)

    def do_get_TSHG(self):
        s = self._query('?TSHG')
        return float(s)


    def do_get_TBRF(self):
        s = self._query('?TBRF')
        return float(s)

    def do_get_headhours(self):
        s = self._query('?HH')
        return float(s)


    def do_get_current(self):
        s = self._query('?C')
        return float(s)

    def do_get_faultcode(self):
        s = self._query('?FF')
        return int(s)
