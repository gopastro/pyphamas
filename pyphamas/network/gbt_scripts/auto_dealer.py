# This is GBT/Ygor specific:
from gbt.ygor import GrailClient
import dealer

cl = GrailClient("wind", 18000)
SC = cl.create_manager('ScanCoordinator')
V = cl.create_manager('VEGAS')
d = dealer.Dealer()

class SWbits:
    """
    A class to hold and encode the bits of a single phase of a switching signal generator phase
    """
    SIG=0
    REF=1
    CALON=1
    CALOFF=0


auto_set = False

def state_callback(a, b, c):
    """This is called whenever scans are run on the GBT telescope. The GBT
    M&C system states transition to "Running" via "Comitted." This is
    thus a good state to look for to catch the system about to start a
    scan. Likewise, 'Stopping' or 'Aborting' is a a good indicator
    that a scan is coming to an end.

    """
    global d
    stateval = c['state']['state']['value']
    print "state:", stateval
    if stateval == 'Committed':
        print "prepare:", d.prepare()
        print "start  :", d.start()
    elif stateval == 'Stopping' or stateval == 'Aborting':
        print d.stop()

def vegas_sb_callback(a, b, c):
    """This callback sets the DIBAS 'subband_freq' parameter based on the
       VEGAS coordinator's "sub_frequencyA" parameter.

    """
    global d
    windows = [float(c['sub_frequencyA'][str(i)]['value']) for i in range(1,9)]
    print "windows:", windows
    try:
        d.set_param(subband_freq=windows)
    except:
        pass

def source_callback(a, b, c):
    """
    This is called whenever the observer sets the 'source' parameter
    """
    global d
    if b == 'source':
        d.set_status(SRC_NAME=c['source']['source']['value'])

def set_auto():
    """
    Enable GBT telescope events to be monitored for state and source parameters.
    """
    global auto_set
    if not auto_set:
        SC.reg_param('state', state_callback)
        SC.reg_param('source', source_callback)
        V.reg_param('sub_frequencyA', vegas_sb_callback)
        auto_set = True

def clear_auto():
    """
    Disable GBT telescope events to be monitored for state and source parameters.
    """
    global auto_set
    if auto_set:
        SC.unreg_param('state', state_callback)
        SC.unreg_param('source', source_callback)
        V.unreg_param('sub_frequencyA', vegas_sb_callback)
        auto_set = False
