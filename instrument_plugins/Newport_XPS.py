# QtLab driver for Newport XPS stage positioner
# David Christle <christle@uchicago.edu>, November 2013

from instrument import Instrument
import types

# These XPS Q8 drivers are provided by Newport, accessible from the XPS
# controller by going to ftp://192.168.0.254 and looking under the Public/Drivers
# directory.

import XPS_Q8_drivers
import logging
import time

class Newport_XPS(Instrument):

    def __init__(self, name, address, reset = False):
        # Looks like Wolfgang is using the physical tag instead of positioner
        # Since our stage is most similar to their Attocube (i.e. the axes are
        # independent), I changed it to physical.
        Instrument.__init__(self, name, tags=['physical'])
        logging.info(__name__ + ' : Initializing instrument XPS stage')

        # Create internal Newport XPS object to utilize Newport's existing
        # Python codebase.
        self._xps = XPS_Q8_drivers.XPS()

        # Connect using TCP to XPS, store socket ID
        self._socketId = self._xps.TCP_ConnectToServer(address, 5001, 20)

        if(self._socketId ==-1):
            logging.error(__name__ +  'Connection to XPS failed, check IP & Port')




        # Instrument parameters
        self.add_parameter('abs_position',
            type=types.FloatType,
            channels=('X', 'Y', 'Z'),
            flags=Instrument.FLAG_GETSET,
            minval=-12.5, maxval=12.5,
            units='mm',
            format='%.06f')
##        self.add_parameter('velocity',
##            type=types.TupleType,
##            flags=Instrument.FLAG_SET|Instrument.FLAG_SOFTGET,
##            format='%.1f, %.01f, %.01f')
##        self.add_parameter('channels',
##            type=types.IntType,
##            flags=Instrument.FLAG_SET|Instrument.FLAG_SOFTGET)
##
##        self.set_channels(channels)
        # Error checking function

        # Instrument functions
        self.add_function('home', channels=('X', 'Y', 'Z'))
##        self.add_function('stop')
##        self.add_function('move_abs')
        if reset:
            self.reset()
        else:
            self.get_all()
    def _displayErrorAndClose(self, errorCode, APIName):
        if (errorCode !=-2) and(errorCode !=-108):
            [errorCode2, errorString] = self._xps.ErrorStringGet(self._socketId,
                errorCode)
            if(errorCode2 !=0):
               print APIName + ': ERROR '+ str(errorCode)
               logging.error(__name__ + APIName + ': ERROR '+ str(errorCode))
            else:
                logging.error(__name__ + APIName + ': '+ errorString)
        else:
            if (errorCode ==-2):
                logging.error(__name__ + APIName + ': TCP timeout')
            if(errorCode ==-108):
                logging.error(__name__ + APIName + ': The TCP/IP connection\
                was closed by an administrator')
        return
    def get_all(self):
        '''
        Reads all relevant parameters from instrument

        Input:
            None

        Output:
            None
        '''
        logging.info(__name__ + 'Get all relevant data from device')
        for chan in 'X', 'Y', 'Z':
            self.get('abs_position%s' % chan)


    def _channel_to_positioner(self, channel):
        # Hard code the positioner strings versus axis. Not sure how to do this
        # in a more "qt"/Pythonic way, but this will do for now till someone
        # figures out how.
        #
        # Update -- it appears Wolfgang uses the "qtconfig" file; we should
        # look into that. It is probably used for defining all these little
        # things.


        nummap = {'X': 'Group1.Pos',
                'Y': 'Group2.Pos',
                'Z': 'Group3.Pos'}
        return nummap.get(channel.upper(), None)

    def do_set_abs_position(self, position, channel):
        [errorCode, returnString] = self._xps.GroupMoveAbsolute(self._socketId,
        self._channel_to_positioner(channel), [position])
        if(errorCode != 0):
            self._displayErrorAndClose(errorCode, 'GroupMoveAbsolute')

        else:
            logging.debug('Positioner '+ self._channel_to_positioner(channel) + ' is in position '+
            str(position))

        return
    def do_get_abs_position(self, channel):
        [errorCode, currentPosition] = self._xps.GroupPositionCurrentGet(self._socketId, self._channel_to_positioner(channel), 1)
        if(errorCode != 0):
            self.displayErrorAndClose(errorCode, 'GroupPositionCurrentGet')
        return float(currentPosition)

##    def do_set_velocity(self, velocity, channel):
##
##        [errorCode, returnString] =self._xps.GroupMoveAbsolute(self._socketId,
##        self._channel_to_positioner(channel), position)
##
##        if(errorCode != 0):
##            displayErrorAndClose(errorCode, 'GroupPositionCurrentGet')
##
##        else:
##            logging.debug('Positioner '+ positioner + ' is in position '+
##            str(currentPosition))
##
##        return
##    def do_get_velocity(self, channel):
##        [errorCode, currentVelocity] = self._xps.GroupVelocityCurrentGet(self._socketId, self._channel_to_positioner(channel), 1)
##        if(errorCode != 0):
##            displayErrorAndClose(errorCode, 'GroupPositionCurrentGet')
##        return float(currentPosition)

    def home(self, channel):
        [errorCode, returnedString] = self._xps.GroupHomeSearch(self._socketId, self._channel_to_positioner(channel))
        if(errorCode != 0):
            self._displayErrorAndClose(errorCode, 'GroupHomeSearch')
        return
