from .scanLog import scanLog
from .antfits import ANTFITS
from .dcrfits import DCRFITS

#import argparse
import numpy
import pylab as plt
from scipy import signal
from numpy import random
from scipy.optimize import curve_fit
#import pyfits


def gauss(x, height, width, center, offset):
    return height * numpy.exp(-(x-center)**2 / width**2) + offset


class DCRPoint(object):
    def __init__(self, projId="AGBT15B_338", 
                 session=4, scan=9):
        self.projId = projId
        self.session = session
        self.scan = scan
        self.projDir = self.projId + "_0" + str(self.session)

    def gatherData(self):
        self.sl = scanLog(self.projDir)
        antFile = self.sl.getAntenna(self.scan)
        dcrFile = self.sl.getDCR(self.scan)
        print antFile
        
        # get DCR data

        dcrHDU = DCRFITS(dcrFile)
        dcrHDU.obtain_time_samples()
        dcrHDU.obtain_data()
        self.dcrTime = dcrHDU.dcrTimes
        self.dcrData = dcrHDU.data
        #dcrData = dcrHDU['DATA'].data.field('DATA')
        dcrHDU.close()
        self.dataArr = []
        for i in range(6):
            self.dataArr.append(self.dcrData[:, i])

        # get Antenna header info, and data

        # This only works for J2000 / encoder combination? I will need
        # to check with Joe! Can get around this with a 
        # GetCurrentLocation("J2000") call

        antHDU = ANTFITS(antFile)
        antHDU.obtain_positional_data()
        antHDU.obtain_time_samples()
        self.antTime = antHDU.antTimes
        self.source = antHDU.hdulist[0].header['OBJECT']
        #self.obsc_el = antHDU.obsc_el
        #self.mnt_el = antHDU.mnt_el
        #self.sobsc_el = antHDU.sobsc_el
        #self.smntc_el = antHDU.smntc_el

        #self.obsc_az = antHDU.obsc_az
        #self.mnt_az = antHDU.mnt_az
        #self.sobsc_az = antHDU.sobsc_az
        #self.smntc_az = antHDU.smntc_az
        self.az, self.el = antHDU.compute_tracking_cen_coords()
        antHDU.close()
        #self.el =  (self.obsc_el - self.mnt_el - (self.sobsc_el - self.smntc_el))
        #self.az =  (self.obsc_az - self.mnt_az - (self.sobsc_az - self.smntc_az))


        
        
        # interpolate over time samples
        self.data = []
        for i in range(6):
            self.data.append(np.interp(self.antTime, self.dcrTime, self.dataArr[i]))

        # and create a "time since start" array
        self.time = (self.antTime - self.antTime[0]) * 24.0 * 3600.0


    def fit_data(self, chan=0, xtype='el'):
        p4 = numpy.mean(self.data[chan])
        p1 = numpy.max(self.data[chan]) - p4
        x = getattr(self, xtype)
        p2 = x[-1]/20.0
        p3 = x[-1] / 2.0
        print p1,p2,p3,p4        

        # do the fit

        popt, pcov = curve_fit(gauss, x, self.data[chan], 
                               p0 = [p1, p2, p3, p4] )
        self.fit = gauss(x, popt[0], popt[1], popt[2], popt[3])

#         # This should be linearly increasing, but for planets it is flat.

#         plt.plot(time,el)
#         plt.show()

# # Here is what the data looks like

#     plt.plot(time,data)
#     plt.show()

# # hard code here some initial guesses

#     p4 = numpy.mean(data)
#     p1 = numpy.max(data) - p4
#     p2 = time[-1] /20.0
#     p3 = time[-1] / 2.0
#     print p1,p2,p3,p4

# # do the fit

#     popt, pcov = curve_fit(gauss, time, data, 
#                            p0 = [p1, p2, p3, p4] )
#     fit = gauss(time, popt[0],popt[1],popt[2],popt[3])


# # plot the results

#     plt.plot(time,data)
#     plt.plot(time,fit,"r-")
#     plt.show()

