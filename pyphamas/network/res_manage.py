'''
Resource Manager (res_manage.py)

This module manages the various ROACH boards and software processes.
It ensures that processes are running as long as necessary as well as
ensuring that a ROACH isn't repurposed before it is terminated.

The way it manages the various processes is by creating an object
and associating it with a ROACH board. When a TCP/IP command tries
to start a process that is already associated with a ROACH board,
this module sends an error message to the Telescope Control.
'''

#from elementtree.ElementTree import parse
from xml.etree.ElementTree import parse
import datetime
import time
import struct
import corr
import subprocess
import os
import signal
import re

class manager:
    
    def __init__(self, config, simulate):
        self.roaches = dict()
        self.cmds = dict()
        self.cmd_params = dict()

        self.ack_flags = dict()
        self.err_flags = dict()
        self.ack_formats = dict()
        self.ack_timings = dict()
        self.err_formats = dict()

        self.simulate = simulate
        tree = parse(config)
        elem = tree.getroot()
        
        msg_tag = elem.find("msg_parse")

        # Iterate through all msg tags
        iterate = msg_tag.findall("msg")
        for child in iterate:
            if child.get("name") != None:
                msg_name = child.get("name").strip()
                
                # Link message name to command name
                self.cmds[msg_name] = child.get("cmd").strip()
                
                # Create structure for dynamic parameter regular expressions
                if msg_name not in self.cmd_params:
                    self.cmd_params[msg_name] = dict()

                # Iterate over all message param tags
                msg_params = child.findall("param")
                for child2 in msg_params:
                    # Link param name and regular expressions to message name
                    param_name = child2.get("name").strip()
                    if param_name not in self.cmd_params[msg_name]:
                        self.cmd_params[msg_name][param_name] = []
                    regex1 = re.compile(child2.text)
                    temp = re.split("\(\?\#\)", child2.text)
                    regex2 = re.compile(temp[1])
                    self.cmd_params[msg_name][param_name] = [regex1, regex2]
                
                # Save ack flags and ack message formats (if applicable)
                if child.get("ack") != None:
                    if child.get("ack") == "1":
                        self.ack_flags[msg_name] = True

                        # Extract ack message format
                        self.ack_formats[msg_name] = child.find("ack_format").text

                        # Extract ack timing
                        self.ack_timings[msg_name] = child.find("ack_timing").text

                    else:
                        self.ack_flags[msg_name] = False
                else:
                    self.ack_flags[msg_name] = False
                
                # Save err flags and err message formats (if applicable)
                if child.get("err") != None:
                    if child.get("err") == "1":
                        self.err_flags[msg_name] = True

                        # Extract err message format
                        self.err_formats[msg_name] = child.find("err_format").text
                    else:
                        self.err_flags[msg_name] = False
                else:
                    self.err_flags[msg_name] = False

        res_mang_tag = elem.find("res_manage")
	res_tag = res_mang_tag.find("resources")
        iterate = res_tag.getiterator()
        for child in iterate:
            if child.get("name") != None:
                self.roaches[child.get("name")] = child.text

        config_tag = res_mang_tag.find("configuration")
        process_tags = config_tag.findall("process")
        for process in process_tags:
            if process.get("name") == "daq":
                self.parse_daq(process)
            elif process.get("name") == "bf":
                self.parse_bf(process)
            elif process.get("name") == "x":
                self.parse_x(process)
        
        self.gulp = None

        gulp_tag = res_mang_tag.find("gulp")
        self.params["buffer"] = gulp_tag.find("buffer").text
        self.params["out_dir"] = gulp_tag.find("out_dir").text
        self.params["if"] = gulp_tag.find("if").text
        self.params["verbose"] = int(gulp_tag.find("verbose").text)


    def parse_daq(self, process_tag):
        self.daq_bits = dict()
        bitstreams = process_tag.findall("bitstream")
        for bits in bitstreams:
            self.daq_bits[bits.get("fft")] = bits.text

        self.params = dict()
        param_tag = process_tag.find("params")
        params = param_tag.findall("param")
        for child in params:
           if child.get("name") == "spec_dir":
               self.params[child.get("name")] = child.text
           else:
               self.params[child.get("name")] = int(child.text)
        
        roach_tag = process_tag.find("roach")
        self.daq_roach = roach_tag.text
        if process_tag.find("ip") != None:
             self.params["ip"] = process_tag.find("ip").text


    def parse_bf(self, process_tag):
        self.bf_bits = dict()
        bitstreams = process_tag.findall("bitstream")
        for bits in bitstreams:
            self.bf_bits[bits.get("fft")] = bits.text
        
        roach_tag = process_tag.find("roach")
        self.bf_roach = roach_tag.text
        
        
    def parse_x(self, process_tag):
        self.x_bits = dict()
        bitstreams = process_tag.findall("bitstream")
        for bits in bitstreams:
            self.x_bits[bits.get("fft")] = bits.text
            
        roach_tag = process_tag.find("roachf")
        self.x_roachf = roach_tag.text
        
        roach_tag = process_tag.find("roachx")
        self.x_roachx = roach_tag.text

   
    def parse_cmd_params(self, data, server, sock):
        msg_name = data[0]
        for param_name in self.cmd_params[msg_name]:
            regex1 = self.cmd_params[msg_name][param_name][0]
            regex2 = self.cmd_params[msg_name][param_name][1]
            a = re.search(regex1, data[1])
            if a == None:
                continue
            b = re.search(regex2, a.group(0))
            new_param = b.group(0)
            self.params[param_name] = new_param
            print "BYU: Parameter Change, " + param_name + " = " + new_param

    def run_process(self, data, server, sock):
        print "\n"
        self.cur_msg_name = data[0]
        self.parse_cmd_params(data, server, sock)
        if self.ack_flags[self.cur_msg_name]:
            if self.ack_timings[self.cur_msg_name] == "before":
                print "BYU->Telescope: " + self.ack_formats[self.cur_msg_name]
                sock.sendall(self.ack_formats[self.cur_msg_name] + "\n")

        if self.cmds[data[0]] == "daq_start":
            self.run_daq_start(data, server, sock)

        elif self.cmds[data[0]] == "daq_scan":
            self.run_daq_scan(data, server, sock)

        elif self.cmds[data[0]] == "daq_setup":
            self.run_daq_setup(data, server, sock)

        elif self.cmds[data[0]] == "gbt_scan":
            self.run_gbt_scan(data, server, sock)

        elif self.cmds[data[0]] == "daq_spec":
            self.run_daq_spec(data, server, sock)

        elif self.cmds[data[0]] == "daq_end":
            self.run_daq_end(data, server, sock)

        elif self.cmds[data[0]] == "bf":
            #self.run_bf(data, server, sock)
            print "BYU->Telescope: " + self.err_formats[self.cur_msg_name] % "bf command is not implemented"
            sock.sendall(self.err_formats[self.cur_msg_name] % "bf command is not implemented\n")

        elif self.cmds[data[0]] == "bf_coeff":
            #self.run_bfcoeff(data, server, sock)
            print "BYU->Telescope: " + self.err_formats[self.cur_msg_name] % "bf_coeff command is not implemented"
            sock.sendall(self.err_formats[self.cur_msg_name] % "bf_coeff command is not implemented\n")

        elif self.cmds[data[0]] == "spec":
            #self.run_spec(data, server, sock)
            print "BYU->Telescope: " + self.err_formats[self.cur_msg_name] % "spec command is not implemented"
            sock.sendall(self.err_formats[self.cur_msg_name] % "spec command is not implemented\n")

        elif self.cmds[data[0]] == "x":
            #self.run_x(data, server, sock)
            print "BYU->Telescope: " + self.err_formats[self.cur_msg_name] % "x command is not implemented"
            sock.sendall(self.err_formats[self.cur_msg_name] % "x command is not implemented\n")

        else:
            print "BYU->Telescope: " + data[0].lower() + " no x64 BYU process exists for this command. Check your configuration file (.xml)."
            sock.sendall(data[0].lower() + " no x64 BYU process exists for this command. Check your configuration file (.xml)\n")
            return
        
        if self.ack_flags[self.cur_msg_name]:
            if self.ack_timings[self.cur_msg_name] == "after":
                print "BYU->Telescope: " + self.ack_formats[self.cur_msg_name]
                sock.sendall(self.ack_formats[self.cur_msg_name] + "\n")
    
    

    def prog_fpga(self, fpga, roach, bitstream, sock):
        time.sleep(0.5)
        
        if not fpga.is_connected():
            print "BYU->Telescope: " + self.err_formats[self.cur_msg_name] % roach + " is not connected."
            sock.sendall(self.err_formats[self.cur_msg_name] % roach + " is not connected.\n")
            exit()
            
        fpga.progdev(bitstream)
        time.sleep(0.1)
        
        fpga.write_int("sys_scratchpad", 0xdeadbeef)
        time.sleep(0.1)

        temp = fpga.read_uint("sys_scratchpad")
        
        if temp != 0xdeadbeef:
            print "BYU->Telescope: " + self.err_formats[self.cur_msg_name] % "sys_scratchpad = " + str(temp) + " vs. " + str(0xdeadbeef)
            sock.sendall(self.err_formats[self.cur_msg_name] % "sys_scratchpad = " + str(temp) + " vs. " + str(0xdeadbeef) + "\n")


    def align_adc(self, fpga, sock):
        calreg = "x64_adc_ctrl"
        CTRL = 0x0
        DELAY_CTRL = 0x4
        DATASEL = 0x8
        DATAVAL = 0xc
        for j in range(0,8):
            fpga.blindwrite(calreg, "%c%c%c%c"%(0x0,0x0,0x0,j//2), DATASEL)
            fpga.blindwrite(calreg, "%c%c%c%c"%(0x0,0x0,0x0,1<<j), DELAY_CTRL)
            
            # This is a counter for a rudimentary watchdog timer
            w_dog = 0
            # This is a magic number for the timer (may need to be adjusted)
            w_dog_max = 100000
            
            stable = 1
            while stable == 1:
                fpga.blindwrite(calreg, "%c%c%c%c"%(0x0,0xff,1<<j,0x0),DELAY_CTRL)
                val 	= struct.unpack('>L', (fpga.read(calreg,4,DATAVAL)))[0]
                val0	= (val & ((0xffff)<<(16*(j%2))))>>(16*(j%2))
                stable	= (val0 & 0x1000)>>12
                w_dog 	= w_dog + 1		# Increment watchdog timer
                if w_dog > w_dog_max:	# If watchdog timer overflows, print error and return
                    print "BYU->Telescope: " + self.err_formats[self.cur_msg_name] % "WATCHDOG ADC ERROR in calibrate_adc."
                    sock.sendall(self.err_formats[self.cur_msg_name] % "WATCHDOG ADC ERROR in calibrate_adc.\n")
                    exit()

                for i in range(10):
                    fpga.blindwrite(calreg, "%c%c%c%c"%(0x0,0xff,1<<j,0x0),DELAY_CTRL)
        return 1
        
        
    def init_gbe(self, fpga):
        if self.params["ip"] != None:
            ip_str = self.params["ip"]
            values = re.split("\.", ip_str)
            dest_ip = (int(values[0]) << 24) + (int(values[1]) << 16) + (int(values[2]) << 8) + int(values[3])
        else:
            dest_ip = (10 << 24) + 30 # This can be parameterized!!!!!!!!
            ip_str = "10.0.0.30"
        
        print "BYU: Setting up 10 GbE to transmit to " + ip_str
        source_ip = (10 << 24) + 20
        mac_base = (2 << 40) + (2 << 32)
        fabric_port = 60000
        
        if self.simulate == False:
            fpga.write_int("ctrl", 0)
            fpga.write_int("ctrl", 1)
            fpga.write_int("ctrl", 0)
        
            fpga.write_int("ctrl", 16)
        
            linkup = bool(fpga.read_int("gbe0_linkup"))
            if not linkup:
                print "BYU->Telescope: " + self.err_formats[self.cur_msg_name] % "There is no cable plugged into port 0."
                sock.sendall(self.err_formats[self.cur_msg_name] % "There is no cable plugged into port 0.\n")
                exit()
            
            fpga.tap_start(
                "gbe0",
                mac_base + source_ip,
                source_ip,
                fabric_port)
            
            fpga.write_int("dest_ip", dest_ip)
            fpga.write_int("dest_port", fabric_port)
        
            fpga.write_int("rst", 3)
            fpga.write_int("rst", 0)
        
        return 1
        
    
    '''
    run_daq_start
    This method starts the Data Acquisition System.
    '''
    def run_daq_start(self, data, server, sock):

        cmd = data[0]
        self.fft_length = self.params["fft_length"]
        
        bitstream = self.daq_bits[str(self.fft_length)]
        self.fpga = corr.katcp_wrapper.FpgaClient(self.daq_roach)
        
        print "BYU: Initializing " + self.daq_roach + " for Data Acquisition"
        print "BYU: Programming FPGA..."
        if self.simulate == False:
            self.prog_fpga(self.fpga, self.daq_roach, bitstream, sock)
        print "BYU: Configuring ADC for alignment..."
        if self.simulate == False:
            self.align_adc(self.fpga, sock)
        print "BYU: Initializing 10 GbE..."
        self.init_gbe(self.fpga)
        
        if self.simulate == False:
            while self.fpga.read_uint("check_bits1") != 16:
                print self.fpga.read_uint("check_bits1")
                #print "caspermain: Programming FPGA..."
                #self.prog_fpga(self.fpga, self.daq_roach, bitstream)
                print "BYU: Configuring ADC for alignment..."
                self.align_adc(self.fpga, sock)
                print "BYU: Initializing 10 GbE..."
                self.init_gbe(self.fpga)

        #print "BYU: Starting Gulp..."
        #self.start_gulp(r"/media/Disk1")
        #self.start_gulp(self.params["out_dir"])
        
        self.k = 0
        self.i = 0
        
        time.sleep(2.5)
        #sock.sendall("Finished!")
        

    def start_gulp(self, direct):
        if self.simulate == False:
            print "BYU: Running set_cores.sh"
            set_cores = subprocess.Popen(
                "/set_cores.sh 0xff00", #Could be added to config file
                shell=True,
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE)
            set_cores.wait()
        
#        gulp_str = "schedtool -F -p 99 -a 0xf -e /apps/gulp -i " + self.params["if"] + " -f 'udp' -r " + str(140000)
        gulp_str = "schedtool -F -p 99 -a 0xf -e /apps/gulp -i " + self.params["if"] + " -f 'udp' -r " + self.params["buffer"]
        if self.params["verbose"] == 1:
            gulp_str = gulp_str + " -V xx"
        gulp_str = gulp_str + " -g " + direct
            
        print "BYU: " + gulp_str
        if self.simulate == False:
            self.gulp = subprocess.Popen( #Process could be added to config file
                gulp_str,
                shell=True,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                preexec_fn=os.setsid)
        
            while True:
                line = self.gulp.stderr.readline()
                print line
                if "Waiting for new file..." in line:
                    break
                
            self.gulp.stdin.write("null\n")
            self.gulp.stdin.flush()
            
            while True:
                line = self.gulp.stderr.readline()
                print line
                if "READY!" in line:
                    break
        time.sleep(0.5)
        
        
    def end_gulp(self):
        if self.simulate == False:
            os.killpg(self.gulp.pid, signal.SIGINT)
            time.sleep(0.1)
            os.killpg(self.gulp.pid, signal.SIGINT)
            while True:
                line = self.gulp.stderr.readline()
                #print "Gulp: " + line
                if "Exiting Writer thread" in line:
                    print "Gulp: Found end message"
                    break
            self.gulp.wait()
            time.sleep(30.0)
            try:
                self.gulp.kill()
            except OSError:
                print "BYU: Gulp has been shut down properly."
    
    
    def start_capture(self, bin_start, bin_end, row_start, row_end, col_start,
                      col_end, seconds, fft_length, fpga, sock):
        if self.gulp == None and self.simulate == False:
            print "BYU->Telescope: " + self.err_formats[self.cur_msg_name] % "Gulp is not running..."
            sock.sendall(self.err_formats[self.cur_msg_name] % "Gulp is not running...\n")
            return
        
        num_bins = bin_end - bin_start + 1
        num_cols = col_end - col_start + 1
        num_rows = row_end - row_start + 1
        
        sample_rate = 50e6
        bits_per_word = 64
        
        num_words = num_bins * (num_rows / 4) * num_cols + 1
        
        if num_words > 1024:
            print "BYU->Telescope: " + self.err_formats[self.cur_msg_name] % "Packet size may not exceed 1024 words."
            sock.sendall(self.err_formats[self.cur_msg_name] % "Packet size may not exceed 1024 words.\n")
            return
    
        num_packets = seconds*sample_rate/fft_length
	print "BYU: Number Packets = " + str(int(num_packets))
        bitrate = num_words * sample_rate * bits_per_word / fft_length
        
        print "BYU: Bitrate = " + str(bitrate)
        
        if self.simulate == False:
            fpga.write_int("num_packets", num_packets)
            fpga.write_int("input_time_start", col_start)
            fpga.write_int("input_time_end", col_end)
            fpga.write_int("input_line_start", row_start)
            fpga.write_int("input_line_end", row_end)
            fpga.write_int("freq_start", bin_start)
            fpga.write_int("freq_end", bin_end)
            fpga.write_int("lsb_select", self.lsb_select)
        
            fpga.write_int("ctrl", 16)
            fpga.write_int("ctrl", 48)
        
            timer = 0
            flag = 0
            while True:
                line = self.gulp.stderr.readline()
                if "Waiting for new file..." in line:
                    break
            while timer < seconds + 0.2:
                start = time.time()
                line = self.gulp.stderr.readline()
            
                if line.startswith("Time:"):
                    pairs = line.split(',')
                
                    k_drp = pairs[4]
                    i_drp = pairs[5]
                
                    k_pair = k_drp.split(':')
                    i_pair = i_drp.split(':')
                
                    k = int(k_pair[1].strip())
                    i = int(i_pair[1].strip())
    
                    if flag == 0:
                        if self.k < k:
                            flag = 1
                            self.k = k
                            print "Gulp: Found kernel drop"
                        elif self.i < i:
                            flag = 2
                            self.i = i
                            print "Gulp: Found interface drop"
                        else:
                            flag = 0
                    else:
                        if self.k < k:
                            self.k = k
                        elif self.i < i:
                            self.i = i
            
                print "Gulp: " + line.strip()
                end = time.time()
            
                timer = timer + end - start
            
            if flag != 0:
                if flag == 1:
                    print "Gulp: packets dropped in kernel"
                else:
                    print "Gulp: packets dropped in interface"
                return -1
        else:
            time.sleep(seconds)
        print "BYU: Capture Complete"
        
    
    def run_daq_spec(self, data, server, sock):
        ts = time.time()
        base_file_name = datetime.datetime.fromtimestamp(ts).strftime('%Y%m%d-%H%M%S') + "_spec_"
        for t in range(int(self.params["num_specs"])):
           file_name = base_file_name + str(t) + ".bin"
           self.run_daq_scan(data, server, sock, file_name)
    
    '''
    run_gbt_scan
    '''
    def run_gbt_scan(self, data, server, soc, file_name=None,
                     scan_file_name=None):
        ts = time.time()
        self.source_name = self.params["source_name"]
        self.scan_number = int(self.params["scan_number"])
        self.dmjd_start = self.params["dmjd_start"]
        out_dir = self.params["out_dir"]
        basetxt = datetime.datetime.fromtimestamp(ts).strftime('%Y%m%d-%H%M%S')
        if scan_file_name == None:
            scan_file_name = basetxt + "_%d.txt" % self.scan_number        
        fp = open(os.path.join(out_dir, scan_file_name), 'w')
        fp.write("%d\n" % self.scan_number)
        fp.write("%s\n" % self.source_name)
        fp.write("%s\n" % self.dmjd_start)
        if file_name == None:
            scan_file_name = basetxt + "_%d.bin" % self.scan_number

        r = -1;
        k = 1;
        while r == -1:
            print "BYU: Sending Gulp signal to start new file..."
            if self.simulate == False:
                os.killpg(self.gulp.pid, signal.SIGUSR1)
            time.sleep(0.1)
            print "BYU: Starting new file " + file_name
            if self.simulate == False:
                self.gulp.stdin.write(file_name + "\n")
                    
            r = self.start_capture(self.bin_start, self.bin_end,
                                   self.row_start, self.row_end,
                                   self.col_start, self.col_end,
                                   self.seconds, self.fft_length, self.fpga, sock)

            r = 1

        
    '''
    run_daq_scan
    '''
    def run_daq_scan(self, data, server, sock, file_name=None):
        ts = time.time()

        if file_name == None:
            file_name = datetime.datetime.fromtimestamp(ts).strftime('%Y%m%d-%H%M%S') + ".bin"
        self.bin_start = int(self.params["bin_start"])
        self.bin_end = int(self.params["bin_end"])
        self.row_start = int(self.params["row_start"])
        self.row_end = int(self.params["row_end"])
        self.col_start = int(self.params["col_start"])
        self.col_end = int(self.params["col_end"])
        self.seconds = float(self.params["num_secs"])
        self.lsb_select = int(self.params["lsb_select"])
        
        r = -1;
        k = 1;
        while r == -1:
            print "BYU: Sending Gulp signal to start new file..."
            if self.simulate == False:
                os.killpg(self.gulp.pid, signal.SIGUSR1)
            time.sleep(0.1)
            print "BYU: Starting new file " + file_name
            if self.simulate == False:
                self.gulp.stdin.write(file_name + "\n")
                    
            r = self.start_capture(self.bin_start, self.bin_end,
                                   self.row_start, self.row_end,
                                   self.col_start, self.col_end,
                                   self.seconds, self.fft_length, self.fpga, sock)
#            if r == -1:
#                print "REDO!!!!"
#                fpair = file_name.split('.')
#                cur_file = fpair[0] + "-redo" + str(k) + "." + fpair[1]
#                print "REDO FILE: " +  cur_file
#                k = k + 1
            r = 1
                               
        #sock.sendall("Finished!")
        
    '''
    run_daq_setup
    '''
    def run_daq_setup(self, data, server, sock):
        #for item in data:
        #    if item.startswith("TM_SECS"):
        #        pair = re.split("=",item)
        #        self.params["time"] = float(pair[1].strip())
        print "BYU: daq_setup command called"


    '''
    run_daq_end
    '''
    def run_daq_end(self, data, server, sock):
        #self.end_gulp()
        sock.sendall("Finished!\n")
       
    '''
    run_bf
    '''
    def run_bf(self, data, server, sock):
        sock.sendall("Running BF...\n")
        
    '''
    run_bfcoeff
    '''
    def run_bfcoeff(self, data, server, sock):
        sock.sendall("Running BF_Coeff...\n")
        
    '''
    run_x
    '''
    def run_x(self, data, server, sock):
        sock.sendall("Running Correlator...\n")
        
    '''
    run_spec
    '''
    def run_spec(self, data, server, sock):
        sock.sendall("Running Spectrometer...\n")
        

