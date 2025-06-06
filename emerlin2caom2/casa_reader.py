# This module extracts metadata from eMERLIN measurement sets via casa
# -built operations.  When more table.open operations are added, it 
# would be good to combine them all into one open.
import casatools
import math
import numpy as np
import datetime

msmd = casatools.msmetadata()
ms = casatools.ms()
tb = casatools.table()

def msmd_collect(ms_file, targ_name):
    """
    Consolidate opening measurement set to one function
    :param ms_file: Input measurement set
    :param targ_name: Primary target name string
    :returns msmd_elements: data structure dictionary of relevant 
    metadata

    """
    
    msmd.open(ms_file)
    nspw = msmd.nspw()

    antenna_ids = msmd.antennaids()
    field_ids = range(msmd.nfields())
    targets = targ_name.split(",")
    if len(targets) > 1:
        print("Warning: Multiple Science Targets, Position included for first target only.")
    first_scan = msmd.scannumbers()[0]    

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
        'nchan'   : nspw * len(msmd.chanwidths(0)),
        'prop_id' : msmd.projects()[0],
        #'num_scans': len(msmd.scansforfield(targets[0])),
        'int_time' : msmd.exposuretime(first_scan)['value']
    }

    # Not sure if this is still necessary with latest merge; keep for now? 
    nice_order = ['Lo', 'Mk2', 'Pi', 'Da', 'Kn', 'De', 'Cm']
    refant = [a for a in nice_order if a in msmd_elements['antennas']]
    geo = msmd.antennaposition(refant[0])
    msmd.close()

    # Dictionary of changes
    elements_convert = {
        'wl_upper': freq2wl(msmd_elements['wl_upper']),
        'wl_lower': freq2wl(msmd_elements['wl_lower']),
        'chan_res': freq2wl(msmd_elements['chan_res']), 
        'bp_name': emerlin_band(msmd_elements['wl_upper']),
    }

    # Update dictionary with converted values and additions.
    msmd_elements.update(elements_convert)

    return msmd_elements

def ms_other_collect(ms_file):
    """
    Consolidate non-msmd-type opens to a second dictionary?
    param ms_file: Input measurement set
    returns ms_other_elements: dictionary of non-msmd-retrievable elements \
                               which need various table/col combinations.
    """

    ms_other_elements = {
        'data_release': get_release_date(ms_file),
        'obs_start_time': get_obstime(ms_file)[0],
        'obs_stop_time': get_obstime(ms_file)[1],
        'polar_dim': get_polar(ms_file)[1],
        'polar_states': get_polar(ms_file)[0]
    }


    return ms_other_elements


# Enabler-functions for above dictionaries 

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
    """
    Convert frequency (Hz) to wavelength (m)
    :param freq: Frequency to convert
    :returns: wavelength
    """
    sol = 299792458
    wl = sol/freq
    return wl

def get_polar(ms_file):
    """
    Get polarisation state
    :param ms_file: Name of measurement set
    :returns: polarisation type and number of dimensions.
    """
    tb.open(ms_file+'/FEED')
    polarization = tb.getcol('POLARIZATION_TYPE')
    pol_dim = tb.getcol('NUM_RECEPTORS')[0]
    tb.close()
    pol_type = list(polarization[:,0])    
    if pol_type == ['R','L']:
        pol_type = ['RR', 'LL']
    for i in range(len(pol_type)):
        pol_type[i] = pol_type[i]
 
    return pol_type, pol_dim

def get_uvdist(ms_file):
    """
    Collect list of uvdistances or baselines.
    :param ms_file: Name of measurement set
    :returns: list of uv distances in m.
    """
    tb.open(ms_file)
    uvw = tb.getcol('UVW')
    tb.close()
    uvdist = numpy.sqrt(uvw[0]**2+uvw[1]**2)
    
    return uvdist

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
    targets = target.split(",")
    tb.open(ms_file+'/FIELD')
    source_name = tb.getcol('NAME')
    source_ref = tb.getcol('REFERENCE_DIR')
    source_coords_ra = np.rad2deg(source_ref[0][0][source_name.tolist().index(targets[0])]) % 360
    source_coords_dec = np.rad2deg(source_ref[1][0][source_name.tolist().index(targets[0])]) % 360
    tb.close()
    return [source_coords_ra, source_coords_dec]

def target_position_all(ms_file):
    """
    Get position and names of all targets within a measurement set.
    :param ms_file: input measurement set name
    :param target: target object name
    :returns: ra, dec, names (coords in degrees)
    """
    tb.open(ms_file+'/FIELD')
    source_name = tb.getcol('NAME')
    source_ref = tb.getcol('REFERENCE_DIR')
    source_coords_ra = [np.rad2deg(x) % 360 for x in source_ref[0]]
    source_coords_dec = [np.rad2deg(x) % 360 for x in source_ref[1]]
    tb.close()
    return {"ra":source_coords_ra[0], "dec":source_coords_dec[0], "name":source_name}
  
def polar2cart(r, theta, phi):
    """
    Convert frequency (Hz) to wavelength (m)
    :param freq: Frequency to convert
    :returns: wavelength
    """
    x = r * math.sin(theta) * math.cos(phi)
    y = r * math.sin(theta) * math.sin(phi)
    z = r * math.cos(theta)
    return {'x':x, 'y':y, 'z':z}

def get_release_date(ms_file):
    """
    To do convert to ivoa:datetime
    Retrieve data release date (not metadata release date) in mjd sec.
    :param ms_file: Name of measurement set
    :returns rel_date: date in mjd seconds... which is what caom wants.
    """
    tb.open(ms_file+'/OBSERVATION')
    rel_date = mjdtodate(tb.getcol('RELEASE_DATE')[0]/60./60./24)
    tb.close()
    return rel_date

def mjdtodate(mjd):
    """
    Converts date from MJD to the conventional format
    :param mjd: date in mjd
    :returns: date in pedestrian format
    """
    origin = datetime.datetime(1858,11,17)
    date = origin + datetime.timedelta(mjd)
    return date


def get_obstime(ms_file):
    """
    Retrieve start and end time of total observation in mjd seconds.
    :param ms_file: Name of measurement set
    :returns t_ini, t_end: datetimes initial (or start time), \
                           and Time End (finish time) in mjd sec
    """
    ms.open(ms_file)
    t = ms.getdata('TIME')['time']
    t_ini = np.min(t)
    t_end = np.max(t)
    ms.close()
    return t_ini, t_end
