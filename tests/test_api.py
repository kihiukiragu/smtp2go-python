import json
import pytest
import responses
import os
import base64

# Correct import for __version__ from core.py
from smtp2go.core import Smtp2goClient, __version__
from smtp2go.exceptions import (
    Smtp2goAPIKeyException,
    Smtp2goParameterException
)
from smtp2go.settings import API_ROOT, ENDPOINT_SEND
from tests.test_helpers import (
    EnvironmentVariableContextManager,
    # Import the partial functions now that get_response is removed
    get_successful_response_partial,
    get_failed_response_partial,
    PAYLOAD,
    FAILED_RESPONSE_BODY,
    SUCCESSFUL_RESPONSE_BODY,
    HEADERS # Import HEADERS for assertions
)

# --- Helper for common API response mocking ---
def _mock_smtp2go_success_response():
    """Mocks a successful SMTP2GO API response."""
    responses.add(
        responses.POST,
        API_ROOT + ENDPOINT_SEND,
        json=SUCCESSFUL_RESPONSE_BODY,
        status=200,
        headers=HEADERS # Use the imported HEADERS
    )

def _mock_smtp2go_failed_response():
    """Mocks a failed SMTP2GO API response."""
    responses.add(
        responses.POST,
        API_ROOT + ENDPOINT_SEND,
        json=FAILED_RESPONSE_BODY,
        status=400, # Use 400 for explicit failure
        headers=HEADERS # Use the imported HEADERS
    )

# --- Test Cases ---

@responses.activate # Activate responses for this test
def test_successful_endpoint_send():
    _mock_smtp2go_success_response() # Add the mock response BEFORE calling the helper
    response = get_successful_response_partial()
    assert response.success is True
    assert response.json == SUCCESSFUL_RESPONSE_BODY
    assert response.status_code == 200
    assert not response.errors
    assert response.errors == SUCCESSFUL_RESPONSE_BODY.get(
        'data').get('failures')


@responses.activate # Activate responses for this test
def test_failed_endpoint_send():
    _mock_smtp2go_failed_response() # Add the mock response BEFORE calling the helper
    response = get_failed_response_partial()

    assert response.success is False
    assert response.status_code == 400
    assert response.json == FAILED_RESPONSE_BODY
    assert response.errors # Should not be empty if there are failures
    assert response.errors == FAILED_RESPONSE_BODY.get('data').get('failures')


def test_no_environment_variable_raises_api_exception():
    with EnvironmentVariableContextManager('SMTP2GO_API_KEY', None):
        with pytest.raises(Smtp2goAPIKeyException, match='Smtp2goClient requires api_key'):
            Smtp2goClient()


@responses.activate
def test_environment_variable_can_be_passed_into_constructor():
    test_api_key = 'constructor-api-key'
    client = Smtp2goClient(api_key=test_api_key)
    assert client.api_key == test_api_key
    _mock_smtp2go_success_response() # Add the mock response
    response = client.send(**PAYLOAD)
    assert response.success is True
    assert response.json == SUCCESSFUL_RESPONSE_BODY
    assert response.status_code == 200
    assert not response.errors
    assert response.errors == SUCCESSFUL_RESPONSE_BODY.get(
        'data').get('failures')
    # Check api key hasn't been altered:
    assert client.api_key == test_api_key


@responses.activate
def test_version_header_sent(monkeypatch):
    monkeypatch.setenv('SMTP2GO_API_KEY', 'testapikey')

    # This callback now only checks HTTP headers that are *expected* to be there
    def test_http_headers_callback(request):
        assert request.headers.get('X-Smtp2go-Api') == 'smtp2go-python'
        assert request.headers.get('X-Smtp2go-Api-Version') == __version__
        assert request.headers.get('Content-Type') == 'application/json'

        # Return a successful response for the callback
        return (200, {}, json.dumps(SUCCESSFUL_RESPONSE_BODY))

    responses.add_callback(
        responses.POST, API_ROOT + ENDPOINT_SEND,
        callback=test_http_headers_callback
    )
    s = Smtp2goClient()
    s.send(**PAYLOAD)


@responses.activate
def test_custom_headers_sent(monkeypatch):
    monkeypatch.setenv('SMTP2GO_API_KEY', 'testapikey')
    custom_header_key, custom_header_val = 'Test-Custom-Header', 'Test Value'

    _mock_smtp2go_success_response() # Add the mock response

    s = Smtp2goClient()
    payload = PAYLOAD.copy()
    payload['custom_headers'] = {custom_header_key: custom_header_val} # Pass as dict

    s.send(**payload)

    # --- THE CRUCIAL CHANGE IS HERE ---
    # Assert that the custom headers are present in the JSON payload's 'custom_headers' list
    assert len(responses.calls) == 1
    request_body = json.loads(responses.calls[0].request.body)

    assert 'custom_headers' in request_body
    assert isinstance(request_body['custom_headers'], list)
    assert len(request_body['custom_headers']) == 1 # Expecting 1 custom header

    # Verify the structure and content of the custom header in the payload
    assert request_body['custom_headers'][0]['header'] == custom_header_key
    assert request_body['custom_headers'][0]['value'] == custom_header_val

    # Also, explicitly assert that these custom headers are NOT in the HTTP request headers
    # This confirms our SDK change is working as intended
    assert custom_header_key not in responses.calls[0].request.headers.keys()


# --- New Test Cases to cover recent SDK updates ---

@responses.activate
def test_send_with_attachments():
    _mock_smtp2go_success_response()

    # Create a dummy base64 encoded content for testing
    dummy_content = base64.b64encode(b"This is a test attachment content.").decode('utf-8')
    attachments_to_send = [
        {'filename': 'test.txt', 'content': dummy_content, 'mimetype': 'text/plain'},
        {'filename': 'image.jpg', 'content': dummy_content} # Mimetype optional, should default
    ]

    client = Smtp2goClient(api_key="test_api_key")
    resp = client.send(
        sender='test@example.com',
        recipients=['recipient@example.com'],
        subject='Test Subject',
        text='Test Body',
        attachments=attachments_to_send
    )

    assert resp.success
    assert len(responses.calls) == 1
    request_body = json.loads(responses.calls[0].request.body)

    assert 'attachments' in request_body
    assert isinstance(request_body['attachments'], list)
    assert len(request_body['attachments']) == 2

    # Verify attachment details
    assert request_body['attachments'][0]['filename'] == 'test.txt'
    assert request_body['attachments'][0]['content'] == dummy_content
    assert request_body['attachments'][0]['mimetype'] == 'text/plain'

    assert request_body['attachments'][1]['filename'] == 'image.jpg'
    assert request_body['attachments'][1]['content'] == dummy_content
    assert request_body['attachments'][1]['mimetype'] == 'application/octet-stream' # Default mimetype


@responses.activate
def test_send_sender_as_dict():
    _mock_smtp2go_success_response()
    client = Smtp2goClient(api_key="test_api_key")
    resp = client.send(
        sender={'email': 'sender@example.com', 'name': 'Sender Name'},
        recipients=['recipient@example.com'],
        subject='Test Subject',
        text='Test Body'
    )
    assert resp.success
    payload = json.loads(responses.calls[0].request.body)
    assert payload['sender'] == {'email': 'sender@example.com', 'name': 'Sender Name'}


@responses.activate
def test_send_recipients_as_dicts():
    _mock_smtp2go_success_response()
    client = Smtp2goClient(api_key="test_api_key")
    resp = client.send(
        sender='test@example.com',
        recipients=[{'email': 'rec1@example.com', 'name': 'Rec One'}, 'rec2@example.com'], # Mix of dict and string
        subject='Test Subject',
        text='Test Body'
    )
    assert resp.success
    payload = json.loads(responses.calls[0].request.body)
    # The SDK should normalize all recipients to the dict format
    assert payload['to'] == [{'email': 'rec1@example.com', 'name': 'Rec One'}, {'email': 'rec2@example.com'}]


@responses.activate
def test_send_template_email():
    _mock_smtp2go_success_response()
    client = Smtp2goClient(api_key="test_api_key")
    resp = client.send(
        sender='template@example.com',
        recipients=['template_rec@example.com'],
        template_id='12345',
        template_data={'name': 'User', 'product': 'Widget'}
    )
    assert resp.success
    payload = json.loads(responses.calls[0].request.body)
    assert payload['template_id'] == '12345'
    assert payload['template_data'] == {'name': 'User', 'product': 'Widget'}
    assert 'subject' not in payload # Subject is optional with template_id
    assert 'text_body' not in payload
    assert 'html_body' not in payload


@responses.activate
def test_send_empty_custom_headers_not_sent():
    _mock_smtp2go_success_response()
    client = Smtp2goClient(api_key="test_api_key")
    resp = client.send(
        sender='test@example.com',
        recipients=['recipient@example.com'],
        subject='Test Subject',
        text='Test Body',
        custom_headers={} # Empty dict
    )
    assert resp.success
    request_body = json.loads(responses.calls[0].request.body)
    assert 'custom_headers' not in request_body or request_body['custom_headers'] == []


@responses.activate
def test_send_empty_attachments_not_sent():
    _mock_smtp2go_success_response()
    client = Smtp2goClient(api_key="test_api_key")
    resp = client.send(
        sender='test@example.com',
        recipients=['recipient@example.com'],
        subject='Test Subject',
        text='Test Body',
        attachments=[] # Empty list
    )
    assert resp.success
    request_body = json.loads(responses.calls[0].request.body)
    assert 'attachments' not in request_body or request_body['attachments'] == []


# --- Additional tests for parameter validation ---

def test_send_method_raises_exception_if_text_html_template_not_present():
    client = Smtp2goClient(api_key="test_api_key")
    with pytest.raises(Smtp2goParameterException, match=r'send\(\) requires text, html or template_id arguments\.'):
        client.send(sender='test@example.com', recipients=['rec@example.com'], subject='Test Subject')


def test_send_method_raises_exception_if_subject_and_template_id_not_present():
    client = Smtp2goClient(api_key="test_api_key")
    with pytest.raises(Smtp2goParameterException, match=r'send\(\) requires template_id or subject arguments\.'):
        client.send(sender='test@example.com', recipients=['rec@example.com'], text='Test Body')


@responses.activate # Added decorator
def test_send_method_does_not_raise_exception_if_text_present():
    _mock_smtp2go_success_response()
    client = Smtp2goClient(api_key="test_api_key")
    resp = client.send(sender='test@example.com', recipients=['rec@example.com'], subject='Test Subject', text='Test Body')
    assert resp.success


@responses.activate # Added decorator
def test_send_method_does_not_raise_exception_if_html_present():
    _mock_smtp2go_success_response()
    client = Smtp2goClient(api_key="test_api_key")
    resp = client.send(sender='test@example.com', recipients=['rec@example.com'], subject='Test Subject', html='Test HTML')
    assert resp.success


@responses.activate # Added decorator
def test_send_method_does_not_raise_exception_if_template_id_present():
    _mock_smtp2go_success_response()
    client = Smtp2goClient(api_key="test_api_key")
    resp = client.send(sender='test@example.com', recipients=['rec@example.com'], template_id='123')
    assert resp.success


def test_send_method_raises_exception_for_invalid_sender_format():
    client = Smtp2goClient(api_key="test_api_key")
    with pytest.raises(Smtp2goParameterException, match=r"Sender must be an email string or a dictionary with 'email'\."):
        client.send(sender=123, recipients=['rec@example.com'], subject='Test', text='Body')

def test_send_method_raises_exception_for_invalid_recipients_format():
    client = Smtp2goClient(api_key="test_api_key")
    with pytest.raises(Smtp2goParameterException, match=r"Recipients must be a list of email strings or dictionaries\."):
        client.send(sender='test@example.com', recipients='invalid_string', subject='Test', text='Body')

    with pytest.raises(Smtp2goParameterException, match=r"Each recipient must be an email string or a dictionary with 'email'\."):
        client.send(sender='test@example.com', recipients=['rec@example.com', 123], subject='Test', text='Body')

def test_send_method_raises_exception_for_invalid_custom_headers_format():
    client = Smtp2goClient(api_key="test_api_key")
    with pytest.raises(Smtp2goParameterException, match=r"custom_headers must be a dictionary\."):
        client.send(sender='test@example.com', recipients=['rec@example.com'], subject='Test', text='Body', custom_headers="invalid")

def test_send_method_raises_exception_for_invalid_attachments_format():
    client = Smtp2goClient(api_key="test_api_key")
    with pytest.raises(Smtp2goParameterException, match=r"Attachments must be a list of dictionaries\."):
        client.send(sender='test@example.com', recipients=['rec@example.com'], subject='Test', text='Body', attachments="invalid")

    with pytest.raises(Smtp2goParameterException, match=r"Each attachment must be a dictionary with 'filename' and 'content' \(base64 encoded\)\."):
        client.send(sender='test@example.com', recipients=['rec@example.com'], subject='Test', text='Body', attachments=[{'filename': 'no_content'}])

