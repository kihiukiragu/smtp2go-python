class Smtp2goBaseException(Exception):
    """
    Base exception for all SMTP2GO SDK-related errors.
    All custom exceptions in this SDK should inherit from this class.
    """
    pass


class Smtp2goAPIKeyException(Smtp2goBaseException):
    """
    Raised when the SMTP2GO API key is missing or invalid.
    This typically occurs if the 'api_key' is not provided during client
    initialization and the 'SMTP2GO_API_KEY' environment variable is not set.
    """
    pass


class Smtp2goParameterException(Smtp2goBaseException):
    """
    Raised when required parameters for an API call are missing or malformed.
    This indicates an issue with the arguments provided to SDK methods (e.g., send()).
    """
    def __init__(self, message=None, parameter_name=None, reason=None):
        """
        Initializes the Smtp2goParameterException.

        Args:
            message (str, optional): A general error message.
            parameter_name (str, optional): The name of the parameter that caused the error.
            reason (str, optional): A specific reason for the parameter error.
        """
        if message:
            super().__init__(message)
        elif parameter_name and reason:
            super().__init__(f"Parameter '{parameter_name}' is invalid or missing: {reason}")
        elif parameter_name:
            super().__init__(f"Parameter '{parameter_name}' is invalid or missing.")
        else:
            super().__init__("One or more required parameters are invalid or missing.")

        self.parameter_name = parameter_name
        self.reason = reason

    