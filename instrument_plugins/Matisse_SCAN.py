from instrument import Instrument
import visa
import types
from pyvisa import vpp43
import qt

class Matisse_SCAN(Instrument):

    def __init__(self, name, address):
        Instrument.__init__(self, name)

        self._address = address
        self._visa = visa.instrument(self._address)
        self._adwin_fpar=38

        self.add_parameter('value',
            flags=Instrument.FLAG_GETSET,
            type=types.FloatType,
            units='V',
            minval=0,maxval=0.65)

    def do_get_value(self):
        vpp43.lock(self._visa.vi,vpp43.VI_EXCLUSIVE_LOCK,5000)
        ret_str=self._visa.ask('SCAN:NOW?')
        vpp43.unlock(self._visa.vi)
        return float(ret_str.split(':SCAN:NOW: ')[1])

    #def do_set_value(self,val):
    #    vpp43.lock(self._visa.vi,vpp43.VI_EXCLUSIVE_LOCK,5000)
    #    w_str='SCAN:NOW%.12f' %(val)
    #    self._visa.write(w_str)
    #    vpp43.unlock(self._visa.vi)
    #
    def do_set_value(self,val):
        qt.instruments['physical_adwin'].Set_FPar(self._adwin_fpar,val)
