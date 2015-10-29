import socket
import time
from gbt.ygor import GrailClient, getConfigValue

class GBTScan(object):
    def __init__(self, x64IP="172.23.1.60", x64port=6023,
                 grailhost="toe", grailport=18000, 
                 verbose=True):
        self.verbose = verbose
        self.grailhost = getConfigValue(grailhost, 'GrailHost')
        if self.verbose:
            print "Grailhost is > %s" % self.grailhost
        self.cl = GrailClient(self.grailhost, grailport)
        self.SC = self.cl.create_manager('ScanCoordinator')
        self.auto_set = False
        self.x64IP = x64IP
        self.x64port = x64port
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
        stateval = value['state']['state']['value']
        print "state:", stateval
        if stateval == 'Committed':
            print "Stateval changed to committed"
            print "Current Scan number is : %s" % self.SC.get_value('scanNumber')
            print "Current Scan number within cbis : %s" % device.get_value('scanNumber')
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
        
    def init_roach(self):
        self.sock.sendall('INIT\n')
        msg = self.sock.recv(128)
        if self.verbose:
            print msg

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
                       dmjd_start=None):
        # do setup parameters first
        self.x64_send_with_ack("SETUP BIN_START=%d BIN_END=%d\n" % (bin_start, bin_end))
        self.x64_send_with_ack("SETUP COL_START=%d COL_END=%d\n" % (col_start, col_end))
        self.x64_send_with_ack("SETUP ROW_START=%d ROW_END=%d\n" % (row_start, row_end))
        self.x64_send_with_ack("SETUP NUM_SECS=%g LSB_SEL=%d\n" % (num_secs, lsb_sel))
        self.x64_send_with_ack("GBTSCAN SOURCE_NAME=%s SCAN_NUMBER=%d DMJD_START=%s\n" % (source_name, scan_number, dmjd_start))
        
