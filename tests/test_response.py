import responses
# Removed: import sys # Removed debugging import
from tests.test_helpers import (
    get_failed_response_partial,
    get_successful_response_partial,
    HEADERS,
    FAILED_RESPONSE_BODY,
    SUCCESSFUL_RESPONSE_BODY,
    mock_smtp2go_success_response,
    mock_smtp2go_failed_response,
    exceptions # Import the aliased exceptions module
)
from smtp2go.settings import API_ROOT, ENDPOINT_SEND
import json


# Removed: --- DEBUGGING IMPORTS in test_response.py ---
# Removed: print(f"\n--- DEBUGGING IMPORTS in test_response.py ---")
# Removed: print(f"sys.path: {sys.path}")
# Removed: try:
# Removed:     print(f"ID of Smtp2goAPIKeyException: {id(exceptions.Smtp2goAPIKeyException)}")
# Removed:     print(f"ID of Smtp2goParameterException: {id(exceptions.Smtp2goParameterException)}")
# Removed:     print(f"Module for Smtp2goAPIKeyException: {exceptions.Smtp2goAPIKeyException.__module__}")
# Removed:     print(f"Module for Smtp2goParameterException: {exceptions.Smtp2goParameterException.__module__}")
# Removed:     print(f"File for Smtp2goAPIKeyException: {exceptions.__file__}")
# Removed: except NameError as e:
# Removed:     print(f"NameError during debug print: {e}. Exceptions might not be fully loaded yet.")
# Removed: print(f"--- END DEBUGGING IMPORTS in test_response.py ---\n")
# Removed: --- END DEBUGGING ---


@responses.activate
def test_successful_response_json():
    mock_smtp2go_success_response() # Use the imported helper
    response = get_successful_response_partial()
    assert response.json == SUCCESSFUL_RESPONSE_BODY


@responses.activate
def test_failed_response_json():
    mock_smtp2go_failed_response() # Use the imported helper
    response = get_failed_response_partial()
    assert response.json == FAILED_RESPONSE_BODY


@responses.activate
def test_successful_response_success():
    mock_smtp2go_success_response() # Use the imported helper
    response = get_successful_response_partial()
    assert response.success is True


@responses.activate
def test_failed_response_success():
    mock_smtp2go_failed_response() # Use the imported helper
    response = get_failed_response_partial()
    assert response.success is False


@responses.activate
def test_response_errors_on_successful_response():
    mock_smtp2go_success_response() # Use the imported helper
    response = get_successful_response_partial()
    assert response.errors == []


@responses.activate
def test_response_errors_on_failed_response():
    mock_smtp2go_failed_response() # Use the imported helper
    response = get_failed_response_partial()
    assert response.errors == FAILED_RESPONSE_BODY.get('data').get('failures')


@responses.activate
def test_successful_response_status_code():
    mock_smtp2go_success_response() # Use the imported helper
    response = get_successful_response_partial()
    assert response.status_code == 200


@responses.activate
def test_failed_response_status_code():
    mock_smtp2go_failed_response() # Use the imported helper
    response = get_failed_response_partial()
    assert response.status_code == 400


@responses.activate
def test_successful_response_request_id():
    mock_smtp2go_success_response() # Use the imported helper
    response = get_successful_response_partial()
    assert response.request_id == SUCCESSFUL_RESPONSE_BODY['request_id']


@responses.activate
def test_failed_response_request_id():
    mock_smtp2go_failed_response() # Use the imported helper
    response = get_failed_response_partial()
    assert response.request_id == FAILED_RESPONSE_BODY['request_id']


@responses.activate
def test_successful_response_rate_limit_limit():
    mock_smtp2go_success_response() # Use the imported helper
    response = get_successful_response_partial()
    assert response.rate_limit.limit == int(HEADERS.get('X-Ratelimit-Limit'))


@responses.activate
def test_failed_response_rate_limit_limit():
    mock_smtp2go_failed_response() # Use the imported helper
    response = get_failed_response_partial()
    assert response.rate_limit.limit == int(HEADERS.get('X-Ratelimit-Limit'))


@responses.activate
def test_successful_response_rate_limit_reset():
    mock_smtp2go_success_response() # Use the imported helper
    response = get_successful_response_partial()
    assert response.rate_limit.reset == int(HEADERS.get('X-Ratelimit-Reset'))


@responses.activate
def test_failed_response_rate_limit_reset():
    mock_smtp2go_failed_response() # Use the imported helper
    response = get_failed_response_partial()
    assert response.rate_limit.reset == int(HEADERS.get('X-Ratelimit-Reset'))


@responses.activate
def test_successful_response_rate_limit_remaining():
    mock_smtp2go_success_response() # Use the imported helper
    response = get_successful_response_partial()
    assert response.rate_limit.remaining == int(
        HEADERS.get('X-Ratelimit-Remaining'))


@responses.activate
def test_failed_response_rate_limit_remaining():
    mock_smtp2go_failed_response() # Use the imported helper
    response = get_failed_response_partial()
    assert response.rate_limit.remaining == int(
        HEADERS.get('X-Ratelimit-Remaining'))

