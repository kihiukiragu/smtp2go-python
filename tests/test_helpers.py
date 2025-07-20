import os
# No need to import 'responses' here if it's not directly used in these functions
import json
from functools import partial

from smtp2go.core import Smtp2goClient
from smtp2go.settings import API_ROOT, ENDPOINT_SEND
from smtp2go.exceptions import Smtp2goAPIKeyException, Smtp2goParameterException


SEND_ENDPOINT = API_ROOT + ENDPOINT_SEND
TEST_API_KEY = 'testapikey'

# --- Consistent Mock Response Bodies ---
SUCCESSFUL_RESPONSE_BODY = {
    "data": {"succeeded": True, "failed": 0, "failures": []},
    "request_id": "mock_request_id_123"
}

FAILED_RESPONSE_BODY = {
    "data": {
        "succeeded": 0,
        "failed": 1,
        "failures": [
            'The API Key passed was not in the correct format, Please '
            'check the key is correct and try again, The full API key can '
            'be found in the API Keys section in the admin console.'
        ]
    },
    "request_id": "mock_request_id_123"
}

# --- Common Payload for tests ---
PAYLOAD = {
    'sender': 'dave@example.com',
    'recipients': ['matt@example.com'],
    'subject': 'Trying out smtp2go',
    'text': 'Test message',
    'html': '<html><body><p>Test Message</p></body></html>'
}

# --- HEADERS for Rate Limit Assertions ---
HEADERS = {
    'X-Ratelimit-Remaining': '250',
    'X-Ratelimit-Limit': '250',
    'X-Ratelimit-Reset': '37'
}


class EnvironmentVariableContextManager():
    """
    Context manager for creating a temporary environment variable.
    Handles setting to None (unsetting) and restoring original value.
    """
    def __init__(self, key, value):
        self.key = key
        self.new_value = value
        self.original_value = None

    def __enter__(self):
        self.original_value = os.getenv(self.key)
        if self.new_value is None:
            if self.key in os.environ:
                del os.environ[self.key]
        else:
            os.environ[self.key] = self.new_value

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.original_value:
            os.environ[self.key] = self.original_value
        elif self.key in os.environ: # Only delete if it was set by __enter__ and no original value
            del os.environ[self.key]


# --- Simplified Helper Functions for Responses ---
# IMPORTANT: These functions DO NOT have @responses.activate.
# They simply call the Smtp2goClient.send method.
# The mock responses must be set up by the *calling test function* using responses.add.
def get_successful_response(payload=None):
    """
    Sends a request that is expected to receive a successful mock response.
    Assumes a mock response has already been added to `responses`
    by the calling test function.
    """
    with EnvironmentVariableContextManager('SMTP2GO_API_KEY', TEST_API_KEY):
        client = Smtp2goClient()
        return client.send(**(payload if payload is not None else PAYLOAD))

def get_failed_response(payload=None):
    """
    Sends a request that is expected to receive a failed mock response.
    Assumes a mock response has already been added to `responses`
    by the calling test function.
    """
    with EnvironmentVariableContextManager('SMTP2GO_API_KEY', TEST_API_KEY):
        client = Smtp2goClient()
        return client.send(**(payload if payload is not None else PAYLOAD))

# The partial functions are fine as they just wrap the above
get_successful_response_partial = partial(
    get_successful_response, payload=PAYLOAD)
get_failed_response_partial = partial(
    get_failed_response, payload=PAYLOAD)

