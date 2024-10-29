# This module extracts metadata from eMERLIN measurement sets via casa
# -built operations.  When more table.open operations are added, it 
# would be good to combine them all into one open.
import casatools
import numpy as np


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

    antenna_ids = msmd.antennaids()
    field_ids = range(msmd.nfields())


    msmd_elements = {
        'mssources': msmd.fieldnames(),
        'phs_cntr': [msmd.phasecenter(x) for x in field_ids],
        'field_time': [msmd.timesforfield(x) for x in field_ids],
        'tel_name': msmd.observatorynames(),
        'antennas': msmd.antennanames(),
        'ante_off': [msmd.antennaoffset(x) for x in antenna_ids],
        'ante_pos': [msmd.antennaposition(x) for x in antenna_ids],
        'obs_pos' : msmd.observatoryposition(),
        'wl_upper': msmd.chanfreqs(0)[0],
        'wl_lower': msmd.chanfreqs(nspw-1)[-1],
        'chan_res': msmd.chanwidths(0)[0],
        'nchan'   : len(msmd.chanwidths(0)),
        'prop_id' : msmd.projects()[0]
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

def target_position(ms_file, target):
    """
    Get position of target object. Right now it takes an input target. Can instead go entirely via the measurement set
    and instead return two target positions, without knowledge of which is the primary.
    :param ms_file: input measurement set name
    :param target: target object name
    :returns: [ra, dec] in degrees
    """
    tb.open(ms_file+'/FIELD')
    source_name = tb.getcol('NAME')
    source_ref = tb.getcol('REFERENCE_DIR')
    source_coords_ra = np.rad2deg(source_ref[0][0][source_name.tolist().index(target)]) % 360
    source_coords_dec = np.rad2deg(source_ref[1][0][source_name.tolist().index(target)]) % 360
    tb.close()
    return [source_coords_ra, source_coords_dec]