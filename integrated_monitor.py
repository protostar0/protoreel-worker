#!/usr/bin/env python3
"""
Integrated Monitor for ProtoReel Worker.
Combines timeout checker and Slack notifications for comprehensive task monitoring.
"""

import os
import sys
import time
from datetime import datetime

# Add the current directory to Python path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from timeout_checker import process_stuck_tasks
from slack_notifier import SlackNotifier
from video_generator.logging_utils import get_logger

logger = get_logger()

class IntegratedMonitor:
    def __init__(self, timeout_minutes: int = 30, slack_webhook: str = None):
        """
        Initialize integrated monitor.
        
        Args:
            timeout_minutes: Timeout for stuck tasks
            slack_webhook: Slack webhook URL (optional)
        """
        self.timeout_minutes = timeout_minutes
        self.slack_notifier = SlackNotifier(slack_webhook)
        logger.info(f"Integrated monitor initialized with {timeout_minutes} minute timeout")

    def run_monitoring_cycle(self) -> dict:
        """
        Run a complete monitoring cycle.
        
        Returns:
            Dictionary with monitoring results
        """
        logger.info("Starting monitoring cycle")
        
        # Step 1: Process stuck tasks (update to failed)
        logger.info("Step 1: Processing stuck tasks...")
        timeout_result = process_stuck_tasks(
            self.timeout_minutes, 
            "Timeout error: Task exceeded maximum processing time"
        )
        
        # Step 2: Send Slack notifications
        logger.info("Step 2: Sending Slack notifications...")
        slack_result = self.slack_notifier.send_combined_notification(self.timeout_minutes)
        
        # Combine results
        result = {
            'timestamp': datetime.utcnow().isoformat(),
            'timeout_processing': timeout_result,
            'slack_notifications': slack_result,
            'summary': {
                'stuck_tasks_processed': timeout_result.get('successfully_updated', 0),
                'failed_tasks_reported': slack_result.get('failed_tasks_count', 0),
                'stuck_tasks_reported': slack_result.get('stuck_tasks_count', 0),
                'notifications_sent': (
                    slack_result.get('failed_notification_sent', False) and 
                    slack_result.get('stuck_notification_sent', False)
                )
            }
        }
        
        logger.info(f"Monitoring cycle completed: {result['summary']}")
        return result

    def run_continuous_monitoring(self, interval_minutes: int = 15, max_cycles: int = None):
        """
        Run continuous monitoring with specified interval.
        
        Args:
            interval_minutes: Interval between monitoring cycles
            max_cycles: Maximum number of cycles (None for infinite)
        """
        logger.info(f"Starting continuous monitoring (interval: {interval_minutes} minutes)")
        
        cycle_count = 0
        while max_cycles is None or cycle_count < max_cycles:
            try:
                cycle_count += 1
                logger.info(f"Running monitoring cycle {cycle_count}")
                
                result = self.run_monitoring_cycle()
                
                # Log summary
                summary = result['summary']
                logger.info(
                    f"Cycle {cycle_count} summary: "
                    f"Processed {summary['stuck_tasks_processed']} stuck tasks, "
                    f"Reported {summary['failed_tasks_reported']} failed tasks, "
                    f"Reported {summary['stuck_tasks_reported']} stuck tasks"
                )
                
                # Wait for next cycle
                if max_cycles is None or cycle_count < max_cycles:
                    logger.info(f"Waiting {interval_minutes} minutes until next cycle...")
                    time.sleep(interval_minutes * 60)
                    
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring cycle {cycle_count}: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
                
        logger.info(f"Continuous monitoring completed after {cycle_count} cycles")

def main():
    """
    Main function for integrated monitor.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Integrated task monitoring with Slack notifications')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Timeout in minutes for stuck tasks (default: 30)')
    parser.add_argument('--interval', type=int, default=15,
                       help='Interval in minutes between monitoring cycles (default: 15)')
    parser.add_argument('--max-cycles', type=int, default=None,
                       help='Maximum number of monitoring cycles (default: infinite)')
    parser.add_argument('--single-cycle', action='store_true',
                       help='Run only one monitoring cycle')
    parser.add_argument('--webhook-url', type=str,
                       help='Slack webhook URL (overrides SLACK_WEBHOOK env var)')
    
    args = parser.parse_args()
    
    # Initialize monitor
    monitor = IntegratedMonitor(args.timeout, args.webhook_url)
    
    if args.single_cycle:
        # Run single cycle
        result = monitor.run_monitoring_cycle()
        print(f"Monitoring cycle completed: {result['summary']}")
    else:
        # Run continuous monitoring
        monitor.run_continuous_monitoring(args.interval, args.max_cycles)

if __name__ == "__main__":
    main() 