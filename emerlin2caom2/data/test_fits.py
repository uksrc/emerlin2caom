import sys 
from astropy.io import fits

def get_local_headers_from_fits(fqn):
    """Create a list of fits.Header instances from a fits file.
    :param fqn str  fully-qualified name of the FITS file on disk
    :return list of fits.Header instances
    """
    hdulist = fits.open(fqn, memmap=True, lazy_load_hdus=True)
    hdulist.verify('fix')
    hdulist.close()
    headers = [h.header for h in hdulist]
    return headers

a = get_local_headers_from_fits(sys.argv[1])
# print(str(a))
print(type(a))
