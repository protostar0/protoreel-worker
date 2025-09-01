#!/usr/bin/env python3
"""
Slack Notification System for ProtoReel Worker.
Reports failed tasks in the last 30 minutes and stuck tasks to Slack channel.
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import quote

# Add the current directory to Python path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import SessionLocal, Task
from video_generator.logging_utils import get_logger

logger = get_logger()

class SlackNotifier:
    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize Slack notifier with webhook URL.
        
        Args:
            webhook_url: Slack webhook URL (defaults to SLACK_WEBHOOK env var)
        """
        self.webhook_url = webhook_url or os.environ.get('SLACK_WEBHOOK')
        self.notify_on_task_creation = os.environ.get('SLACK_NOTIFY_ON_TASK_CREATION', 'true').lower() == 'true'
        
        if not self.webhook_url:
            logger.warning("SLACK_WEBHOOK environment variable not set. Notifications will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"Slack notifier initialized with webhook URL. Task creation notifications: {'enabled' if self.notify_on_task_creation else 'disabled'}")

    def send_message(self, message: str, blocks: Optional[List[Dict]] = None) -> bool:
        """
        Send a message to Slack.
        
        Args:
            message: Text message to send
            blocks: Optional Slack blocks for rich formatting
            
        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("Slack notifier is disabled. Message not sent.")
            return False
            
        try:
            payload = {
                "text": message
            }
            
            if blocks:
                payload["blocks"] = blocks
                
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Slack message sent successfully")
                return True
            else:
                logger.error(f"Failed to send Slack message. Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Slack message: {e}")
            return False

    def get_failed_tasks_last_30min(self) -> List[Dict]:
        """
        Get tasks that failed in the last 30 minutes.
        
        Returns:
            List of failed task dictionaries
        """
        try:
            session = SessionLocal()
            
            # Calculate cutoff time (30 minutes ago)
            cutoff_time = datetime.utcnow() - timedelta(minutes=30)
            
            # Find failed tasks in the last 30 minutes
            failed_tasks = session.query(Task).filter(
                Task.status == 'failed',
                Task.updated_at >= cutoff_time
            ).all()
            
            failed_task_list = []
            for task in failed_tasks:
                failed_task_list.append({
                    'id': task.id,
                    'status': task.status,
                    'error': task.error,
                    'log_uri': task.log_uri,
                    'created_at': task.created_at,
                    'updated_at': task.updated_at,
                    'user_api_key': task.user_api_key
                })
                
            session.close()
            
            logger.info(f"Found {len(failed_task_list)} failed tasks in the last 30 minutes")
            return failed_task_list
            
        except Exception as e:
            logger.error(f"Error getting failed tasks: {e}")
            return []

    def get_stuck_tasks(self, timeout_minutes: int = 30) -> List[Dict]:
        """
        Get tasks stuck in queued or in_progress status for more than specified time.
        
        Args:
            timeout_minutes: Number of minutes after which a task is considered stuck
            
        Returns:
            List of stuck task dictionaries
        """
        try:
            session = SessionLocal()
            
            # Calculate cutoff time
            cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
            
            # Find stuck tasks
            stuck_tasks = session.query(Task).filter(
                Task.status.in_(['queued', 'inprogress']),
                Task.created_at < cutoff_time
            ).all()
            
            stuck_task_list = []
            for task in stuck_tasks:
                stuck_task_list.append({
                    'id': task.id,
                    'status': task.status,
                    'error': task.error,
                    'log_uri': task.log_uri,
                    'created_at': task.created_at,
                    'updated_at': task.updated_at,
                    'user_api_key': task.user_api_key
                })
                
            session.close()
            
            logger.info(f"Found {len(stuck_task_list)} stuck tasks older than {timeout_minutes} minutes")
            return stuck_task_list
            
        except Exception as e:
            logger.error(f"Error getting stuck tasks: {e}")
            return []

    def format_task_info(self, task: Dict) -> str:
        """
        Format task information for Slack message.
        
        Args:
            task: Task dictionary
            
        Returns:
            Formatted task information string
        """
        task_id = task['id']
        status = task['status']
        error = task['error'] or "No error message"
        log_uri = task['log_uri'] or "No log URL"
        created_at = task['created_at'].strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Truncate long error messages
        if len(error) > 200:
            error = error[:200] + "..."
            
        # Format log URL as clickable link if available
        if log_uri and log_uri != "No log URL":
            log_link = f"<{log_uri}|View Logs>"
        else:
            log_link = "No logs available"
            
        return f"• *Task ID:* `{task_id}`\n  *Status:* {status}\n  *Created:* {created_at}\n  *Error:* {error}\n  *Logs:* {log_link}"

    def send_failed_tasks_notification(self) -> bool:
        """
        Send notification about failed tasks in the last 30 minutes.
        
        Returns:
            True if notification sent successfully, False otherwise
        """
        failed_tasks = self.get_failed_tasks_last_30min()
        
        if not failed_tasks:
            logger.info("No failed tasks in the last 30 minutes")
            return True
            
        # Create message
        message = f"🚨 *Failed Tasks Alert*\n{len(failed_tasks)} tasks failed in the last 30 minutes:"
        
        # Create blocks for rich formatting
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 Failed Tasks Alert",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{len(failed_tasks)} tasks failed in the last 30 minutes:*"
                }
            }
        ]
        
        # Add each failed task
        for task in failed_tasks:
            task_info = self.format_task_info(task)
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": task_info
                }
            })
            
        # Add timestamp
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Reported at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                }
            ]
        })
        
        return self.send_message(message, blocks)

    def send_stuck_tasks_notification(self, timeout_minutes: int = 30) -> bool:
        """
        Send notification about stuck tasks.
        
        Args:
            timeout_minutes: Number of minutes after which a task is considered stuck
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        stuck_tasks = self.get_stuck_tasks(timeout_minutes)
        
        if not stuck_tasks:
            logger.info(f"No stuck tasks found (timeout: {timeout_minutes} minutes)")
            return True
            
        # Group tasks by status
        queued_tasks = [task for task in stuck_tasks if task['status'] == 'queued']
        in_progress_tasks = [task for task in stuck_tasks if task['status'] == 'in_progress']
        
        # Create message
        message = f"⚠️ *Stuck Tasks Alert*\n{len(stuck_tasks)} tasks stuck for more than {timeout_minutes} minutes:"
        
        # Create blocks for rich formatting
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "⚠️ Stuck Tasks Alert",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{len(stuck_tasks)} tasks stuck for more than {timeout_minutes} minutes:*"
                }
            }
        ]
        
        # Add queued tasks section
        if queued_tasks:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Queued Tasks ({len(queued_tasks)}):*"
                }
            })
            
            for task in queued_tasks:
                task_info = self.format_task_info(task)
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": task_info
                    }
                })
        
        # Add in_progress tasks section
        if in_progress_tasks:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*In Progress Tasks ({len(in_progress_tasks)}):*"
                }
            })
            
            for task in in_progress_tasks:
                task_info = self.format_task_info(task)
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": task_info
                    }
                })
        
        # Add timestamp
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Reported at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                }
            ]
        })
        
        return self.send_message(message, blocks)

    def send_task_creation_notification(self, task_id: str, user_api_key: str, payload: dict, log_uri: str = None) -> bool:
        """
        Send notification when a new task is created.
        
        Args:
            task_id: The ID of the created task
            user_api_key: The API key of the user who created the task
            payload: The task payload/configuration
            log_uri: Optional log URL for the task
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("Slack notifier is disabled. Task creation notification not sent.")
            return False
            
        if not self.notify_on_task_creation:
            logger.info("Task creation notifications are disabled. Skipping notification.")
            return True
            
        try:
            # Extract useful information from payload
            scenes_count = len(payload.get('scenes', []))
            total_duration = payload.get('total_duration', 'Unknown')
            subtitle_config = payload.get('subtitle_config', {})
            logo_config = payload.get('logo_config', {})
            
            # Create message
            message = f"🎬 *New Task Created*\nTask `{task_id}` has been created and queued for processing."
            
            # Create blocks for rich formatting
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🎬 New Task Created",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Task ID:* `{task_id}`\n*User API Key:* `{user_api_key[:8]}...`\n*Status:* queued"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Scenes:* {scenes_count}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Duration:* {total_duration}s"
                        }
                    ]
                }
            ]
            
            # Add subtitle config if present
            if subtitle_config:
                subtitle_info = []
                if subtitle_config.get('font'):
                    subtitle_info.append(f"Font: {subtitle_config['font']}")
                if subtitle_config.get('font_size'):
                    subtitle_info.append(f"Size: {subtitle_config['font_size']}")
                if subtitle_config.get('position'):
                    subtitle_info.append(f"Position: {subtitle_config['position']}")
                
                if subtitle_info:
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Subtitle Config:* {', '.join(subtitle_info)}"
                        }
                    })
            
            # Add logo config if present
            if logo_config:
                logo_info = []
                if logo_config.get('url'):
                    logo_info.append("Logo URL provided")
                if logo_config.get('position'):
                    logo_info.append(f"Position: {logo_config['position']}")
                if logo_config.get('size'):
                    logo_info.append(f"Size: {logo_config['size']}")
                
                if logo_info:
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Logo Config:* {', '.join(logo_info)}"
                        }
                    })
            
            # Add log URL if available
            if log_uri:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Logs:* <{log_uri}|View Task Logs>"
                    }
                })
            else:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Logs:* Not available yet"
                    }
                })
            
            # Add timestamp
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Created at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    }
                ]
            })
            
            return self.send_message(message, blocks)
            
        except Exception as e:
            logger.error(f"Error sending task creation notification: {e}")
            return False

    def send_task_start_notification(self, task_id: str, user_api_key: str, payload: dict, log_uri: str = None) -> bool:
        """
        Send notification when a task starts processing.
        
        Args:
            task_id: The ID of the task that started
            user_api_key: The API key of the user who created the task
            payload: The task payload/configuration
            log_uri: Optional log URL for the task
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("Slack notifier is disabled. Task start notification not sent.")
            return False
            
        try:
            # Extract useful information from payload
            scenes_count = len(payload.get('scenes', []))
            total_duration = payload.get('total_duration', 'Unknown')
            subtitle_config = payload.get('subtitle_config', {})
            logo_config = payload.get('logo_config', {})
            
            # Create message
            message = f"▶️ *Task Started Processing*\nTask `{task_id}` has started processing."
            
            # Create blocks for rich formatting
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "▶️ Task Started Processing",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Task ID:* `{task_id}`\n*User API Key:* `{user_api_key[:8]}...`\n*Status:* in_progress"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Scenes:* {scenes_count}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Duration:* {total_duration}s"
                        }
                    ]
                }
            ]
            
            # Add subtitle config if present
            if subtitle_config:
                subtitle_info = []
                if subtitle_config.get('font'):
                    subtitle_info.append(f"Font: {subtitle_config['font']}")
                if subtitle_config.get('font_size'):
                    subtitle_info.append(f"Size: {subtitle_config['font_size']}")
                if subtitle_config.get('position'):
                    subtitle_info.append(f"Position: {subtitle_config['position']}")
                
                if subtitle_info:
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Subtitle Config:* {', '.join(subtitle_info)}"
                        }
                    })
            
            # Add logo config if present
            if logo_config:
                logo_info = []
                if logo_config.get('url'):
                    logo_info.append("Logo URL provided")
                if logo_config.get('position'):
                    logo_info.append(f"Position: {logo_config['position']}")
                if logo_config.get('size'):
                    logo_info.append(f"Size: {logo_config['size']}")
                
                if logo_info:
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Logo Config:* {', '.join(logo_info)}"
                        }
                    })
            
            # Add log URL if available
            if log_uri:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Logs:* <{log_uri}|View Task Logs>"
                    }
                })
            else:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Logs:* Not available yet"
                    }
                })
            
            # Add timestamp
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Started at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    }
                ]
            })
            
            return self.send_message(message, blocks)
            
        except Exception as e:
            logger.error(f"Error sending task start notification: {e}")
            return False

    def send_combined_notification(self, timeout_minutes: int = 30) -> Dict:
        """
        Send combined notification about both failed and stuck tasks.
        
        Args:
            timeout_minutes: Number of minutes after which a task is considered stuck
            
        Returns:
            Dictionary with notification results
        """
        failed_tasks = self.get_failed_tasks_last_30min()
        stuck_tasks = self.get_stuck_tasks(timeout_minutes)
        
        if not failed_tasks and not stuck_tasks:
            logger.info("No failed or stuck tasks to report")
            return {
                'failed_tasks_count': 0,
                'stuck_tasks_count': 0,
                'failed_notification_sent': True,
                'stuck_notification_sent': True,
                'error': None
            }
        
        # Send notifications
        failed_sent = self.send_failed_tasks_notification() if failed_tasks else True
        stuck_sent = self.send_stuck_tasks_notification(timeout_minutes) if stuck_tasks else True
        
        result = {
            'failed_tasks_count': len(failed_tasks),
            'stuck_tasks_count': len(stuck_tasks),
            'failed_notification_sent': failed_sent,
            'stuck_notification_sent': stuck_sent,
            'error': None
        }
        
        if not failed_sent or not stuck_sent:
            result['error'] = "Failed to send one or more notifications"
            
        logger.info(f"Combined notification sent: {result}")
        return result

def main():
    """
    Main function to run the Slack notifier.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Send Slack notifications about failed and stuck tasks')
    parser.add_argument('--timeout', type=int, default=30, 
                       help='Timeout in minutes for stuck tasks (default: 30)')
    parser.add_argument('--failed-only', action='store_true',
                       help='Send notification only for failed tasks')
    parser.add_argument('--stuck-only', action='store_true',
                       help='Send notification only for stuck tasks')
    parser.add_argument('--test-creation', action='store_true',
                       help='Send a test task creation notification')
    parser.add_argument('--test-start', action='store_true',
                       help='Send a test task start notification')
    parser.add_argument('--webhook-url', type=str,
                       help='Slack webhook URL (overrides SLACK_WEBHOOK env var)')
    
    args = parser.parse_args()
    
    # Initialize notifier
    notifier = SlackNotifier(args.webhook_url)
    
    if not notifier.enabled:
        logger.error("Slack webhook not configured. Please set SLACK_WEBHOOK environment variable.")
        sys.exit(1)
    
    # Send notifications based on arguments
    if args.test_creation:
        # Send test task creation notification
        test_payload = {
            'scenes': [
                {'type': 'image', 'image_url': 'https://example.com/image1.jpg'},
                {'type': 'video', 'prompt_video': 'A beautiful sunset over mountains'},
                {'type': 'image', 'image_url': 'https://example.com/image2.jpg'}
            ],
            'total_duration': 30,
            'subtitle_config': {
                'font': 'Bangers-Regular.ttf',
                'font_size': 90,
                'position': 'middle',
                'font_color': 'yellow'
            },
            'logo_config': {
                'url': 'https://example.com/logo.png',
                'position': 'top-right',
                'size': 100
            }
        }
        success = notifier.send_task_creation_notification(
            task_id='test-task-creation-123',
            user_api_key='test-api-key-456',
            payload=test_payload,
            log_uri='https://console.cloud.google.com/logs/query?project=test-project'
        )
    elif args.test_start:
        # Send test task start notification
        test_payload = {
            'scenes': [
                {'type': 'image', 'image_url': 'https://example.com/image1.jpg'},
                {'type': 'video', 'prompt_video': 'A beautiful sunset over mountains'},
                {'type': 'image', 'image_url': 'https://example.com/image2.jpg'}
            ],
            'total_duration': 30,
            'subtitle_config': {
                'font': 'Bangers-Regular.ttf',
                'font_size': 90,
                'position': 'middle',
                'font_color': 'yellow'
            },
            'logo_config': {
                'url': 'https://example.com/logo.png',
                'position': 'top-right',
                'size': 100
            }
        }
        success = notifier.send_task_start_notification(
            task_id='test-task-start-123',
            user_api_key='test-api-key-456',
            payload=test_payload,
            log_uri='https://console.cloud.google.com/logs/query?project=test-project'
        )
    elif args.failed_only:
        success = notifier.send_failed_tasks_notification()
    elif args.stuck_only:
        success = notifier.send_stuck_tasks_notification(args.timeout)
    else:
        result = notifier.send_combined_notification(args.timeout)
        success = result['failed_notification_sent'] and result['stuck_notification_sent']
    
    if success:
        logger.info("Slack notifications sent successfully")
        sys.exit(0)
    else:
        logger.error("Failed to send Slack notifications")
        sys.exit(1)

if __name__ == "__main__":
    main() 