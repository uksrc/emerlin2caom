import casatools

msmd = casatools.msmetadata()
ms = casatools.ms()

def find_mssources(ms_file):
    # Get list of sources from measurement set
    # To do: discern target and calibrators for CAOM Observation.targetName
    msmd.open(ms_file)
    mssources = ','.join(numpy.sort(msmd.fieldnames()))
    #mssources = msmd.fieldnames()
    msmd.done()
    # logger.debug('Sources in MS {0}: {1}'.format(msfile, mssources))
    return mssources

def get_obs_name(ms_file):
    msmd.open(ms_file)
    obs_name = msmd.observatorynames()
    msmd.done()
    return obs_name[0]

def get_scan_sum(ms_file):
    ms.open(ms_file)
    scan_sum = ms.getscansummary()
    ms.close()
    return scan_sum