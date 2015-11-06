import numpy
from .gbtfits import GBTFITS

class ANTFITS(GBTFITS):
    def __init__(self, filename):
        GBTFITS.__init__(self, filename)
    
    def obtain_positional_data(self):
        if (self.hdulist[2].header['EXTNAME']  != 'ANTPOSGR'):
            raise Exception("Method only applies for ANTENNA FITS file")
        ## get location of tracking center on sky
        self.obsc_az = self.hdulist['ANTPOSGR'].data['OBSC_AZ']
        self.obsc_el = self.hdulist['ANTPOSGR'].data['OBSC_EL']
        ## get 'actual' direction of antenna (with servo errors)
        self.mnt_az = self.hdulist['ANTPOSGR'].data['MNT_AZ']
        self.mnt_el = self.hdulist['ANTPOSGR'].data['MNT_EL']
        ## get computed (at the center of each scan) command values to 
        ## remove pointing model
        self.sobsc_az = self.hdulist[0].header['SOBSC_AZ']
        self.sobsc_el = self.hdulist[0].header['SOBSC_EL']
        self.smntc_az = self.hdulist[0].header['SMNTC_AZ']
        self.smntc_el = self.hdulist[0].header['SMNTC_EL']

    def obtain_time_samples(self):
        """
        Obtain time samples from Antenna FITS file for later interpolation; 
        returns numpy array
        """
        if (self.hdulist[2].header['EXTNAME']  != 'ANTPOSGR'):
            raise Exception("Method only applies for ANTENNA FITS file")      
        self.antTimes = self.hdulist['ANTPOSGR'].data['DMJD']
        return self.antTimes

    def compute_pointing_model(self):
        """
        Compute pointing model contribution 
        """
        if (self.hdulist[2].header['EXTNAME']  != 'ANTPOSGR'):
            raise Exception("Method only applies for ANTENNA FITS file")        
        self.pnt_az = self.sobsc_az - self.smntc_az
        self.pnt_el = self.sobsc_el - self.smntc_el

    def compute_tracking_cen_coords(self):
        """ 
        Compute final 'source-centered' coordinates in cross 
        Elev. and Elev; returns these values  
        """
        if (self.hdulist[2].header['EXTNAME']  != 'ANTPOSGR'):
            raise Exception("Method only applies for ANTENNA FITS file")          
        self.obtain_positional_data()        
        self.compute_pointing_model()
        self.crossEl = ((self.obsc_az - self.mnt_az - self.pnt_az) * 60.) * numpy.cos(numpy.radians(self.mnt_el))
        self.El = (self.obsc_el - self.mnt_el - self.pnt_el)*60.
        return self.crossEl,self.El

