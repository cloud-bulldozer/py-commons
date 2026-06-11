"""Exceptions for inference client operations"""


class InferenceClientError(Exception):
    """Base exception for inference client errors"""


class InferenceAPIError(InferenceClientError):
    """Inference API is unavailable or returns an error"""


class InferenceIterationLimitError(InferenceClientError):
    """Exceeds maximum iterations"""
