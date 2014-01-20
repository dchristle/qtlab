from instrument import Instrument
import visa
import types
import logging
import re
import math

class NewportAgilisUC2(Instrument):

    def __init__(self, name, address):
        Instrument.__init__(self, name)

        self._address = address
        self._visa = visa.instrument(self._address,
                        baud_rate=921600, data_bits=8, stop_bits=1,
                        parity=visa.no_parity, term_chars='\r')
        self.EnterRemoteMode()

    def SetChannel(self,channel):
        self._visa.write('CC'+str(channel))

    def EnterRemoteMode(self):
        self._visa.write('MR')
        
    def ExitRemoteMode(self):
        self._visa.write('ML')

    def Jog(self,axis = 1,speed = 0):
        self._visa.write(str(axis)+'JA'+str(speed))

#    def MeasureAbsolutePosition(self,axis):
#        return self._visa.ask(str(axis)+'MA')

#    def MoveAbsolutePosition(self,axis,position):
#        self._visa.write(str(axis)+'PA'+str(position))

    def MoveRelative(self,axis,steps):
        self._visa.write(str(axis)+'PR'+str(steps))

    def StopMotion(self,axis,steps):
        self._visa.write(str(axis)+'ST')

    def ZeroPosition(self,axis, steps):
        self._visa.write(str(axis)+'ZP')

    def GetControllerVersion(self):
        return self._visa.ask('VE')

    def TellError(self):
        return self._visa.ask('TE')

    def TellHardwareStatus(self):
        return self._visa.ask('PH')

    def Reset(self):
        self._visa.write('RS')

       

