import corr
import numpy as np
from matplotlib import pyplot as plt
import pylab as p
import time
import itertools
import bitstring
import os
import binascii
import struct
import math
import glob
import re
import datetime
import scipy.io as sio
import logFileXML
import pickle
import sys
import filecmp

from pprint import pprint
from IPython.Debugger import Tracer; debug_here = Tracer()

data = np.zeros((3,1024),dtype='uint32')
MAX_BEAMFORMERS = 7
INITBF = 'bf7_pipeline'
#INITBF = 'bf7_read_weights_revamped'

class x64():
    '''
    wrapper class for controlling x64-based ROACH builds
    (specifically the x64-based F-engine / Beamformer designed by Megan F, Jay B & Vikas A)
    Written by Jay B (based off code from Vikas)
    documentation added Jun 28 '12 by Jay B
    doc & general cleanup Oct 31 12 Jay B
    update to include ROACH programming + run BF in single function MAy 6 13
    '''
###########################################################################################
#Helper / private functions     
#----------------------------------------------------------------------------------------
    def __init__(self,roach):                                                                    
        ''' initialize ROACH variable 'u' '''    
        self.u = corr.katcp_wrapper.FpgaClient(roach)
        self.did_rst = 0
        self.chipssyncd = 0
        self.baselineSet = 0
        self.fromRegister = 0
        time.sleep(0.5)

        self.bitstreams = {'old_7_bfs':'multi_beamformer_7_beams_slice_2012_Nov_10_1057.bof', \
                           'bf3': 'bf3_2013_May_24_1210.bof',                         \
                           'bf7_reorder': 'bf7_reorder_bfs_2013_May_23_1529.bof',  #BROKEN ALL 7 FAIL    \ 
                           'bf7_pipeline': 'bf7_pipeline_test_2013_May_20_1026.bof',    # 6 7 failed \ <_ does not have even_coeffs and off_coeff BRAMs. Cannot verify weights
                           'bf7_read_weights': 'bf7_read_weights_2013_Jun_03_0947.bof',  # 1 2 3 5 FAIL\
                           #'NOTE1' : 'read_weights has even/odd brams switched (accident, will fix. see read_coeffs())!', \
                           'bf7_read_weights_snap': 'bf7_read_weights_2013_Jun_03_1331.bof',  # 6 7 FAIL\
                           'bf7_read_weights_new_vhdl': 'bf7_read_weights_2013_Jun_07_1019.bof',  #last value diesn't get written to bf weights\
                           'bf7_read_weights_revamped': 'bf7_read_weights_revamped_2013_Jun_15_1737.bof' }

        if not self.u.is_connected():
            print "ROACH " + roach + " is not connected"
            print "  Check that the ethernet cable is hooked up,"
            print "  the ROACH is booted up, and that the ROACH's"
            print "  IP address is correct."
            self.exit_clean()

        self.set_bitstream(INITBF)

        self.program_roach()
        self.calibrate_adc()
        self.check_sync()   
       # self.finished_message()

#----------------------------------------------------------------------------------------
    def set_new_bitsream(self):
        '''
        Reprogram the roach to a specified bitstream
        '''

        print 'Available bitstreams:'
        for k,v in sorted(self.bitstreams.items()):
#            print ('{}: {}{}').format(k,''.rjust(20), v)
            print ('{}:'.format(k)).ljust(len(max(self.bitstreams, key=len))+1), '{}'.format(v)

        new_bitstream = raw_input('\nWhich bitstream? (choose from left column above)\n\t')
        self.set_bitstream(new_bitstream)
        self.program_roach()
        self.calibrate_adc()
        self.check_sync() 
 
#----------------------------------------------------------------------------------------
    def set_bitstream(self, new_bitstream):
        ''' updates bitstream - does not reprogram the roach '''

        
#        if isinstance(new_bitstream, str):
#            self.bitstream = new_bitstream
#        else:
#            print new_bitstream + " is not a string. Value unchanged"

        try:
            self.bitstream = self.bitstreams[new_bitstream]
        except KeyError:
            print '\''+new_bitstream+'\'' + ' is not a valid bitstream.'
            print 'Please choose from the following: '
            for k,v in sorted(self.bitstreams.items()):
                print ('{}:'.format(k)).ljust(len(max(self.bitstreams, key=len))+1), '{}'.format(v)


#----------------------------------------------------------------------------------------
    def program_roach(self):
        try:
            self.u.progdev(self.bitstream)
        except corr.katcp_wrapper.KatcpClientError:
            print "Client not connected; verify that the specified IP"
            print "  is a valid IP address"
            self.exit_clean()
        time.sleep(0.5)
        try:
            self.u.write_int("sys_scratchpad", 0xDEADBEEF)
        except RuntimeError:
            print "Unable to write to sys_scratchpad"
            print "  Make sure that your bitstream \'" + self.bitstream + "\'"
            print "  is in /boffiles on the ROACH filesystem"
#----------------------------------------------------------------------------------------
    def calibrate_adc(self):
        calreg = 'x64_adc_ctrl'
        CTRL = 0x0
        DELAY_CTRL = 0x4
        DATASEL = 0x8
        DATAVAL = 0xc

        for j in range(0,8):
            self.u.blindwrite(calreg, "%c%c%c%c"%(0x0,0x0,0x0,j//2), DATASEL)
            self.u.blindwrite(calreg, "%c%c%c%c"%(0x0,0x0,0x0,1<<j), DELAY_CTRL)

            stable = 1
            while stable == 1:
                self.u.blindwrite(calreg, "%c%c%c%c"%(0x0,0xff,1<<j,0x0),DELAY_CTRL)
                val          = struct.unpack('>L', (self.u.read(calreg,4,DATAVAL)))[0]
                val0         = (val & ((0xffff)<<(16*(j%2))))>>(16*(j%2))
                stable       = (val0&0x1000)>>12
            for i in range(10):
                self.u.blindwrite(calreg, "%c%c%c%c"%(0x0,0xff,1<<j,0x0),DELAY_CTRL)
#----------------------------------------------------------------------------------------
    def check_sync(self):
        ''' 
        pulses sync signal if adc_reset() has not been called

        checks if adc chips are syncd
        if not, adc_reset() or rerun_cal() are called until chips are syncd
        '''    
    
        u = self.u
        if self.did_rst == 0:
            self.adc_reset()

        self.check_chipsync()
        while self.chipssyncd == 0:
            print "Chips not sync'd.  Resetting adc"
            self.adc_reset()
            self.check_chipsync()
            if self.chipssyncd == 0:
                print "Chips not sync'd.  Re-running cal script"
                #self.rerun_cal()
                self.calibrate_adc()
        
        print "Chips syncd"
        if self.did_sync == 0:
            print "writing sync pulse";
            u.write_int('ctrl',0)
            u.write_int('ctrl',16)
            self.did_sync = 1;
            
#----------------------------------------------------------------------------------------
    def writeFileToBram(self, fileName, bramName, bramSize = 2048):
        ''' 
        Write the contents of a file to a BRAM
        
        @param fileName - name of the file to write to BRAM
        @param bramName - name of the BRAM to write to
        @param bramSize - size of BRAM in bytes. Defaults to 2048 

        note: the contents of the file should be 32bit hex strings, one per line
            i.e.     '00000000'
                '11111111'
                'BeEfCafE' etc. 
        '''

        packedData = self.getPackedDataFromFile(fileName);

        self.u.write(bramName, packedData);

        self.verifyBramData(fileName, bramName, bramSize);
        
#----------------------------------------------------------------------------------------
    def writeBram (self, triggerReg, triggerbit):
        ''' 
        after the shared BRAM has new coeffs written to it, this will begin the
        BF's write cycle to update its coeffs.
        BF output will be invalid while writing, and will return to normal operation
        once the write is complete.
        '''
        
        u = self.u;
        bit = 2**triggerbit;
        
        oldval = u.read_int(triggerReg);
        u.write_int(triggerReg, oldval+bit); 
        time.sleep(.001)
        u.write_int(triggerReg, oldval);

        #print "\t>>Write pulse sent to: "+str(triggerReg)+"("+str(triggerbit)+")<<"
        
#----------------------------------------------------------------------------------------    
    def getPackedDataFromFile(self, fileName):
        '''
        @param fileName - name of the file to pack
        @return - packed struct of data in file
        
        note: assumes the contents of the file are 32bit hex strings, one per line
            i.e.     '00000000'
                '11111111'
                'BeEfCafE' etc.
        '''

        #read data from file
        f = open(fileName, 'r');
        fileContents = f.readlines(); 
        f.close()
        
        #clean off newlines and convert to int (for packing)    
        for r in range(len(fileContents)): 
            fileContents[r] = fileContents[r].replace('\n', '');
            fileContents[r] = int(fileContents[r], 16);
        
        #pack data
        packedData = struct.pack('>'+str(len(fileContents))+'I', *fileContents);

        return packedData;    
          
#########################################################################################
# Public / Interface  functions
#----------------------------------------------------------------------------------------
    def get_data(self,bram_num='', log = ''):
        '''
        collects data from beamformer's output BRAM
        plots data either with semilog() (if log == 'log' ) or plot()
        
        @param bram_num - its assumed the bram is named acc_bram_# (where # is bram_num)
                            bram numbering is 1 indexed (i.e 1, 2, ... not 0, 1 ...)
        @param log - if 'log' plot data with semilog() else plot().
        @return - the data read from the bram
        '''

        if self.chipssyncd == 0:
            self.check_sync()
        u = self.u

        if bram_num == '':
            bram_name = 'acc_bram'
            bram_num = 1
        else:
            bram_name = 'acc_bram_' + str(bram_num)
        d0t1 = np.fromstring(u.read(bram_name,256*4),dtype='uint8')
        d0_1 = bitstring.pack('uint:8',d0t1[0])
        for idx in range(256*4 - 1):
            d0_1 = d0_1 + bitstring.pack('uint:8',d0t1[idx+1])
        
        for col in range(256):
            data[0][col] = d0_1.read(32).uint

        if log == "log":
            plt.figure(bram_num); plt.semilogy(data[0][0::1]);
            plt.axis([ 0, 256, 0, max(data[0])+max(data[0])/20 ]);
            plt.show(); 
        else:
            plt.figure(bram_num); plt.plot(data[0][0::1]);
            plt.axis([ 0, 256, 0, max(data[0])+max(data[0])/20 ]);
            plt.show();

        return data[0]
        
#----------------------------------------------------------------------------------------    
    def get_all_data(self,bram_num, log = ''):
        '''
        collects data from all beamformer's output BRAMs
        plots data either with semilog() (if log == 'log' ) or plot()
        like multi_get_data() this assumes the brams are named acc_bram_#
        
        @param bram_num - number of BFs
        @param log - if 'log' plot data with semilog() else plot().
        @return - the data read from the bram
        '''

        self.check_sync()
        u = self.u

        for r in range(bram_num):
            idx = int(r)+1
            print idx
            bram_name = 'acc_bram_' + str(idx)
            d0t1 = np.fromstring(u.read(bram_name,256*4),dtype='uint8')
            d0_1 = bitstring.pack('uint:8',d0t1[0])
            for idx in range(256*4 - 1):
                d0_1 = d0_1 + bitstring.pack('uint:8',d0t1[idx+1])
        
            for col in range(256):
                data[0][col] = d0_1.read(32).uint

            if log != '':
                plt.figure(idx); plt.semilogy(data[0][0::1]);
                plt.axis([ 0, 256, 0, max(data[0])+max(data[0])/20 ]);
                plt.show(); 
            else:
                plt.figure(idx); plt.plot(data[0][0::1]);
                plt.axis([ 0, 256, 0, max(data[0])+max(data[0])/20 ]);
                plt.show();
        
        return    
        
#----------------------------------------------------------------------------------------    
    def updateBFCoeffs(self, fileName, bf_idx, \
                bramName='coeff_bram', bramSize=2048, triggerReg='ctrl'):
        '''
        NOTE: UPDATES A SINGLE COEFF BRAM!
        This function does all that is necessary to get new coeffs in the BF.
        Read the coeffs from a file, write them to the shared BRAM, then start the BF write cycle.

        During the write, the BF 'data_valid' output will be held low until the write has completed.
        When finished, the BF will have new coeffs and will be running normally.
        
        @param bf_idx   - beamformer number to update. START AT BF # 1 !! BF 0 does not exist
        @param fileName - name of the file to write to BRAM
        @param bramName - name of the BRAM to write to
        @param bramSize - size of BRAM in bytes. (should be 2048) 
        @param triggerReg - BF needs a 1 clock (or longer) pulse to know when to begin the write.
                    triggerReg is a shared reg that is pulsed to begin the write
        '''
        
        self.writeFileToBram(fileName, bramName, bramSize);
        print "\n\tUpdating BF #"+str(bf_idx)+". . ."
        print '\tFilename: %s'%(fileName) 
        self.u.write_int('bf_index', int(bf_idx));
        self. writeBram(triggerReg, bf_idx+4); # +4+1 since bf_1 is at ctrl(5)
        self.u.write_int('bf_index', 0);    
    
#----------------------------------------------------------------------------------------    
    def updateBFCoeffs_no_print(self, fileName, bf_idx, \
                bramName='coeff_bram', bramSize=2048, triggerReg='ctrl'):
        '''
        NOTE: UPDATES A SINGLE COEFF BRAM!
        This function does all that is necessary to get new coeffs in the BF.
        Read the coeffs from a file, write them to the shared BRAM, then start the BF write cycle.

        During the write, the BF 'data_valid' output will be held low until the write has completed.
        When finished, the BF will have new coeffs and will be running normally.
        
        @param bf_idx   - beamformer number to update. START AT BF # 1 !! BF 0 does not exist
        @param fileName - name of the file to write to BRAM
        @param bramName - name of the BRAM to write to
        @param bramSize - size of BRAM in bytes. (should be 2048) 
        @param triggerReg - BF needs a 1 clock (or longer) pulse to know when to begin the write.
                    triggerReg is a shared reg that is pulsed to begin the write
        '''
        
        self.writeFileToBram(fileName, bramName, bramSize);
        self.u.write_int('bf_index', int(bf_idx));
        self. writeBram(triggerReg, bf_idx+4); # +4+1 since bf_1 is at ctrl(5)
        self.u.write_int('bf_index', 0);    
            
#----------------------------------------------------------------------------------------    
    def set_slice(self, idx):
        '''
        Sets the BF input bit slice location. Ranges from 0 - 7
            where 0 is lowest 4 bits, 7 is highest 4
        '''
        if idx <= 7 and idx >= 0:
            self.u.write_int('fft_bit_sel', int(idx))
            print 'FFT output slice set to bits '+str(idx+4)+' downto '+str(idx+1)
        else:
            raise ValueError('Invalid slice location.\nidx value must be an integer 0-7')
            
        
#----------------------------------------------------------------------------------------
    def set_acc_len(self, seconds):
        '''
        Change the amount of time for each accumulation.
        
        @param seconds - number of seconds for each accumulation
        Note: the bounds on 'seconds' are 0.00002 to 30+. A value of greater than 30
            is allowed but can cause overflow. The overflow limit depends on the input voltage,
            number of elements connected and the beamformer weights. 30 is the max for the 
            test rig I had set up. Will vary.
        Note: if seconds = -1 then only accumulate 1 data set.
        '''
        acclen = 0
        if seconds == -1:
            acclen = 1;
        elif seconds < 0.00002:
            raise ValueError('Invalid acc_len value. Must be greater than .00002')
        else:
            if seconds > 30:
                print "Warning: an acc_len value this large may cause overflow issues!"
            acclen = math.floor(seconds * 50000000/512);

        self.u.write_int('acc_len', acclen);
        print 'Accumulation length set to: {0}'.format(seconds)
        print 'This will accumulate %i FFTs'%acclen        
      #  self.clear_baseline();
        
#----------------------------------------------------------------------------------------
    def multi_updateBFCoeffs(self, fileName, num_bf, \
                bramName='coeff_bram', bramSize=2048, triggerReg='ctrl'):
        '''
        Similar to UpdateBFCoeffs(), but writes the same weights to multiple beamformers at once.
        
        @param fileName - name of the file to write to BRAM
        @param bramName - name of the BRAM to write coeffs to before BFs
        @param bramSize - size of BRAM in bytes.
        @param triggerReg - BF needs a 1 clock (or longer) pulse to know when to begin the write.
                    triggerReg is a shared reg that is pulsed to begin the write

        '''
        
        tic = time.time()
        self.writeFileToBram(fileName, bramName, bramSize);
        print "\n\t>>Shared bram written<<"

        for r in range(num_bf):
            print "\n\tUpdating BF #"+str(r+1)+". . ."
            self.u.write_int('bf_index', int(r+1));
            self. writeBram(triggerReg, r+1+4); # +4 since bf_1 is at ctrl(5)
            time.sleep(.05);        
            self.clear_baseline();
            self.u.write_int('bf_index', 0);
        print 'Total time: %.5f'%(time.time()-tic)
#----------------------------------------------------------------------------------------    
    def test_multi_updateBFCoeffs(self, fileName, num_bf, \
                bramName='coeff_bram', bramSize=2048, triggerReg='ctrl'):
        '''
        Similar to UpdateBFCoeffs(), but writes the same weights to multiple beamformers at once.
        
        @param fileName - name of the file to write to BRAM
        @param bramName - name of the BRAM to write coeffs to before BFs
        @param bramSize - size of BRAM in bytes.
        @param triggerReg - BF needs a 1 clock (or longer) pulse to know when to begin the write.
                    triggerReg is a shared reg that is pulsed to begin the write

        '''
        print 'Updating Beamformer Weights. . .'
        tic = time.time();
        for r in range(num_bf):
            self.writeFileToBram(fileName, bramName, bramSize);
#            print "\n\t>>Shared bram written<<"
#            print "\n\tUpdating BF #"+str(r)+". . ."
            self.u.write_int('bf_index', int(r+1));
         #   print 'Time to write shared bram:%.5f'%(time.time()-tic)  ~ 10-15 ms
            self. writeBram(triggerReg, r+1+4); # +4 since bf_1 is at ctrl(5)
 #           time.sleep(.05);        
           # self.clear_baseline();
           # self.u.write_int('bf_index', 0);
        print 'Total time: %.5f'%(time.time()-tic)          
        print 'Done'
###########################################################################################
# Testing / Debug functions
#----------------------------------------------------------------------------------------
    def check_chipsync(self):
        ''' 
        check if adc chips are syncd 
        @return bool 
        '''
        u = self.u
        c0 = u.read_int('check_bits1')
        c0 = np.bitwise_and(16,c0)
        if c0 == 16:
            self.chipssyncd = 1
        else:
            self.chipssyncd = 0
        #self.chipssyncd = 1
            return self.chipssyncd
            
#----------------------------------------------------------------------------------------        
    def rerun_cal(self):
        '''
        re-program ROACH
        reset adc
        check if adc chips are syncd
        '''
        #os.system('python adc_softcal_dump_jack.py roach3')
        self.program_roach()
        self.calibrate_adc()
        self.did_rst = 0
        self.adc_reset()
        self.check_chipsync()
        if self.chipssyncd == 1:
            print "Chips syncd"
        else:
            print "Chips not syncd"
            
#----------------------------------------------------------------------------------------        
    def adc_reset(self):
        ''' 
        resets adc 
        '''
        u = self.u
        u.write_int('ctrl',0)
        u.write_int('ctrl',1)
        u.write_int('ctrl',0)
        self.did_rst = 1;
        self.did_sync = 0;    
        
#----------------------------------------------------------------------------------------
    def toggle_bf_input(self, value='00000000'):
        '''
        switches the bf input from f-engine to register (bf_input) and back
        '''
        self.u.write_int('ctrl', self.u.read_int('ctrl')+2**31)
        self.u.write_int('bf_input', int(value, 16))
        
        # check if using register input (ON), or adc input (OFF)
        ctrl_val_hex = self.u.read('ctrl',4)
        ctrl_val_str =  binascii.hexlify(ctrl_val_hex)
        is_on = int(ctrl_val_str,16) & int('80000000',16)
        if is_on == int('80000000',16):
            print 'Bf_input is from REGISTER'
            self.fromRegister = 1
        else:
            print 'Bf_input is from ADC'
            self.fromRegister = 0
        
#----------------------------------------------------------------------------------------
    def verifyBramData(self, fileName, bramName, bramSize = 2048 ):
        '''
        Verify that the contents of a BRAM is the same as the contents of a file

        @param fileName - name of the file to write to BRAM
        @param bramName - name of the BRAM to write to
        @param bramSize - size of BRAM in bytes. Defaults to 2048 .

        note: the contents of the file should be 32bit hex strings, one per line
            i.e.     '00000000'
                '11111111'
                'BeEfCafE' etc. 

        '''

        #get data from file
        f = open(fileName, 'r');
        fileContents = f.read()
        fileContents = fileContents.replace('\n', '')
        f.close()
        #get data from bram
        bramContents = self.u.read(bramName, bramSize*4);
        #unpack and verify
        unpackedData = binascii.hexlify(bramContents);
        sameContents = unpackedData == fileContents;
        '''if sameContents == True:
        
            print '\tShared Bram data DOES equal contents of \''+fileName+'\''
            print '       _ '
            print '      ( (\ '
            print '       \ =\ '
            print '     ___\_ `-. '  
            print '    (____))(  \---- '
            print '    (____)) _  ' 
            print '    (____))    '
            print'     (____))____/---- '
        else:
            print '\tShared Bram data does NOT equal contents of \''+fileName+'\''
            print'       ______ '
            print'     (( ____ \----'
            print'     (( _____       '
            print'     ((_____        '
            print'     ((____   ---- '
            print'          /  / '
            print'         (_(/  '
        '''
#----------------------------------------------------------------------------------------
    def generateDirectory(self, dirName):
        '''
        <duration>, <period> in seconds
        will do to do a new capture every <period> seconds (if the period is not too small
        this might actually work and not miss any samples)
        <bram_num> irrelevent <dirName> give base of directory to create: dirName_month_day_year_dataidx
        '''
        
   #     self.check_sync()
  #      u = self.u

  #      totalCaptures = int(math.floor(duration / period))
   #     times = []
        #data = np.zeros((3,1024),dtype='uint32')
        
        #make a new directory for this round of data
        #check existing directories and increment the number tag
        #directory should be : BFData_<month>_<day>_<year>_<number tag>
        dirName = os.path.abspath(os.path.expanduser(dirName))
        now = datetime.datetime.now()
        date = now.strftime('%Y_%b_%d')           #'%s_%s_%s'%(now.month, now.day, now.year)
        directories = glob.glob('%s_%s_*/'%(dirName, date))
        newIdx = 1

        #get last numbertag in directories
        if len(directories) > 0:
            numberTags = np.zeros(len(directories), dtype='uint32')
            for r in range(len(directories)):
                try:
                    #strip all digits out of each filename, then keep the final digit (this should be the number tag)
                    digits = [int(s) for s in re.split('_|/', directories[r]) if s.isdigit()]
                    numberTags[r] = digits[len(digits)-1]
                except TypeError:
                    pass
                except ValueError:
                    pass
           # print numberTags
            maxval = max(numberTags)
            newIdx = maxval + 1
    
       # print 'maxval = %i'%(maxval)
      #  print 'newIdx = %i'%(newIdx)
        directory = '%s_%s_%i'%(dirName, date, newIdx)

        if os.path.exists(directory):
            #shouldn't get here ever
            print 'directory already exists'
            return -1
        os.makedirs(directory)

        print 'Directory created. \nPath: %s'%(directory)
        
        return directory
#----------------------------------------------------------------------------------------
    def startContReadSave(self, directory, duration, period):
        self.check_sync()
        u = self.u
        totalCaptures = int(math.floor(duration / period))
        times =[]
        totalTime = time.time()
        for timeIdx in range(totalCaptures):
           # timeStamp = timeIdx*period
            
            startTime = time.time()
          #  busy = u.read_int('busy')
          #  if busy != 10:              # not working right::always busy?
                
            #tic = time.time()
            bramData = np.zeros((7,), dtype=np.object)
            bramData[0] = np.fromstring(u.read('acc_bram_1',256*4),dtype='uint8')
            bramData[1] = np.fromstring(u.read('acc_bram_2',256*4),dtype='uint8')
            bramData[2] = np.fromstring(u.read('acc_bram_3',256*4),dtype='uint8')
            bramData[3] = np.fromstring(u.read('acc_bram_4',256*4),dtype='uint8')
            bramData[4] = np.fromstring(u.read('acc_bram_5',256*4),dtype='uint8')
            bramData[5] = np.fromstring(u.read('acc_bram_6',256*4),dtype='uint8')
            bramData[6] = np.fromstring(u.read('acc_bram_7',256*4),dtype='uint8')
 
            fname = '%s/bramData_%s'%(directory, timeIdx)

            sio.savemat(fname,{'bramData':bramData}, oned_as='column')
         #   times.append(time.time()-tic)           
            
           # print 'Writing file: %s'%(fname)


            elapsed = time.time() - startTime
                           
            if (elapsed < period):
                time.sleep(period - elapsed)
            else:
                strig = 'Time to save all BRAMs is GREATHER than %s seconds :(' %period 
                print strig
                print 'total captures before missing: ', timeIdx
                return -1
        print 'total time elapsed: %s'%(time.time() - totalTime)
      #  print 'max time to read/save: %.5f'%(max(times))
        print 'done'
            
#----------------------------------------------------------------------------------------
    def singleReadSave(self, directory, period, fileIdx, coeFileName):
        u = self.u
        startTime = time.time()
        bramData = np.zeros((7,), dtype=np.object)
        bramData[0] = np.fromstring(u.read('acc_bram_1',256*4),dtype='uint8')
        bramData[1] = np.fromstring(u.read('acc_bram_2',256*4),dtype='uint8')
        bramData[2] = np.fromstring(u.read('acc_bram_3',256*4),dtype='uint8')
        bramData[3] = np.fromstring(u.read('acc_bram_4',256*4),dtype='uint8')
        bramData[4] = np.fromstring(u.read('acc_bram_5',256*4),dtype='uint8')
        bramData[5] = np.fromstring(u.read('acc_bram_6',256*4),dtype='uint8')
        bramData[6] = np.fromstring(u.read('acc_bram_7',256*4),dtype='uint8')

        #NOTE: if only bramData[0] is saved, elapsed time is about .0023 sec
        # if all 7 are saved, elapsed time is about .009 sec
        fname = '%s/bramData_%s'%(directory, fileIdx)
        
        sio.savemat(fname,{'bramData':bramData, 'coeffFile': coeFileName}, oned_as='column')

        elapsed = time.time() - startTime
        if (elapsed < period):
            time.sleep(period - elapsed)
        else:
            strig = 'Time to save all BRAMs is GREATHER than %s seconds :(' %period 
            print strig
            print 'total captures before missing: ', fileIdx
            raise Exception('Accumulation missed')
#----------------------------------------------------------------------------------------
    def plotSavedData(self, filename, log=''):

        data = np.zeros((1,1024),dtype='uint32')

        savedData = np.load(filename)
        d0t1 = np.fromstring(savedData,dtype='uint8')
        d0_1 = bitstring.pack('uint:8',d0t1[0])

        for idx in range(256*4 - 1):
            d0_1 = d0_1 + bitstring.pack('uint:8',d0t1[idx+1])
        for col in range(256):
            data[0][col] = d0_1.read(32).uint

        if log == "log":
            plt.figure(bram_num); plt.semilogy(data[0][0::1]);
            plt.axis([ 0, 256, 0, max(data[0])+max(data[0])/20 ]);
            plt.show(); 
        else:
            plt.figure(bram_num); plt.plot(data[0][0::1]);
            plt.axis([ 0, 256, 0, max(data[0])+max(data[0])/20 ]);
            plt.show();
#----------------------------------------------------------------------------------------
#find a way to read in all filenames like bram_x_time_y_sec.npy and then iterate through
#   the ones you want to plot
    def getSavedFiles(self, filenameSearchRegExp):
        return glob.glob(filenameSearchRegExp)
      
#########################################################################################
#----------------------------------------------------------------------------------------
    def compOnOffDiff(self, accLen):
        '''
        plots the differences between noise and signal

        first, collects data with no signal input
        then, collect data with signal input
        last, plot the differentce    

        @parm accLen - length of time (in seconds) between accumulations
        '''
        if(self.baselineSet == 0):
            raw_input("\tTurn OFF signal source.\n\tPress ENTER when finished")
            print "please wait . . ."
            time.sleep(accLen+1)
            self.baseline = np.array(self.collect_data())
            self.baselineSet = 1
            raw_input("\tTurn ON signal source. \n\tPress ENTER when finished")
            print "please wait . . ."
            time.sleep(accLen+1)
        yesIn = np.array(self.collect_data())
        diff = np.array((yesIn - self.baseline), 'i4')
        plt.plot(diff);
        plt.axis([ 0, 256, min(diff)-min(diff)/20, max(diff)+max(diff)/20 ]);
        plt.show();
#----------------------------------------------------------------------------------------    
    def clear_baseline(self): 
        ''' 
        resets global variable 'baseline' 

        '''
        self.baselineSet = 0
        
#----------------------------------------------------------------------------------------
    def runBeamformer(self, allWeightFiles,dirName,duration, period, sliceIdx, RTIC=False):
        '''
        Begins recording beamformer data. First, a directory is created to store the
        multiple data files, the beamformer coefficients are updated, a log file is
        created and then the data is collected.        

        @param allWeightFiles - list of path for each coeffecient file minus the 
                                extension (max list size is same as number of BFs 
                                in model, currently 7 for ROACH 1 implementation 
                                - May 7 13 - JayB)
                    Notes:   1) weight files MUST have a .coe extension 
                                -> but leave it off in the list!
                             2) weight files + log files must be in the same directory

        @param dirName - path of directory in which to save data files
                    Note:   may or may not currently exist. A new directory will be made

        @param duration - total length of time to run beamformer (in seconds)

        @param period - integration time 
                        (in seconds - should be > .025 for smooth running)
    
        @ param sliceIdx - LSB of FFT output to use as BF input. A 4 bit window
                            is sliced off of the FFT output and used for the BF.
                            Must be an integer 0-7.
        Usage Example: 
            >> import BeamformerCtrl
            >> roach = BeamformerCtrl.x64('roach3')
            >> allWeightFiles = ['~/Files/weightFile1', '~/Files/weightFile2'] 
            >> roach.runBeamformer(allWeightFiles, './newDirectory', 1, 0.5, 7)
            
            This will program the roach with the current boffile, initialize a list 
            of coeffecient files, then run the beamformers using the coeffecinets
            specified in the list of weight files. Data will be gathered for 
            1 second, using a .5 second integreation time and using bits 7-10 of 
            the FFT output as the input for the BFs. A data stamp will be appended to
            the end of newDirectory along with an integer indicating which run this 
            is for that day (i.e. ./newDirectory_2013_May_8_1 would be the first run on
            may 8 2013. Next would be ./newDirectory_2013_May_8_2 and so on).
            
        '''

        tic = time.time()
        # create directory in which to save data
        directory = self.generateDirectory(dirName)

        #debug_here()

        if len(allWeightFiles) > MAX_BEAMFORMERS:
            print '*****ERROR*****'
            print ('Invalid number of beamformer weight files.'
                   '\nNumber of file provided: %i'
                   '\nMax number of files is %i'%(len(allWeightFiles),MAX_BEAMFORMERS))
            print 'Exiting . . .'
            return -1

        #check to be sure files exist. If not, return
        for (i, weightFile) in enumerate(allWeightFiles):
            allWeightFiles[i] = os.path.abspath(os.path.expanduser(weightFile))
            try:
                with open(allWeightFiles[i]+'.coe'): pass
            except IOError:
                print '*****ERROR*****'
                print 'Be sure that \''+allWeightFiles[i]+'.coe\' is a valid file name'
                print 'Exiting . . .'
                return -1

        #load each BF weight file into consecutive BFs
        for (i, weightFile) in  enumerate(allWeightFiles):
            if RTIC==True:
                self.updateBFCoeffs(weightFile+'.coe', i+1)
            else:
                weights_are_correct = False
                while not weights_are_correct:
                    self.updateBFCoeffs(weightFile+'.coe', i+1)
                    weights_are_correct = self.check_bf_weights(i+1, weightFile)

        print '\nBeamformer coefficient update complete.\n'

        #build log file
        #this assumes each weight file has a log file associated with it
        #that has the same base name, with a .log extension saved in the 
        #same loacation as the weight file. If no log file is found,
        #an error msg is saved in the new log file indicating that the 
        #log file was not found.
        allLogFiles = [None] * len(allWeightFiles)
        for(i, fileName) in enumerate(allWeightFiles):
            allLogFiles[i] = allWeightFiles[i]+'.log'
        logFileName = directory+'/'+os.path.basename(directory)
        #logFileXML.bigLogFile(allLogFiles,logFileName)
        logFileName = logFileXML.testSkipNoFile(allLogFiles, logFileName)
        print ('Log file written.\n'
               '\tFile name: %s\n'%logFileName)

        #set accumulation length and slice registers then start saving data.
        #This function will pause at the prompt to allow time for the 
        #matlab plotting function to be started. If no plotting is
        #desired, simply press enter at the prompt.
        #The matlab function (somewhat) depends on this function running, but
        #this function does not depend on the matlab function at all.

        self.check_sync()

        try:
            self.set_acc_len(period)
            print ''
            self.set_slice(sliceIdx)
            print ''
        except ValueError as e:
            print e.message
            return
        print 'Directory created. \n\tPath: %s\n'%(directory)
        
        print 'Time until ready: ' + str(time.time() - tic)
        proceed = raw_input('Start MATLAB plotting function <plotBFData(dirPath, numFiles)>\n'
                  '\tUse directory path as above\n'
                  '\nContinue (y/n)? ').lower()
        if proceed == 'n':
            print ('\nNote: Beamformers are still running, but no data will be saved\n'
                   'Exiting. . . \n')
        else:
            self.startContReadSave(directory, duration, period)


#-------------------------------------------------------------------------------------------
    def save_output(self, outfile, outval):
        with open(outfile, 'w') as f:
            pickle.dump(outval, f)
        return outfile
        
    def test_output(self, correct_outfile, numIter, numBfs):
        ''' 
        this test assumes that all BFS tested have the same weights. Also, 
        the BF must be running in FROM REGISTER mode so taht all BF inputs
        are the same. the Correct outfile must also have been in this mode,
        and the correct_outfile must be a pickeld verseion of the bf output
        (from get_data())

        --jayb May 29 13
        '''


        acc_len = self.u.read_int('acc_len') /50e6/512

        with open(correct_outfile, 'r') as f:
            correct_data = pickle.load(f)

        numFails = 0;
        failingBfs = set();
        for r in range(numIter):
            for k in range(numBfs):
                tmp = self.get_data(k+1)
                if min(tmp == correct_data) == False:
                    print 'BF # '+str(k+1)+' has incorrect data'
                    numFails += 1
                    failingBfs.add(k+1)


        print ('\nThese BFs had failing outputs: {}').format(list(failingBfs))

    def test_suite(self,numFileRuns, acclen, numBfs, getOutFiles=False):
        '''
        Quick test to check if the output of the bfs is correct
        File locations are hard-coded in, so be careful if you've moved stuff
        
        if getOutFiles == True, this will collect the good outputs for each file
        which it will use to compare against later. Be sure you do this at least once!
    
        @param numFileRuns - number of times each file is loaded and checked. This script
                             gets pretty time consuming pretty fast, so watch out if you 
                             make this large. (With this =1 this function takes ~2-3 min)
    
        @param acclen - accumulation length for the beamformers. Keep this small to avoid
                        making this function take forever.
        @param numBfs - number of bfs on the roach
        --jayb May 30 13
        '''
        weightsDir = '/home/jayb/Beamformer/ctrl_scripts/bf_weights/'
        weights = [ 'bin1J', 'bin2J', 'bin3J', 'bin4J', \
                    'bin5J', 'bin6J', 'bin7J', 'bin8J', \
                    'bin9J', 'bin10J', 'bin11J', 'bin12J', \
                    'bin13J', 'bin14J', 'bin15J', 'bin16J', \
                    'bin17J', 'bin18J', 'bin19J', 'bin20J', \
                    'bin21J', 'bin22J', 'bin23J', 'bin24J', \
                    'bin25J', 'bin26J', 'bin27J', 'bin28J', \
                    'bin29J', 'bin30J', 'bin31J', 'bin32J', \
                    'bin33J', 'bin34J', 'bin35J', 'bin36J', \
                    'bin37J', 'bin38J', 'bin39J', 'bin40J', \
                    'bin41J', 'bin42J', 'bin43J', 'bin44J', \
                    'bin45J', 'bin46J', 'bin47J', 'bin48J', \
                    'bin49J', 'bin50J', 'bin51J', 'bin52J', \
                    'bin53J', 'bin54J', 'bin55J', 'bin56J', \
                    'bin57J', 'bin58J', 'bin59J', 'bin60J', \
                    'bin61J', 'bin62J', 'bin63J', 'bin64J', \
                    'one_chan_ones', 'ones', 'parabJ', \
                    'sweep', 'sweep12_5MHz', 'counting' ]
        outfileDir = '/home/jayb/Beamformer/ctrl_scripts/bf_weights/bf_outfiles/'
            
        self.set_acc_len(acclen)
        self.toggle_bf_input('11111111')
        if self.fromRegister == 0:
            self.toggle_bf_input('11111111')

        #get good data from each weight to check against
        if getOutFiles == True:
            for filename in weights:
                saveData = 'n'
                while(saveData.lower() == 'n'):        
                    self.updateBFCoeffs(weightsDir+filename+'.coe', 1)
                    time.sleep(2*acclen)
                    outdata = self.get_data(1)
                    saveData = raw_input('Is outdata OK? [y,n]')
                    if saveData.lower() == 'q':
                        return -1;
                self.save_output(outfileDir+filename+'.out', outdata)

        # Now check if data is good
        numFails = [0, 0, 0, 0, 0, 0, 0]
        checksPerBf = 0
        failingBfs = set()
        totalChecks = 0

        for filename in weights:
            print '\nTesting %s'%filename
            for fileRuns in range(numFileRuns):
                checksPerBf += 1
                for r in range(int(numBfs)):
                    self.updateBFCoeffs_no_print(weightsDir+filename+'.coe', r+1)
                    time.sleep(2*acclen)
                
                with open(outfileDir+filename+'.out', 'r') as f:
                    correct_data = pickle.load(f)
                    for k in range(int(numBfs)):
                        tmp = self.get_data(k+1)
                        #time.sleep(.1)
                        totalChecks += 1
                        if min(tmp == correct_data) == False:
                            print 'BF # '+str(k+1)+' has incorrect data'
                            numFails[k] += 1
                            failingBfs.add(k+1)
#            sys.stdout.flush()
        print ('\n------------------------------------------------------'
               '\nTesting complete'
               '\nTotal number of failures: {}'
               '\nTotal number of checks: {}'
               '\nNumber of checks per BF: {}').format(sum(numFails),totalChecks, checksPerBf)
        for r in range(numBfs):
            print ('Failures on BF #{}: {}').format(r+1, numFails[r])

        print ('\nFailing BFs: {}').format(list(failingBfs))
            
    def save_outfile_for_test_suite(self, weight):
        weightsDir = '/home/jayb/Beamformer/ctrl_scripts/bf_weights/'
        outfileDir = '/home/jayb/Beamformer/ctrl_scripts/bf_weights/bf_outfiles/'
        
        self.set_acc_len(-1)
        if self.fromRegister == 0:
            self.toggle_bf_input('11111111')

        weights = [ 'bin1J', 'bin2J', 'bin3J', 'bin4J', \
                    'bin5J', 'bin6J', 'bin7J', 'bin8J', \
                    'bin9J', 'bin10J', 'bin11J', 'bin12J', \
                    'bin13J', 'bin14J', 'bin15J', 'bin16J',\
                    'bin17J', 'bin18J', 'bin19J', 'bin20J', \
                    'bin21J', 'bin22J', 'bin23J', 'bin24J', \
                    'bin25J', 'bin26J', 'bin27J', 'bin28J', \
                    'bin29J', 'bin30J', 'bin31J', 'bin32J', \
                    'bin33J', 'bin34J', 'bin35J', 'bin36J', \
                    'bin37J', 'bin38J', 'bin39J', 'bin40J', \
                    'bin41J', 'bin42J', 'bin43J', 'bin44J', \
                    'bin45J', 'bin46J', 'bin47J', 'bin48J', \
                    'bin49J', 'bin50J', 'bin51J', 'bin52J', \
                    'bin53J', 'bin54J', 'bin55J', 'bin56J', \
                    'bin57J', 'bin58J', 'bin59J', 'bin60J', \
                    'bin61J', 'bin62J', 'bin63J', 'bin64J', \
                    'one_chan_ones', 'ones', 'parabJ', \
                    'sweep', 'sweep12_5MHz' ]

        saveData = 'n'
        while(saveData.lower() == 'n' or saveData.lower() == 'q'):        
            self.updateBFCoeffs(weightsDir+weights+'.coe', 1)
            outdata = self.get_data(1)
            saveData = raw_input('Is outdata OK? [y,n]')
            if saveData.lower() == 'q':
                return -1;
        
        self.save_output(outfileDir+weights+'.out', outdata)

    def get_bram_contents(self, bram_name, data_width, address_width):
        '''
        gets the contents of a shared bram. If you pass in the correct
        widths, this will make each element of the list correspond to
        each address location. Makes it much easier to verity the contents
    
        @param bram_name - the name of the bram yellow block
        @param data_width - number of bits in each location
        @param address_width - number of bits for the address
        
        @return - a list containing the contents of the bram
        --jayb May 31 13
        '''
        contents = []
        #for r in range(2**address_width):
        #    tmpVal = binascii.hexlify(self.u.read(bram_name, data_width/8, r*data_width/8))
        #    contents.append(tmpVal)
        bram_size = 2**address_width
        tmp = binascii.hexlify(self.u.read(bram_name, 4*bram_size))
        for r in range(bram_size):
            contents.append(tmp[r*8:r*8+8]) #note: x:y in not inclusive
        return contents;

    def save_bram_contents(self, bram_name, data_width, address_width, filename):
        '''
        similar to get_bram_data, but this saves the bram data to a text file
        File has a .brm extension
        --jayb may 31 13
        '''
        bram_data = self.get_bram_contents(bram_name, data_width, address_width)
        with open(filename+'.brm', 'w') as f:
            for r in range(len(bram_data)):
                f.write(bram_data[r]+'\n')
    
    def compare_files(file1, file2, shallow=False):
        '''
        compares the contents of two files using Lib/filecmp.py
        --jayb May 31 13
        '''
        return filecmp.cmp(file1, file2, shallow) 

    def check_bf_weights(self, bf_idx, coe_filename, save_file=False, brm_filename='bramFile'):
        '''
        This is to check if a beamformer has the correct weights loaded into it. This will read the 
        coeffecients and save them to a list, then compare that list aginst what is in the original
        coe file. If desired, this will save the beamformer coefficients to a file to use later.
    
        NOTE: this function has hard-coded bram names, and was written to be used with
              'bf7_read_weights_2013_May_30_1106.bof'
    
        @param bf_idx - which bf you want to check (indexed off of 1)
        @param coe_filename - path for the coe file to check against
                            --> do not include .coe extension
        @param brm_filename - path for the .brm file to be written 
                            --> .brm will be appended to this filename
        @param save_file - True if you want to save the .brm file
    
        @return - a list of the contents of the beamformer coeffecient bram
        --jayb May 31 13
        '''




 #       read_trigger_bit = 30
 #       bit = 2**read_trigger_bit
 #       oldval = self.u.read_int('ctrl');
 #       self.u.write_int('bf_index', int(bf_idx));
 #       #check if trigger is stuck on
 #       read_trigger = binascii.hexlify(self.u.read('ctrl',4))
 #       is_on = int(read_trigger,16) & int('40000000',16)
 #       #if yes, turn it off
 #       if is_on == int('40000000',16):
 #           self.u.write_int('ctrl', oldval-bit); 
 #           #then strobe it to start read.
 #           self.u.write_int('ctrl', oldval); 
 #           self.u.write_int('ctrl', oldval-bit);  
 #       else:
 #           self.u.write_int('ctrl', oldval+bit); 
 #           self.u.write_int('ctrl', oldval); 
 #       time.sleep(0.1)
 #       self.u.write_int('bf_index', 0);
 #       #read even/odd coeffs 
 #       bram_width = 32
 #       bram_depth = 11
 #       even_coeffs = self.get_bram_contents('even_coeffs', bram_width, bram_depth)
 #       odd_coeffs = self.get_bram_contents('odd_coeffs', bram_width, bram_depth)
 #       #interleave into a single list
 #       interleave_coeffs = []
 #       for r in range(2**bram_depth):
 #           if r%2 == 0:
 #               interleave_coeffs.append(even_coeffs[r])
 #           else:
 #               interleave_coeffs.append(odd_coeffs[r])
 #   

        interleave_coeffs = self.read_coeffs(bf_idx)

        with open(coe_filename+'.coe', 'r') as f:
            coefile = f.read().splitlines()

        is_correct = True
        if coefile == interleave_coeffs:
            print '\tThe beamformer coeffs match the given file'
        else:
            print '\tThe beamformer coeffs DO NOT match the given file'
            is_correct = False
    
        if save_file == True:
           with open(brm_filename+'.brm', 'w') as f:
               for r in range(len(interleave_coeffs)):
                   f.write(interleave_coeffs[r]+'\n')     

        return is_correct

    def read_coeffs(self, bf_idx):
        '''
        '''
        read_trigger_bit = 30
        bit = 2**read_trigger_bit
        oldval = self.u.read_int('ctrl');
        self.u.write_int('bf_index', int(bf_idx));
        #check if trigger is stuck on
        read_trigger = binascii.hexlify(self.u.read('ctrl',4))
        is_on = int(read_trigger,16) & int('40000000',16)
        #if yes, turn it off
        if is_on == int('40000000',16):
            self.u.write_int('ctrl', oldval-bit); 
            #then strobe it to start read.
            self.u.write_int('ctrl', oldval); 
            self.u.write_int('ctrl', oldval-bit);  
        else:
            self.u.write_int('ctrl', oldval+bit); 
            self.u.write_int('ctrl', oldval); 

        #read even/odd coeffs 
        bram_width = 32
        bram_depth = 11
        #even_coeffs = self.get_bram_contents('even_coeffs', bram_width, bram_depth)
        #odd_coeffs = self.get_bram_contents('odd_coeffs', bram_width, bram_depth)

        odd_coeffs = self.get_bram_contents('even_coeffs', bram_width, bram_depth) 
        even_coeffs = self.get_bram_contents('odd_coeffs', bram_width, bram_depth) 
        self.u.write_int('bf_index', 0);

        #interleave into a single list
        #debug_here()
        interleave_coeffs = []
        for r in range(2**bram_depth):
            if r%2 == 0:
                interleave_coeffs.append(even_coeffs[r])
            else:
                interleave_coeffs.append(odd_coeffs[r])
        return interleave_coeffs

    def fix_printing():
        sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

    def read_snaps(self, filename, bf_idx,start, end):
        weights_are_correct = True
        self.u.write_int('snap_coeff_dout_ctrl', 1)
        self.u.write_int('snap_coeff_addr_ctrl', 1)
        while weights_are_correct:
            self.u.write_int('snap_coeff_dout_ctrl', 1)
            self.u.write_int('snap_coeff_addr_ctrl', 1)
            self.updateBFCoeffs(filename+'.coe', bf_idx)
            self.u.write_int('snap_coeff_dout_ctrl', 0)
            self.u.write_int('snap_coeff_dout_ctrl', 0)
            weights_are_correct = self.check_bf_weights(bf_idx, filename)

        print 'Coeff_Bram contents:'
        print binascii.hexlify(self.u.read('coeff_bram',4*16))
        print 'Snap_Coeff_Dout_Bram contents:'
        print binascii.hexlify(self.u.read('snap_coeff_dout_bram',256))
        print 'Snap_Coeff_Addr_Bram contents:'
        print binascii.hexlify(self.u.read('snap_coeff_addr_bram',256))
        print 'BF weights:'
        print self.read_coeffs(bf_idx)[start:end]
#----------------------------------------------------------------------------------------
    def runRTICBeamformer(self, allWeightFiles,dirName,coeDirName, coeBaseName, period, sliceIdx):
        '''
        Runs the BF in Real-time Interferance Cancelation mode (RTIC). The BFs is set up,
        then run. when a new .coe file is put in the specified directory, the BF weights
        are updated to the new coefficiants.
        
        CURRENTLY ONLY USES BF # 1 - BUT ALL 7 ARE SAVED (THIS SHOULD BE THE SAME NUMBER)
            
        '''

        try:
            directory = self.initBeamformers(allWeightFiles, dirName, period, sliceIdx, True, True)
        except IOError:
            return -1
        proceed = raw_input('Start MATLAB plotting function <plotBFData(dirPath, numFiles)>\n'
                  '\tUse directory path as above\n'
                  '\nContinue (y/n)? ').lower()
        if proceed == 'n':
            print ('\nNote: Beamformers are still running, but no data will be saved\n'
                   'Exiting. . . \n')
        else:
            coeIdx = 0;
            outIdx = 0;
            while 1:
                try:
                    tic = time.time()
                    fileName = coeDirName +'/'+ coeBaseName + '_'+ str(coeIdx)
                    logFileName = coeDirName +'/'+ coeBaseName + '_'+ str(coeIdx)
                    #print 'opeing file '+fileName
                    with open(fileName+'.coe'): pass
                    with open(logFileName+'.log'): pass
                    self.updateBFCoeffs(fileName+'.coe', 1)
                    #logFileName = directory+'/'+os.path.basename(directory)
                    #print 'logFile: '+logFileName
                    logFileXML.newRTIClogFile([fileName], logFileName, coeIdx, outIdx)
                    self.singleReadSave(directory, period, outIdx, fileName)
                    coeIdx += 1
                    outIdx += 1
                except IOError:
                    try:
                        self.singleReadSave(directory, period, outIdx, fileName) 
                        outIdx += 1
                    except KeyboardInterrupt:
                        print '\nKeyboardInterrupt: Exiting.'
                        return
                except KeyboardInterrupt:
                    print '\nKeyboardInterrupt: Exiting.'
                    return
#--------------------------------------------------------
    def initBeamformers(self, allWeightFiles,dirName, period, sliceIdx, RTIC=False, logging=True):
        tic = time.time()
        # create directory in which to save data
        directory = self.generateDirectory(dirName)
        print directory
        #debug_here()
        print '------------------Initializing Beamformers------------------'
        if len(allWeightFiles) > MAX_BEAMFORMERS:
            print '*****ERROR*****'
            print ('Invalid number of beamformer weight files.'
                   '\nNumber of file provided: %i'
                   '\nMax number of files is %i'%(len(allWeightFiles),MAX_BEAMFORMERS))
            print 'Exiting . . .'
            return -1

        #check to be sure files exist. If not, return
        for (i, weightFile) in enumerate(allWeightFiles):
            allWeightFiles[i] = os.path.abspath(os.path.expanduser(weightFile))
            try:
                with open(allWeightFiles[i]+'.coe'): pass
            except IOError:
                print '*****ERROR*****'
                print 'Be sure that \''+allWeightFiles[i]+'.coe\' is a valid file name'
                print 'Exiting . . .'
                raise

        #load each BF weight file into consecutive BFs
        for (i, weightFile) in  enumerate(allWeightFiles):
            if RTIC==True:
                self.updateBFCoeffs(weightFile+'.coe', i+1)
            else:
                weights_are_correct = False
                while not weights_are_correct:
                    self.updateBFCoeffs(weightFile+'.coe', i+1)
                    weights_are_correct = self.check_bf_weights(i+1, weightFile)

        print '\nBeamformer coefficient update complete.\n'


        #build log file
        #this assumes each weight file has a log file associated with it
        #that has the same base name, with a .log extension saved in the 
        #same loacation as the weight file. If no log file is found,
        #an error msg is saved in the new log file indicating that the 
        #log file was not found.
        if logging == True:
            allLogFiles = [None] * len(allWeightFiles)
            for(i, fileName) in enumerate(allWeightFiles):
                allLogFiles[i] = allWeightFiles[i]+'.log'
            logFileName = directory+'/'+os.path.basename(directory)+'_0'
            #logFileXML.bigLogFile(allLogFiles,logFileName)
            logFileName = logFileXML.testSkipNoFile(allLogFiles, logFileName)
            print ('Log file written.\n'
                   '\tFile name: %s\n'%logFileName)

        #set accumulation length and slice registers then start saving data.
        #This function will pause at the prompt to allow time for the 
        #matlab plotting function to be started. If no plotting is
        #desired, simply press enter at the prompt.
        #The matlab function (somewhat) depends on this function running, but
        #this function does not depend on the matlab function at all.

        self.check_sync()

        try:
            self.set_acc_len(period)
            print ''
            self.set_slice(sliceIdx)
            print ''
        except ValueError as e:
            print e.message
            return
        print 'Directory created. \n\tPath: %s\n'%(directory)
        
        print 'Time until ready: ' + str(time.time() - tic)
        print '------------------Initilization finished------------------'
        return directory

