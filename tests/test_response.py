import responses # Import responses
from tests.test_helpers import (
    get_failed_response_partial,
    get_successful_response_partial,
    HEADERS,
    FAILED_RESPONSE_BODY,
    SUCCESSFUL_RESPONSE_BODY
)
from smtp2go.settings import API_ROOT, ENDPOINT_SEND
import json # Needed for responses.add

# Helper to mock a successful response for test_response.py
def _mock_smtp2go_success_response_for_response_tests():
    responses.add(
        responses.POST,
        API_ROOT + ENDPOINT_SEND,
        json=SUCCESSFUL_RESPONSE_BODY,
        status=200,
        headers=HEADERS
    )

# Helper to mock a failed response for test_response.py
def _mock_smtp2go_failed_response_for_response_tests():
    responses.add(
        responses.POST,
        API_ROOT + ENDPOINT_SEND,
        json=FAILED_RESPONSE_BODY,
        status=400, # Use 400 for explicit failure
        headers=HEADERS
    )


@responses.activate # Add decorator
def test_successful_response_json():
    _mock_smtp2go_success_response_for_response_tests() # Add mock
    response = get_successful_response_partial()
    assert response.json == SUCCESSFUL_RESPONSE_BODY


@responses.activate # Add decorator
def test_failed_response_json():
    _mock_smtp2go_failed_response_for_response_tests() # Add mock
    response = get_failed_response_partial()
    assert response.json == FAILED_RESPONSE_BODY


@responses.activate # Add decorator
def test_successful_response_success():
    _mock_smtp2go_success_response_for_response_tests() # Add mock
    response = get_successful_response_partial()
    assert response.success is True


@responses.activate # Add decorator
def test_failed_response_success():
    _mock_smtp2go_failed_response_for_response_tests() # Add mock
    response = get_failed_response_partial()
    assert response.success is False


@responses.activate # Add decorator
def test_response_errors_on_successful_response():
    _mock_smtp2go_success_response_for_response_tests() # Add mock
    response = get_successful_response_partial()
    assert response.errors == []


@responses.activate # Add decorator
def test_response_errors_on_failed_response():
    _mock_smtp2go_failed_response_for_response_tests() # Add mock
    response = get_failed_response_partial()
    assert response.errors == FAILED_RESPONSE_BODY.get('data').get('failures')


@responses.activate # Add decorator
def test_successful_response_status_code():
    _mock_smtp2go_success_response_for_response_tests() # Add mock
    response = get_successful_response_partial()
    assert response.status_code == 200


@responses.activate # Add decorator
def test_failed_response_status_code():
    _mock_smtp2go_failed_response_for_response_tests() # Add mock
    response = get_failed_response_partial()
    assert response.status_code == 400


@responses.activate # Add decorator
def test_successful_response_request_id():
    _mock_smtp2go_success_response_for_response_tests() # Add mock
    response = get_successful_response_partial()
    assert response.request_id == SUCCESSFUL_RESPONSE_BODY['request_id']


@responses.activate # Add decorator
def test_failed_response_request_id():
    _mock_smtp2go_failed_response_for_response_tests() # Add mock
    response = get_failed_response_partial()
    assert response.request_id == FAILED_RESPONSE_BODY['request_id']


@responses.activate # Add decorator
def test_successful_response_rate_limit_limit():
    _mock_smtp2go_success_response_for_response_tests() # Add mock
    response = get_successful_response_partial()
    assert response.rate_limit.limit == int(HEADERS.get('X-Ratelimit-Limit'))


@responses.activate # Add decorator
def test_failed_response_rate_limit_limit():
    _mock_smtp2go_failed_response_for_response_tests() # Add mock
    response = get_failed_response_partial()
    assert response.rate_limit.limit == int(HEADERS.get('X-Ratelimit-Limit'))


@responses.activate # Add decorator
def test_successful_response_rate_limit_reset():
    _mock_smtp2go_success_response_for_response_tests() # Add mock
    response = get_successful_response_partial()
    assert response.rate_limit.reset == int(HEADERS.get('X-Ratelimit-Reset'))


@responses.activate # Add decorator
def test_failed_response_rate_limit_reset():
    _mock_smtp2go_failed_response_for_response_tests() # Add mock
    response = get_failed_response_partial()
    assert response.rate_limit.reset == int(HEADERS.get('X-Ratelimit-Reset'))


@responses.activate # Add decorator
def test_successful_response_rate_limit_remaining():
    _mock_smtp2go_success_response_for_response_tests() # Add mock
    response = get_successful_response_partial()
    assert response.rate_limit.remaining == int(HEADERS.get('X-Ratelimit-Remaining'))


@responses.activate # Add decorator
def test_failed_response_rate_limit_remaining():
    _mock_smtp2go_failed_response_for_response_tests() # Add mock
    response = get_failed_response_partial()
    assert response.rate_limit.remaining == int(HEADERS.get('X-Ratelimit-Remaining'))

