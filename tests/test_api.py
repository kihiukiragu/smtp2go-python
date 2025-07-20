import json
import pytest
import responses
import os
import base64

# Correct import for __version__ from core.py
from smtp2go.core import Smtp2goClient, __version__
# CRITICAL CHANGE: Import exceptions and mock helpers from test_helpers
from tests.test_helpers import (
    EnvironmentVariableContextManager,
    get_successful_response_partial,
    get_failed_response_partial,
    PAYLOAD,
    FAILED_RESPONSE_BODY,
    SUCCESSFUL_RESPONSE_BODY,
    HEADERS,
    mock_smtp2go_success_response,
    mock_smtp2go_failed_response,
    exceptions # Import the aliased exceptions module
)
from smtp2go.settings import API_ROOT, ENDPOINT_SEND


# --- Test Cases ---

@responses.activate
def test_successful_endpoint_send():
    mock_smtp2go_success_response() # Use the imported helper
    response = get_successful_response_partial()
    assert response.success is True
    assert response.json == SUCCESSFUL_RESPONSE_BODY
    assert response.status_code == 200
    assert not response.errors
    assert response.errors == SUCCESSFUL_RESPONSE_BODY.get(
        'data').get('failures')


@responses.activate
def test_failed_endpoint_send():
    mock_smtp2go_failed_response() # Use the imported helper
    response = get_failed_response_partial()

    assert response.success is False
    assert response.status_code == 400
    assert response.json == FAILED_RESPONSE_BODY
    assert response.errors
    assert response.errors == FAILED_RESPONSE_BODY.get('data').get('failures')


def test_no_environment_variable_raises_api_exception():
    with EnvironmentVariableContextManager('SMTP2GO_API_KEY', None):
        with pytest.raises(exceptions.Smtp2goAPIKeyException, match='Smtp2goClient requires api_key'):
            Smtp2goClient()


@responses.activate
def test_environment_variable_can_be_passed_into_constructor():
    test_api_key = 'constructor-api-key'
    client = Smtp2goClient(api_key=test_api_key)
    assert client.api_key == test_api_key
    mock_smtp2go_success_response() # Use the imported helper
    response = client.send(**PAYLOAD)
    assert response.success is True
    assert response.json == SUCCESSFUL_RESPONSE_BODY
    assert response.status_code == 200
    assert not response.errors
    assert response.errors == SUCCESSFUL_RESPONSE_BODY.get(
        'data').get('failures')
    assert client.api_key == test_api_key


@responses.activate
def test_version_header_sent(monkeypatch):
    monkeypatch.setenv('SMTP2GO_API_KEY', 'testapikey')

    def test_http_headers_callback(request):
        assert request.headers.get('X-Smtp2go-Api') == 'smtp2go-python'
        assert request.headers.get('X-Smtp2go-Api-Version') == __version__
        assert request.headers.get('Content-Type') == 'application/json'

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

    mock_smtp2go_success_response() # Use the imported helper

    s = Smtp2goClient()
    payload = PAYLOAD.copy()
    payload['custom_headers'] = {custom_header_key: custom_header_val}

    s.send(**payload)

    assert len(responses.calls) == 1
    request_body = json.loads(responses.calls[0].request.body)

    assert 'custom_headers' in request_body
    assert isinstance(request_body['custom_headers'], list)
    assert len(request_body['custom_headers']) == 1

    assert request_body['custom_headers'][0]['header'] == custom_header_key
    assert request_body['custom_headers'][0]['value'] == custom_header_val

    assert custom_header_key not in responses.calls[0].request.headers.keys()


@responses.activate
def test_send_with_attachments():
    mock_smtp2go_success_response() # Use the imported helper

    dummy_content = base64.b64encode(b"This is a test attachment content.").decode('utf-8')
    attachments_to_send = [
        {'filename': 'test.txt', 'content': dummy_content, 'mimetype': 'text/plain'},
        {'filename': 'image.jpg', 'content': dummy_content}
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

    assert request_body['attachments'][0]['filename'] == 'test.txt'
    assert request_body['attachments'][0]['content'] == dummy_content
    assert request_body['attachments'][0]['mimetype'] == 'text/plain'

    assert request_body['attachments'][1]['filename'] == 'image.jpg'
    assert request_body['attachments'][1]['content'] == dummy_content
    assert request_body['attachments'][1]['mimetype'] == 'application/octet-stream'


@responses.activate
def test_send_sender_as_dict():
    mock_smtp2go_success_response() # Use the imported helper
    client = Smtp2goClient(api_key="test_api_key")
    resp = client.send(
        sender={'email': 'sender@example.com', 'name': 'Sender Name'},
        recipients=['recipient@example.com'],
        subject='Test Subject',
        text='Test Body'
    )
    assert resp.success
    payload = json.loads(responses.calls[0].request.body)
    assert payload['sender'] == 'sender@example.com'


@responses.activate
def test_send_recipients_as_dicts():
    mock_smtp2go_success_response() # Use the imported helper
    client = Smtp2goClient(api_key="test_api_key")
    resp = client.send(
        sender='test@example.com',
        recipients=[{'email': 'rec1@example.com', 'name': 'Rec One'}, 'rec2@example.com'],
        subject='Test Subject',
        text='Test Body'
    )
    assert resp.success
    payload = json.loads(responses.calls[0].request.body)
    # CRITICAL CHANGE: Assert that 'to' contains formatted strings
    assert payload['to'] == ['Rec One <rec1@example.com>', 'rec2@example.com']


@responses.activate
def test_send_template_email():
    mock_smtp2go_success_response() # Use the imported helper
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
    assert 'subject' not in payload
    assert 'text_body' not in payload
    assert 'html_body' not in payload


@responses.activate
def test_send_empty_custom_headers_not_sent():
    mock_smtp2go_success_response() # Use the imported helper
    client = Smtp2goClient(api_key="test_api_key")
    resp = client.send(
        sender='test@example.com',
        recipients=['recipient@example.com'],
        subject='Test Subject',
        text='Test Body',
        custom_headers={}
    )
    assert resp.success
    request_body = json.loads(responses.calls[0].request.body)
    assert 'custom_headers' not in request_body or request_body['custom_headers'] == []


@responses.activate
def test_send_empty_attachments_not_sent():
    mock_smtp2go_success_response() # Use the imported helper
    client = Smtp2goClient(api_key="test_api_key")
    resp = client.send(
        sender='test@example.com',
        recipients=['recipient@example.com'],
        subject='Test Subject',
        text='Test Body',
        attachments=[]
    )
    assert resp.success
    request_body = json.loads(responses.calls[0].request.body)
    assert 'attachments' not in request_body or request_body['attachments'] == []


# --- Additional tests for parameter validation ---

def test_send_method_raises_exception_if_text_html_template_not_present():
    client = Smtp2goClient(api_key="test_api_key")
    with pytest.raises(exceptions.Smtp2goParameterException, match=r'send\(\) requires text, html or template_id arguments\.'):
        client.send(sender='test@example.com', recipients=['rec@example.com'], subject='Test Subject')


def test_send_method_raises_exception_if_subject_and_template_id_not_present():
    client = Smtp2goClient(api_key="test_api_key")
    with pytest.raises(exceptions.Smtp2goParameterException, match=r'send\(\) requires template_id or subject arguments\.'):
        client.send(sender='test@example.com', recipients=['rec@example.com'], text='Test Body')


@responses.activate
def test_send_method_does_not_raise_exception_if_text_present():
    mock_smtp2go_success_response() # Use the imported helper
    client = Smtp2goClient(api_key="test_api_key")
    resp = client.send(sender='test@example.com', recipients=['rec@example.com'], subject='Test Subject', text='Test Body')
    assert resp.success


@responses.activate
def test_send_method_does_not_raise_exception_if_html_present():
    mock_smtp2go_success_response() # Use the imported helper
    client = Smtp2goClient(api_key="test_api_key")
    resp = client.send(sender='test@example.com', recipients=['rec@example.com'], subject='Test Subject', html='Test HTML')
    assert resp.success


@responses.activate
def test_send_method_does_not_raise_exception_if_template_id_present():
    mock_smtp2go_success_response() # Use the imported helper
    client = Smtp2goClient(api_key="test_api_key")
    resp = client.send(sender='test@example.com', recipients=['rec@example.com'], template_id='123')
    assert resp.success


def test_send_method_raises_exception_for_invalid_sender_format():
    client = Smtp2goClient(api_key="test_api_key")
    with pytest.raises(exceptions.Smtp2goParameterException, match=r"Sender must be an email string or a dictionary with 'email'\."):
        client.send(sender=123, recipients=['rec@example.com'], subject='Test', text='Body')

def test_send_method_raises_exception_for_invalid_recipients_format():
    client = Smtp2goClient(api_key="test_api_key")
    # CRITICAL CHANGE: Update regex to match the exact message from core.py
    with pytest.raises(exceptions.Smtp2goParameterException, match=r"Recipients must be a list of email strings or dictionaries\."):
        client.send(sender='test@example.com', recipients='invalid_string', subject='Test', text='Body')

    # CRITICAL CHANGE: Update regex to match the exact message from core.py
    with pytest.raises(exceptions.Smtp2goParameterException, match=r"Each recipient must be an email string or a dictionary with 'email' \(and optional 'name'\)\."):
        client.send(sender='test@example.com', recipients=['rec@example.com', 123], subject='Test', text='Body')

def test_send_method_raises_exception_for_invalid_custom_headers_format():
    client = Smtp2goClient(api_key="test_api_key")
    with pytest.raises(exceptions.Smtp2goParameterException, match=r"custom_headers must be a dictionary\."):
        client.send(sender='test@example.com', recipients=['rec@example.com'], subject='Test', text='Body', custom_headers="invalid")

def test_send_method_raises_exception_for_invalid_attachments_format():
    client = Smtp2goClient(api_key="test_api_key")
    with pytest.raises(exceptions.Smtp2goParameterException, match=r"Attachments must be a list of dictionaries\."):
        client.send(sender='test@example.com', recipients=['rec@example.com'], subject='Test', text='Body', attachments="invalid")

    with pytest.raises(exceptions.Smtp2goParameterException, match=r"Each attachment must be a dictionary with 'filename' and 'content' \(base64 encoded\)\."):
        client.send(sender='test@example.com', recipients=['rec@example.com'], subject='Test', text='Body', attachments=[{'filename': 'no_content'}])

