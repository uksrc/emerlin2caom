# This module extracts metadata from eMERLIN measurement sets via casa
# -built operations.  When more table.open operations are added, it 
# would be good to combine them all into one open.
import casatools
import math
import numpy
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
        'num_scans': len(msmd.scansforfield(targ_name)),
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
        'chan_res': msmd_elements['chan_res']/1e9, 
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
        'polar_dim': get_polar(ms_file)[1]
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

def polar2cart(r, theta, phi):
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
    t_ini = numpy.min(t)
    t_end = numpy.max(t)
    ms.close()
    return t_ini, t_end
