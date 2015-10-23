# pyphamas
PYPHAMAS: Python tools for PHAMAS (PHAsed Millimeter Array System)

### Usage

    from pyphamas import BinFile
    from pyphamas.plots import X64Plot
    bf = BinFile('20151019-174823_spec_0.bin', number_packets=3000)
    bf.get_spec_data()
    bf.read_xml_config('Configs/umass_oct19.xml')
    pl = X64Plot()
    pl.plot_all_spec(bf)

    
