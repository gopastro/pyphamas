"""
A set of utilities to extract important
information from GBT FITS files
"""

import pyfits
import os

class GBTFITS(object):
    def __init__(self, filename):
        self.filename = filename
        self.open_fits()

    def open_fits(self):
        if not os.path.exists(self.filename):
            raise Exception("FITS file %s not found" % self.filename)
        self.hdulist = pyfits.open(self.filename)
        print "FITS file %s opened" % self.filename
        print self.hdulist.info()

    def close(self):
        self.hdulist.close()
