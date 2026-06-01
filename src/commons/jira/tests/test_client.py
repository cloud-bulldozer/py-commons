"""Tests for JIRA client"""

import unittest
from unittest.mock import MagicMock, Mock, patch

from commons.jira.client import JiraClient
from commons.jira.exceptions import JiraAuthError, JiraUpdateError


class TestJiraClient(unittest.TestCase):
    """Test JIRA client functionality"""

    @patch('commons.jira.client.JIRA')
    def test_init_with_email_and_token(self, mock_jira):
        """Test initialization with email and API token"""
        client = JiraClient(
            server="https://redhat.atlassian.net",
            email="test@example.com",
            api_token="test_token"
        )

        self.assertIsNotNone(client)
        mock_jira.assert_called_once_with(
            server="https://redhat.atlassian.net",
            basic_auth=("test@example.com", "test_token")
        )

    @patch('commons.jira.client.JIRA')
    def test_init_with_username_and_password(self, mock_jira):
        """Test initialization with username and password"""
        client = JiraClient(
            server="https://jira.example.com",
            username="testuser",
            password="testpass"
        )

        self.assertIsNotNone(client)
        mock_jira.assert_called_once_with(
            server="https://jira.example.com",
            basic_auth=("testuser", "testpass")
        )

    @patch('commons.jira.client.JIRA')
    def test_init_without_credentials_raises_error(self, mock_jira):  # pylint: disable=unused-argument
        """Test that missing credentials raises JiraAuthError"""
        with self.assertRaises(JiraAuthError):
            JiraClient(server="https://jira.example.com")

    @patch('commons.jira.client.JIRA')
    def test_query_issues(self, mock_jira):
        """Test querying issues with JQL"""
        mock_instance = MagicMock()
        mock_jira.return_value = mock_instance

        mock_issues = [Mock(), Mock(), Mock()]
        mock_instance.search_issues.return_value = mock_issues

        client = JiraClient(
            server="https://jira.example.com",
            username="test",
            password="test"
        )

        issues = client.query_issues("project = TEST", max_results=10)

        self.assertEqual(len(issues), 3)
        mock_instance.search_issues.assert_called_once_with(
            "project = TEST",
            maxResults=10,
            fields=None
        )

    @patch('commons.jira.client.JIRA')
    def test_get_issues_by_status(self, mock_jira):
        """Test getting issues by status"""
        mock_instance = MagicMock()
        mock_jira.return_value = mock_instance
        mock_instance.search_issues.return_value = []

        client = JiraClient(
            server="https://jira.example.com",
            username="test",
            password="test"
        )

        client.get_issues_by_status("TEST", "New", component="TestComponent")

        # Verify the JQL was constructed correctly with quoted component
        call_args = mock_instance.search_issues.call_args
        jql = call_args[0][0]
        self.assertIn("project = TEST", jql)
        self.assertIn('status = "New"', jql)
        self.assertIn('component = "TestComponent"', jql)

    @patch('commons.jira.client.JIRA')
    def test_add_label(self, mock_jira):
        """Test adding a label to an issue"""
        mock_instance = MagicMock()
        mock_jira.return_value = mock_instance

        client = JiraClient(
            server="https://jira.example.com",
            username="test",
            password="test"
        )

        mock_issue = Mock()
        mock_issue.fields.labels = ["existing_label"]
        mock_issue.update = Mock()

        client.add_label(mock_issue, "new_label")

        mock_issue.update.assert_called_once()
        call_args = mock_issue.update.call_args
        self.assertIn("new_label", call_args[1]["fields"]["labels"])
        self.assertIn("existing_label", call_args[1]["fields"]["labels"])

    @patch('commons.jira.client.JIRA')
    def test_transition_issue(self, mock_jira):
        """Test transitioning an issue"""
        mock_instance = MagicMock()
        mock_jira.return_value = mock_instance

        client = JiraClient(
            server="https://jira.example.com",
            username="test",
            password="test"
        )

        mock_issue = Mock()
        mock_issue.key = "TEST-123"

        mock_instance.transitions.return_value = [
            {"id": "1", "name": "To Do"},
            {"id": "2", "name": "Done"}
        ]

        client.transition_issue(mock_issue, "Done")

        mock_instance.transition_issue.assert_called_once_with(mock_issue, "2")

    @patch('commons.jira.client.JIRA')
    def test_transition_issue_not_found(self, mock_jira):
        """Test transitioning to a non-existent transition raises error"""
        mock_instance = MagicMock()
        mock_jira.return_value = mock_instance

        client = JiraClient(
            server="https://jira.example.com",
            username="test",
            password="test"
        )

        mock_issue = Mock()
        mock_issue.key = "TEST-123"

        mock_instance.transitions.return_value = [
            {"id": "1", "name": "To Do"}
        ]

        with self.assertRaises(JiraUpdateError):
            client.transition_issue(mock_issue, "NonExistent")

    @patch('commons.jira.client.JIRA')
    def test_add_comment(self, mock_jira):
        """Test adding a comment to an issue"""
        mock_instance = MagicMock()
        mock_jira.return_value = mock_instance

        client = JiraClient(
            server="https://jira.example.com",
            username="test",
            password="test"
        )

        mock_issue = Mock()
        client.add_comment(mock_issue, "Test comment")

        mock_instance.add_comment.assert_called_once_with(mock_issue, "Test comment")

    @patch('commons.jira.client.JIRA')
    def test_get_field_value_builtin(self, mock_jira):
        """Test getting built-in field values"""
        mock_instance = MagicMock()
        mock_jira.return_value = mock_instance

        client = JiraClient(
            server="https://jira.example.com",
            username="test",
            password="test"
        )

        mock_issue = Mock()
        mock_issue.fields.description = "Test description"
        mock_issue.fields.summary = "Test summary"

        self.assertEqual(client.get_field_value(mock_issue, "description"), "Test description")
        self.assertEqual(client.get_field_value(mock_issue, "summary"), "Test summary")


if __name__ == "__main__":
    unittest.main()
