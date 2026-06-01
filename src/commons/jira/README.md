# commons.jira

A unified JIRA client for Red Hat projects with support for both Atlassian Cloud and on-premise JIRA instances.

## Installation

```bash
pip install py-commons
```

The JIRA library requires the `jira` package:

```bash
pip install jira>=3.0.0
```

## Quick Start

### Atlassian Cloud Authentication

For Atlassian Cloud (e.g., `yourcompany.atlassian.net`), you need an API token:

1. Generate an API token at: https://id.atlassian.com/manage/api-tokens
2. Use your email and API token for authentication:

```python
from commons.jira import JiraClient

client = JiraClient(
    server="https://yourcompany.atlassian.net",
    email="you@example.com",
    api_token="your-api-token"
)
```

## Usage Examples

### Querying Issues

**Custom JQL Query**
```python
# Query with custom JQL
issues = client.query_issues(
    jql='project = MYPROJECT AND status = "In Progress" AND assignee = currentUser()',
    max_results=50
)

for issue in issues:
    print(f"{issue.key}: {issue.fields.summary}")
```

**Query by Status**
```python
# Get all open bugs in a project
bugs = client.get_issues_by_status(
    project="MYPROJECT",
    status="Open",
    component="Backend"  # Optional component filter
)
```

**Query by Label**
```python
# Get all issues with a specific label
issues = client.get_issues_by_label(
    project="MYPROJECT",
    label="needs-review"
)
```

### Working with Issues

**Get Field Values**
```python
# Get built-in field values
summary = client.get_field_value(issue, "summary")
description = client.get_field_value(issue, "description")
assignee = client.get_field_value(issue, "assignee")

# Get custom field values by name
priority_score = client.get_field_value(issue, "Priority Score")
```

**Add/Remove Labels**
```python
# Add a label
client.add_label(issue, "urgent")

# Remove a label
client.remove_label(issue, "needs-review")
```

**Add Comments**
```python
client.add_comment(issue, "This issue has been reviewed and approved.")
```

**Transition Issues**
```python
# Move issue to a new status
client.transition_issue(issue, "Done")

# Check available transitions first
transitions = client.get_available_transitions(issue)
for t in transitions:
    print(f"{t['name']} (ID: {t['id']})")
```

**Create Issues**
```python
new_issue = client.create_issue(
    project="MYPROJECT",
    summary="Bug: Application crashes on startup",
    description="Detailed description of the bug...",
    issue_type="Bug",
    component="Frontend",
    labels=["critical", "regression"]
)

print(f"Created issue: {new_issue.key}")
```
## License

See [LICENSE](../../../LICENSE) for details.
