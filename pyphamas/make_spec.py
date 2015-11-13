from pyphamas.utils.file_utils get_gbtscan_file
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


    
