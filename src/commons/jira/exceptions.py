"""Custom exceptions for JIRA client"""


class JiraClientError(Exception):
    """Base exception for JIRA client errors"""


class JiraAuthError(JiraClientError):
    """Authentication failed"""


class JiraQueryError(JiraClientError):
    """Query execution failed"""


class JiraUpdateError(JiraClientError):
    """Update operation failed"""
