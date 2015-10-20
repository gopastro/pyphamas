'''
Message Parser (msg_parse.py)

This module serves to parse messages received
by the telescope control.  It extractsm, at minimum,
the following data from the message:

	1. The name of the function to perform
	
The data is stored in a list in the following
manner:
	
	[name, ..., parameter, ...]

In other words, if the list is named "data," this would be
the array breakdown:

    data[0] = function name
    data[1] = parameter
	...
	
The first element in "data" will always be the name of the
function to perform.  This can be any of the following:

	1. daq (Data Acquisition)
	2. bf (Beamforming)
	3. x (Correlation)
	4. spec (Spectrometry)

'''

#from elementtree.ElementTree import parse
from xml.etree.ElementTree import parse
import re
import string

class parser:
    
    def __init__(self, config, simulate):
        self.regexs = dict()
        self.errs = dict()
        self.err_formats = dict()
        self.simulate = simulate

        tree = parse(config)
        root = tree.getroot()
        parse_tag = root.find("msg_parse")
        msg_iter = parse_tag.findall("msg")
        for child in msg_iter:
            self.regexs[child.get("name")] = child.text.strip()
            if child.get("err") != None:
                if child.get("err") == "1":
                    self.errs[child.get("name")] = True
                    if child.get("err_format") != None:
                        self.err_formats[child.get("name")] = child.get("err_format").text
                else:
                    self.errs[child.get("name")] = False
            else:
                self.errs[child.get("name")] = False

    '''
    parse
    Checks the message against all of the regular expression
    patterns.  If a match is made, the appropriate parsing
    method is called.
    '''
    def parse(self, msg, pthread, sock):
        match = 0
        for key in self.regexs.keys():
            reg = re.compile(self.regexs[key])
            if reg.match(msg.strip()) != None:
                match = 1
	        return [key, msg]
        #if match == 0:
            #if self.acks[key] == 1:
            #    sock.sendall(key.lower() + " err - msg \"" + msg + "\" does not match any predefined patterns")
