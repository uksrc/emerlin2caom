# This module extracts metadata from eMERLIN measurement sets via casa
# -built operations.  When more table.open operations are added, it 
# would be good to combine them all into one open.

import numpy
import casatools

msmd = casatools.msmetadata()
ms = casatools.ms()
tb = casatools.table()

def msmd_collect(ms_file):
    """
    Consolidate opening measurement set to one function
    :param ms_file: Input measurement set
    :returns msmd_elements: data structure dictionary of relevant 
    metadata

    """

    msmd.open(ms_file)
    nspw = msmd.nspw()
    msmd_elements = {
        'mssources': msmd.fieldnames(),
        'tel_name': msmd.observatorynames(),
        'antennas': msmd.antennanames(),
        'wl_upper': msmd.chanfreqs(0)[0],
        'wl_lower': msmd.chanfreqs(nspw-1)[-1],
        'chan_res': msmd.chanwidths(0)[0],
        'nchan': len(msmd.chanwidths(0)),
    }
    msmd.close()

    # Dictionary of changes
    elements_convert = {
        'wl_upper': freq2wl(msmd_elements['wl_upper']),
        'wl_lower': freq2wl(msmd_elements['wl_lower']),
        'chan_res': msmd_elements['chan_res']/1e9,
        'bp_name': emerlin_band(msmd_elements['wl_upper'])
    }

    # Update dictionary with converted values and additions.
    msmd_elements.update(elements_convert)

    return msmd_elements

def emerlin_band(freq):
    """
    Determine eMERLIN band name from frequency
    :param freq: Frequency in Hz
    :return band_name: string
    """
    freq = freq/1e9
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

def freq2wl(freq):
    # Convert frequency (Hz) to wavelength (m)
    sol = 299792458
    wl = sol/freq
    return wl

def get_polar(ms_file):
    """
    Get polarisation state
    :param ms_file: Name of measurement set
    :returns: polarization type and number of dimensions.
    """
    tb.open(ms_file+'/FEED')
    polarization = tb.getcol('POLARIZATION_TYPE')
    pol_dim = tb.getcol('NUM_RECEPTORS')[0]
    tb.close()
    pol_type = list(polarization[:,0])    
    return pol_type, pol_dim

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
