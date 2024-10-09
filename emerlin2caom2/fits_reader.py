from astropy.io import fits


def header_extraction(fits_file):
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

    return fits_out