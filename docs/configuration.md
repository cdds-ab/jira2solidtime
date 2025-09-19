# Configuration Guide

## Sync Scheduling Configuration

The jira2solidtime application supports external configuration of sync schedules through environment variables. This allows you to customize when and how often sync operations run without modifying Docker Compose files.

### Environment Variables

Add these variables to your `.env` file:

```bash
# Sync schedule: cron format "minute hour day-of-month month day-of-week"
# Default: Every 10 minutes during business hours (6 AM - 10 PM)
SYNC_SCHEDULE=0 */10 6-22 * * *

# Health check schedule: cron format
# Default: Every minute for health monitoring
HEALTH_CHECK_SCHEDULE=0 */1 * * * *

# Alert thresholds (in seconds)
# How long to wait before alerting about missing sync during business hours
SYNC_ALERT_THRESHOLD=900

# Business hours for sync operations (24-hour format)
SYNC_START_HOUR=6
SYNC_END_HOUR=22
```

### Schedule Examples

#### Business Hours Only
```bash
# Every 10 minutes from 6 AM to 10 PM
SYNC_SCHEDULE=0 */10 6-22 * * *
```

#### 24/7 Operation
```bash
# Every 15 minutes, all day
SYNC_SCHEDULE=0 */15 * * * *
```

#### Workdays Only
```bash
# Every 10 minutes, Monday to Friday, 8 AM to 6 PM
SYNC_SCHEDULE=0 */10 8-18 * * 1-5
```

#### Hourly Sync
```bash
# Every hour at minute 0
SYNC_SCHEDULE=0 0 * * * *
```

### Alert Configuration

When you change the sync schedule, you should also update the alert thresholds:

- **SYNC_ALERT_THRESHOLD**: Set this to be longer than your sync interval
  - For 10-minute syncs: 900 seconds (15 minutes)
  - For 15-minute syncs: 1200 seconds (20 minutes)
  - For hourly syncs: 4200 seconds (70 minutes)

### Applying Configuration Changes

1. Update your `.env` file with the desired values
2. Generate new alert rules:
   ```bash
   ./scripts/generate-alert-rules.sh
   ```
3. Restart the Docker Compose stack:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### Cron Format Reference

```
 ┌───────────── minute (0-59)
 │ ┌───────────── hour (0-23)
 │ │ ┌───────────── day of month (1-31)
 │ │ │ ┌───────────── month (1-12)
 │ │ │ │ ┌───────────── day of week (0-6) (Sunday = 0)
 │ │ │ │ │
 * * * * *
```

### Common Patterns

- `*/10`: Every 10 units (minutes, hours)
- `8-18`: Range from 8 to 18 (inclusive)
- `1-5`: Monday to Friday
- `0,30`: At minute 0 and 30 (twice per hour)

### Monitoring

The application exposes these metrics for monitoring:

- `jira2solidtime_last_sync_timestamp`: Unix timestamp of last successful sync
- `jira2solidtime_sync_success`: 1 if last sync was successful, 0 if failed
- `jira2solidtime_sync_duration_seconds`: Duration of last sync operation

Alerts are configured to trigger based on:
- Sync failures (critical)
- Slow sync operations (warning > 15s, critical > 30s)
- Missing syncs during business hours (warning)
- API service failures (critical)