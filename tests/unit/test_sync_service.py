"""Basic tests for SyncService to ensure core functionality."""
from unittest.mock import Mock
from jira2solidtime.services.sync_service import SyncService


class TestSyncService:
    """Test SyncService functionality."""

    def test_init(self):
        """Test SyncService initialization with mocked dependencies."""
        # Mock all dependencies
        tempo_client = Mock()
        jira_client = Mock()
        solidtime_client = Mock()
        field_mapper = Mock()
        worklog_mapping = Mock()
        logger = Mock()

        # Create service
        service = SyncService(
            tempo_client=tempo_client,
            jira_client=jira_client,
            solidtime_client=solidtime_client,
            field_mapper=field_mapper,
            worklog_mapping=worklog_mapping,
            logger=logger,
        )

        # Verify initialization
        assert service.tempo_client == tempo_client
        assert service.jira_client == jira_client
        assert service.solidtime_client == solidtime_client
        assert service.field_mapper == field_mapper
        assert service.worklog_mapping == worklog_mapping
        assert service.logger == logger
        assert service.health_checker is not None
