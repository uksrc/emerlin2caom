# place-holder for new astro composable module


from astropy.io import fits

def _clean_headers(fits_header):
    """
    Hopefully not Gemini specific. Remove invalid cards and add missing END cards after extensions.
    :param fits_header: fits_header a string of keyword/value pairs
    """
    new_header = []
    first_header_encountered = False
    for line in fits_header.split('\n'):
        if len(line.strip()) == 0:
            pass
        elif line.startswith('--- PHU ---'):
            first_header_encountered = True
        elif line.startswith('--- HDU 0'):
            if first_header_encountered:
                new_header.append('END\n')
            else:
                first_header_encountered = True
        elif line.startswith('--- HDU'):
            new_header.append('END\n')
        elif line.strip() == 'END':
            new_header.append('END\n')
        elif '=' not in line and not (line.startswith('COMMENT') or line.startswith('HISTORY')):
            pass
        else:
            new_header.append(f'{line}\n')
    new_header.append('END\n')
    return ''.join(new_header)

def make_headers_from_string(fits_header):
    """Create a list of fits.Header instances from a string.
    :param fits_header a string of keyword/value pairs"""
    fits_header = _clean_headers(fits_header)
    delim = 'END\n'
    extensions = [e + delim for e in fits_header.split(delim) if e.strip()]
    headers = [fits.Header.fromstring(e, sep='\n') for e in extensions]
    return headers

def make_headers_from_file(fqn):
    """
    Make keyword/value pairs from a non-FITS file behave like the headers for
    a FITS file.

    :param fqn:
    :return: [fits.Header]
    """
    try:
        fits_header = open(fqn).read()
        headers = make_headers_from_string(fits_header)
    except IsADirectoryError:
        headers = ''

    return headers
