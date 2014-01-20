from instrument import Instrument
import visa
import types
import logging
import re, qt
import math
import numpy as np

#====================================================================
#USEFUL VALUES:
#====================================================================
#Positive x (i.e. set_relative_position(+x)) rotates towards positive 
#degrees. Negative x rotates towards negative degrees.

class NewportAgilisUC2_v2(Instrument):

    def __init__(self, name, address,maxjog_cfg,maxpr_cfg,step_deg_cfg):
        Instrument.__init__(self, name)

        self._address = address
        self._visa = visa.instrument(self._address,
                        baud_rate=921600, data_bits=8, stop_bits=1,
                        parity=visa.no_parity, term_chars='\r')
        self._channels = (1,2)

        #calibrated to 5000 steps == 10 degrees
        #self.maxjog_cfg = { 1 : {'positive' : 1.000/0.989,
        #                         'negative' : 0.940/0.930},
        #                    2 : {'positive' : 0.995/0.984,
        #                         'negative' : 1.025/1.013},
        #                   }

        self.maxjog_cfg = maxjog_cfg
        #normalized to ~ 481 steps/degree
        # TODO is that actually used?
        self.maxpr_cfg  = maxpr_cfg

        #values provided here are in deg/step
        self.step_deg_cfg = step_deg_cfg

        #define the get and set functions of the positioner. order is 
        #according to the manual page 24.
        
        self.add_parameter('step_deg_cfg',
                flags=Instrument.FLAG_GET,
                type=types.DictType)
                
        self.add_parameter('jog_ch',
                flags=Instrument.FLAG_GETSET,
                type=types.IntType,
                channels = self._channels)

        self.add_parameter('position_ch',
                flags=Instrument.FLAG_GET,
                type=types.FloatType,
                channels = self._channels)
 
        self.add_parameter('mode', 
                flags=Instrument.FLAG_SET,
                type=types.StringType,
                format_map={'L': 'Local', 'R': 'Remote'})

        self.add_parameter('move_to_limit_ch',
                flags=Instrument.FLAG_SET,
                type=types.IntType,
                channels = self._channels)

        self.add_parameter('absolute_position_ch',
                flags=Instrument.FLAG_SET,
                type=types.IntType,
                channels = self._channels)

        self.add_parameter('limit_status',
                flags=Instrument.FLAG_GET,
                type=types.StringType)

        self.add_parameter('relative_position_ch',
                flags=Instrument.FLAG_GETSET,
                type=types.IntType,
                channels = self._channels)

        self.add_parameter('step_size_ch',
                flags=Instrument.FLAG_GETSET,
                type=types.IntType,
                channels = self._channels)

        self.add_parameter('error',
                flags=Instrument.FLAG_GET,
                type=types.StringType)

        self.add_parameter('noof_steps_ch',
                flags=Instrument.FLAG_GET,
                type=types.IntType,
                channels = self._channels)

        self.add_parameter('status_ch',
                flags=Instrument.FLAG_GET,
                type=types.StringType,
                channels = self._channels)

        self.add_parameter('firmware_version',
                flags=Instrument.FLAG_GET,
                type=types.StringType)

      
        #add functions to the QT instrument
        self.add_function('local')
        self.add_function('remote')
        self.add_function('reset')
        self.add_function('quick_scan')
        self.add_function('write_raw')

              
        #last things
        self.remote()
        #set speeds to max
        for k in self._channels:
            getattr(self, 'set_step_size_ch%d'%k)(50)
            getattr(self, 'set_step_size_ch%d'%k)(-50)


    #added functions
    def local(self):
        self.set_mode('L')

    def remote(self):
        self.set_mode('R')
        
    #define the get and set functions
    def do_get_step_deg_cfg(self):
        return self.step_deg_cfg
    
    def stop_moving(self, channel):
        """
        Stops the motion on the defined axis. Sets the state to ready.
        """
        print '%dST'%ch
        self._visa.write('%dST'%ch)


    def set_zero_position(self, channel):
        """
        Resets the step counter to zero. See TP command for further details.
        """
        self._visa.write('%dZP'%channel)
        print 'Zero position channel %d set to current position.'%channel


    def do_get_jog_ch(self, channel): #OK!
        """
        Returns the speed during a jog session.
        """
        jog_dict = {-4 : 'Negative direction, 666 steps/s at defined step amplitude.',
                    -3 : 'Negative direction, 1700 steps/s at max. step amplitude.',
                    -2 : 'Negative direction, 100 step/s at max. step amplitude.',
                    -1 : 'Negative direction, 5 steps/s at defined step amplitude.',
                    0 : 'No move, go to READY state.',
                    1 : 'Positive direction, 5 steps/s at defined step amplitude.',
                    2 : 'Positive direction, 100 steps/s at max. step amplitude.',
                    3 : 'Positive direction, 1700 steps/s at max. step amplitude.',
                    4 : 'Positive direction, 666 steps/s at defined step amplitude.'}

        try:
            [ch, rawans] = self._visa.ask_for_values('%dJA?'%channel)
            ans = jog_dict[rawans]
        except:
            ans = self.get_error()

        return ans

    def do_set_jog_ch(self, jogmode, channel): #OK!
        """
        Starts a jog motion at a defined speed or returns jog mode. 
        Defined steps are steps with step amplitude defined by the SU command 
        (default 16). Max. amplitude steps are equivalent to step amplitude 50:
        -4  Negative direction, 666 steps/s at defined step amplitude.
        -3  Negative direction, 1700 steps/s at max. step amplitude.
        -2  Negative direction, 100 step/s at max. step amplitude.
        -1  Negative direction, 5 steps/s at defined step amplitude.
        0   No move, go to READY state.
        1   Positive direction, 5 steps/s at defined step amplitude.
        2   Positive direction, 100 steps/s at max. step amplitude.
        3   Positive direction, 1700 steps/s at max. step amplitude.
        4   Positive direction, 666 steps/s at defined step amplitude.
        """
        self._visa.write('%dJA%d'%(channel,jogmode))

    def do_get_position_ch(self, channel): #DON'T USE WITH PR100
        """
        The MA command functions properly only with devices that feature a limit switch
        like models AG-LS25, AG-M050L and AG-M100L.
        """
        #ans = self._visa.ask('%dMA'%channel)
        #return ans
        pass

    def do_set_mode(self, mode): #OK!
        """
        To set the controller to local mode use 'L'. 
        To go to remote mode, use 'R'.
        In local mode the pushbuttons on the controller are enabled and all 
        commands that configure or operate the controller are disabled. 
        """        
        self._visa.write('M'+str(mode))

    def do_set_move_to_limit_ch(self, channel, jogmode): #DON'T USE WITH PR100
        """
        Starts a jog motion at a defined speed to the limit and stops 
        automatically when the limit is activated. See JA command for details.
        The MA command functions properly only with devices that feature a 
        limit switch like models AG-LS25, AG-M050L and AG-M100L.
        """
        #self._visa.write('%dMV%d'%(channel,jogmode))
        pass

    def do_get_absolute_position_ch(self, channel): #DON'T USE WITH PR100
        """
        This command functions properly only with devices that feature a 
        limit switch like models AG-LS25, AG-M050L and AG-M100L.
        """
        #ans = self._visa.ask('%dPA?'%channel)
        #return ans
        pass

    def do_set_absolute_position_ch(self, channel, target_position): #DON'T USE WITH PR100
        """
        This command functions properly only with devices that feature a 
        limit switch like models AG-LS25, AG-M050L and AG-M100L.
        The execution of the command can last up to 2 minutes.
        """
        #self._visa.write('%dPA%d'%(channel, target_position))
        pass

    def do_get_limit_status(self): #OK!
        """
        PH0 No limit switch is active
        PH1 Limit switch of channel #1 is active, limit switch of channel #2 is not active
        PH2 Limit switch of channel #2 is active, limit switch of channel #1 is not active
        PH3 Limit switch of channel #1 and channel #2 are active
        """        
        self._visa.write('PH')
        rawans = self._visa.read_values()[0]
        status_dict = {0 : 'No limit switch is active',
                1 : 'Limit switch of channel #1 is active, limit switch of channel #2 is not active',
                2 : 'Limit switch of channel #2 is active, limit switch of channel #1 is not active',
                3 : 'Limit switch of channel #1 and channel #2 are active'}

        return status_dict[rawans]

    def do_get_relative_position_ch(self,channel): #NOTE: don't understand why error

        ans = self._visa.ask_for_values('%dPR?'%channel)
        return ans

    def do_set_relative_position_ch(self, noof_steps, channel, verbose = False): #OK!
        """
        Starts a relative move of noof_steps steps with step amplitude defined 
        by the SU command (default 16).
        noof_steps: Signed integer, between -2,147,483,648 and 2,147,483,647
        """
        self._visa.write('%dPR%d'%(channel,noof_steps))

        if verbose:
            print 'Adjusted position by %d'%noof_steps

    def reset(self): #OK!
        """
        Resets the controller. All temporary settings are reset to default 
        and the controller is in local mode.
        """        
        
        self._visa.write('RS')

    def do_get_step_size_ch(self, channel, direction = '+'): #OK!
        """
        Returns the step amplitude (step size) in positive or negative direction. 
        If the parameter is positive, it will set the step amplitude in the 
        forward direction. If the parameter is negative, it will set the step 
        amplitude in the backward direction.
        direction = '+' or '-' for positive or negative direction
        """
        [ch, ans] = self._visa.ask_for_values('%dSU%s?'%(channel,direction))
        return int(ans)

    def do_set_step_size_ch(self, step_size, channel): #OK!
        """
        Sets the step amplitude (step size) in positive or negative direction. 
        If the parameter is positive, it will set the step amplitude in the 
        forward direction. If the parameter is negative, it will set the step 
        amplitude in the backward direction.
        step_size = Integer between -50 and 50 included, except zero
        """
        self._visa.write('%dSU%d'%(channel,step_size))

    def do_get_error(self): #OK!
        """
        Returns error of the previous command.
        """  
        rawans = self._visa.ask('TE')
        err_dict = {0 : 'No error', 
                    -1 : 'Unknown command',
                    -2 : 'Axis out of range (must be 1 or 2, or must not be specified)',
                    -3 : 'Wrong format for parameter nn (or must not be specified)',
                    -4 : 'Parameter nn out of range',
                    -5 : 'Not allowed in local mode',
                    -6 : 'Not allowed in current state'}
        
        try:
            ans = err_dict[int(rawans[2:len(rawans)])]
        except:
            ans = 'No error'

        return ans

    def do_get_noof_steps_ch(self, channel): #OK!
        """
        The TP command provides only limited information about the actual 
        position of the device. In particular, an Agilis device can be at 
        very different positions even though a TP command may return the same
        result.

        Returns TPnn, where nn is the number of accumulated steps in forward 
        direction minus the number of steps in backward direction as Integer.
        """
        self._visa.write('%dTP'%channel)
        [ch_nr, ans] = self._visa.read_values()

        return int(ans)

    def do_get_status_ch(self, channel, return_type = 'cooked'): #OK!
        """
        Input:
        return_type : "raw" (returns 0,...,3) or any other (returns a string)

        Returns:
        0   Ready (not moving)
        1   Stepping (currently executing a PR command)
        2   Jogging (currently executing a JA command with command
            parameter different than 0).
        3   Moving to limit (currently executing MV, MA, PA commands)
        """
        [ch, rawans] = self._visa.ask_for_values('%dTS'%channel)
        status_dict = {0 : 'Ready (not moving)',
                1 : 'Stepping (currently executing a PR command)',
                2 :  'Jogging (currently executing a JA command with command parameter different than 0).', 
                3 : 'Moving to limit (currently executing MV, MA, PA commands)'}

        if return_type == 'raw':
            ret = int(rawans)
        else:
            ret = status_dict[rawans]

        return ret

    def do_get_firmware_version(self): #OK!
        """
        Returns the firmware version of the controller.
        """
        ans = self._visa.ask('VE')
        return ans

    def quick_scan(self, steps, channel):
        """
        Scans a channel at maximum step speed, for a time that is given by time
        """
        
        if np.sign(steps) == +1:
            steps = steps * self.maxjog_cfg[channel]['positive']
        elif np.sign(steps) == -1:
            steps = steps * self.maxjog_cfg[channel]['negative']

        if channel in self._channels:
            
            speed = 1750.
            getattr(self, 'set_jog_ch%d'%channel)(np.sign(steps)*3)
            qt.msleep(abs(steps)/float(speed))
            getattr(self, 'set_jog_ch%d'%channel)(0)

        else:
            raise ValueError('Unknown channel')

    def write_raw(self, string):
        self._visa.write(string)

    
       



