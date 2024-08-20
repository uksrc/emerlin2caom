import numpy

import casatools

msmd = casatools.msmetadata()
ms = casatools.ms()


def find_mssources(ms_file):
    """
    Get list of sources contained within a measurement set
    :param ms_file: Input measurement set name
    :returns: List of coordinates for sources
    """
    # Get list of sources from measurement set
    # To do: discern target and calibrators for CAOM Observation.targetName
    msmd.open(ms_file)
    # mssources = ','.join(numpy.sort(msmd.fieldnames()))
    mssources = msmd.fieldnames()
    msmd.done()
    # logger.debug('Sources in MS {0}: {1}'.format(msfile, mssources))
    return mssources


def get_obs_name(ms_file):
    """
    Get name of observatory from measurement set
    :param ms_file: Name of measurement set
    :returns: Name of observatory, string
    """
    msmd.open(ms_file)
    obs_name = msmd.observatorynames()
    msmd.done()
    return obs_name

def get_antennas(ms_file):
    # Returns Antenna names list included in interferometer for this obs
    msmd.open(ms_file)
    antennas = msmd.antennanames()
    msmd.close()
    return antennas

def freq2wl(freq):
    # Convert frequency (Hz) to wavelength (m)
    sol = 299792458
    wl = sol/freq
    return wl

def energy_bounds(ms_file):
    # Return energy bounds in wavelength (m)
    msmd.open(ms_file)
    nspw = msmd.nspw()
    freq_ini = msmd.chanfreqs(0)[0]
    freq_end = msmd.chanfreqs(nspw-1)[-1]
    wl_upper = freq2wl(freq_ini)
    wl_lower = freq2wl(freq_end)
    return wl_upper, wl_lower

def get_bandpass(ms_file):
    # Returns eMERLIN name for bandpass CAOM energy.bandpass_name
    # To do: Combine with get_obsfreq for one open on nspw?
    msmd.open(ms_file)
    freq = msmd.chanfreqs(0)[0]/1e9
    msmd.done()
    band = ''
    if (freq > 1.2) and (freq < 1.7):
        band = 'L'
    elif (freq > 4) and (freq < 8):
        band = 'C'
    elif (freq > 17) and (freq < 26):
        band = 'K'
    else:
        print('Cannot determine band from frequency')
        band = 'Null'
    return band



def get_scan_sum(ms_file):
    """
    Get summary for scan information
    :param ms_file: input measurement set name
    :returns scan_sum: Summary of scan information in nested dictionaries
    """
    ms.open(ms_file)
    scan_sum = ms.getscansummary()
    ms.close()
    return scan_sum
