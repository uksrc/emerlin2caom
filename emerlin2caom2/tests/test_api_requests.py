import pytest
import requests
import pyvo as vo
from unittest.mock import patch, Mock, MagicMock

from api_requests import request_post, request_delete, find_existing
from main_app import EmerlinMetadata

@pytest.fixture
def mock_requests():
    with patch('requests.post'), patch('requests.delete') as mock_del:
        yield mock_del

@pytest.fixture
def test_instance():
    # Create test instance with dummy values
    return Obs_class(base_url = 'http://test.url', rootca = 'dummy_ca')

def test_request_post_success(test_instance, mock_requests):
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 201
    requests.post.return_value = mock_response
    test_file = "test.xml"

    # Act
    result = test_instance.request_post(test_file)

    # Assert
    requests.post.assert_called_once_with(
        url="http://test.url",
        data=open(test_file, 'rb'),
        verify="dummy_ca",
        headers={'Content-type': 'application/xml', 'accept': 'application/xml'}
    )
    assert result == 201

def test_request_post_file_handling(test_instance, mock_requests):
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 400
    requests.post.return_value = mock_response
    test_file = "test.xml"

    # Act
    test_instance.request_post(test_file)

def test_request_delete_success(test_instance, mock_requests):
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 204
    requests.delete.return_value = mock_response
    test_id = "12345"

    # Act
    result = test_instance.request_delete(test_id)

    # Assert
    requests.delete.assert_called_once_with(
        url="http://test.url/12345",
        verify="dummy_ca"
    )
    assert result == 204

def test_request_delete_failure(test_instance, mock_requests, capsys):
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 404
    requests.delete.return_value = mock_response
    test_id = "12345"

    # Act
    result = test_instance.request_delete(test_id)

    # Assert
    captured = capsys.readouterr()
    assert "404: Delete may have failed for 12345" in captured.out
    assert result == 404

