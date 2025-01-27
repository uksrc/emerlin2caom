import pytest
import os
from datetime import datetime
from unittest.mock import patch, mock_open
from hashlib import md5

from file_metadata import FileInfo, basename, get_size, get_file_type, get_local_file_info


# Tests for FileInfo class
def test_file_info_creation():
    file_info = FileInfo(id="test_id", size=100, name="test.txt", md5sum="abc123",
                         lastmod=datetime.now(), file_type="text/plain", encoding="utf-8")
    assert file_info.id == "test_id"
    assert file_info.size == 100
    assert file_info.name == "test.txt"
    assert file_info.md5sum == "abc123"
    assert file_info.file_type == "text/plain"
    assert file_info.encoding == "utf-8"


def test_file_info_str_representation():
    file_info = FileInfo(id="test_id", size=100, name="test.txt", md5sum="abc123",
                         lastmod=datetime.now(), file_type="text/plain", encoding="utf-8")
    assert str(file_info).startswith("id=test_id, name=test.txt, size=100, type=text/plain")


def test_file_info_missing_id():
    with pytest.raises(AttributeError):
        FileInfo(id=None)


# Tests for basename function
def test_basename():
    assert basename("/path/to/directory/") == "directory"
    assert basename("/path/to/directory") == "to"
    assert basename("directory/") == "directory"


# Tests for get_size function
@pytest.fixture
def mock_file_system(tmp_path):
    # Create a mock file system
    (tmp_path / "file1.txt").write_text("Hello")
    (tmp_path / "file2.txt").write_text("World")
    return tmp_path


def test_get_size(mock_file_system):
    assert get_size(mock_file_system) == 10  # "Hello" + "World" = 10 bytes


# Tests for get_file_type function
@pytest.mark.parametrize("filename,expected_type", [
    ("test.fits", "application/fits"),
    ("test.gif", "image/gif"),
    ("test.png", "image/png"),
    ("test.jpg", "image/jpeg"),
    ("test.tar.gz", "application/x-tar"),
    ("test.csv", "text/csv"),
    ("test.hdf5", "application/x-hdf5"),
    ("test.pkl", "python/pickle"),
    ("test.txt", "text/plain"),
])
def test_get_file_type(filename, expected_type):
    assert get_file_type(filename) == expected_type


def test_get_file_type_directory():
    with patch('os.path.isdir', return_value=True):
        assert get_file_type("/path/to/directory") == "application/measurement-set"


# Tests for get_local_file_info function
@patch('file_metadata.get_file_type')
@patch('file_metadata.get_size')
@patch('file_metadata.dirhash')
@patch('os.stat')
@patch('builtins.open', new_callable=mock_open, read_data=b'test data')
def test_get_local_file_info_measurement_set(mock_open, mock_stat, mock_dirhash, mock_get_size, mock_get_file_type):
    mock_get_file_type.return_value = 'application/measurement-set'
    mock_get_size.return_value = 1000
    mock_dirhash.return_value = 'mock_hash'

    result = get_local_file_info('/path/to/measurement/set')

    assert isinstance(result, FileInfo)
    assert result.id == "measurement"
    assert result.size == 1000
    assert result.md5sum == 'mock_hash'
    assert result.file_type == 'application/measurement-set'


@patch('file_metadata.get_file_type')
@patch('os.stat')
@patch('builtins.open', new_callable=mock_open, read_data=b'test data')
def test_get_local_file_info_regular_file(mock_open, mock_stat, mock_get_file_type):
    mock_get_file_type.return_value = 'text/plain'
    mock_stat.return_value.st_size = 9  # Length of 'test data'

    result = get_local_file_info('/path/to/file.txt')

    assert isinstance(result, FileInfo)
    assert result.id == "file.txt"
    assert result.size == 9
    assert result.md5sum == md5(b'test data').hexdigest()
    assert result.file_type == 'text/plain'

