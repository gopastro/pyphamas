"""
A parser class to read GULP bin files
from the x64 BYU ROACH system
Based on the MATLAB program fast_x64_parse.m
"""

import struct
import os
import numpy
import time
from xml.etree.ElementTree import parse
from pyphamas.utils import sti_correlate
import pickle

UDP_HEADER_LENGTH = 66
GULP_HEADER_LENGTH = 24
DAQ_HEADER_LENGTH = 8

# Element Matrix
# table = [...
#      0,  8,  2, 10,  4, 12,  6, 14;...
#      1,  9,  3, 11,  5, 13,  7, 15;...
#     16, 24, 18, 26, 20, 28, 22, 30;...
#     17, 25, 19, 27, 21, 29, 23, 31;...
#     32, 40, 34, 42, 36, 44, 38, 46;...
#     33, 41, 35, 43, 37, 45, 39, 47;...
#     48, 56, 50, 58, 52, 60, 54, 62;...
#     49, 57, 51, 59, 53, 61, 55, 63] + 1;

map_pixel_spec = {
    '2,1' : 0,
    '2,2' : 1,
    '2,3' : 2,
    '2,4' : 3,
    '2,5' : 4,
    '2,6' : 5,
    '2,7' : 6,
    '2,8' : 7,
    '3,1' : 8,
    '3,2' : 9,
    '3,3' : 10,
    '3,4' : 11,
    '3,5' : 12,
    '3,7' : 13, 
    '3,8' : 14,
    '4,1' : 15,
    '4,2' : 16,
    '4,3' : 17,
    '4,4' : 18,
    '4,5' : 19,
    '4,6' : 20,
    '4,7' : 21,
    '5,3' : 22, 
    '5,7' : 23,
    '5,8' : 24,
    '6,2' : 25,
    '6,4' : 26,
    '6,5' : 27,
    '6,6' : 28,
    '6,7' : 29,
    '6,8' : 30,
    '7,1' : 31,
    '7,2' : 32,
    '7,3' : 33, 
    '7,4' : 34,
    '7,5' : 35,
    '7,7' : 36,
    '7,8' : 37
    }

map_spec_pixel = dict((v, k) for k, v in map_pixel_spec.iteritems())

def get_rowcol_for_cable(cable):
    if cable % 8 == 0:
        col = 7
        row = (cable/8) - 1
    else:
        row = cable/8
        col = cable%8 - 1
    return col, row

def rebin(specin, outsize=2048):
    """Very simple boxcar average of input spectra or timestream"""
    f = len(specin)/outsize
    return numpy.array([specin[f*i:f*i+f].mean() for i in range(outsize)])


class BinFile(object):
    def __init__(self, filename, number_packets=None,
                 packets_to_skip=None,
                 number_bins=None):
        self.filename = filename
        self.number_packets = number_packets
        self.packets_to_skip = packets_to_skip
        self.number_bins = number_bins
        if not os.path.exists(self.filename):
            raise Exception("File %s does not exist" % self.filename)
        self.basename, _ = os.path.splitext(os.path.basename(self.filename))
        stat = os.stat(self.filename)
        self.file_length = stat.st_size
        self.fp = open(self.filename, 'rb')
        print "Filename %s with size %.3f MB opened" % (self.filename, float(self.file_length)/(1024.*1024))
        self.get_param_data(verbose=True)
        self.adc_list = numpy.reshape(numpy.array([1, 2, 17, 18, 33, 34, 49, 50,
                                                   9, 10, 25, 26, 41, 42, 57, 58,
                                                   3, 4, 19, 20, 35, 36, 51, 52,
                                                   11, 12, 27, 28, 43, 44, 59, 60,
                                                   5, 6, 21, 22, 37, 38, 53, 54, 
                                                   13, 14, 29, 30, 45, 46, 61, 62,
                                                   7, 8, 23, 24, 39, 40, 55, 56,
                                                   15, 16, 31, 32, 47, 48, 63, 64]), 
                                      (8, 8),
                                      order='F')
        self.bad_inputs = [14, 15, 20, 21, 31, 38, 44, 45, 46, 47]
        self.bad_inputs = numpy.array(self.bad_inputs)
        self.map_pixel_spec = map_pixel_spec
        self.map_spec_pixel = map_spec_pixel

    def get_param_data(self, verbose=False):
        self.fp.seek(0)
        gulp_bytes = struct.unpack('4B', self.fp.read(4))
        # Check to see if the Gulp header (d4 c3 b2 a1) is present
        if gulp_bytes[0] != 0xd4 or gulp_bytes[1] != 0xc3 or gulp_bytes[2] != 0xb2 or gulp_bytes[3] != 0xa1:
            if verbose:
                print "No GULP Bytes found"
            GULP_HEADER_LENGTH = 0
        
        self.fp.seek(0)

        header_start = GULP_HEADER_LENGTH + UDP_HEADER_LENGTH
        header_end = header_start + DAQ_HEADER_LENGTH 
    
        header = self.fp.read(header_end)
        if len(header) != header_end:
            raise Exception("Did not read correct number of bytes: %s" % header_end)
        header = struct.unpack("%dB" % len(header), header)
        # Extract first packet's header information
        # i.e. rows, cols, bins, etc.
    
        # Extract the DAQ header (8 bytes)
        custom_header = numpy.array(header[header_start:header_start+DAQ_HEADER_LENGTH], 
                                    dtype='int32')
        self.bin_start = ((custom_header[0]<<8) + custom_header[1])>>6
        self.bin_end = (((custom_header[1]<<8) + custom_header[2])<<2)>>6
        self.row_start = (custom_header[2]<<4)>>5
        self.row_flag = custom_header[2]
        self.col_start = custom_header[3]>>5
        self.col_end = custom_header[3]>>2
        self.fft_length = custom_header[3]

        ten_mask = 2**9 + 2**8 + 2**7 + 2**6 + 2**5 + 2**4 + 2**3 + 2**2 + 2 + 1
        three_mask = 2**2 + 2 + 1
        two_mask = 2 + 1
        one_mask = 1

        self.bin_start = self.bin_start & ten_mask

        self.bin_end = self.bin_end & ten_mask
        self.row_start = self.row_start & three_mask
        self.row_flag = self.row_flag & one_mask
        self.row_end = self.row_start + 4*(self.row_flag + 1) - 1
        self.col_start = self.col_start & three_mask
        self.col_end = self.col_end & three_mask
        self.fft_length = 2**((self.fft_length & two_mask) + 8)
        
        self.num_bins = self.bin_end - self.bin_start + 1
        self.num_rows = self.row_end - self.row_start + 1
        self.num_cols = self.col_end - self.col_start + 1

        self.params_dic = {'bin_start': self.bin_start,
                           'bin_end': self.bin_end,
                           'row_start': self.row_start,
                           'row_end': self.row_end,
                           'col_start': self.col_start,
                           'col_end': self.col_end,
                           'fft_length': self.fft_length}
        # Calculate data packet length
        self.packet_length = self.num_rows * self.num_bins * self.num_cols * 8/4
        
        # Calculate distance between packets
        self.dist_between = self.packet_length + UDP_HEADER_LENGTH + DAQ_HEADER_LENGTH
    
        # Calculate the number of packets
        self.total_packets = (self.file_length - GULP_HEADER_LENGTH)/self.dist_between
        self.total_seconds = self.total_packets * 512./50.e6
        if verbose:
            print "Number of total packets available: %d (%g seconds)" % (self.total_packets, self.total_seconds)

        # Create element/bin packet table
        self.I = numpy.zeros((self.num_rows*self.num_cols, self.num_bins), 
                             dtype='int')
        for e in range(0, self.num_rows*self.num_cols, 4):
            self.I[e+3, :] = numpy.arange(0, 4*self.num_bins, 4) + self.num_bins*e
            self.I[e+2, :] = numpy.arange(1, 4*self.num_bins, 4) + self.num_bins*e
            self.I[e+1, :] = numpy.arange(2, 4*self.num_bins, 4) + self.num_bins*e
            self.I[e, :] = numpy.arange(3, 4*self.num_bins+1, 4) + self.num_bins*e

    def get_spec_data(self, packets_to_skip=None,
                      number_packets=None,
                      number_bins=None):
        t1 = time.time()
        self.get_param_data()  # always get to point after header in file
        self.packets_to_skip = packets_to_skip or self.packets_to_skip
        self.number_packets = number_packets or self.number_packets
        self.number_bins = number_bins or self.number_bins
        
        if self.number_bins is not None and self.number_bins < self.num_bins:
            self.num_bins = self.number_bins
        
        packets_to_skip = 0
        if self.packets_to_skip is not None:
            packets_to_skip = self.packets_to_skip - 1
            
        # Determine the number of bytes to skip
        bytes_to_skip = self.dist_between * packets_to_skip;
    
        # Fast-forward through file to new start location
        self.fp.seek(bytes_to_skip, 1)
        
        # Check to see if user wants a shorter integration time (fewer packets)
        if self.number_packets is None:
            number_packets = self.total_packets - packets_to_skip
        else:
            # Make sure not to parse more packets than are available
            if self.number_packets > self.total_packets - packets_to_skip:
                number_packets = self.total_packets - packets_to_skip;
            else:
                number_packets = self.number_packets

        # Create placeholder for 4D matrix
        # corr_matrix = zeros(num_rows*num_cols, num_rows*num_cols, num_bins);
        self.data_out = numpy.zeros((self.num_rows, self.num_cols, self.num_bins, 
                                     number_packets), dtype='complex')
        
        # Calculate number of bytes to read from the rest of the file
        bytes_to_read = (self.dist_between * number_packets) - (UDP_HEADER_LENGTH + DAQ_HEADER_LENGTH)
        
        # Read in the rest of the packet
        buff = numpy.array(struct.unpack("%db" % bytes_to_read, 
                                         self.fp.read(bytes_to_read)))
        
        first_start = 0
        for i in range(number_packets):
            #Get starting byte of packet
            packet_start = i * self.dist_between + first_start
        
            # Convert to complex values
            complexes = buff[packet_start:packet_start + self.packet_length:2] + \
                1j*buff[packet_start+1:packet_start + self.packet_length:2]
            #if i == 0:
            #    print complexes.shape
            #    print complexes

            self.data_out[:, :, :, i] = numpy.reshape(complexes[self.I],
                                                      (self.num_rows, self.num_cols,
                                                       self.num_bins),
                                                      order='F')
            #for b in range(self.num_bins):
            #    self.data_out[:,:,b,i] = numpy.reshape(complexes[self.I[:,b]], 
            #                                           (self.num_rows, self.num_cols),
            #order='F')
        t2 = time.time()
        print "Done with get_spec_data in %.2f seconds" % (t2-t1)


    def get_accum_spec_data(self, packets_to_skip=None,
                            number_packets=None,
                            number_bins=None):
        t1 = time.time()
        self.get_param_data()  # always get to point after header in file
        self.packets_to_skip = packets_to_skip or self.packets_to_skip
        self.number_packets = number_packets or self.number_packets
        self.number_bins = number_bins or self.number_bins
        
        if self.number_bins is not None and self.number_bins < self.num_bins:
            self.num_bins = self.number_bins
        
        packets_to_skip = 0
        if self.packets_to_skip is not None:
            packets_to_skip = self.packets_to_skip - 1
            
        # Determine the number of bytes to skip
        bytes_to_skip = self.dist_between * packets_to_skip;
    
        # Fast-forward through file to new start location
        self.fp.seek(bytes_to_skip, 1)
        
        # Check to see if user wants a shorter integration time (fewer packets)
        if self.number_packets is None:
            number_packets = self.total_packets - packets_to_skip
        else:
            # Make sure not to parse more packets than are available
            if self.number_packets > self.total_packets - packets_to_skip:
                number_packets = self.total_packets - packets_to_skip;
            else:
                number_packets = self.number_packets

        # Create placeholder for 3D matrix
        # corr_matrix = zeros(num_rows*num_cols, num_rows*num_cols, num_bins);
        # data accum is sum of absolute values
        self.data_accum = numpy.zeros((self.num_rows, self.num_cols, 
                                       self.num_bins),
                                      dtype='complex')
        
        # Calculate number of bytes to read from the rest of the file
        bytes_to_read = (self.dist_between * number_packets) - (UDP_HEADER_LENGTH + DAQ_HEADER_LENGTH)
        
        # Read in the rest of the packet
        buff = numpy.array(struct.unpack("%db" % bytes_to_read, 
                                         self.fp.read(bytes_to_read)))
        
        first_start = 0
        for i in range(number_packets):
            #Get starting byte of packet
            packet_start = i * self.dist_between + first_start
        
            # Convert to complex values
            complexes = buff[packet_start:packet_start + self.packet_length:2] + \
                1j*buff[packet_start+1:packet_start + self.packet_length:2]
            
            if i == 0:
                print complexes[self.I].shape
            self.data_accum += numpy.abs(numpy.reshape(complexes[self.I], 
                                             (self.num_rows, self.num_cols, self.num_bins),
                                             order='F')
                                         )**2
            #if i == 0:
            #    print complexes.shape
            #    print complexes

            #for b in range(self.num_bins):
            #    self.data_out[:,:,b,i] = numpy.reshape(complexes[self.I[:,b]], 
            #                                           (self.num_rows, self.num_cols))
        self.data_accum = self.data_accum/float(number_packets)
        t2 = time.time()
        print "Done with get_spec_data in %.2f seconds" % (t2-t1)

    def get_cross_corr_data(self, packets_to_skip=None,
                            number_packets=None,
                            number_bins=None,
                            bin_start=None,
                            bin_end=None):
        t1 = time.time()
        self.get_param_data()  # always get to point after header in file
        self.packets_to_skip = packets_to_skip or self.packets_to_skip
        self.number_packets = number_packets or self.number_packets
        self.number_bins = number_bins or self.number_bins
        
        if self.number_bins is not None and self.number_bins < self.num_bins:
            self.num_bins = self.number_bins
        
        packets_to_skip = 0
        if self.packets_to_skip is not None:
            packets_to_skip = self.packets_to_skip - 1
            
        # Determine the number of bytes to skip
        bytes_to_skip = self.dist_between * packets_to_skip;
    
        # Fast-forward through file to new start location
        self.fp.seek(bytes_to_skip, 1)
        
        # Check to see if user wants a shorter integration time (fewer packets)
        if self.number_packets is None:
            number_packets = self.total_packets - packets_to_skip
        else:
            # Make sure not to parse more packets than are available
            if self.number_packets > self.total_packets - packets_to_skip:
                number_packets = self.total_packets - packets_to_skip;
            else:
                number_packets = self.number_packets

        # Create placeholder for 4D matrix
        # corr_matrix = zeros(num_rows*num_cols, num_rows*num_cols, num_bins);
        num_horns = self.num_rows * self.num_cols
        self.cross_corr = numpy.zeros((num_horns,
                                       num_horns,
                                       self.num_bins), 
                                      dtype='complex')
        mean_data = numpy.zeros((num_horns, self.num_bins), dtype='complex')
        print mean_data.shape
        # Calculate number of bytes to read from the rest of the file
        bytes_to_read = (self.dist_between * number_packets) - (UDP_HEADER_LENGTH + DAQ_HEADER_LENGTH)
        
        # Read in the rest of the packet
        buff = numpy.array(struct.unpack("%db" % bytes_to_read, 
                                         self.fp.read(bytes_to_read)))
        
        first_start = 0
        for i in range(number_packets):
            #Get starting byte of packet
            packet_start = i * self.dist_between + first_start
        
            # Convert to complex values
            complexes = buff[packet_start:packet_start + self.packet_length:2] + \
                1j*buff[packet_start+1:packet_start + self.packet_length:2]
            if i == 0:
                print complexes.shape
            #    print complexes

            for b in range(self.num_bins):
                self.cross_corr[:, :, b] += numpy.reshape(complexes[self.I[:,b]], (num_horns, 1))  * numpy.reshape((complexes[self.I[:, b]]).conj(), (1, num_horns))
                mean_data[:, b] += complexes[self.I[:, b]]
        print mean_data.shape
        #self.cross_corr = self.cross_corr/(number_packets-1) - ((number_packets/(number_packets-1)) * (numpy.reshape(mean_data, (num_horns, 1, self.num_bins)) * numpy.reshape(mean_data.conj(), (1, num_horns, self.num_bins)) ))
        #for b in range(self.num_bins):
        #    self.cross_corr[:, :, b] = self.cross_corr[:, :, b]/(number_packets-1) - \
        #        ((number_packets/(number_packets-1)) * (numpy.reshape(mean_data[:, b], (num_horns, 1)) * numpy.reshape((mean_data[:, b]).conj(), (1, num_horns)) ))
        self.cross_corr = self.cross_corr/(number_packets-1)
        t2 = time.time()
        print "Done with get_cross_corr_data in %.2f seconds" % (t2-t1)

    def get_cross_corr_data_fast(self, packets_to_skip=None,
                                 number_packets=None,
                                 number_bins=None,
                                 bin_start=None,
                                 bin_end=None):
        t1 = time.time()
        self.get_param_data()  # always get to point after header in file
        self.packets_to_skip = packets_to_skip or self.packets_to_skip
        self.number_packets = number_packets or self.number_packets
        self.number_bins = number_bins or self.number_bins
        
        if self.number_bins is not None and self.number_bins < self.num_bins:
            self.num_bins = self.number_bins
        
        packets_to_skip = 0
        if self.packets_to_skip is not None:
            packets_to_skip = self.packets_to_skip - 1
            
        # Determine the number of bytes to skip
        bytes_to_skip = self.dist_between * packets_to_skip;
    
        # Fast-forward through file to new start location
        self.fp.seek(bytes_to_skip, 1)
        
        # Check to see if user wants a shorter integration time (fewer packets)
        if self.number_packets is None:
            number_packets = self.total_packets - packets_to_skip
        else:
            # Make sure not to parse more packets than are available
            if self.number_packets > self.total_packets - packets_to_skip:
                number_packets = self.total_packets - packets_to_skip;
            else:
                number_packets = self.number_packets

        # Create placeholder for 4D matrix
        # corr_matrix = zeros(num_rows*num_cols, num_rows*num_cols, num_bins);
        num_horns = self.num_rows * self.num_cols
        self.cross_corr = numpy.zeros((num_horns,
                                       num_horns,
                                       self.num_bins), 
                                      dtype='complex')
        mean_data = numpy.zeros((num_horns, self.num_bins), dtype='complex')
        # Calculate number of bytes to read from the rest of the file
        bytes_to_read = (self.dist_between * number_packets) - (UDP_HEADER_LENGTH + DAQ_HEADER_LENGTH)
        
        # Read in the rest of the packet
        buff = numpy.array(struct.unpack("%db" % bytes_to_read, 
                                         self.fp.read(bytes_to_read)))
        
        first_start = 0
        for i in range(number_packets):
            #Get starting byte of packet
            packet_start = i * self.dist_between + first_start
        
            # Convert to complex values
            complexes = buff[packet_start:packet_start + self.packet_length:2] + \
                1j*buff[packet_start+1:packet_start + self.packet_length:2]
            comp = complexes[self.I]
            self.cross_corr += numpy.reshape(comp, (num_horns, 1, self.num_bins), order='F') * \
                numpy.reshape(comp.conj(), (1, num_horns, self.num_bins), order='F')
            mean_data += comp
        mean_data = mean_data/float(number_packets)
        self.cross_corr = self.cross_corr/(number_packets-1) - ((float(number_packets)/float(number_packets-1.)) * numpy.reshape(mean_data, (num_horns, 1, self.num_bins)) * numpy.reshape(mean_data.conj(), (1, num_horns, self.num_bins)) )
        t2 = time.time()
        print "Done with get_cross_corr_data in %.2f seconds" % (t2-t1)
                
        
    def get_spec_data_new(self, packets_to_skip=None,
                          number_packets=None,
                          number_bins=None):
        """
        Gives results compressed into number_horns
        """
        t1 = time.time()
        self.get_param_data()  # always get to point after header in file
        self.packets_to_skip = packets_to_skip or self.packets_to_skip
        self.number_packets = number_packets or self.number_packets
        self.number_bins = number_bins or self.number_bins
        
        if self.number_bins is not None and self.number_bins < self.num_bins:
            self.num_bins = self.number_bins
        
        packets_to_skip = 0
        if self.packets_to_skip is not None:
            packets_to_skip = self.packets_to_skip - 1
            
        # Determine the number of bytes to skip
        bytes_to_skip = self.dist_between * packets_to_skip;
    
        # Fast-forward through file to new start location
        self.fp.seek(bytes_to_skip, 1)
        
        # Check to see if user wants a shorter integration time (fewer packets)
        if self.number_packets is None:
            number_packets = self.total_packets - packets_to_skip
        else:
            # Make sure not to parse more packets than are available
            if self.number_packets > self.total_packets - packets_to_skip:
                number_packets = self.total_packets - packets_to_skip;
            else:
                number_packets = self.number_packets

        num_horns = self.num_rows * self.num_cols
        # Create placeholder for 3D matrix
        # corr_matrix = zeros(num_rows*num_cols, num_rows*num_cols, num_bins);
        self.data_out = numpy.zeros((num_horns, self.num_bins, 
                                     number_packets), dtype='complex')
        
        # Calculate number of bytes to read from the rest of the file
        bytes_to_read = (self.dist_between * number_packets) - (UDP_HEADER_LENGTH + DAQ_HEADER_LENGTH)
        
        # Read in the rest of the packet
        buff = numpy.array(struct.unpack("%db" % bytes_to_read, 
                                         self.fp.read(bytes_to_read)))
        
        first_start = 0
        for i in range(number_packets):
            #Get starting byte of packet
            packet_start = i * self.dist_between + first_start
        
            # Convert to complex values
            complexes = buff[packet_start:packet_start + self.packet_length:2] + \
                1j*buff[packet_start+1:packet_start + self.packet_length:2]
            #if i == 0:
            #    print complexes.shape
            #    print complexes
            self.data_out[:, :, i] = complexes[self.I]
            #for b in range(self.num_bins):
            #    self.data_out[:,:,b,i] = numpy.reshape(complexes[self.I[:,b]], 
            #                                           (self.num_rows, self.num_cols))
        t2 = time.time()
        print "Done with get_spec_data in %.2f seconds" % (t2-t1)


    def read_xml_config(self, configfile):
        """
        Reads the XML configuration file used in data taking
        and reads the configuration object. Reads the configuration
        tag and reads the text in there and assigns actual receiver 
        elements to rows and columns from binary file
        This one is for the 6 column newer format configuration options
        """
        if not os.path.exists(configfile):
            raise Exception("Config file %s does not exist" % configfile)
        tree = parse(configfile)
        elem = tree.getroot()
        cfg = elem.find("configuration")
        txt = cfg.text
        rows = txt.split('\n\t')
        self.pixeldic = {} # for a given frontend pixel has
                           # tuple of row, col of bf 
        self.fiberdic = {} # for a given frontend pixel has
                           # fiber receiver used
        self.rxcarddic = {} # for a given frontend pixel has
                            # mapping to rxdownconverter card used
        self.cable_adc_dic = {} # for a given IF cable number 
                                # what is the ADC it is attached to
        for row in rows[2:-1]:
            args = row.split()
            adc = int(args[0])
            try:
                cable = int(args[1])
            except ValueError:
                cable = -1
            pixel = args[2].strip()
            fibercable = args[3].strip()
            rxcard = args[4].strip()
            print "ADC: %d, cable: %d, pixel: %s" % (adc, cable, pixel)
            if cable != -1:
                self.cable_adc_dic[cable] = adc
            if pixel != 'NC':
                self.pixeldic[pixel] = self.get_rowcol_for_adc(self.cable_adc_dic[cable])
                self.fiberdic[pixel] = fibercable
                self.rxcarddic[pixel] = rxcard
        self.pixel_label = dict((v, k) for k, v in self.pixeldic.iteritems())

    def get_rowcol_for_adc(self, adc):
        indices = numpy.where(self.adc_list == adc)
        return indices[0][0], indices[1][0]

    def read_xml_config_old(self, configfile):
        """
        Reads the XML configuration file used in data taking
        and reads the configuration object. Reads the configuration
        tag and reads the text in there and assigns actual receiver 
        elements to rows and columns from binary file
        This one is for the old 3 column configuration we used to have
        """
        if not os.path.exists(configfile):
            raise Exception("Config file %s does not exist" % configfile)
        tree = parse(configfile)
        elem = tree.getroot()
        cfg = elem.find("configuration")
        txt = cfg.text
        rows = txt.split('\n\t')
        self.pixeldic = {} # for a given frontend pixel has
                           # tuple of row, col of bf 
        for row in rows[2:-1]:
            args = row.split('\t')
            adc = int(args[1])
            cable = int(args[2])
            pixel = args[3].strip()
            print "ADC: %d, cable: %d, pixel: %s" % (adc, cable, pixel)
            if pixel != 'NC':
                self.pixeldic[pixel] = get_rowcol_for_cable(cable)
        self.pixel_label = dict((v, k) for k, v in self.pixeldic.iteritems())

    def sti_cross_correlate(self, total_time,
                            sti_time):
        t1 = time.time()
        self.sti_cc = sti_correlate(self.filename, total_time, 
                                    sti_time)
        self.sti_totpower = numpy.zeros((self.num_rows*self.num_cols, self.sti_cc.shape[2],
                                         self.sti_cc.shape[3]), dtype='complex')
        for i in range(self.num_rows*self.num_cols):
            self.sti_totpower[i, :, :] = self.sti_cc[i, i, :, :]
        self.sti_totpower = numpy.reshape(self.sti_totpower, 
                                          (self.num_rows, self.num_cols, 
                                           self.sti_cc.shape[2],
                                           self.sti_cc.shape[3]),
                                          order='F')
        t2 = time.time()
        print "Done with sti_cross_correlate in %.2f seconds" % (t2-t1)

    def save_par(self):
        t1 = time.time()
        basedir, fname = os.path.split(self.filename)
        newdir = os.path.join(basedir, 'cross')
        if not os.path.exists(newdir):
            os.makedirs(newdir)
        par_file = os.path.join(newdir, fname + '.par')
        pickle.dump(self.__dict__, open(par_file, 'w'), protocol=2)
        print "Done writing parameter file %s in %.2f seconds" % (par_file, time.time()-t1)
    def load_par(self):
        t1 = time.time()
        basedir, fname = os.path.split(self.filename)
        newdir = os.path.join(basedir, 'cross')
        par_file = os.path.join(newdir, fname + '.par')
        if not os.path.exists(par_file):
            if fname.rfind('_corr') != -1:
                fname = fname.replace('_corr', '')
                par_file = os.path.join(newdir, fname + '.par')
                if not os.path.exists(par_file):
                    raise Exception("No stored pickle parameter file %s" % par_file)
            else:
                raise Exception("No stored pickle parameter file %s" % par_file)
        par = pickle.load(open(par_file, 'r'))
        for k, v in par.items():
            if k not in ('fp', 'filename'):
                setattr(self, k, v)

        print "Done loading parameter file %s in %.2f seconds" % (par_file, time.time()-t1)           

        
    def save_sti_dumps(self):
        """
        Changed back to pickle protocol 2
        """
        if not hasattr(self, 'sti_cc'):
            raise Exception("First run sti_cross_correlate before saving dump file")
        t1 = time.time()
        basedir, fname = os.path.split(self.filename)
        newdir = os.path.join(basedir, 'cross')
        if not os.path.exists(newdir):
            os.makedirs(newdir)
        bfile, _ = os.path.splitext(fname)
        cc_pklfile = os.path.join(newdir, bfile + '_cross.pkl')
        tp_pklfile = os.path.join(newdir, bfile + '_totpower.pkl')
        pickle.dump(self.sti_cc, open(cc_pklfile, 'w'), protocol=2)
        t2 = time.time()
        print "Done writing cross_corr dump file %s in %.2f seconds" % (cc_pklfile, t2-t1)
        pickle.dump(self.sti_totpower, open(tp_pklfile, 'w'), protocol=2)
        t3 = time.time()
        print "Done writing total power dump file %s in %.2f seconds" % (tp_pklfile, t3-t2)

    def load_sti_dumps(self):
        if hasattr(self, 'sti_cc'):
            print "Already has sti_cc and sti_totpower"
            return
        t1 = time.time()
        basedir, fname = os.path.split(self.filename)
        newdir = os.path.join(basedir, 'cross')
        if not os.path.exists(newdir):
            raise Exception("Does not contain dir %s" % newdir)
        bfile, _ = os.path.splitext(fname)
        if bfile.rfind('_corr') != -1:
            bfile, _ = bfile.split('_corr')
        cc_pklfile = os.path.join(newdir, bfile + '_cross.pkl')
        tp_pklfile = os.path.join(newdir, bfile + '_totpower.pkl')
        if not os.path.exists(cc_pklfile):
            raise Exception("No stored pickle file %s" % cc_pklfile)
        self.sti_cc = pickle.load(open(cc_pklfile, 'r'))
        t2 = time.time()
        print "Done loading sti_cc from %s in %.2f seconds" % (cc_pklfile, t2-t1)
        if not os.path.exists(tp_pklfile):
            raise Exception("No stored pickle file %s" % tp_pklfile)
        self.sti_totpower = pickle.load(open(tp_pklfile, 'r'))
        t3 = time.time()
        print "Done loading sti_totpower from %s in %.2f seconds" % (tp_pklfile, t3-t2)

    def load_sti_cross_correlate(self, total_time,
                                 sti_time):
        """
        This method looks for an already existing cross-correlation
        data set in the cross directory. If available, just load 
        it. Else perform the cross correlate and save the pickle dumps
        """
        if hasattr(self, 'sti_cc'):
            print "Already has sti_cc and sti_totpower"
            return
        t1 = time.time()
        basedir, fname = os.path.split(self.filename)
        newdir = os.path.join(basedir, 'cross')
        if not os.path.exists(newdir):
            raise Exception("Does not contain dir %s" % newdir)
        bfile, _ = os.path.splitext(fname)
        cc_pklfile = os.path.join(newdir, bfile + '_cross.pkl')
        tp_pklfile = os.path.join(newdir, bfile + '_totpower.pkl')
        if not os.path.exists(cc_pklfile):
            print "No stored pickle file %s" % cc_pklfile
            print "Will perform sti cross_correlate"
            self.sti_cross_correlate(self, total_time,
                                     sti_time)
            self.save_sti_dumps()
        else:
            print "Stored pickle file %s found" % cc_pklfile
            self.load_sti_dumps()
        
    def make_factors(self, c_y=[-0.0056, -2.6627],
                     c_z=[0.1417, 1.0651]):
        """
        you can pass fits to c_y and c_z
        """
        b = numpy.arange(1, 64)
        #c_y = [-0.0056, -2.6627]
        #c_z = [0.1417, 1.0651]
        self.factors = numpy.zeros((38, 63), dtype='float')
        self.factors[:12, :] = 1
        self.factors[12:24, :] = numpy.dot(numpy.ones((12, 1)), 
                                      numpy.reshape((c_y[0]*b+c_y[1]), (1, 63)))
        self.factors[24:, :] = numpy.dot(numpy.ones((14, 1)), 
                                    numpy.reshape((c_z[0]*b+c_z[1]), (1, 63)))
        return self.factors

    def remove_bad_inputs(self):
        if not hasattr(self, 'sti_cc'):
            print "Does not have sti_cc and sti_totpower"
            return        
        self.sti_cc = numpy.delete(self.sti_cc, self.bad_inputs, axis=0)
        self.sti_cc = numpy.delete(self.sti_cc, self.bad_inputs, axis=1)
        
    def correct_phase_dispersion(self, c_y=[-0.0056, -2.6627],
                                 c_z=[0.1417, 1.0651]):
        if not hasattr(self, 'factors'):
            factors = self.make_factors(c_y=c_y, c_z=c_z)
        if self.sti_cc.shape[0] == 48:
            self.remove_bad_inputs() # reduce from 48 to 38 elements
        nbins = self.sti_cc.shape[2]
        sti_cc = self.sti_cc
        ntimes = self.sti_cc.shape[3]
        corr = numpy.zeros((38, 38, nbins, ntimes), dtype='complex')
        corr_unnorm = numpy.zeros((38, 38, nbins, ntimes), dtype='complex')
        #for n in range(ntimes):
        for t in range(ntimes):
            for b in range(nbins):
                B = numpy.diag(numpy.exp(1j*self.factors[:, b]))
                A = numpy.diag(1./numpy.sqrt(numpy.diag(reduce(numpy.dot, [B, sti_cc[:, :, b, t], B.conj().transpose()]) ) )) # for normalization
                corr[:, :, b, t] = reduce(numpy.dot, [A, B, sti_cc[:, :, b, t], B.conj().transpose(), A])
                #uncorr[:, :, b] = reduce(numpy.dot, [A, newcc[:, :, b], A])
                corr_unnorm[:, :, b, t] = reduce(numpy.dot, [B, sti_cc[:, :, b, t], B.conj().transpose()])
        #self.sti_cc = corr.copy()
        self.sti_cc_corrected = corr
        self.sti_totpower_corrected = numpy.zeros((38, nbins, ntimes), dtype='complex')
        for i in range(38):
            self.sti_totpower_corrected[i, :, :] = corr_unnorm[i, i, :, :]
        return corr_unnorm
