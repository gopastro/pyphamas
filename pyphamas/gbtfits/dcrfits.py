# -*- coding: utf-8 -*-
"""
A set of utilities to extract important
information and calibrate a GBT DCR FITS files
"""

#import pyfits
from .gbtfits import GBTFITS
import os
import numpy

class DCRFITS(GBTFITS):
    def __init__(self, filename):
        GBTFITS.__init__(self, filename)

    def obtain_time_samples(self):
        if (self.hdulist[0].header['BACKEND']  != 'DCR'):
            raise Exception("Method only applies for DCR FITS file")      
        self.dcrTimes = numpy.array(self.hdulist[3].data['TIMETAG'])

    def obtain_data(self):
        dataTable = self.hdulist['DATA'].data
        self.data = dataTable.field('DATA')
        
    def calibrate(self):
        tCal = 3.3 # Standard value
        iport = 1        
        nPhases = self.hdulist[0].header['NPHASES']
        nRec    = self.hdulist[0].header['NRCVRS']
        stateTable = self.hdulist['STATE'].data
        recTable = self.hdulist['RECEIVER'].data
        dataTable = self.hdulist['DATA'].data
        # Since this is TPWCAL, there are only two phases,CAL ON and CAL OFF
        # decide which is the first.
        cal = stateTable.field('CAL')
        if (cal[0] == 1):
          calOn = 0
          calOff = 1
        else:
           calOn = 1
           calOff = 0
        ports = recTable.field('CHANNELID')
        for i in range(len(ports)):
          if (ports[i] == iport):
            iport = i
            break
      
        data = dataTable.field('DATA')
        shape = data.shape
        data.shape = (shape[0], nRec, nPhases)
        
        ## Now, actually process the data
        toff = data[:, iport, calOff]
        ton  = data[:, iport, calOn]
      
        counts_per_K = numpy.sum((ton - toff)/tCal) / len(ton) ##Gain
        ta = 0.5 * (ton + toff) / counts_per_K - tCal/2.0 
        self.calib_data_vector = ta
        return self.calib_data_vector
    
