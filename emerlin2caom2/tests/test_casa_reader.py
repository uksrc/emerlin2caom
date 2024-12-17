import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import the functions you want to test
from casa_reader import (msmd_collect, ms_other_collect, emerlin_band, freq2wl,
                         get_polar, get_scan_sum, target_position, polar2cart,
                         get_release_date, mjdtodate, get_obstime)


# Mock casatools objects
@pytest.fixture
def mock_casatools():
    with patch('your_module.casatools') as mock_casa:
        mock_casa.msmetadata.return_value = MagicMock()
        mock_casa.ms.return_value = MagicMock()
        mock_casa.table.return_value = MagicMock()
        yield mock_casa


# Test msmd_collect function
def test_msmd_collect(mock_casatools):
    msmd = mock_casatools.msmetadata.return_value
    msmd.nspw.return_value = 2
    msmd.antennaids.return_value = [0, 1]
    msmd.nfields.return_value = 2
    msmd.scannumbers.return_value = [1, 2]
    msmd.fieldnames.return_value = ['target', 'calibrator']
    msmd.phasecenter.side_effect = ['pc1', 'pc2']
    msmd.timesforfield.side_effect = [[1, 2], [3, 4]]
    msmd.observatorynames.return_value = ['obs1']
    msmd.antennanames.return_value = ['ant1', 'ant2']
    msmd.antennaoffset.side_effect = [[1, 2, 3], [4, 5, 6]]
    msmd.antennaposition.side_effect = [[7, 8, 9], [10, 11, 12]]
    msmd.observatoryposition.return_value = [13, 14, 15]
    msmd.chanfreqs.side_effect = [[1e9], [2e9]]
    msmd.chanwidths.return_value = [1e6]
    msmd.projects.return_value = ['proj1']
    msmd.scansforfield.return_value = [1, 2]
    msmd.exposuretime.return_value = {'value': 10}

    result = msmd_collect('dummy.ms', 'target')

    assert isinstance(result, dict)
    assert 'mssources' in result
    assert 'wl_upper' in result
    assert 'wl_lower' in result
    assert 'bp_name' in result


# Test ms_other_collect function
@patch('your_module.get_release_date')
@patch('your_module.get_obstime')
@patch('your_module.get_polar')
def test_ms_other_collect(mock_get_polar, mock_get_obstime, mock_get_release_date):
    mock_get_release_date.return_value = datetime(2023, 1, 1)
    mock_get_obstime.return_value = (1000, 2000)
    mock_get_polar.return_value = (['R', 'L'], 2)

    result = ms_other_collect('dummy.ms')

    assert isinstance(result, dict)
    assert 'data_release' in result
    assert 'obs_start_time' in result
    assert 'obs_stop_time' in result
    assert 'polar_dim' in result


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
def test_get_polar(mock_casatools):
    tb = mock_casatools.table.return_value
    tb.getcol.side_effect = [np.array([['R'], ['L']]), np.array([2])]

    pol_type, pol_dim = get_polar('dummy.ms')

    assert pol_type == ['R', 'L']
    assert pol_dim == 2


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
