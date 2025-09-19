"""Basic tests for IssueComparator to ensure functionality."""

from jira2solidtime.sync.issue_comparator import IssueComparator


class TestIssueComparator:
    """Test IssueComparator functionality."""

    def test_init(self):
        """Test IssueComparator initialization."""
        comparator = IssueComparator()
        assert comparator is not None
        assert comparator.worklog_mapping is not None

    def test_group_tempo_worklogs_by_issue_empty(self):
        """Test grouping empty tempo worklogs."""
        comparator = IssueComparator()
        result = comparator.group_tempo_worklogs_by_issue([])
        assert result == {}

    def test_group_solidtime_entries_by_issue_empty(self):
        """Test grouping empty solidtime entries."""
        comparator = IssueComparator()
        result = comparator.group_solidtime_entries_by_issue([])
        assert result == {}

    def test_find_issues_to_sync_empty(self):
        """Test finding issues to sync with empty data."""
        comparator = IssueComparator()
        result = comparator.find_issues_to_sync({}, {})
        assert result == set()
