"""JIRA client for interacting with JIRA issues

Unified client supporting both Atlassian Cloud and on-premise JIRA instances.
Includes retry logic, error handling, and common query patterns.
"""

import logging
import time
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode

try:
    from jira import JIRA
    from jira.resources import Issue
    from jira.exceptions import JIRAError
    JIRA_AVAILABLE = True
except ImportError:
    JIRA_AVAILABLE = False
    JIRA = None
    Issue = None
    JIRAError = Exception

from .exceptions import JiraAuthError, JiraQueryError, JiraUpdateError

logger = logging.getLogger(__name__)


class JiraClient:
    """Client for JIRA operations with retry logic and error handling"""

    def __init__(
        self,
        server: str,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: int = 2,
    ):
        """Initialize JIRA client

        Args:
            server: JIRA server URL
            email: JIRA email (for Atlassian Cloud token auth)
            api_token: JIRA API token (for Atlassian Cloud)
            username: JIRA username (for on-premise basic auth)
            password: JIRA password (for on-premise basic auth)
            max_retries: Maximum number of retry attempts for failed operations
            retry_delay: Delay in seconds between retries

        Raises:
            ImportError: If jira library is not installed
            JiraAuthError: If authentication fails or credentials are invalid
        """
        if not JIRA_AVAILABLE:
            raise ImportError(
                "jira library not installed. Install with: pip install jira"
            )

        self.server = server
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Detect if this is Atlassian Cloud or on-premise
        is_cloud = "atlassian.net" in server.lower()

        try:
            if is_cloud:
                # Atlassian Cloud requires email + API token
                if email and api_token:
                    logger.debug("Using Atlassian Cloud auth (email + API token)")
                    self.jira = JIRA(server=server, basic_auth=(email, api_token))
                    logger.info("Connected to Atlassian Cloud JIRA: %s", server)
                else:
                    raise JiraAuthError(
                        "Atlassian Cloud requires both 'email' and 'api_token'. "
                        "Generate an API token at: https://id.atlassian.com/manage/api-tokens"
                    )
            else:
                # On-premise supports: (email, api_token), api_token alone, or (username, password)
                if email and api_token:
                    logger.debug("Using token auth with email for on-premise JIRA")
                    self.jira = JIRA(server=server, basic_auth=(email, api_token))
                    logger.info("Connected to JIRA using API token: %s", server)
                elif api_token and not email:
                    logger.debug("Using token-only auth for on-premise JIRA")
                    self.jira = JIRA(server=server, token_auth=api_token)
                    logger.info("Connected to JIRA using token-only auth: %s", server)
                elif username and password:
                    logger.debug("Using username/password auth for on-premise JIRA")
                    self.jira = JIRA(server=server, basic_auth=(username, password))
                    logger.info("Connected to JIRA using username/password: %s", server)
                else:
                    raise JiraAuthError(
                        "Must provide one of: (email, api_token), api_token alone, "
                        "or (username, password)"
                    )
        except JIRAError as e:
            raise JiraAuthError(f"Failed to connect to JIRA: {e}") from e

    def _retry_operation(self, operation, *args, **kwargs):
        """Retry an operation with exponential backoff

        Args:
            operation: Function to retry
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation

        Returns:
            Result of operation

        Raises:
            Last exception encountered if all retries fail
        """
        last_exception = None
        attempts = max(1, self.max_retries)
        for attempt in range(attempts):
            try:
                return operation(*args, **kwargs)
            except JIRAError as e:
                last_exception = e
                if attempt < attempts - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        "Operation failed (attempt %d/%d): %s. Retrying in %ds...",
                        attempt + 1, attempts, e, delay
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "Operation failed after %d attempts: %s",
                        attempts, e
                    )

        raise last_exception

    def query_issues(
        self, jql: str, max_results: int = 100, fields: Optional[str] = None
    ) -> List[Issue]:
        """Query JIRA issues using JQL with retry logic

        Args:
            jql: JQL query string
            max_results: Maximum number of results to return
            fields: Comma-separated list of fields to retrieve (None = all fields)

        Returns:
            List of JIRA issues

        Raises:
            JiraQueryError: If query fails after retries
        """
        logger.info("Querying JIRA with JQL: %s", jql)

        # Construct the full URL for debugging
        params = {"jql": jql, "maxResults": max_results}
        if fields:
            params["fields"] = fields
        query_string = urlencode(params)
        full_url = f"{self.server}/rest/api/2/search?{query_string}"

        # Log for debugging
        logger.debug("=" * 80)
        logger.debug("JIRA Query URL: %s", full_url)
        logger.debug("=" * 80)

        try:
            issues = self._retry_operation(
                self.jira.search_issues,
                jql,
                maxResults=max_results,
                fields=fields
            )
            logger.info("Found %d issues", len(issues))
            return issues
        except Exception as e:
            raise JiraQueryError(f"Failed to query JIRA: {e}") from e

    def query_custom(self, jql: str, max_results: int = 100) -> List[Issue]:
        """Query JIRA issues using custom JQL (alias for query_issues)

        Args:
            jql: JQL query string
            max_results: Maximum number of results to return

        Returns:
            List of JIRA issues
        """
        return self.query_issues(jql, max_results)

    def get_issues_by_status(
        self, project: str, status: str, component: Optional[str] = None
    ) -> List[Issue]:
        """Get issues by project and status

        Args:
            project: JIRA project key
            status: Issue status
            component: Optional component filter

        Returns:
            List of JIRA issues
        """
        escaped_status = status.replace('"', '\\"')
        jql = f'project = {project} AND status = "{escaped_status}"'
        if component:
            escaped_component = component.replace('"', '\\"')
            jql += f' AND component = "{escaped_component}"'
        return self.query_issues(jql)

    def get_issues_by_label(
        self, project: str, label: str, component: Optional[str] = None
    ) -> List[Issue]:
        """Get issues by project and label

        Args:
            project: JIRA project key
            label: Issue label
            component: Optional component filter

        Returns:
            List of JIRA issues
        """
        escaped_label = label.replace('"', '\\"')
        jql = f'project = {project} AND labels = "{escaped_label}"'
        if component:
            escaped_component = component.replace('"', '\\"')
            jql += f' AND component = "{escaped_component}"'
        return self.query_issues(jql)

    def get_field_value(self, issue: Issue, field_name: str) -> Optional[Any]:
        """Get field value from issue (built-in or custom fields)

        Args:
            issue: JIRA issue
            field_name: Field name (e.g., 'description', 'summary', or custom field name)

        Returns:
            Field value or None if not found
        """
        # Handle built-in fields
        field_name_lower = field_name.lower()
        if field_name_lower == "description":
            return getattr(issue.fields, "description", None)
        if field_name_lower == "summary":
            return getattr(issue.fields, "summary", None)
        if field_name_lower == "status":
            status = getattr(issue.fields, "status", None)
            return status.name if status else None
        if field_name_lower == "assignee":
            assignee = getattr(issue.fields, "assignee", None)
            return assignee.displayName if assignee else None

        # Handle custom fields - search by name
        try:
            fields = self._retry_operation(self.jira.fields)
        except Exception as e:
            raise JiraQueryError(f"Failed to fetch JIRA fields: {e}") from e

        for field in fields:
            if field["name"].lower() == field_name_lower:
                return getattr(issue.fields, field["id"], None)

        logger.warning("Field '%s' not found in issue %s", field_name, issue.key)
        return None

    def add_label(self, issue: Issue, label: str):
        """Add label to issue with retry logic

        Args:
            issue: JIRA issue
            label: Label to add

        Raises:
            JiraUpdateError: If update fails after retries
        """
        try:
            current_labels = list(issue.fields.labels or [])
            if label not in current_labels:
                updated_labels = [*current_labels, label]
                self._retry_operation(issue.update, fields={"labels": updated_labels})
                issue.fields.labels = updated_labels
                logger.info("Added label '%s' to %s", label, issue.key)
            else:
                logger.debug("Label '%s' already exists on %s", label, issue.key)
        except Exception as e:
            raise JiraUpdateError(f"Failed to add label to {issue.key}: {e}") from e

    def remove_label(self, issue: Issue, label: str):
        """Remove label from issue

        Args:
            issue: JIRA issue
            label: Label to remove

        Raises:
            JiraUpdateError: If update fails after retries
        """
        try:
            current_labels = list(issue.fields.labels or [])
            if label in current_labels:
                updated_labels = [lbl for lbl in current_labels if lbl != label]
                self._retry_operation(issue.update, fields={"labels": updated_labels})
                issue.fields.labels = updated_labels
                logger.info("Removed label '%s' from %s", label, issue.key)
            else:
                logger.debug("Label '%s' not found on %s", label, issue.key)
        except Exception as e:
            raise JiraUpdateError(f"Failed to remove label from {issue.key}: {e}") from e

    def transition_issue(self, issue: Issue, transition_name: str):
        """Transition issue to new status

        Args:
            issue: JIRA issue
            transition_name: Name of transition (e.g., 'Done', 'In Progress')

        Raises:
            JiraUpdateError: If transition fails or is not found
        """
        try:
            transitions = self._retry_operation(self.jira.transitions, issue)
            transition_id = None

            for t in transitions:
                if t["name"].lower() == transition_name.lower():
                    transition_id = t["id"]
                    break

            if transition_id:
                self._retry_operation(self.jira.transition_issue, issue, transition_id)
                logger.info("Transitioned %s to '%s'", issue.key, transition_name)
            else:
                available = [t["name"] for t in transitions]
                raise JiraUpdateError(
                    f"Transition '{transition_name}' not found for {issue.key}. "
                    f"Available transitions: {available}"
                )
        except JiraUpdateError:
            raise
        except Exception as e:
            raise JiraUpdateError(f"Failed to transition {issue.key}: {e}") from e

    def add_comment(self, issue: Issue, comment: str):
        """Add comment to issue

        Args:
            issue: JIRA issue
            comment: Comment text

        Raises:
            JiraUpdateError: If comment fails to add
        """
        try:
            self._retry_operation(self.jira.add_comment, issue, comment)
            logger.info("Added comment to %s", issue.key)
        except Exception as e:
            raise JiraUpdateError(f"Failed to add comment to {issue.key}: {e}") from e

    def create_issue(
        self,
        project: str,
        summary: str,
        description: str,
        issue_type: str = "Bug",
        component: Optional[str] = None,
        labels: Optional[List[str]] = None,
        **extra_fields
    ) -> Issue:
        """Create a new JIRA issue

        Args:
            project: JIRA project key
            summary: Issue summary/title
            description: Issue description
            issue_type: Issue type (e.g., 'Bug', 'Task', 'Story')
            component: Optional component name
            labels: Optional list of labels
            **extra_fields: Additional fields to set

        Returns:
            Created JIRA issue

        Raises:
            JiraUpdateError: If issue creation fails
        """
        try:
            fields = {
                "project": {"key": project},
                "summary": summary,
                "description": description,
                "issuetype": {"name": issue_type},
            }

            if component:
                fields["components"] = [{"name": component}]

            if labels:
                fields["labels"] = labels

            # Add any extra fields
            fields.update(extra_fields)

            issue = self._retry_operation(self.jira.create_issue, fields=fields)
            logger.info("Created issue %s: %s", issue.key, summary)
            return issue
        except Exception as e:
            raise JiraUpdateError(f"Failed to create issue: {e}") from e

    def get_available_transitions(self, issue: Issue) -> List[Dict[str, str]]:
        """Get available transitions for an issue

        Args:
            issue: JIRA issue

        Returns:
            List of transition dictionaries with 'id' and 'name' keys

        Raises:
            JiraUpdateError: If fetching transitions fails
        """
        try:
            return self._retry_operation(self.jira.transitions, issue)
        except Exception as e:
            raise JiraUpdateError(
                f"Failed to get transitions for {issue.key}: {e}"
            ) from e
