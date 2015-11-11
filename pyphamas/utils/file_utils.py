"""
Some simple file utilities
"""

import os
import glob

def get_latest_files(direc='/media/Disk1/spec', globpat="*.bin", 
                     numfiles=1):
    if not os.path.exists(direc):
        raise Exception("direc: %s does not exist" % direc)
    lis = glob.glob(os.path.join(direc, globpat))
    lis.sort(key=os.path.getctime, reverse=True)
    return lis[:numfiles]

def get_gbtscan_file(direc='/media/Disk1/nov8_2015', 
                     scan=17, numfiles=1):
    if not os.path.exists(direc):
        raise Exception("direc: %s does not exits" % direc)
    lis = glob.glob(os.path.join(direc, "*_%d.bin" % scan))
    lis.sort(key=os.path.ctime, reverse=True)
    return lis[:numfiles]
