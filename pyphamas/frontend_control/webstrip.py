"""Utility script that is used to control the
ethernet-controlled webstrip to turn on and off ports"""

import urllib2
import urllib
import re
from optparse import OptionParser
import sys

def get_status(msg):
    stat_dic = {}
    for i in range(1, 9):
        #if 'ON' in re.findall(r'a href=outlet\?%d=([A-Z]{1,3})>' % i, msg):
        if 'ON' in re.findall(r'href=outlet\?%d=([A-Z]{1,3})>' % i, msg):            
            stat_dic[i] = 0
        else:
            stat_dic[i] = 1
    return stat_dic

class WebStrip(object):
    def __init__(self, host="rempwrstrip.gbt.nrao.edu",
                 admin="admin",
                 password="dbps"):
        self.host = host
        self.admin = admin
        self.password = password
        self.basename = "http://%s/" % self.host
        self._get_connection()

    def _get_connection(self):
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
        urllib2.install_opener(self.opener)
        self.params = urllib.urlencode(dict(Username=self.admin, 
                                       Password=self.password))
        try:
            f = self.opener.open("%slogin.tgi" % self.basename, self.params)
            f.read()
            f.close()
        except:
            print "Could not login"
            raise Exception("Could not login")
        
    def get_status(self):
        f = self.opener.open("%sindex.htm" % self.basename)
        msg = f.read()
        stat = get_status(msg)
        f.close()
        return stat
    
    def port_on(self, port):
        f = self.opener.open("%soutlet?%d=%s" % (self.basename, port, "ON"))
        f.read()
        f.close()    
        return self.get_status()
    
    def port_off(self, port):
        f = self.opener.open("%soutlet?%d=%s" % (self.basename, port, "OFF"))
        f.read()
        f.close()    
        return self.get_status()
        
if __name__ == '__main__':
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option("-H", "--host", dest="hostname",
                      default="192.168.151.101:80",
                      help="hostname to connect like: 192.168.151.101:80 or localhost:9022 [default: %default]")
    parser.add_option("-s", "--status", dest="status",
                      action="store_true", default=False,
                      help="return status of ports")
    parser.add_option("-p", "--password", dest="password",
                      default="1234",
                      help="password for admin")
    for i in range(1, 9):
        parser.add_option("--port%d" % i,
                          dest="port%d" % i,
                          choices=["ON", "OFF"],
                          type="choice",
                          help="choices are ON or OFF")
    (options, args) = parser.parse_args()
    password = options.password
    hostname = options.hostname
    basename = "http://%s/" % hostname
    #turn on cookies
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
    urllib2.install_opener(opener)
    params = urllib.urlencode(dict(Username='admin', Password=password))
    try:
        f = opener.open("%slogin.tgi" % basename, params)
        f.read()
        f.close()
    except:
        print "Could not login"
        sys.exit(-1)
    f = opener.open("%sindex.htm" % basename)
    msg = f.read()
    stat = get_status(msg)
    f.close()
    if options.status:
        print stat
    prt_set = False
    for i in range(1, 9):
        prt = getattr(options, "port%d" % i)
        if prt is not None:
            f = opener.open("%soutlet?%d=%s" % (basename, i, prt))
            f.read()
            f.close()
            prt_set = True  #some port was set
    if prt_set:
        f = opener.open("%sindex.htm" % basename)
        msg = f.read()
        stat = get_status(msg)
        f.close()    
        print stat

    #f = opener.open("
