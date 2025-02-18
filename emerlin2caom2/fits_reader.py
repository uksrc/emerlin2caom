from astropy.io import fits


def header_extraction(fits_file):
    """
    Function to extract CAOM relevant metadata from fits files.
    :param fits_file: name and location of fits file
    :returns: dictionary of metadata
    """
    hdu = fits.open(fits_file)
    newhead = hdu[0].header

    fits_out = dict()

    fits_out['coord_scheme'] = newhead['EQUINOX']
    fits_out['ra_unit'] = newhead['CTYPE1']
    fits_out['ra_deg'] = newhead['CRVAL1']
    fits_out['dec_unit'] = newhead['CTYPE2']
    fits_out['dec_deg'] = newhead['CRVAL2']
    fits_out['wsc_version'] = newhead['WSCVERSI']
    fits_out['central_freq'] = newhead['CRVAL3']
    fits_out['pix_width'] = newhead['NAXIS1']
    fits_out['pix_length'] = newhead['NAXIS2']
    fits_out['pix_width_scale'] = newhead['CDELT1']
    fits_out['pix_length_scale'] = newhead['CDELT2']
    return fits_out
