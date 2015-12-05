import subprocess
import struct
import numpy
import os
import multiprocessing

def correlate(filename, output_filename, 
              seconds_to_skip=None,
              number_seconds=None,
              index=0,
              remove_out=True):
    if seconds_to_skip is None:
        c_correlate_str = "correlate %s %s" % (filename, output_filename)
    else:
        if number_seconds is None:
            c_correlate_str = "correlate %s %s %f" % (filename, output_filename, seconds_to_skip)
        else:
            c_correlate_str = "correlate %s %s %f %f" % (filename, output_filename, seconds_to_skip, number_seconds)
    cmd = subprocess.Popen(
        c_correlate_str,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE
        )
    cmd.wait()
    stdout_value = cmd.communicate()[0]
    print '\tstdout:', repr(stdout_value)
    fp = open(output_filename, 'rb')
    params = struct.unpack('7i', fp.read(7*4))
    bin_start, bin_end, row_start, row_end, col_start, col_end, fft_length = params
    nrows = row_end - row_start + 1
    ncols = col_end - col_start + 1
    nele = nrows * ncols
    nbins = bin_end - bin_start + 1
    
    data = numpy.array(struct.unpack("%df" % (nele*nele*nbins*2),
                                     fp.read(nele*nele*nbins*2*4)))
    fp.close()
    data = data[0::2] + 1j*data[1::2]
    data = numpy.transpose(numpy.reshape(data, (nbins, nele, nele)),
                           (2, 1, 0))
    corr = numpy.zeros((nele, nele, nbins), dtype='complex')
    for i in range(nbins):
        corr[:, :, i] = data[:, :, i] + data[:, :, i].conj().transpose() + \
            numpy.diag(numpy.diag(data[:, :, i]))
    if remove_out:
        print "Removing output file %s" % output_filename
        os.remove(output_filename)
    return index, corr

def sti_correlate(filename, total_time=None,
                  sti_time=0.1):
    from pyphamas import BinFile
    bf = BinFile(filename, number_packets=2000)
    if total_time is None:
        total_time = float(bf.total_packets)*512./50e6 - 0.1
    bin_start = bf.params_dic['bin_start']
    bin_end = bf.params_dic['bin_end']
    row_start = bf.params_dic['row_start']
    row_end = bf.params_dic['row_end']
    col_start = bf.params_dic['col_start']
    col_end = bf.params_dic['col_end']
    nrows = row_end - row_start + 1
    ncols = col_end - col_start + 1
    nele = nrows * ncols
    nbins = bin_end - bin_start + 1
    Nsti = int(total_time/sti_time)
    ncpu = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(processes=ncpu)
    results = []
    cross_corr = numpy.zeros((nele, nele, nbins, Nsti), dtype='complex')
    for i in range(Nsti):
        seconds_to_skip = i*sti_time
        results.append(pool.apply_async(correlate, args=(filename, filename+"_%d" % i, seconds_to_skip, sti_time, i)))
        
    outputs = [p.get() for p in results]
    for i in range(Nsti):
        cross_corr[:, :, :, i] = outputs[i][1]
    pool.terminate()
    return cross_corr
