import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from datetime import datetime
import casa_reader
# Import the functions you want to test
from casa_reader import (msmd_collect, ms_other_collect, emerlin_band, freq2wl,
                         get_polar, get_scan_sum, target_position, polar2cart,
                         get_release_date, mjdtodate, get_obstime)



# Test emerlin_band function
@pytest.mark.parametrize("freq,expected", [
    (1.5e9, 'L'),
    (5e9, 'C'),
    (20e9, 'K'),
    (10e9, 'Null'),
])
def test_emerlin_band(freq, expected):
    assert emerlin_band(freq) == expected


# Test freq2wl function
def test_freq2wl():
    assert freq2wl(1e9) == pytest.approx(0.299792458)


# Test get_polar function
# def test_get_polar(mock_casatools):
#     tb = mock_casatools.table.return_value
#     tb.getcol.side_effect = [np.array([['R'], ['L']]), np.array([2])]
#
#     pol_type, pol_dim = get_polar('dummy.ms')
#
#     assert pol_type == ['R', 'L']
#     assert pol_dim == 2


# Add more tests for other functions...

# Test polar2cart function
def test_polar2cart():
    result = polar2cart(1, np.pi / 4, np.pi / 4)
    assert result['x'] == pytest.approx(0.5)
    assert result['y'] == pytest.approx(0.5)
    assert result['z'] == pytest.approx(0.707, rel=1e-3)


# Test mjdtodate function
def test_mjdtodate():
    assert mjdtodate(0) == datetime(1858, 11, 17)
    assert mjdtodate(1) == datetime(1858, 11, 18)
