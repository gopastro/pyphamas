import socket
import time
from gbt.ygor import GrailClient, getConfigValue

class GBTScan(object):
    def __init__(self, x64IP="172.23.1.60", x64port=6023,
                 grailhost="toe", grailport=18000, 
                 verbose=True, testmode=False):
        self.verbose = verbose
        self.grailhost = getConfigValue(grailhost, 'GrailHost')
        if self.verbose:
            print "Grailhost is > %s" % self.grailhost
        self.cl = GrailClient(self.grailhost, grailport)
        self.SC = self.cl.create_manager('ScanCoordinator')
        self.auto_set = False
        self.x64IP = x64IP
        self.x64port = x64port
        self.testmode = testmode
        self.connect_x64()

    def connect_x64(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.x64IP, self.x64port))

    def state_callback(self, device, parameter, value):
        """This is called whenever scans are run on the GBT telescope. The GBT
        M&C system states transition to "Running" via "Comitted." This is
        thus a good state to look for to catch the system about to start a
        scan. Likewise, 'Stopping' or 'Aborting' is a a good indicator
        that a scan is coming to an end.
        """
        if self.verbose:
            print "Device: %s. Parameter: %s" % (device, parameter)
        stateval = value['state']['state']['value']
        if self.verbose:
            print "state: %s" % stateval
        if stateval == 'Committed':
            print "Stateval changed to committed"
            print "Current Scan number is : %s" % self.SC.get_value('scanNumber')
            dmjd_start = self.get_mjd()
            source_name = self.SC.get_value('source')
            try:
                scan_number = int(self.SC.get_value('scanNumber'))
            except ValueError:
                scan_number = 0
            # need to get integration time correctly
            num_secs = self.get_scanLength()
            if self.testmode:
                if num_secs > 1.0:
                    num_secs = 1.0 # cap at 1 seconds for test mode to prevent large files
            project_id = self.SC.get_value('projectId')
            receiver = self.SC.get_value('receiver')
            self.start_gbt_scan(dmjd_start=dmjd_start, source_name=source_name,
                                num_secs=num_secs,
                                scan_number=scan_number,
                                project_id=project_id,
                                receiver=receiver)
        elif stateval == 'Stopping' or stateval == 'Aborting':
            print "Stopping with stateval : %s" % stateval

    def source_callback(self, device, parameter, value):
        """
        This is called whenever the observer sets the 'source' parameter
        """
        if parameter == 'source':
            print "Source changed to: %s" % value['source']['source']['value']        

    def set_auto(self):
        """
        Enable GBT telescope events to be monitored for state and source parameters.
        """
        if not self.auto_set:
            self.SC.reg_param('state', self.state_callback)
            self.SC.reg_param('source', self.source_callback)
            self.auto_set = True        

    def clear_auto(self):
        """
        Disable GBT telescope events to be monitored for state and source parameters.
        """
        if self.auto_set:
            self.SC.unreg_param('state', self.state_callback)
            self.SC.unreg_param('source', self.source_callback)
            self.auto_set = False        
        
    def get_mjd(self):
        """
        Gets Modified Julian Date from
        the startTime structure of ScanCoordinator
        """
        st = self.SC.get_parameter('startTime')
        # integer number of seconds since midnight
        secs = int(st['startTime']['startTime']['seconds']['value'])
        return int(st['startTime']['startTime']['MJD']['value']) + \
            (float(secs)/(24*3600.))

    def get_scanLength(self):
        sl = self.SC.get_parameter('scanLength')
        # floating point seconds of integration
        try:
            secs = float(sl['scanLength']['scanLength']['seconds']['value'])
        except ValueError:
            secs = 1.0 # some sane default
        return secs
                   
    def init_roach(self):
        self.sock.sendall('INIT\n')
        msg = self.sock.recv(128)
        if self.verbose:
            print msg
        if msg == "init ok":
            print "Roach successfully initialized"
            
    def close_x64(self):
        self.sock.close()

    def x64_send_with_ack(self, text):
        self.sock.sendall(text)
        msg = self.sock.recv(128)
        if self.verbose:
            print msg

    def start_gbt_scan(self, bin_start=98, bin_end=160,
                       col_start=0, col_end=5,
                       row_start=0, row_end=7,
                       num_secs=1.0, lsb_sel=8,
                       source_name='', scan_number=1,
                       dmjd_start=None, project_id="",
                       receiver=""):
        # do setup parameters first
        self.x64_send_with_ack("SETUP BIN_START=%d BIN_END=%d\n" % (bin_start, bin_end))
        self.x64_send_with_ack("SETUP COL_START=%d COL_END=%d\n" % (col_start, col_end))
        self.x64_send_with_ack("SETUP ROW_START=%d ROW_END=%d\n" % (row_start, row_end))
        self.x64_send_with_ack("SETUP NUM_SECS=%g LSB_SEL=%d\n" % (num_secs, lsb_sel))
        self.x64_send_with_ack("GBTSCAN SOURCE_NAME=%s SCAN_NUMBER=%d DMJD_START=%s PROJECT_ID=%s RECEIVER=%s\n" % (source_name, scan_number, dmjd_start, project_id, receiver))
        
