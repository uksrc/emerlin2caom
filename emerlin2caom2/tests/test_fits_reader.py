import pytest
from astropy.io import fits
from astropy.io.fits.header import Header
from unittest.mock import patch, MagicMock
from test_fits_reader import header_extraction  # Replace 'your_module' with the actual module name


@pytest.fixture
def mock_fits_header():
    return Header({
        'EQUINOX': 2000.0,
        'CTYPE1': 'RA---SIN',
        'CRVAL1': 83.63308,
        'CTYPE2': 'DEC--SIN',
        'CRVAL2': 22.01446,
        'WSCVERSI': '1.0',
        'CRVAL3': 1400000000.0,
        'NAXIS1': 1024,
        'NAXIS2': 1024,
        'CDELT1': -0.00277777,
        'CDELT2': 0.00277777
    })


@pytest.fixture
def mock_fits_hdu(mock_fits_header):
    mock_hdu = MagicMock()
    mock_hdu.header = mock_fits_header
    return mock_hdu


@patch('astropy.io.fits.open')
def test_header_extraction(mock_fits_open, mock_fits_hdu):
    mock_fits_open.return_value = [mock_fits_hdu]

    result = header_extraction('dummy.fits')

    assert isinstance(result, dict)
    assert result['coord_scheme'] == 2000.0
    assert result['ra_unit'] == 'RA---SIN'
    assert result['ra_deg'] == 83.63308
    assert result['dec_unit'] == 'DEC--SIN'
    assert result['dec_deg'] == 22.01446
    assert result['wsc_version'] == '1.0'
    assert result['central_freq'] == 1400000000.0
    assert result['pix_width'] == 1024
    assert result['pix_length'] == 1024
    assert result['pix_width_scale'] == -0.00277777
    assert result['pix_length_scale'] == 0.00277777


@patch('astropy.io.fits.open')
def test_header_extraction_missing_key(mock_fits_open, mock_fits_hdu, mock_fits_header):
    del mock_fits_header['WSCVERSI']
    mock_fits_open.return_value = [mock_fits_hdu]

    with pytest.raises(KeyError):
        header_extraction('dummy.fits')


@patch('astropy.io.fits.open')
def test_header_extraction_file_not_found(mock_fits_open):
    mock_fits_open.side_effect = FileNotFoundError

    with pytest.raises(FileNotFoundError):
        header_extraction('nonexistent.fits')


@patch('astropy.io.fits.open')
def test_header_extraction_invalid_fits(mock_fits_open):
    mock_fits_open.side_effect = fits.InvalidHDUException

    with pytest.raises(fits.InvalidHDUException):
        header_extraction('invalid.fits')
