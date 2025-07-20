import json
import os
import requests
import logging

# CRITICAL CHANGE: Import API_ROOT and ENDPOINT_SEND from settings.py
from smtp2go.settings import API_ROOT, ENDPOINT_SEND
# CRITICAL CHANGE: Import exceptions here so they are defined
from smtp2go.exceptions import Smtp2goAPIKeyException, Smtp2goParameterException

# Define the SDK version (used in X-Smtp2go-Api-Version header)
__version__ = "2.3.2"

# Configure logging for the SDK itself
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Set to DEBUG to see all detailed logs from the SDK

class Smtp2goResponse:
    """
    Represents the response from the SMTP2GO API.
    """
    def __init__(self, json_data, status_code, headers):
        self.json = json_data
        self.status_code = status_code
        self.headers = headers
        # Ensure success is explicitly a boolean
        self.success = bool(json_data.get('data', {}).get('succeeded', False)) if json_data else False
        self.errors = json_data.get('data', {}).get('failures', []) if json_data else []
        self.request_id = json_data.get('request_id')

        self.rate_limit = self._parse_rate_limit_headers(headers)

    def _parse_rate_limit_headers(self, headers):
        """Parses X-Ratelimit headers into a RateLimit object."""
        class RateLimit:
            def __init__(self, limit=0, remaining=0, reset=0):
                self.limit = limit
                self.remaining = remaining
                self.reset = reset

        limit = int(headers.get('X-Ratelimit-Limit', 0))
        remaining = int(headers.get('X-Ratelimit-Remaining', 0))
        reset = int(headers.get('X-Ratelimit-Reset', 0))

        return RateLimit(limit, remaining, reset)

class Smtp2goClient:
    """
    Client for interacting with the SMTP2GO API.
    """
    def __init__(self, api_key=None):
        if api_key is None:
            api_key = os.getenv('SMTP2GO_API_KEY')

        if not api_key:
            raise Smtp2goAPIKeyException("Smtp2goClient requires api_key to be provided "
                                         "or set as an environment variable 'SMTP2GO_API_KEY'.")
        self.api_key = api_key
        logger.debug(f"Smtp2goClient initialized with API Key (first 5 chars): {self.api_key[:5]}...")

    def _get_headers(self):
        """
        Returns standard HTTP headers for API requests.
        """
        return {
            'X-Smtp2go-Api': 'smtp2go-python',
            'X-Smtp2go-Api-Version': __version__,
            'Content-Type': 'application/json' # Ensure Content-Type is explicitly set
        }

    def _prepare_payload(self, **kwargs):
        """
        Prepares the JSON payload for the /email/send API call.
        """
        payload = {}

        # SENDER FIELD FIX (Support string or dict, match test regex)
        sender = kwargs.get('sender')
        logger.debug(f"[_prepare_payload] Processing sender: {sender}")
        if isinstance(sender, dict):
            if 'email' not in sender:
                raise Smtp2goParameterException("Sender dictionary must contain an 'email' key.")
            payload['sender'] = sender['email'] # Extract email from dict
            if 'name' in sender: # Add sender_name if present in dict
                payload['sender_name'] = sender['name']
        elif isinstance(sender, str):
            payload['sender'] = sender
        else:
            raise Smtp2goParameterException("Sender must be an email string or a dictionary with 'email'.") # Matches test regex

        # RECIPIENTS FIELD FIX (Support list of strings/dicts, format as strings for 'to' field)
        recipients = kwargs.get('recipients')
        logger.debug(f"[_prepare_payload] Raw recipients from kwargs: {recipients}")
        if not isinstance(recipients, list):
            raise Smtp2goParameterException("Recipients must be a list of email strings or dictionaries.") # Matches test regex

        to_list = []
        for rec in recipients:
            logger.debug(f"[_prepare_payload] Processing recipient: {rec}")
            if isinstance(rec, str):
                # If it's already a string, use it directly
                to_list.append(rec)
            elif isinstance(rec, dict) and 'email' in rec:
                email = rec['email']
                name = rec.get('name')
                if name:
                    # Format as "Name <email@example.com>" string
                    to_list.append(f"{name} <{email}>")
                else:
                    # Just the email string
                    to_list.append(email)
            else:
                raise Smtp2goParameterException("Each recipient must be an email string or a dictionary with 'email' (and optional 'name').")

        if not to_list:
            raise Smtp2goParameterException("Recipients must be a non-empty list.") # Fallback if list is empty after processing

        payload['to'] = to_list
        logger.debug(f"[_prepare_payload] Final 'to' list in payload: {payload['to']}")

        # Subject (required unless template_id is used)
        subject = kwargs.get('subject')
        template_id = kwargs.get('template_id')
        if not subject and not template_id:
            raise Smtp2goParameterException("send() requires template_id or subject arguments.")
        if subject:
            payload['subject'] = subject

        # Text, HTML, Template (at least one of text, html, or template_id is required)
        text_body = kwargs.get('text')
        html_body = kwargs.get('html')
        template_data = kwargs.get('template_data')

        if not (text_body or html_body or template_id):
            raise Smtp2goParameterException("send() requires text, html or template_id arguments.")

        if text_body:
            payload['text_body'] = text_body
        if html_body:
            payload['html_body'] = html_body
        if template_id:
            payload['template_id'] = template_id
            if template_data:
                payload['template_data'] = template_data

        # sender_name (top-level parameter, only if not already set by sender dict)
        # This logic is correct as per SMTP2GO API docs, which allow separate sender_name
        if 'sender_name' not in payload: # Only add if not derived from sender dict
            sender_name = kwargs.get('sender_name')
            if sender_name:
                payload['sender_name'] = sender_name

        # Custom Headers
        custom_headers = kwargs.get('custom_headers')
        if custom_headers:
            if not isinstance(custom_headers, dict):
                raise Smtp2goParameterException("custom_headers must be a dictionary.")
            payload['custom_headers'] = [{'header': k, 'value': v} for k, v in custom_headers.items()]

        # Attachments
        attachments = kwargs.get('attachments')
        if attachments:
            if not isinstance(attachments, list):
                raise Smtp2goParameterException("Attachments must be a list of dictionaries.")

            processed_attachments = []
            for att in attachments:
                if not isinstance(att, dict) or 'filename' not in att or 'content' not in att:
                    raise Smtp2goParameterException("Each attachment must be a dictionary with 'filename' and 'content' (base64 encoded).")

                # Add default mimetype if not provided
                if 'mimetype' not in att:
                    att['mimetype'] = 'application/octet-stream'
                processed_attachments.append(att)
            payload['attachments'] = processed_attachments

        return payload

    def send(self, **kwargs):
        """
        Sends an email using the SMTP2GO /email/send API endpoint.
        """
        try:
            logger.debug(f"[Smtp2goClient.send] kwargs received: {kwargs.keys()}")
            logger.debug(f"[Smtp2goClient.send] recipients kwarg: {kwargs.get('recipients')}")

            payload = self._prepare_payload(**kwargs)

            payload['api_key'] = self.api_key

            headers = self._get_headers()

            logger.info(f"Sending email via SMTP2GO API. Payload keys: {list(payload.keys())}, To: {payload.get('to')}")
            logger.debug(f"Full JSON Payload being sent: {json.dumps(payload, indent=2)}")

            response = requests.post(
                API_ROOT + ENDPOINT_SEND,
                headers=headers,
                json=payload # CRITICAL CHANGE: Reverted to 'json=payload' as per API reference
            )

            json_data = response.json()
            return Smtp2goResponse(json_data, response.status_code, response.headers)

        except requests.exceptions.RequestException as e:
            logger.error(f"Network or HTTP error during SMTP2GO API call: {e}")
            return Smtp2goResponse(
                json_data={"data": {"succeeded": False, "failures": [f"Network Error: {e}"]}, "request_id": "network-error"},
                status_code=500,
                headers={}
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response from SMTP2GO: {e}. Response text: {response.text}")
            return Smtp2goResponse(
                json_data={"data": {"succeeded": False, "failures": [f"JSON Decode Error: {e}"]}, "request_id": "json-decode-error"},
                status_code=response.status_code,
                headers=response.headers
            )
        except Smtp2goParameterException as e:
            logger.error(f"SMTP2GO Parameter Validation Error: {e}")
            raise # Re-raise parameter validation errors
        except Exception as e:
            logger.error(f"An unexpected error occurred in Smtp2goClient.send: {e}")
            raise # Re-raise unexpected errors

