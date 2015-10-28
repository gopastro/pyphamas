import serial
import time

class OmegaCYD208:
    """Helper class for the Omega CYD208 Thermometer
    """
    def __init__(self, port='/dev/ttyUSB1'):
	"Initializes usb port, baudrate, bytesize, parity and stopbits"
	
	self.baudrate = 300
	self.bytesize = serial.SEVENBITS
	self.parity = serial.PARITY_ODD
	self.stopbits = serial.STOPBITS_ONE
	
	self.ser = serial.Serial(port=port, baudrate=self.baudrate,
				 bytesize=self.bytesize, parity=self.parity,
				 stopbits=self.stopbits)

    def parse_temperature(self, txt):
	"Parses Omega text output into channel # and temp"
	
	chantxt, temptxt, alarmtxt = txt.strip().split(',')
	dic = {}
	dic[chantxt] = temptxt
	return dic
    
    def  read_chan(self, chan, unit='K', settle=6, verbose=False):
	"Reads temperature ('K','C','F') from given channel ('chan');\n\
	Meter settle time should be set to >= 6 seconds"
	
	self.ser.write('F0%s\r\n' %unit) # Sets temp. unit (K/C/F)
	self.ser.write('YC%s\r\n' %chan) # Sets channel number
	time.sleep(settle) # Time needed for therm to settle
	
	self.ser.write('WS\r\n') # Requests sample sensor reading
	
	txt = ''
	t = self.ser.read() # Arguments are delimitted by ','
	txt += t
		
	while t != '\n': # Newline is final read argument
	    t = self.ser.read()
	    txt += t

	info = self.parse_temperature(txt) #Parse text for channel # and temp
	
	chan = info.keys()[0]
	temp = info[chan]

	if verbose:
	    print 'Channel %s, Temp = %s' %(chan,temp)
	    
	    return info

    def monitor_mode(self, chan_list = [1,2,3,4,5,6], unit='K', dwell=1): 
	"Indefinitely runs ticker of channels in 'chan_list'; use adjustable\n\
	'dwell' time for pacing, not necessary for meter to settle"
	
	while(True):	
	
	    print
	    print 'Omega CYD208 Monitor Mode'
	    print 'Channels = ', chan_list
	    print 'Use Ctrl + "c" to stop'
	    print
	    
	    for chan in chan_list:
		
		self.read_chan(chan, unit, verbose=True)
		time.sleep(dwell) # total time = dwell + settle

		

