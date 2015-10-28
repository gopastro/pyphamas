"""
A set of utilities to extract important
information from GBT Antenna FITS files
"""

import pyfits
import os
import numpy as np

class ANTFITS(object):
    def __init__(self, filename):
        self.filename = filename
        self.open_fits()

    def open_fits(self):
        if not os.path.exists(self.filename):
            raise Exception("FITS file %s not found" % self.filename)
        self.hdulist = pyfits.open(self.filename)
        print "FITS file %s opened" % self.filename
        print self.hdulist.info()
    
    def obtain_positional_data(self):
    ## Should add check for ANTPOSGR table; if it does not exist throw exception 
        if (self.hdulist[2].header['EXTNAME']  != 'ANTPOSGR'):
            raise Exception("Method only applies for ANTENNA FITS file")
    ## get location of tracking center on sky
        self.obsc_az = self.hdulist['ANTPOSGR'].data['OBSC_AZ']
        self.obsc_el = self.hdulist['ANTPOSGR'].data['OBSC_EL']
    ## get 'actual' direction of antenna (with servo errors)
        self.mnt_az = self.hdulist['ANTPOSGR'].data['MNT_AZ']
        self.mnt_el = self.hdulist['ANTPOSGR'].data['MNT_EL']
    ## get computed (at the center of each scan) command values to remove pointing model
        self.sobsc_az = self.hdulist[0].header['SOBSC_AZ']
        self.sobsc_el = self.hdulist[0].header['SOBSC_EL']
        self.smntc_az = self.hdulist[0].header['SMNTC_AZ']
        self.smntc_el = self.hdulist[0].header['SMNTC_EL']
    
    ## Obtain time samples from Antenna FITS file for later interpolation; returns numpy array
    def obtain_time_samples(self):
        if (self.hdulist[2].header['EXTNAME']  != 'ANTPOSGR'):
            raise Exception("Method only applies for ANTENNA FITS file")      
        self.antTimes = self.hdulist['ANTPOSGR'].data['DMJD']
        return self.antTimes
    ##Compute pointing model contribution 
    def compute_pointing_model(self):
        if (self.hdulist[2].header['EXTNAME']  != 'ANTPOSGR'):
            raise Exception("Method only applies for ANTENNA FITS file")        
        self.pnt_az = self.sobsc_az - self.smntc_az
        self.pnt_el = self.sobsc_el - self.smntc_el
    ## Compute final 'source-centered' coordinates in cross Elev. and Elev; returns these values  
    def compute_tracking_cen_coords(self):
        if (self.hdulist[2].header['EXTNAME']  != 'ANTPOSGR'):
            raise Exception("Method only applies for ANTENNA FITS file")          
        self.obtain_positional_data()        
        self.compute_pointing_model()
        self.crossEl = ((self.obsc_az - self.mnt_az - self.pnt_az) * 60.) * np.cos(np.radians(self.mnt_el))
        self.El = (self.obsc_el - self.mnt_el - self.pnt_el)*60.
        return self.crossEl,self.El
