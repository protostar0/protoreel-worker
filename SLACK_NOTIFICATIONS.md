# Slack Notification System

## Overview

The Slack Notification System for ProtoReel Worker automatically reports failed tasks and stuck tasks to a Slack channel using webhooks. This system helps monitor task health and provides real-time alerts for issues that need attention.

## Features

### 🔥 **Failed Tasks Monitoring**
- Reports tasks that failed in the last 30 minutes
- Includes task ID, error message, and log URL
- Real-time alerts for immediate attention

### ⚠️ **Stuck Tasks Monitoring**
- Identifies tasks stuck in `queued` or `in_progress` status
- Configurable timeout (default: 30 minutes)
- Groups tasks by status for better organization

### 🎬 **Task Creation Notifications**
- Sends notifications when new tasks are created
- Includes task ID, user API key, scene count, duration
- Shows subtitle and logo configuration details
- Configurable via environment variable (default: enabled)

### ▶️ **Task Start Notifications**
- Sends notifications when tasks start processing
- Includes task ID, user API key, scene count, duration
- Shows subtitle and logo configuration details
- Automatically integrated into worker processing

### 📊 **Rich Slack Messages**
- Uses Slack Blocks for beautiful formatting
- Clickable log URLs for easy access
- Emojis and structured layout
- Timestamps for tracking

## Setup

### 1. Environment Variables

Set the required environment variables:

```bash
# Required: Slack webhook URL
export SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Optional: Enable/disable task creation notifications (default: true)
export SLACK_NOTIFY_ON_TASK_CREATION="true"
```

### 2. Create Slack Webhook

1. Go to your Slack workspace
2. Navigate to **Apps** → **Incoming Webhooks**
3. Click **Add to Slack**
4. Choose a channel for notifications
5. Copy the webhook URL
6. Set it as the `SLACK_WEBHOOK` environment variable

## Usage

### Command Line Interface

#### Send Combined Notifications
```bash
# Send notifications for both failed and stuck tasks
python slack_notifier.py

# Custom timeout for stuck tasks
python slack_notifier.py --timeout 60

# Custom webhook URL (overrides env var)
python slack_notifier.py --webhook-url "https://hooks.slack.com/services/CUSTOM/URL"
```

#### Send Specific Notifications
```bash
# Failed tasks only
python slack_notifier.py --failed-only

# Stuck tasks only
python slack_notifier.py --stuck-only --timeout 45

# Test task creation notification
python slack_notifier.py --test-creation
```

#### Help
```bash
python slack_notifier.py --help
```

### Programmatic Usage

#### Basic Usage
```python
from slack_notifier import SlackNotifier

# Initialize notifier
notifier = SlackNotifier()

# Send combined notification
result = notifier.send_combined_notification(30)
print(f"Failed tasks: {result['failed_tasks_count']}")
print(f"Stuck tasks: {result['stuck_tasks_count']}")
```

#### Individual Notifications
```python
from slack_notifier import SlackNotifier

notifier = SlackNotifier()

# Send failed tasks notification
failed_sent = notifier.send_failed_tasks_notification()

# Send stuck tasks notification
stuck_sent = notifier.send_stuck_tasks_notification(30)

# Send task creation notification
creation_sent = notifier.send_task_creation_notification(
    task_id='task-123',
    user_api_key='user-api-key',
    payload={'scenes': [], 'total_duration': 30},
    log_uri='https://logs.example.com'
)
```

#### Get Task Data
```python
from slack_notifier import SlackNotifier

notifier = SlackNotifier()

# Get failed tasks from last 30 minutes
failed_tasks = notifier.get_failed_tasks_last_30min()

# Get stuck tasks (timeout: 30 minutes)
stuck_tasks = notifier.get_stuck_tasks(30)

# Process task data
for task in failed_tasks:
    print(f"Task {task['id']}: {task['error']}")
```

## Message Format

### Failed Tasks Alert
```
🚨 Failed Tasks Alert
3 tasks failed in the last 30 minutes:

• Task ID: `abc123-def456`
  Status: failed
  Created: 2025-09-01 12:00:00 UTC
  Error: Captacity subtitle generation failed: Permission denied
  Logs: View Logs

• Task ID: `xyz789-uvw012`
  Status: failed
  Created: 2025-09-01 12:15:00 UTC
  Error: Video processing timeout
  Logs: View Logs

Reported at 2025-09-01 12:30:00 UTC
```

### Task Creation Alert
```
🎬 New Task Created
Task `abc123-def456` has been created and queued for processing.

Task ID: `abc123-def456`
User API Key: `test-api...`
Status: queued

Scenes: 3
Duration: 45s

Subtitle Config: Font: Bangers-Regular.ttf, Size: 90, Position: middle
Logo Config: Logo URL provided, Position: top-right, Size: 100

Logs: View Task Logs

Created at 2025-09-01 12:30:00 UTC
```

### Stuck Tasks Alert
```
⚠️ Stuck Tasks Alert
5 tasks stuck for more than 30 minutes:

Queued Tasks (3):
• Task ID: `task-001`
  Status: queued
  Created: 2025-08-31 15:30:00 UTC
  Error: No error message
  Logs: No logs available

In Progress Tasks (2):
• Task ID: `task-002`
  Status: in_progress
  Created: 2025-08-31 16:00:00 UTC
  Error: No error message
  Logs: View Logs

Reported at 2025-09-01 12:30:00 UTC
```

## Configuration Options

### Timeout Settings
- **Default**: 30 minutes
- **Range**: Any positive integer
- **Usage**: `--timeout 60` or `timeout_minutes=60`

### Error Message Truncation
- **Limit**: 200 characters
- **Format**: Truncated with "..." if longer
- **Example**: "Very long error message..." (truncated)

### Log URL Formatting
- **Available**: Clickable Slack link
- **Missing**: "No logs available"
- **Format**: `<URL|View Logs>`

## Integration Examples

### 1. Cron Job Integration
```bash
# Run every 15 minutes
*/15 * * * * cd /path/to/protoreel-worker && python slack_notifier.py --timeout 30
```

### 2. Docker Integration
```bash
# Run in Docker container
docker exec protoreel-worker python slack_notifier.py --timeout 30
```

### 3. Main Worker Integration
```python
# In main_worker.py
from slack_notifier import SlackNotifier

def process_task():
    try:
        # Process task...
        pass
    except Exception as e:
        # Handle error...
        
        # Send notification about failed task
        notifier = SlackNotifier()
        notifier.send_failed_tasks_notification()
```

### 4. Timeout Checker Integration
```python
# In timeout_checker.py
from slack_notifier import SlackNotifier

def process_stuck_tasks():
    # Update stuck tasks to failed...
    
    # Send notification about stuck tasks
    notifier = SlackNotifier()
    notifier.send_stuck_tasks_notification(30)
```

### 5. Automatic Task Creation Notifications
```python
# Task creation notifications are automatically sent when create_task() is called
# No additional code needed - just set the environment variables:

# Enable notifications (default)
export SLACK_NOTIFY_ON_TASK_CREATION="true"

# Disable notifications
export SLACK_NOTIFY_ON_TASK_CREATION="false"
```

## Error Handling

### Webhook Not Configured
- **Behavior**: Logs warning, disables notifications
- **Action**: Set `SLACK_WEBHOOK` environment variable

### Network Errors
- **Behavior**: Logs error, returns False
- **Retry**: Manual retry required

### Invalid Webhook URL
- **Behavior**: HTTP error response
- **Action**: Check webhook URL format

### Database Errors
- **Behavior**: Logs error, returns empty list
- **Action**: Check database connection

## Testing

### Test Script
```bash
# Run comprehensive tests
python test_slack_notifier.py

# Test task creation notifications
python test_task_creation_notification.py
```

### Manual Testing
```bash
# Test without webhook (will show warnings)
python slack_notifier.py --dry-run

# Test task creation notification
python slack_notifier.py --test-creation

# Test with real webhook
export SLACK_WEBHOOK="your-webhook-url"
python slack_notifier.py
```

## Monitoring

### Log Messages
- **Info**: "Slack message sent successfully"
- **Warning**: "SLACK_WEBHOOK environment variable not set"
- **Error**: "Failed to send Slack message"

### Return Values
```python
{
    'failed_tasks_count': 3,
    'stuck_tasks_count': 5,
    'failed_notification_sent': True,
    'stuck_notification_sent': True,
    'error': None
}
```

## Best Practices

### 1. Environment Variables
- Use environment variables for webhook URLs
- Never commit webhook URLs to version control
- Use different webhooks for different environments

### 2. Notification Frequency
- Don't spam with too frequent notifications
- Use appropriate timeouts (30-60 minutes)
- Consider quiet hours for non-critical alerts

### 3. Error Messages
- Keep error messages concise
- Include relevant context
- Use consistent formatting

### 4. Monitoring
- Monitor notification delivery
- Set up alerts for notification failures
- Track notification patterns

## Troubleshooting

### Common Issues

#### 1. "SLACK_WEBHOOK environment variable not set"
**Solution**: Set the environment variable
```bash
export SLACK_WEBHOOK="your-webhook-url"
```

#### 2. "Failed to send Slack message"
**Solution**: Check webhook URL and network connectivity

#### 3. "No failed or stuck tasks to report"
**Solution**: This is normal when there are no issues

#### 4. Database connection errors
**Solution**: Check database configuration and connectivity

### Debug Mode
```bash
# Enable debug logging
export DEBUG=true
python slack_notifier.py
```

## Security Considerations

### Webhook Security
- Keep webhook URLs private
- Use environment variables
- Rotate webhook URLs periodically
- Monitor webhook usage

### Data Privacy
- Don't include sensitive data in notifications
- Truncate long error messages
- Sanitize user information

### Access Control
- Limit webhook access to necessary channels
- Use dedicated channels for different environments
- Monitor webhook activity

## Future Enhancements

### Planned Features
- [ ] Email notifications as backup
- [ ] Custom notification templates
- [ ] Notification scheduling
- [ ] Alert severity levels
- [ ] Integration with other monitoring tools

### Customization
- [ ] Custom message formatting
- [ ] Multiple webhook support
- [ ] Channel-specific notifications
- [ ] User-specific alerts

---

## Quick Start Checklist

- [ ] Set `SLACK_WEBHOOK` environment variable
- [ ] Test webhook connectivity
- [ ] Configure notification frequency
- [ ] Set up monitoring
- [ ] Test with real data
- [ ] Document team procedures

Your Slack notification system is ready to monitor task health! 🚀 