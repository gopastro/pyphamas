# Copyright (C) 2004 Associated Universities, Inc. Washington DC, USA.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 675 Mass Ave Cambridge, MA 02139, USA.

# This version by Bojan Nikolic
# Some parts after R. Prestage,  B. Mason and J. Brand?

# Only works on Python 2.3 and above
import pdb
import os
import math

#import numarray
#import numpy
import numpy
import pyfits

from itertools import izip


    
def daisy( map_radius,
           radial_osc_period,
           radial_phase,
           rotation_phase,
           scan_length,
           fnameout,
           calc_dt=0.1
           ):
    "Generates a daisy-petal pattern"

    """
    map_radius:     radius of the pattern,
    radial_osc:     period of the radial oscillation
    radial_phase:   radial phase, in radians
    rotation_phase: rotational phase, in radians    
    scan_length:    total time of the scan
    """

    # Note that needs to be the first line,
    # otherwise will pick up local variables which are not parameters
    paramtab=scanpars( locals() )

    phdu=pyfits.PrimaryHDU()
    phdu.header.update("stype", "daisy")
    phdu.header.update("ver", "$Revision: 1.10 $")
    
    
    # Need extra steps for extimates of velocity and acceleration...
    t=numpy.arange( float(scan_length) / calc_dt + 2 ) * calc_dt - calc_dt


    major, minor = daisypatern(map_radius,
                               radial_osc_period,
                               radial_phase,
                               rotation_phase,
                               t)
    #pdb.set_trace()

    st = scantable( [major[1:-1] , minor[1:-1]] , # cut off the extra steps       
                    DerVel(major, minor, t),
                    DerAcc(major, minor, t),
                    numpy.ones(len(t)-2 ,numpy.Float64) *  calc_dt
                    )


    
    hdl=[
        phdu,
        st,
        paramtab
        ]


    
    pyfits.HDUList(hdl ).writeto(fnameout)    
    
                           
def StraightLine( startp,
                  endp,
                  scan_length,
                  fnameout,
                  calc_dt=0.1 ):
    "Generates a straight line scan"

    """
    startp = [Major starting point, Minor Starting point]
    endp   = same for ending point
    """

    paramtab=scanpars( locals() )

    phdu=pyfits.PrimaryHDU()
    phdu.header.update("stype", "StraightLine")
    phdu.header.update("ver", "$Revision: 1.10 $")
    
    
    # Need extra steps for extimates of velocity and acceleration...
    t=numpy.arange( float(scan_length) / calc_dt + 2 ) * calc_dt - calc_dt


    major, minor = StraightLineGen(startp, endp, scan_length , t)

    st = scantable( [major[1:-1] , minor[1:-1]] , # cut off the extra steps       
                    DerVel(major, minor, t),
                    DerAcc(major, minor, t),
                    numpy.ones(len(t)-2 ,numpy.Float64) *  calc_dt
                    )


    
    hdl=[
        phdu,
        st,
        paramtab
        ]


    
    pyfits.HDUList(hdl ).writeto(fnameout)    



def DerVel(major,minor,t):
    "Derive velocities using differencing"


    # This makes use of index arrays
    # see http://stsdas.stsci.edu/numpy/numpy-1.1.html/node27.html

    mp = numpy.arange(len(major) -2 ) + 1


    def vel( mv ,t ):
        return ( mv [mp+1] - mv[mp-1]  ) / (t[mp+1] - t[mp-1] )

    majv= vel(major, t)
    minv= vel(minor, t)
    return majv, minv

def DerAcc(major,minor,t):
    "Derive acceleration using  differencing"

    mp = numpy.arange(len(major) -2 ) +1 
    
    def acc( mv ,t ):
        return ( mv[mp-1] -
                 2 * mv[mp] +
                 mv[mp+1] ) / ( ((t[mp+1] - t[mp-1] ))/2)**2
    
    
    maja= acc(major, t)
    mina= acc(minor, t)
    return maja, mina
    



def daisypatern ( map_radius,
                  radial_osc_period,
                  radial_phase,
                  rotation_phase,
                  times):

    "Calculates postions on a daisy pattern"

    """
    See documantatin of daisy for meanings of parameters.
    times is a numpy of time values to evalute the pattern on.

    Returns [ majorposvector, minorposvector ]
    """
    
    
    RadOscFreq = 2* math.pi / radial_osc_period
    AngPscFreq = math.pi  / ( radial_osc_period * 2)
    
    return [ map_radius *
             numpy.cos(times * AngPscFreq  + rotation_phase) *
             numpy.sin(times * RadOscFreq + radial_phase),
             
             map_radius*
             numpy.sin(times * AngPscFreq  + rotation_phase) *
             numpy.sin(times * RadOscFreq + radial_phase)
             ]


def StraightLineGen ( startp, endp, duration,
                      times):
    
    "Generates a straight line"

    """ startp, endp are 2-tuples start and end points"""

    MajorSlope = float(endp[0] - startp[0] ) / duration
    MinorSlope = float(endp[1] - startp[1] ) / duration

    return [
        times * MajorSlope + startp[0] ,
        times * MinorSlope + startp[1]
        ]

    
    
    

def scantable( posp, velp, accp, dur ):
    "Prepares a FITS file representing a scan track"

    """
    posp: pair of vectors representing the positions
    velp: pair of vectors representing the velocities
    accp: pair of vectors representing the accelerations
    dur : a vector containing the duration of each segment
    """

    coldefs= [ pyfits.Column( "MajorPos" , "E" , "", array=posp[0] ),
               pyfits.Column( "MinorPos" , "E" , "", array=posp[1] ),
               pyfits.Column( "MajorVel" , "E" , "", array=velp[0] ),
               pyfits.Column( "MinorVel" , "E" , "", array=velp[1] ),
               pyfits.Column( "MajorAcc" , "E" , "", array=accp[0] ),
               pyfits.Column( "MinorAcc" , "E" , "", array=accp[1] ),
               pyfits.Column( "Duration" , "E" , "", array=dur )            
               ]


    return     pyfits.new_table( coldefs)
    

def scanpars( d ):

    coldefs= [ pyfits.Column( "Parameter" , "30A" ) ,
               pyfits.Column( "Value" , "80A" ) ]

    tabout=pyfits.new_table( coldefs , nrows=len(d) )

    for x,rowout in izip(d, tabout.data ):
        rowout.setfield("Parameter", x )
        rowout.setfield("Value", str(d[x])       )
        

    return  tabout

    

def test():

    # This is not a realistic file
    #daisy(1, 20, 0,0, 440, "test2.fits", calc_dt=0.25)
    pass

#daisy( 4/ 60.0,  60 , 0, -3 * math.pi / 4, 240, "xband4.fits", calc_dt=0.1)

#StraightLine( [-2.0/60, 0] ,  [2.0/60, 0],  20,    "straight1.fits")


#daisy( 0/ 60.0,  60 , 0, -3 * math.pi / 4, 240, "longzero.fits", calc_dt=10.0)
#daisy( 0/ 60.0,  60 , 0, -3 * math.pi / 4, 240, "shortzero.fits", calc_dt=0.1)

#daisy( 1.75/ 60.0,  60 , 0, -3 * math.pi / 4, 120, "ka-daisy-short.fits", calc_dt=0.1)
#daisy( 1.75/ 60.0,  30.0 , 0, -3 * math.pi / 4, 120, "ka-daisy-shortv2.fits", calc_dt=0.1)

