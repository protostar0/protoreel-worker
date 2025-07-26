#!/usr/bin/env python3
"""
Test script to verify that started_at and finished_at timestamps are set correctly.
"""

import os
import sys
import uuid
from datetime import datetime
from db import create_task, update_task_status, get_task_by_id

def test_timestamps():
    """Test that timestamps are set correctly when task status changes."""
    print("Testing timestamp functionality...")
    
    # Create a test task
    task_id = str(uuid.uuid4())
    user_api_key = "test_api_key"
    payload = {
        "output_filename": "test_timestamps.mp4",
        "scenes": [
            {
                "type": "image",
                "image": "https://example.com/image.jpg",
                "duration": 5
            }
        ]
    }
    
    # Create task (should have no timestamps initially)
    task = create_task(task_id, user_api_key, payload)
    print(f"✓ Task created with ID: {task_id}")
    
    # Check initial state
    task = get_task_by_id(task_id)
    if hasattr(task, 'started_at'):
        print(f"  Initial started_at: {task.started_at}")
        print(f"  Initial finished_at: {task.finished_at}")
    else:
        print(f"  Initial started_at: {task.get('started_at')}")
        print(f"  Initial finished_at: {task.get('finished_at')}")
    
    # Update to inprogress (should set started_at)
    print("\nUpdating status to 'inprogress'...")
    update_task_status(task_id, 'inprogress')
    
    task = get_task_by_id(task_id)
    if hasattr(task, 'started_at'):
        print(f"  After inprogress - started_at: {task.started_at}")
        print(f"  After inprogress - finished_at: {task.finished_at}")
        assert task.started_at is not None, "started_at should be set when status is inprogress"
        assert task.finished_at is None, "finished_at should still be None"
    else:
        print(f"  After inprogress - started_at: {task.get('started_at')}")
        print(f"  After inprogress - finished_at: {task.get('finished_at')}")
        assert task.get('started_at') is not None, "started_at should be set when status is inprogress"
        assert task.get('finished_at') is None, "finished_at should still be None"
    
    # Update to finished (should set finished_at)
    print("\nUpdating status to 'finished'...")
    result = {"r2_url": "https://example.com/video.mp4"}
    update_task_status(task_id, 'finished', result=result)
    
    task = get_task_by_id(task_id)
    if hasattr(task, 'started_at'):
        print(f"  After finished - started_at: {task.started_at}")
        print(f"  After finished - finished_at: {task.finished_at}")
        assert task.started_at is not None, "started_at should still be set"
        assert task.finished_at is not None, "finished_at should be set when status is finished"
    else:
        print(f"  After finished - started_at: {task.get('started_at')}")
        print(f"  After finished - finished_at: {task.get('finished_at')}")
        assert task.get('started_at') is not None, "started_at should still be set"
        assert task.get('finished_at') is not None, "finished_at should be set when status is finished"
    
    print("\n✓ All timestamp tests passed!")
    
    # Test that timestamps don't get overwritten
    print("\nTesting that timestamps don't get overwritten...")
    update_task_status(task_id, 'inprogress')  # Should not change started_at
    update_task_status(task_id, 'finished')    # Should not change finished_at
    
    task = get_task_by_id(task_id)
    if hasattr(task, 'started_at'):
        original_started = task.started_at
        original_finished = task.finished_at
    else:
        original_started = task.get('started_at')
        original_finished = task.get('finished_at')
    
    print(f"  Original started_at: {original_started}")
    print(f"  Original finished_at: {original_finished}")
    
    # Update status again
    update_task_status(task_id, 'inprogress')
    update_task_status(task_id, 'finished')
    
    task = get_task_by_id(task_id)
    if hasattr(task, 'started_at'):
        new_started = task.started_at
        new_finished = task.finished_at
    else:
        new_started = task.get('started_at')
        new_finished = task.get('finished_at')
    
    print(f"  New started_at: {new_started}")
    print(f"  New finished_at: {new_finished}")
    
    assert new_started == original_started, "started_at should not change on subsequent inprogress updates"
    assert new_finished == original_finished, "finished_at should not change on subsequent finished updates"
    
    print("✓ Timestamp overwrite protection works!")
    
    return True

if __name__ == "__main__":
    try:
        test_timestamps()
        print("\n🎉 All tests passed! Timestamp functionality is working correctly.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1) 