"""
At the GBT uses the terminal server
"""
import telnetlib
import time

class OmegaServer:
    """
    Helper class for the Omega CYD208 Thermometer
    """
    def __init__(self, IP="172.23.1.68", 
		 PORT=15, unit="K", verbose=False):
	"""
	Initializes telnet connection. Port 15 has been set up
	with the right serial port parameters
	"""
	self.tn = telnetlib.Telnet(host=IP, port=PORT)
	self.verbose = verbose
	if self.verbose:
	    print "Setting Unit to %s" % unit
	self.unit = unit
	self.tn.write('F0%s\r\n' % self.unit) # Sets temp. unit (K/C/F)
	
    def parse_temperature(self, txt):
	"Parses Omega text output into channel # and temp"
	
	chantxt, temptxt, alarmtxt = txt.strip().split(',')
	dic = {}
	dic[chantxt] = temptxt
	return dic
    
    def read_chan(self, chan, unit='K', settle=8):
	"""
	Reads temperature ('K','C','F') from given channel ('chan');
	Meter settle time should be set to >= 6 seconds
	"""
	if self.unit != unit:
	    self.tn.write('F0%s\r\n' %unit) # Sets temp. unit (K/C/F)
	    time.sleep(5) # time to change units
	self.tn.write('YC%s\r\n' %chan) # Sets channel number
	time.sleep(settle) # Time needed for therm to settle
	
	self.tn.write('WS\r\n') # Requests sample sensor reading
	
	txt = self.tn.read_some()
	if self.verbose:
	    print "Received text: %s" % txt
	# txt = ''
	# t = self.ser.read() # Arguments are delimitted by ','
	# txt += t
		
	# while t != '\n': # Newline is final read argument
	#     t = self.ser.read()
	#     txt += t

	info = self.parse_temperature(txt) #Parse text for channel # and temp
	
	chan = info.keys()[0]
	temp = info[chan]

	if self.verbose:
	    print 'Channel %s, Temp = %s' %(chan,temp)
	    
	return info

    def monitor_mode(self, chan_list = [1,2,3,4,5,6], unit='K', dwell=1): 
	"""
	Indefinitely runs ticker of channels in 'chan_list'; 
	use adjustable 'dwell' time for pacing, not necessary 
	for meter to settle
	"""
	
	while(True):	
	
	    print
	    print 'Omega CYD208 Monitor Mode'
	    print 'Channels = ', chan_list
	    print 'Use Ctrl + "c" to stop'
	    print
	    
	    for chan in chan_list:
		self.read_chan(chan, unit)
		time.sleep(dwell) # total time = dwell + settle

		

