import json
import logging
import os
import requests
from collections import namedtuple

# Assuming these are defined in smtp2go/settings.py
# For demonstration, let's define them here if not available
# API_ROOT = 'https://api.smtp2go.com/v3/'
# ENDPOINT_SEND = 'email/send'

# If you don't have these, you might need to create a settings.py or define them directly
try:
    from smtp2go.settings import API_ROOT, ENDPOINT_SEND
except ImportError:
    # Fallback for demonstration if settings.py is not provided
    API_ROOT = 'https://api.smtp2go.com/v3/'
    ENDPOINT_SEND = 'email/send'
    logging.warning("smtp2go.settings not found, using default API_ROOT and ENDPOINT_SEND.")

# Assuming these are defined in smtp2go/exceptions.py
try:
    from smtp2go.exceptions import (
        Smtp2goAPIKeyException,
        Smtp2goParameterException
    )
except ImportError:
    # Fallback for demonstration if exceptions.py is not provided
    class Smtp2goAPIKeyException(Exception):
        pass
    class Smtp2goParameterException(Exception):
        pass
    logging.warning("smtp2go.exceptions not found, using default exception classes.")


__version__ = '2.3.2' # Incrementing version for the update

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Smtp2goClient:
    """
    Thin Python wrapper over Smtp2go API.

    Usage:

    Ensure API key is set via either:

    # Environment variable:
    # $ export SMTP2GO_API_KEY=<Your API Key>

    client = Smtp2goClient()
    client.send(
        sender='dave@example.com', # Can be string or {'email': 'dave@example.com', 'name': 'Dave Sender'}
        recipients=['matt@example.com', {'email': 'jane@example.com', 'name': 'Jane Doe'}],
        subject='Trying out smtp2go',
        text ='Test message',
        html='<html><body><p>Test HTML message</p></body></html>',
        template_id='8832556',
        template_data={
            'template_variable': 'variableValue'
        },
        custom_headers={
            'X-My-Custom-Header': 'Custom header value' # These go into the email payload
        },
        attachments=[
            {
                'filename': 'document.pdf',
                'content': 'JVBERi0xLjQKJ...', # Base64 encoded content
                'mimetype': 'application/pdf' # Optional, defaults to application/octet-stream
            }
        ]
    )

    Returns:

    Smtp2goResponse instance
    """

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('SMTP2GO_API_KEY', None)
        if not self.api_key:
            raise Smtp2goAPIKeyException(
                'Smtp2goClient requires api_key as SMTP2GO_API_KEY Environment Variable to be set'
            )

    def send(self, sender, recipients, subject=None, text=None,
             html=None, template_id=None, template_data=None, custom_headers=None, attachments=None, **kwargs):
        """
        Sends an email via the SMTP2GO API.

        Args:
            sender (str or dict): The sender's email address (e.g., 'sender@example.com')
                                  or a dictionary {'email': 'sender@example.com', 'name': 'Sender Name'}.
            recipients (list): A list of recipient email addresses (strings)
                               or a list of dictionaries like [{'email': 'rec@example.com', 'name': 'Recipient Name'}].
            subject (str, optional): The email subject. Required if template_id is not provided.
            text (str, optional): The plain text body of the email. Required if html and template_id are not provided.
            html (str, optional): The HTML body of the email. Required if text and template_id are not provided.
            template_id (str, optional): The ID of an SMTP2GO template to use.
            template_data (dict, optional): Dictionary of data for the template variables.
            custom_headers (dict, optional): Dictionary of custom headers to add to the email payload.
                                              E.g., {'X-My-Header': 'My Value'}.
            attachments (list, optional): A list of dictionaries, each representing an attachment.
                                          Each dict must have 'filename' and 'content' (base64 encoded string).
                                          'mimetype' is optional.
                                          Example: [{'filename': 'doc.pdf', 'content': 'base64_string', 'mimetype': 'application/pdf'}]
            **kwargs: Additional keyword arguments (currently not used but kept for flexibility).

        Raises:
            Smtp2goParameterException: If required arguments are missing or malformed.
        """

        # Ensure that either html, text, or template_id was passed:
        if not any([text, html, template_id]):
            raise Smtp2goParameterException(
                'send() requires text, html or template_id arguments.')

        # Ensure subject is provided if not using a template
        if not template_id and not subject:
            raise Smtp2goParameterException(
                'send() requires template_id or subject arguments.')

        # --- Format Sender ---
        formatted_sender = {}
        if isinstance(sender, dict) and 'email' in sender:
            formatted_sender = sender
        elif isinstance(sender, str):
            formatted_sender = {'email': sender}
        else:
            raise Smtp2goParameterException("Sender must be an email string or a dictionary with 'email'.")

        # --- Format Recipients ---
        formatted_recipients = []
        if isinstance(recipients, list):
            for recipient in recipients:
                if isinstance(recipient, dict) and 'email' in recipient:
                    formatted_recipients.append(recipient)
                elif isinstance(recipient, str):
                    formatted_recipients.append({'email': recipient})
                else:
                    raise Smtp2goParameterException("Each recipient must be an email string or a dictionary with 'email'.")
        else:
            raise Smtp2goParameterException("Recipients must be a list of email strings or dictionaries.")

        # --- Format Custom Headers for Payload ---
        # The API expects custom_headers as a list of dicts {'header': 'Name', 'value': 'Value'}
        formatted_custom_headers = []
        if custom_headers:
            if not isinstance(custom_headers, dict):
                raise Smtp2goParameterException("custom_headers must be a dictionary.")
            for header_name, header_value in custom_headers.items():
                formatted_custom_headers.append({
                    'header': header_name,
                    'value': header_value
                })

        # --- Format Attachments ---
        formatted_attachments = []
        if attachments:
            if not isinstance(attachments, list):
                raise Smtp2goParameterException("Attachments must be a list of dictionaries.")
            for attachment in attachments:
                if not isinstance(attachment, dict) or 'filename' not in attachment or 'content' not in attachment:
                    raise Smtp2goParameterException(
                        "Each attachment must be a dictionary with 'filename' and 'content' (base64 encoded)."
                    )
                formatted_attachments.append({
                    'filename': attachment['filename'],
                    'content': attachment['content'],
                    'mimetype': attachment.get('mimetype', 'application/octet-stream')
                })

        # --- Construct Payload ---
        payload_data = {
            'api_key': self.api_key,
            'sender': formatted_sender,
            'to': formatted_recipients,
            'subject': subject,
            'text_body': text,
            'html_body': html,
            'template_id': template_id,
            'template_data': template_data,
            'custom_headers': formatted_custom_headers, # Use the formatted list
            'attachments': formatted_attachments
        }

        # Remove None values from payload to avoid sending them if not provided
        # This is crucial as the API might reject nulls for optional fields
        payload_data = {k: v for k, v in payload_data.items() if v is not None and v != []} # Also remove empty lists

        payload = json.dumps(payload_data)

        # --- Get HTTP Headers ---
        # This method now only returns the necessary HTTP request headers
        headers = self._get_headers()

        response = requests.post(
            API_ROOT + ENDPOINT_SEND, data=payload, headers=headers)
        return Smtp2goResponse(response)

    def _get_headers(self):
        """
        Returns the standard HTTP headers for the API request.
        Custom email headers are part of the JSON payload, not HTTP headers.
        """
        headers = {
            'X-Smtp2go-Api': 'smtp2go-python',
            'X-Smtp2go-Api-Version': __version__,
            'Content-Type': 'application/json' # Essential for JSON payloads
        }
        return headers


class Smtp2goResponse:
    """
    Wrapper over requests.models.response to expose Smtp2go
    specific data.

    Attributes:
    - resp.json: JSON response from API call
    - resp.success: Boolean indicating success of API call
    - resp.errors: List of errors from API call
    - resp.status_code: HTTP status code from API call
    - resp.request_id: Request ID returned from API call
    - resp.rate_limit: Named tuple with remaining, limit, reset for rate limiting
    """

    def __init__(self, response):
        self._response = response
        self.json = self.json() # Call json() once and store
        self.success = self._success()
        self.errors = self._get_errors()
        self.status_code = self._get_status_code()
        self.request_id = self._get_request_id()
        self.rate_limit = self._get_rate_limit()

        logger.info('Success? {0}'.format(self.success))
        logger.info('Status Code: {0}'.format(self.status_code))
        logger.info('Request ID: {0}'.format(self.request_id))
        logger.info('Rate Limit: Remaining={0}, Limit={1}, Reset={2}'.format(
            self.rate_limit.remaining, self.rate_limit.limit, self.rate_limit.reset
        ))


    def _success(self):
        """
        Returns True if API call successful, False otherwise.
        Checks for 'succeeded' flag within 'data' object of the JSON response.
        """
        # Safely get 'succeeded' flag, defaulting to False if not found
        return bool(self.json.get('data', {}).get('succeeded', False))

    def _get_errors(self):
        """
        Gets errors from HTTP response.
        Checks for 'failures' list within 'data' object of the JSON response.
        """
        errors = self.json.get('data', {}).get('failures')
        if errors:
            logger.error("API Errors: %s", errors) # Use proper logging format
        return errors

    def _get_status_code(self):
        """
        Gets HTTP status code from HTTP response.
        """
        return self._response.status_code

    def _get_request_id(self):
        """
        Gets HTTP request ID from HTTP response.
        """
        return self.json.get('request_id')

    def _get_rate_limit(self):
        """
        Parses rate limit headers from the HTTP response.
        """
        rate_limit = namedtuple('rate_limit', ['remaining', 'limit', 'reset'])
        headers = self._response.headers
        return rate_limit(
            int(headers.get('x-ratelimit-remaining', 0)),
            int(headers.get('x-ratelimit-limit', 0)),
            int(headers.get('x-ratelimit-reset', 0))
        )

    def json(self):
        """
        Gets JSON from HTTP response. Handles potential JSON decoding errors.
        """
        try:
            return self._response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {e}")
            logger.error(f"Response text: {self._response.text}")
            return {} # Return empty dict on error
