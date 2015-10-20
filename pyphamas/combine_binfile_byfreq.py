"""
Given a list of files and ranges of frequency bins
these functions will combine the files and produce
a single auto-correlation dataset or single
cross-correlation dataset
"""
from binfile_parser import BinFile
import numpy

def combine_binfile_autocorr_byfreq(bflist, number_packets=3000):
    """
    bflist is a list of filenames. Please be sure to order the files in 
    ascending order of frequency coverage For eg:
    ['20151013-074846.bin', '20151013-074847.bin']
    """
    for i, filename in enumerate(bflist):
        print "Processing %s" % filename
        bf = BinFile(filename, number_packets=number_packets)
        bf.get_spec_data()
        if i == 0:
            ac = bf.data_out
        else:
            ac = numpy.append(ac, bf.data_out, axis=2)
    return ac

def combine_binfile_autocorr_accum_byfreq(bflist, number_packets=3000):
    """
    bflist is a list of filenames. Please be sure to order the files in 
    ascending order of frequency coverage For eg:
    ['20151013-074846.bin', '20151013-074847.bin']
    """
    for i, filename in enumerate(bflist):
        print "Processing %s" % filename
        bf = BinFile(filename, number_packets=number_packets)
        bf.get_accum_spec_data()
        if i == 0:
            ac = bf.data_accum
        else:
            ac = numpy.append(ac, bf.data_accum, axis=2)
    return ac

def combine_binfile_crosscorr_byfreq(bflist, number_packets=3000):
    """
    bflist is a list of filenames. Please be sure to order the files in 
    ascending order of frequency coverage For eg:
    ['20151013-074846.bin', '20151013-074847.bin']
    """
    for i, filename in enumerate(bflist):
        print "Processing %s" % filename
        bf = BinFile(filename, number_packets=number_packets)
        bf.get_cross_corr_data_fast()
        if i == 0:
            cc = bf.cross_corr
        else:
            cc = numpy.append(cc, bf.cross_corr, axis=2)
    return cc

def delete_rows_cols_from_crosscorr(arr, lis):
    """
    Given a cross_corr array of 3 dimensions (rows, columns, bins)
    removes rows and columns corresponding to dead pixels or unconnected 
    pixels.
    lis is index of rows and columns to delete
    """
    cc = arr.copy()
    cc = numpy.delete(cc, tuple(lis), axis=0)
    cc = numpy.delete(cc, tuple(lis), axis=1)
    return cc


      
