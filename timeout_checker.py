#!/usr/bin/env python3
"""
Timeout Checker Script for ProtoReel Worker.
Checks for tasks that have been stuck in queued or in_progress status for more than 30 minutes
and updates them to failed status with timeout error.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import List, Optional

# Add the current directory to Python path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import SessionLocal, Task
from video_generator.logging_utils import get_logger

logger = get_logger()

def check_stuck_tasks(timeout_minutes: int = 30) -> List[dict]:
    """
    Check for tasks that have been stuck in queued or in_progress status for more than the specified timeout.
    
    Args:
        timeout_minutes: Number of minutes after which a task is considered stuck (default: 30)
        
    Returns:
        List of stuck task dictionaries with task information
    """
    try:
        session = SessionLocal()
        
        # Calculate the cutoff time
        cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        
        # Find stuck tasks
        stuck_tasks = session.query(Task).filter(
            Task.status.in_(['queued', 'in_progress']),
            Task.created_at < cutoff_time
        ).all()
        
        stuck_task_list = []
        for task in stuck_tasks:
            stuck_task_list.append({
                'id': task.id,
                'status': task.status,
                'created_at': task.created_at,
                'updated_at': task.updated_at,
                'user_api_key': task.user_api_key,
                'request_payload': task.request_payload
            })
            
        session.close()
        
        logger.info(f"Found {len(stuck_task_list)} stuck tasks older than {timeout_minutes} minutes")
        return stuck_task_list
        
    except Exception as e:
        logger.error(f"Error checking for stuck tasks: {e}")
        return []

def update_task_to_failed(task_id: str, error_message: str = "Timeout error: Task exceeded maximum processing time") -> bool:
    """
    Update a task status to failed with the specified error message.
    
    Args:
        task_id: The ID of the task to update
        error_message: Error message to set for the failed task
        
    Returns:
        True if update was successful, False otherwise
    """
    try:
        session = SessionLocal()
        
        # Find the task
        task = session.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            logger.warning(f"Task with ID {task_id} not found")
            session.close()
            return False
        
        # Update task status
        task.status = 'failed'
        task.error = error_message
        task.updated_at = datetime.utcnow()
        
        # Commit the changes
        session.commit()
        session.close()
        
        logger.info(f"Successfully updated task {task_id} to failed status")
        return True
        
    except Exception as e:
        logger.error(f"Error updating task {task_id} to failed: {e}")
        try:
            session.rollback()
            session.close()
        except:
            pass
        return False

def process_stuck_tasks(timeout_minutes: int = 30, error_message: str = "Timeout error: Task exceeded maximum processing time") -> dict:
    """
    Process all stuck tasks and update them to failed status.
    
    Args:
        timeout_minutes: Number of minutes after which a task is considered stuck (default: 30)
        error_message: Error message to set for failed tasks
        
    Returns:
        Dictionary with processing results
    """
    try:
        logger.info(f"Starting stuck task processing with {timeout_minutes} minute timeout")
        
        # Find stuck tasks
        stuck_tasks = check_stuck_tasks(timeout_minutes)
        
        if not stuck_tasks:
            logger.info("No stuck tasks found")
            return {
                'total_checked': 0,
                'stuck_found': 0,
                'successfully_updated': 0,
                'failed_updates': 0,
                'error': None
            }
        
        # Process each stuck task
        successfully_updated = 0
        failed_updates = 0
        
        for task_info in stuck_tasks:
            task_id = task_info['id']
            
            # Update task to failed
            if update_task_to_failed(task_id, error_message):
                successfully_updated += 1
                logger.info(f"Task {task_id} marked as failed due to timeout")
            else:
                failed_updates += 1
                logger.error(f"Failed to update task {task_id} to failed status")
        
        result = {
            'total_checked': len(stuck_tasks),
            'stuck_found': len(stuck_tasks),
            'successfully_updated': successfully_updated,
            'failed_updates': failed_updates,
            'error': None
        }
        
        logger.info(f"Stuck task processing completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing stuck tasks: {e}")
        return {
            'total_checked': 0,
            'stuck_found': 0,
            'successfully_updated': 0,
            'failed_updates': 0,
            'error': str(e)
        }

def main():
    """
    Main function to run the timeout checker script.
    Can be called from command line or imported as a module.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Check for stuck tasks and update them to failed status')
    parser.add_argument('--timeout', type=int, default=30, 
                       help='Timeout in minutes (default: 30)')
    parser.add_argument('--error-message', type=str, 
                       default="Timeout error: Task exceeded maximum processing time",
                       help='Error message for failed tasks')
    parser.add_argument('--dry-run', action='store_true',
                       help='Check for stuck tasks without updating them')
    
    args = parser.parse_args()
    
    if args.dry_run:
        # Just check for stuck tasks without updating
        stuck_tasks = check_stuck_tasks(args.timeout)
        logger.info(f"DRY RUN: Found {len(stuck_tasks)} stuck tasks")
        for task in stuck_tasks:
            logger.info(f"DRY RUN: Task {task['id']} - Status: {task['status']}, Created: {task['created_at']}")
    else:
        # Process stuck tasks
        result = process_stuck_tasks(args.timeout, args.error_message)
        logger.info(f"Processing completed: {result}")

if __name__ == "__main__":
    main() 