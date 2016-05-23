import numpy
from .gbtfits import GBTFITS

class QuadrantDetectorFITS(GBTFITS):
    def __init__(self, filename):
        GBTFITS.__init__(self, filename)
        self.obtain_time_samples()
        self.obtain_pointing_offsets()
    
    def obtain_time_samples(self):
        """
        Obtain time samples from Quadrant Detector FITS file for later interpolation; 
        returns numpy array
        """
        if (self.hdulist[1].header['EXTNAME'].strip()  != 'QDATA'):
            raise Exception("Method only applies for Quadrant Data FITS file")      
        self.quadTimes = self.hdulist['QDATA'].data['DMJD']
        return self.quadTimes

    def obtain_pointing_offsets(self):
        """
        Compute pointing offsets
        """
        if (self.hdulist[1].header['EXTNAME'].strip()  != 'QDATA'):
            raise Exception("Method only applies for Quadrant Data FITS file")        
        self._total_offset = self.hdulist['QDATA'].data['total_offset']
        self._mc_total_offset = self.hdulist['QDATA'].data['mc_total_offset']

    def mc_total_offset(self, time):
        """
        Given a time array, reinterpolates intrinsic time array
        to given time array and return mc_total_offset
        """
        return numpy.interp(time, self.quadTimes, self._mc_total_offset)

        

