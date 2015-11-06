#
# scanLog.py - class to create directories with GBT data filenames
#
# R. Prestage    Aug 2013: original
# R. Prestage 30 Aug 2013: update to look in other directories
# R. Prestage 31 Dec 2013: generalize to all devices
# R. Prestage 24 Jan 2014: add get functions for all (most) receivers
# R. Prestage 24 Jan 2014: add generic getRx capability
# R. Prestage 24 Jan 2014: fix error than Antenna was matching archivist dirs.

import pyfits
import os.path

class scanLog:

    def __init__(self, projId, fileroot = None,
                 vegasroot = "/lustre/gbtdata"):
        self.projId = projId
        self.fileroot = fileroot
        self.vegasroot = vegasroot

        # the list of devices that will be found by this routine - note VEGAS 
        # is special

        self.devices = ["ActiveSurfaceMgr" ,
                       "Antenna" ,
                       "CCB26_40" ,
                       "DCR" ,
                       "GUPPI" ,
                       "GO" ,
                       "IF" ,
                       "LO1A" ,
                       "LO1B" ,
                       "QuadrantDetector" ,
                       "RcvrPF_1" ,
                       "RcvrPF_2" ,
                       "RcvrArray1_2" ,
                       "RcvrArray18_26" ,
                       "Rcvr1_2" ,
                       "Rcvr2_3" ,
                       "Rcvr4_6" ,
                       "Rcvr8_10" ,
                       "Rcvr12_18" ,
                       "Rcvr26_40" ,
                       "Rcvr40_52" ,
                       "Rcvr68_92" ,
                       "Rcvr_PAR" ,
                       "SpectalProcessor" ,
                       "Spectrometer" ,
                       "VEGAS" ,
                       "Zpectrometer" ]

        # search for the full path to the project, if not specified

        currRoot = "/home/gbtdata/"
        testRoot = "/home/archive/test-data/"
        scienceRoot = "/home/archive/science-data/"


        if not fileroot:
            found = False
            dir = currRoot + projId
            if os.path.isdir(dir):
                found = True
                self.fileroot = currRoot
                
            if not found:
                for i in range(2014, 2002, -1):
                    root = testRoot + str(i) + "/"
                    dir = root + projId
                    if os.path.isdir(dir):
                        found = True
                        self.fileroot = root
                        break

            if not found:
                for i in range(14, 0, -1):
                    for year in ["A", "B", "C"]:
                        root = scienceRoot + '{0:0=2d}'.format(i) + year + "/" 
                        dir = root + projId
                        if os.path.isdir(dir):
                            found = True
                            self.fileroot = root
                            break

            if not found:
                detail = "Project " + projId + " does not exist"
                raise NameError(detail)


        # create an empty directionary containing an internal dictionary for each
        # device 
        self.dict = {}
        for device in self.devices:
            self.dict[device] = {}

        # add a special generic "Rcvr" dictionary

        self.rcvrDict = {}

        # the list of known scans

        self.scanList = []

        # on initialization, call the "update" function to initially populate the
        # dictionaries

        self.update()

    def update(self):
        """
        function to update the dictionaries for a given scan log
        """
        # allow all VEGAS banks to be used

        banks = ["A","B","C","D","E","F","G","H"]

        # scans that we find on this pass

        newScanList = []

        # read the data from the fits file (if it exists)

        fname = self.fileroot + "/" + self.projId + "/ScanLog.fits"
        if os.path.isfile(fname):
            fits = pyfits.open(fname)
            bindata = fits['ScanLog'].data
            date = bindata.field('DATE-OBS')
            scan = bindata.field('SCAN')
            filepath = bindata.field('FILEPATH')
            fits.close()
        else:
            detail = "File " + fname + " does not exist"
            raise NameError(detail)


        # Now update the dictionaries, keyed by scan number, for each device

        currScan = 0
        for i in range(len(scan)):

            # if this scan is in the list already, skip over it
            if scan[i] in self.scanList:
                continue

            # are we starting a new scan?
            if scan[i] != currScan:
                currScan = scan[i]
                newScanList.append(currScan)

            # make the complete filename

            filename = self.fileroot + filepath[i][1:].strip()

            # search for the appropriate device in the file name

            for device in self.devices:
                if device in filepath[i]:

                    # exclude Archivist-generated directories

                    if ('-' in filepath[i]):
                        continue

                    # for VEGAS, need to deal with the Bank in the filename

                    if device == "VEGAS":
                        for bank in banks:
                            if bank + ".fits" in filepath[i]:
                                filename = self.vegasroot + \
                                              filepath[i][1:].strip()
                                self.dict["VEGAS"].update( \
                                              {str(currScan)+bank : filename} )
                    else:
                        self.dict[device].update({currScan : filename})

                    # if the device was a receiver, add to the generic Rcvr dictionary also

                        if device[0:4] == "Rcvr":
                            self.rcvrDict.update({currScan : filename})

                    continue

        self.scanList = self.scanList + newScanList

# 

    def scans(self):
        """
        function to return list of scans
        """
        return self.scanList

    # functions to return filenames associated to given scan numbers
    # add additional functions here as they are needed

    def getAntenna(self, scanNo):
        return self.dict["Antenna"][scanNo]

    def getLo(self, scanNo):
        return self.dict["LO1A"][scanNo]

    def getIF(self, scanNo):
        return self.dict["IF"][scanNo]

    def getGo(self, scanNo):
        return self.dict["GO"][scanNo]

    def getVegas(self, scanNo, Bank):
        key = str(scanNo) + Bank
        return self.dict["VEGAS"][key]

    def getAs(self, scanNo):
        return self.dict["ActiveSurfaceMgr"][scanNo]

    def getCCB(self, scanNo):
        return self.dict["CCB26_40"][scanNo]

    def getDCR(self, scanNo):
        return self.dict["DCR"][scanNo]

    def getRcvr1_2(self, scanNo):
        return self.dict["Rcvr1_2"][scanNo]

    def getRcvr2_3(self, scanNo):
        return self.dict["Rcvr2_3"][scanNo]

    def getRcvr4_6(self, scanNo):
        return self.dict["Rcvr4_6"][scanNo]

    def getRcvr8_10(self, scanNo):
        return self.dict["Rcvr8_10"][scanNo]

    def getRcvr12_18(self, scanNo):
        return self.dict["Rcvr12_18"][scanNo]

    def getRcvr26_40(self, scanNo):
        return self.dict["Rcvr4_6"][scanNo]

    def getRcvr40_52(self, scanNo):
        return self.dict["Rcvr4_6"][scanNo]

    def getRx(self, scanNo):
        return self.rcvrDict[scanNo]


    #
    # function to return the naked FITS file name. Assumes a GO fits file
    # exits

    def getFile(self, scanNo):
        fullFile = self.dict["GO"][scanNo]
        pos = fullFile.find("GO") + 3
        thisFile = fullFile[pos:]
        return thisFile

def main():
    x = scanLog('TPTCSOOF_131124')
    print x.scans()
    print x.getGo(69)
    print x.getFile(69)
    print x.getAntenna(69)
    print x.getAs(70)
    print ""
    x = scanLog('TGBT13B_502_25')
    print x.getVegas(25,"A")
    print x.getVegas(25,"B")
    print x.getRx(25)
    x = scanLog('TPTCSRMP_120201')
    print x.getCCB(15)

    x = scanLog("ABCDE")

if __name__ == '__main__':
    main()

