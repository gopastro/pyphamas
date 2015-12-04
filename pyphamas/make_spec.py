from pyphamas.utils.file_utils import get_gbtscan_file
from pyphamas import BinFile
import numpy

def get_Tsys(hot_scan, sky_scan, scanLen=10.0,
             deltaT=0.5,
             Tamb=290.0, 
             direc='/media/Disk1/nov11_2015',
             config='/media/Disk1/nov11_2015/Config/gbt_nov11.xml'):
    """
    Gets Tsys dictionary given hot and sky scans
    """
    bf = BinFile(get_gbtscan_file(direc=direc, scan=hot_scan)[0], 
                 number_packets=3000)
    bf.sti_cross_correlate(scanLen, deltaT)
    hot = bf.sti_totpower

    bf = BinFile(get_gbtscan_file(direc=direc, scan=sky_scan)[0], 
                 number_packets=3000)
    bf.sti_cross_correlate(scanLen, deltaT)
    sky = bf.sti_totpower

    bf.read_xml_config(config)
    pixels = bf.pixeldic.keys()
    pixels.sort()
    
    Tsys = {}
    for pixel in pixels:
        row, col = bf.pixeldic[pixel]
        H = numpy.abs(hot[row, col, :, :]).mean(axis=1).mean(axis=0)
        S = numpy.abs(sky[row, col, :, :]).mean(axis=1).mean(axis=0)
        Tsys[pixel] = 290. * S /(H - S)
    return Tsys


def get_spec(on_scan, off_scan, Tsys, scanLen=30.0,
             deltaT=0.1,
             direc='/media/Disk1/nov11_2015',
             config='/media/Disk1/nov11_2015/Config/gbt_nov11.xml'):
    """
    Gets spec dictionary given ON and off scans and 
    Tsys dictionary
    """
    bf = BinFile(get_gbtscan_file(direc=direc, scan=on_scan)[0], 
                 number_packets=3000)
    bf.sti_cross_correlate(scanLen, deltaT)
    on = bf.sti_totpower

    bf = BinFile(get_gbtscan_file(direc=direc, scan=off_scan)[0], 
                 number_packets=3000)
    bf.sti_cross_correlate(scanLen, deltaT)
    off = bf.sti_totpower    

    bf.read_xml_config(config)
    pixels = bf.pixeldic.keys()
    pixels.sort()

    spec = {}
    for pixel in pixels:
        row, col = bf.pixeldic[pixel]
        spec[pixel] = Tsys[pixel] * (numpy.abs(on[row, col, :, :]).mean(axis=1) - numpy.abs(off[row, col, :, :]).mean(axis=1))/numpy.abs(off[row, col, :, :]).mean(axis=1)
    return spec


def get_dispersion_correction(on_scan, off_scan, scanLen=30.0,
                              deltaT=0.1,
                              direc='/media/Disk1/nov14_2015'):
    """
    Gets the linear fits for c_y and c_z 
    given On and Off scans
    """
    bf = BinFile(get_gbtscan_file(direc=direc, scan=on_scan)[0], 
                 number_packets=3000)
    bf.sti_cross_correlate(scanLen, deltaT)
    Ron = bf.sti_cc.mean(axis=3)
    Ron = numpy.delete(Ron, bf.bad_inputs, axis=0)
    Ron = numpy.delete(Ron, bf.bad_inputs, axis=1)

    bf = BinFile(get_gbtscan_file(direc=direc, scan=off_scan)[0], 
                 number_packets=3000)
    bf.sti_cross_correlate(scanLen, deltaT)
    Roff = bf.sti_cc.mean(axis=3)
    Roff = numpy.delete(Roff, bf.bad_inputs, axis=0)
    Roff = numpy.delete(Roff, bf.bad_inputs, axis=1)
    
    alpha_y = numpy.zeros(bf.num_bins)
    alpha_z = numpy.zeros(bf.num_bins)
    
    for b in range(bf.num_bins):
        onoff = Ron[:, :, b] - Roff[:, :, b]
        Rxy = onoff[:12, 12:24]
        Rxz = onoff[:12, 24:]
        alpha_y[b] = numpy.angle(Rxy.sum())
        alpha_z[b] = numpy.angle(Rxz.sum())
        
    x = numpy.arange(1, bf.num_bins+1)
    c_y = numpy.polyfit(x, numpy.unwrap(alpha_y), 1)
    c_z = numpy.polyfit(x, numpy.unwrap(alpha_z), 1)
    return c_y, c_z



