#
# path.py
#
# routines to solve for acceleration coefficients, and generate
# trajectories.
#
# R. Prestage   23 Jan 2005
# various modifications (bsm, 2006 - 2008)
# modify into a reasonably usable stand alone package - bsm feb 2013
# Modified and inserted into pyphamas by GN, Nov 2015
# 

#from numarray import *
#import numarray.linear_algebra as la 
import numpy
import  pyfits
from generate import scantable
#from matplotlib import *
import matplotlib.pyplot as pyp

# bsm-- seems to return two 3-element arrays -- major axis accel, minor axis accel
def pathSolve(p0, p1, v0, v1, T):
    """
    Solve for acceleration coefficients for a jerk-minimized trajectory.
    Given:
        p0:  initial position
        v0:  initial velocity
        p1:  final position
        v1:  final velocity
        T:   time for the route
        
    and the constraint A0 = A1 = 0, returns acceleration coefficents
    A1, A2, A3 such that an acceleration profile:
    
        a = A1 * t + A2 * t**2 + A3 * t**3

    will generate the required trajectory to turn around.

    Note: this version makes no attempt to check velocity or
    acceleration limits.
    """
    
    # Set up three simultaneous equations in three unknowns using the
    # integral and double integral of the acceleration profile, and
    # the known start and end values

    M = numpy.array( [ [ T**2 / 2.0,  T**3 / 3.0 ,  T**4 / 4.0  ],
                       [ T**3 / 6.0,  T**4 / 12.0,  T**5 / 20.0 ],
                       [ T         ,  T**2       ,  T**3        ] ])

    # TBD there is a way to do both of these simultaneously; clean that
    # up later

    Dmajor = numpy.array( [ v1[0] - v0[0]             ,
                      p1[0] - p0[0] - v0[0] * T ,
                      0                         ])
    Dminor = numpy.array( [ v1[1] - v0[1]             ,
                            p1[1] - p0[1] - v0[1] * T ,
                            0                         ])

    # And solve it using the power of python...
    #Amajor = solve_linear_equations(M,Dmajor)
    #Aminor = solve_linear_equations(M,Dminor)
    Amajor = numpy.linalg.solve(M, Dmajor)
    Aminor = numpy.linalg.solve(M, Dminor)
    return Amajor, Aminor

# bsm - seems to return 6 arrays of p,v,a (major & minor)
def trajGenerate(p0, v0, A, t):
    """
    Given starting positions and velocities an acceleration
    profile and a time array, calculate position, velocity and
    acceleration trajectories.
    """

    aMajor = A[0][0] * t + A[0][1] * t**2 + A[0][2] * t**3
    vMajor = v0[0] + A[0][0] * t**2 / 2.0 + A[0][1] * t**3 / 3.0 \
                                                   + A[0][2] * t**4 / 4.0
    pMajor = p0[0] + v0[0]*t + A[0][0] * t**3 /6.0 + A[0][1] * t**4 / 12.0 + \
                                                     A[0][2] * t**5 / 20.0
    
    aMinor = A[1][0] * t + A[1][1] * t**2 + A[1][2] * t**3
    vMinor = v0[1] + A[1][0] * t**2 / 2.0 + A[1][1] * t**3 / 3.0 \
                                                   + A[1][2] * t**4 / 4.0
    pMinor = p0[1] + v0[1]*t + A[1][0] * t**3 /6.0 + A[1][1] * t**4 / 12.0 + \
                                                     A[1][2] * t**5 / 20.0

    return pMajor, pMinor, vMajor, vMinor, aMajor, aMinor


#     Returns a three-dimensional array [nPoints, [p,v,t], [major, minor])
def makeRectangleEndPoints(xs, ys, xf, yf, rLen,
                           vel, nRows, yStep, tSlew):
    """
    Makes an array of start and end points for rows. For example,
    five rows starting and ending in the middle: 

                9             10
                8              7
                5     0/11     6
                4              3
                1              2

    Returns a three-dimensional array [nPoints, [p,v,t], [major, minor])
    """

    tRow = rLen / vel
    nPoints = 2 * nRows + 2
    endPoints = numpy.zeros((nPoints,3,2))

    # starting position has zero velocity
    endPoints[0] = [[xs,ys], [0,0], [0,0]]

    t = tSlew
    # add each row start and end (remember, first row is even!)
    for i in range(nRows):
        if (not i%2):
            x = -0.5 * rLen
            xVel = vel
        else:
            x = 0.5 * rLen
            xVel = -1.0 * vel
        y = (i - nRows / 2) * yStep 
        yVel = 0
        endPoints[2*i + 1] = [[x, y], [xVel, yVel], [t,t]]
        t = t + tRow
        endPoints[2*i + 2] = [[-1.0 * x, y], [xVel, yVel] ,[t,t]]
        t = t + tSlew

   # and the last point
    endPoints[nPoints-1] = [[xf, yf], [0,0], [t,t]]

    return endPoints

def getInputs():
    configOk = False
    while (not configOk):
        pattern = raw_input("cloverleaf or rectangle (C/R): ").upper()
        if (pattern == "R"):
            print "ok, making a rectangle"
            xs, ys = input("     Enter start position (x, y): ")
            xf, yf = input("        Enter end position (x,y): ")
            rLen = input("      Enter row length in arcmin: ")
            vel   = input("Enter row velocity in arcmin/min: ")
            nRows = input("            Enter number of rows: ")
            yStep = input("      Enter row spacing (arcmin): ")
            tSlew = input("  Enter time to move to next row: ")
            vel = vel / 60.0
            tRow = rLen / vel
            scanLength = (nRows + 1) * tSlew + (nRows * tRow)
            print
            print "ok, starting at position (%5.2f,%5.2f)" % (xs, ys)
            print "      ending at position (%5.2f,%5.2f)" % (xf, yf)
            print "executing %d rows at velocity %5.2f arcmin/sec" % \
                                                    (nRows, vel)
            print "with %5.2f arcmin spacing between rows" % yStep
            print "performing (%d+1 x %5.2fs) slews + (%d x %5.2fs) rows" % \
                                     (nRows, tSlew, nRows, tRow)
            print "for a total scan time of %5.2f seconds" % scanLength
            print
            temp = raw_input("Accept this configuration (Y/N): ").upper()
            if (temp == "Y") or (temp == "T"):
                configOk = True

            return xs, ys, xf, yf, rLen, vel, nRows, yStep, tSlew

class rasterscan:
    def __init__(self,hdulist, x, y, vx, vy, ax, ay, t):
        self.hdulist = hdulist
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.ax = ax
        self.ay = ay
        self.t = t
        self.jx = ax
        self.jy = ay
        # calculate the jerk numerically (crudely)
        for i in range(len(ax)-2):
            self.jx[i] -= self.jx[i+1]
            self.jx[i] /= t[i+1]-t[i]
            self.jy[i] -= self.jy[i+1]
            self.jy[i] /= t[i+1]-t[i]
        self.jx[len(ax)-1] = 0.0
        self.jy[len(ax)-1] = 0.0

def savetraj(traj, outfilename='foobar.fits'):
    pyfits.HDUList(traj.hdulist).writeto(outfilename)    

def plottraj(traj):
    mint = min(traj.t)
    maxt = max(traj.t)
    pyp.figure()
    pyp.subplot(411)
    xx = 60.0*asarray(traj.x)
    yy = 60.0*asarray(traj.y)
    pyp.plot(xx,yy)
    if (min(yy)<0):
        ymin = 1.15*min(yy)
    else:
        ymin = 0.85*min(yy)
    if (max(yy)>0):
        ymax = 1.15*max(yy)
    else:
        ymax = 0.85*max(yy)
    pyp.ylim([ymin,ymax])
    pyp.xlabel('Position/arcmin')
    pyp.ylabel('Position/arcmin')
    pyp.subplot(412)
    pyp.plot(traj.t,traj.vx,'b',traj.t,traj.vy,'g',[mint,maxt],[0.3,0.3],'r',[mint,maxt],[-0.3,-0.3],'r')
    pyp.ylim([-0.4,0.4])
    pyp.xlabel('time/sec')
    pyp.ylabel('velocity [deg/sec]')
    pyp.subplot(413)
    pyp.plot(traj.t,traj.ax,'b',traj.t,traj.ay,'g',[mint,maxt],[0.08,0.08],'r',[mint,maxt],[-0.08,-0.08],'r')
    pyp.ylim([-0.1,0.1])
    pyp.xlabel('time/sec')
    pyp.ylabel('acceleration [deg/sec^2]')
    pyp.subplot(414)
    # approximate jerk limit from Paul Ries' analysis - 0.2 arcmin/sec^3 ~ 0.003 deg/s^3
    pyp.plot(traj.t,traj.jx,'b',traj.t,traj.jy,'g',[mint,maxt],[0.003,0.003],'r',[mint,maxt],[-0.003,-0.003],'r')
    pyp.ylim([-0.005,0.005])
    pyp.xlabel('time/sec')
    pyp.ylabel('jerk [deg/sec^3]')
    pyp.show()
    
def makerasterscan(xs = 0.0, ys = 0.0, 
                   xf = 0.0, yf = 0.0,
                   rLen=5.0, vel=0.75, 
                   nRows=10, yStep=0.1,
                   tSlew = 8.0, calc_dt=0.25,
                   declat = False):
    """
    ARGUMENTS:
    (xs,ys), (xf,yf) : start and finish location for scan in arcminutes - default to origin
    rLen : row length in arc minutes
    vel : in arcmin/sec
    nRows : # of rows
    yStep : spacing between rows in arcmin
    tSlew : time spent turning around between rows, in seconds - generally 
    be careful with values less than say 8 sec (the default value)
    calc_dt : granularity in sec at which trajectory is calculated (default 0.25s)
    declat : make dec/lat instead of ra/long? (default false)
             note that declat=True will simply swap around the output, input argument
             interpretations are not affected
    RETURNS: a structure with an HDU list that can be passed to saveraster()
    the structure can also be passed to plotraster() 
    """

    # This recods all of the parameters
    paramtab = generate.scanpars( locals() )

    # convert all inputs from arcmin to deg
    xs = xs/60.0
    ys = ys/60.0
    xf = xf/60.0
    yf = yf/60.0
    rLen = rLen/60.0
    vel = vel/60.0
    yStep = yStep/60.0
    
    phdu = pyfits.PrimaryHDU()
    phdu.header.update("stype", "smoothraster")
    phdu.header.update("ver", "$Revision: 1.2 $")

    # make and array of start and end points, starting and ending
    # with a slew
    endPoints = makeRectangleEndPoints(xs,ys,xf,yf,rLen,vel,nRows,yStep,tSlew)
    
    # now generate the trajectories, adding on segment by segment

    pMajTot, pMinTot, vMajTot, vMinTot, aMajTot, aMinTot = [],[],[],[],[],[]
    tTot = []

    for i in range(endPoints.shape[0]-1):
        p0 = endPoints[i][0]
        p1 = endPoints[i+1][0]
        v0 = endPoints[i][1]
        v1 = endPoints[i+1][1]
        T  = endPoints[i+1][2][0] - endPoints[i][2][0]

        # first segment is a slew
        if (not i % 2):
            A = pathSolve(p0, p1, v0, v1, T)
        else:
            A = zeros((2,3))

        # calculate this segment, with times starting at zero
        trajT = arange( float(T) / calc_dt) * calc_dt
        pMajor, pMinor, vMajor, vMinor, aMajor, aMinor = \
                trajGenerate(p0, v0, A, trajT)

        # increment the times to be the start of this segment, and add
        # to the accumulated total. Must be a better way to do this.

        trajT = trajT + endPoints[i][2][0]
        for j in range(len(trajT)):
            pMajTot.append(pMajor[j])
            pMinTot.append(pMinor[j])
            vMajTot.append(vMajor[j])
            vMinTot.append(vMinor[j])
            aMajTot.append(aMajor[j])
            aMinTot.append(aMinor[j])
            tTot.append(trajT[j])


    durations =  ones( len(tTot)) * calc_dt
    st = generate.scantable( [array(pMajTot) , array(pMinTot)] ,
                             [array(vMajTot) , array(vMinTot)] ,
                             [array(aMajTot) , array(aMinTot)] ,
                             durations
                             )
    
    hdl = [
        phdu,
        st,
        paramtab
        ]

    myraster = rasterscan(hdulist=hdl, x=pMajTot, y=pMinTot,
                          vx=vMajTot, vy=vMinTot,
                          ax=aMajTot, ay=aMinTot,
                          t=tTot)

    return myraster

#main("raster-19arcm-0p75vel-19row-0p12spcg-10secturn-0p1tab.fits",0.0,0.0,0.0,0.0,19.0,0.75,19,0.12,10.0,0.1)
#main("raster-19arcm-0p75vel-19row-0p12spcg-10secturn-0p2tab.fits",0.0,0.0,0.0,0.0,19.0,0.75,19,0.12,10.0,0.2)
#main("raster-19arcm-0p5vel-19row-0p12spcg-10secturn-0p2tab.fits",0.0,0.0,0.0,0.0,19.0,0.5,19,0.12,10.0,0.2)

#main("raster-4arcm-0p5vel-17row-0p12spcg-10secturn-0p1tab.fits",0.0,0.0,0.0,0.0,4.0,0.5,17,0.12,10.0,0.1)

#main("raster-30arcm-3p0vel-10row-0p5spcg-10secturn-0p2tab.fits",0.0,0.0,0.0,0.0,30.0,3.0,10,0.5,10.0,0.2)

#main("test.fits",0.0,0.0,0.0,0.0,19.0,0.5,19,0.12,10.0,calc_dt=0.2,xoff=10.0,yoff=-20.0)

#     1.0,18,24.0/60/60,5.0)

#main()
#main("noy-test1.fits",0.0, 0.0, 0.0, 0.0, 30.0 / 60, 30.0 / 60 / 60, 3, 0.0, 20.0)

#main("noy-test2.fits",0.0, 0.0, 0.0, 0.0, 30.0 / 60, 30.0 / 60 / 60, 3, 0.0, 40.0)
#main("raster1.fits",0.0, 0.0, 0.0, 0.0, 30.0 / 60, 30.0 / 60 / 60, 3,  20.0 / 60 / 60 , 10.0)

# main( fnameout,    xs,ys,xf,yf,rLen,vel,nRows,yStep,tSlew, calc_dt = 0.1 ):

#main("ka-raster1.fits",0.0, 0.0, 0.0, 0.0, 500.0 /60/ 60, 50.0 / 60 / 60, 13,  14.0 / 60 / 60 , 10.0)

#main("mustang7x7raster.fits",0.0,0.0,0.0,0.0,1.0,18,24.0/60/60,5.0)


     
#ptcsoutdir="/home/groups/ptcs/obs/turtle/scanpatterns/"
#ptcsoutdir="/users/bmason/gbt-dev/scanning/ptcsTraj/"

#if 1:

    #main('karaster15x2-6sec.fits',0.0,0.0,0.0,0.0,15.0/60.0,1.0,15,8.0/60.0/60.0,0.5)
    # notes: angles are input in deg ; vel is deg/sec
    # 13apr07 nominal for ldn1622--
   # main('karaster15x2-6sec.fits',xs=-0.13,ys=-0.015,xf=0.13,yf=0.015,rLen=(15.0/60.0),vel=1.0/60.0,
   #      nRows=15,yStep=(8.0/60.0/60.0),tSlew=6.0)    
    ##main('karaster5x2-6sec.fits',xs=0.0,ys=0.0,xf=0.0,yf=0.0,rLen=(5.0/60.0),vel=0.5/60.0,
    #     nRows=15,yStep=(8.0/60.0/60.0),tSlew=6.0)    
    
    #main('parfind.fits',0.0,0.0,0.0,0.0,)
    # This is to fully sample a ka-band at 28GHz and be about 7 beams clear at 28 GHz
    #main(os.path.join(ptcsoutdir,"ka-raster2.fits"),
#         0.0, 0.0, 0.0, 0.0,
#         500.0 /60/ 60,
#         50.0 / 60 / 60,
#         nRows=17,
#         yStep=(12.0 / 60 / 60 ),
#         tSlew=10.0)


