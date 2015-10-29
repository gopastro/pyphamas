from gbt.ygor import GrailClient, getConfigValue

class GBTCoordinate(object):
    def __init__(self, hostname, portnumber=18000):
        grailhost = getConfigValue(hostname, 'GrailHost')
        print "Grailhost is > %s" % grailhost
        self.cl = GrailClient(grailhost, portnumber)
        self.SC = self.cl.create_manager('ScanCoordinator')
        self.auto_set = False

    def state_callback(self, device, parameter, value):
        """This is called whenever scans are run on the GBT telescope. The GBT
        M&C system states transition to "Running" via "Comitted." This is
        thus a good state to look for to catch the system about to start a
        scan. Likewise, 'Stopping' or 'Aborting' is a a good indicator
        that a scan is coming to an end.
        """
        print "Received parameter", parameter, "from device", device
        stateval = value['state']['state']['value']
        print "state:", stateval
        if stateval == 'Committed':
            print "Stateval changed to committed"
            print "Current Scan number is : %s" % self.SC.get_value('scanNumber')
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

