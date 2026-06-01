# py-commons

A collection of shared Python libraries for Red Hat tools and automation.

## Libraries

### commons.jira

A unified JIRA client for Red Hat projects with support for both Atlassian Cloud and on-premise instances.

**Features:**
- Unified authentication for Cloud (email + API token) and on-premise (username/password or token)
- Automatic retry logic with exponential backoff
- Common query patterns (by status, label, custom JQL)
- Issue management (create, update, transition, labels, comments)
- Custom field support
- Comprehensive error handling

See [jira documentation](src/commons/jira/README.md) for detailed usage.

## Installation

Install from PyPI:

```bash
pip install py-commons
```

Or install from source:

```bash
git clone https://github.com/redhat-performance/py-commons.git
cd py-commons
pip install -e .
```

## Usage

```python
from commons.jira import JiraClient

# Connect to Atlassian Cloud
client = JiraClient(
    server="https://yourcompany.atlassian.net",
    email="you@example.com",
    api_token="your-api-token"
)

# Query issues
issues = client.query_issues("project = MYPROJECT AND status = 'In Progress'")

# Get issues by status
bugs = client.get_issues_by_status("MYPROJECT", "Open")

# Add label to issue
client.add_label(issues[0], "needs-review")
```

## License

See [LICENSE](LICENSE) for details.
