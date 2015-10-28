# -*- coding: utf-8 -*-

"""
A set of utilities to collate time samples of a backend to antenna time samples 
(and thus position)
"""

import numpy as np
from scipy.interpolate import griddata
import matplotlib.pyplot as plt

## give antenna time samples, device (e.g. DCR, PHAMAS) timesamples, and calibrated data vector
def collateTimes(antTimes,devTimes,data_orig):
    data_interp = np.interp(antTimes,devTimes,data_orig)
    return data_interp

## Plot results of interpolatation over original data
def plotInterp(antTimes,devTimes,data_orig,data_interp):
  plt.figure()
  plt.xlabel('Time [DMJD]')
  plt.ylabel('T$_A$ [K]')
  plt.plot(devTimes,data_orig,linestyle='--',color='red', label='DCR')
  plt.plot(antTimes,data_interp,color='black', label='Interpolated')
  plt.legend(loc=0,prop={'size':14},fontsize='large')
  plt.show()


## give crossEl, El, and interpolated data vector to grid image 
def grid(crossEl,El,data_interp):  
  combArr = np.vstack((crossEl,El))  
  grid_x,grid_y = np.mgrid[min(crossEl):max(crossEl):1024j,min(El):max(El):1024j]
  ##grid for cross-elevation angle, radius
  return griddata(combArr.T, data_interp, (grid_x, grid_y), method='nearest')

## Plot gridded data; give grid from grid() and crossEl, El 
def plotGrid(grid, crossEl,El):
  plt.figure()
  plt.xlabel('AZ Offset [arcmin]')
  plt.ylabel('EL Offset [armin]')
  im=plt.imshow(grid, extent=[min(crossEl), max(crossEl), min(El), max(El)], aspect='auto')
  plt.colorbar(im,label='T$_A$ [K]')
  plt.show()



