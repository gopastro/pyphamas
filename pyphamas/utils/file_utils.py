"""
Some simple file utilities
"""

import os
import glob

def get_latest_files(direc='/media/Disk1/spec', globpat="*.bin", 
                     numfiles=1):
    if not os.path.exists(direc):
        raise Exception("direc: %s does not exist")
    lis = glob.glob(os.path.join(direc, globpat))
    lis.sort(key=os.path.getctime, reverse=True)
    return lis[:numfiles]
