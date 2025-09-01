#!/usr/bin/env python3
"""
Test script for Slack Notifier System.
Demonstrates how to use the Slack notifier to send notifications.
"""

import os
import sys
from slack_notifier import SlackNotifier

def test_slack_notifier():
    """
    Test the Slack notifier functionality.
    """
    print("🧪 Testing Slack Notifier System")
    print("=" * 50)
    
    # Initialize notifier
    notifier = SlackNotifier()
    
    if not notifier.enabled:
        print("❌ SLACK_WEBHOOK environment variable not set")
        print("   To test with a real webhook, set the environment variable:")
        print("   export SLACK_WEBHOOK='https://hooks.slack.com/services/YOUR/WEBHOOK/URL'")
        return False
    
    print("✅ Slack notifier initialized successfully")
    
    # Test getting failed tasks
    print("\n📊 Checking for failed tasks in the last 30 minutes...")
    failed_tasks = notifier.get_failed_tasks_last_30min()
    print(f"   Found {len(failed_tasks)} failed tasks")
    
    # Test getting stuck tasks
    print("\n📊 Checking for stuck tasks (timeout: 30 minutes)...")
    stuck_tasks = notifier.get_stuck_tasks(30)
    print(f"   Found {len(stuck_tasks)} stuck tasks")
    
    # Test sending notifications
    print("\n📤 Testing notification sending...")
    
    if failed_tasks or stuck_tasks:
        result = notifier.send_combined_notification(30)
        print(f"   Combined notification result: {result}")
        
        if result['failed_notification_sent'] and result['stuck_notification_sent']:
            print("✅ All notifications sent successfully!")
            return True
        else:
            print("❌ Some notifications failed to send")
            return False
    else:
        print("ℹ️  No failed or stuck tasks to report")
        return True

def test_individual_notifications():
    """
    Test individual notification types.
    """
    print("\n🧪 Testing Individual Notifications")
    print("=" * 50)
    
    notifier = SlackNotifier()
    
    if not notifier.enabled:
        print("❌ Cannot test without webhook URL")
        return False
    
    # Test failed tasks notification
    print("\n📤 Testing failed tasks notification...")
    failed_sent = notifier.send_failed_tasks_notification()
    print(f"   Failed tasks notification: {'✅ Sent' if failed_sent else '❌ Failed'}")
    
    # Test stuck tasks notification
    print("\n📤 Testing stuck tasks notification...")
    stuck_sent = notifier.send_stuck_tasks_notification(30)
    print(f"   Stuck tasks notification: {'✅ Sent' if stuck_sent else '❌ Failed'}")
    
    return failed_sent and stuck_sent

def test_message_formatting():
    """
    Test message formatting functionality.
    """
    print("\n🧪 Testing Message Formatting")
    print("=" * 50)
    
    notifier = SlackNotifier()
    
    # Test task info formatting
    from datetime import datetime
    test_task = {
        'id': 'test-task-123',
        'status': 'failed',
        'error': 'This is a test error message that should be truncated if it gets too long',
        'log_uri': 'https://console.cloud.google.com/logs/query?project=test-project',
        'created_at': datetime(2025, 9, 1, 12, 0, 0),
        'updated_at': datetime(2025, 9, 1, 12, 30, 0),
        'user_api_key': 'test-api-key'
    }
    
    formatted_info = notifier.format_task_info(test_task)
    print("📝 Formatted task info:")
    print(formatted_info)
    
    return True

if __name__ == "__main__":
    print("🚀 Slack Notifier Test Suite")
    print("=" * 60)
    
    # Run tests
    test1 = test_slack_notifier()
    test2 = test_individual_notifications()
    test3 = test_message_formatting()
    
    print("\n📋 Test Results Summary")
    print("=" * 30)
    print(f"Main functionality test: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Individual notifications: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"Message formatting: {'✅ PASS' if test3 else '❌ FAIL'}")
    
    if test1 and test2 and test3:
        print("\n🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        sys.exit(1) 