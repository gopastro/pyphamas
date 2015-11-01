"""
At the GBT uses the prologix ethernet to GPIB 
adapter to talk to the synthesizer
"""
import telnetlib
import time

class SecondSynth(object):
    """
    Helper class for the Second Synth
    HP83620A
    """
    def __init__(self, IP="gpib1.gbt.nrao.edu",
		 PORT=1234, verbose=True):
	"""
	Initializes telnet connection. Port 1234
	is the port to talk to the synth
	"""
	self.tn = telnetlib.Telnet(host=IP, port=PORT)
	self.verbose = verbose
	if self.verbose:
	    print "Connected to Synthesizer H83620A"
            print self.getID()
            

    def ask(self, txt):
        """
        Sends some txt that merits a response
        and adjusts the meta commands to prologix
        to get data back
        """
        self.tn.write(txt)
        self.tn.write("++read eoi\n")
        return self.tn.read_some()
	
    def write(self, txt):
        self.tn.write(txt)

    def getID(self):
        return self.ask("*IDN?\n")

    def getFreq(self):
        freqtxt = self.ask(":FREQ:CW?\n")
        return float(freqtxt.strip())

    def setFreq(self, freq):
        if freq<1e9:
            fstr = "%s MHz" % (freq/1.e6)
        else:
            fstr = "%s GHz" % (freq/1.e9)
        self.write(":FREQ:CW %s\n" % fstr)

    def getPower(self):
        powertxt = self.ask(":POW:LEV?\n")
        return float(powertxt.strip())
    
    def setPower(self, level):
        self.write(":POW:LEV %sDBM\n" % float(level))

    def close(self):
        self.tn.close()
