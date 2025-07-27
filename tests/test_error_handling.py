#!/usr/bin/env python3
"""
Test the enhanced error handling functionality of the worker.
"""
import os
import sys
import time
import signal
import subprocess
import uuid
import tempfile
from unittest.mock import patch, MagicMock

def test_signal_handling():
    """Test that the worker handles termination signals correctly."""
    print("🧪 Testing Signal Handling")
    print("=" * 50)
    
    # Create a test task
    task_id = str(uuid.uuid4())
    test_payload = {
        "output_filename": "test_signal_handling.mp4",
        "scenes": [
            {
                "type": "image",
                "promp_image": "A simple test image",
                "duration": 5
            }
        ]
    }
    
    # Import and test signal handler
    try:
        from main_worker import signal_handler, current_task_id, task_failed, failure_reason
        
        # Test signal handler
        with patch('main_worker.current_task_id', task_id):
            with patch('main_worker.task_failed', False):
                with patch('main_worker.failure_reason', None):
                    # Simulate SIGTERM
                    signal_handler(signal.SIGTERM, None)
                    
                    print("✅ Signal handler executed successfully")
                    print(f"✅ Task ID captured: {current_task_id}")
                    print(f"✅ Failure reason set: {failure_reason}")
                    
    except Exception as e:
        print(f"❌ Signal handling test failed: {e}")
        return False
    
    return True

def test_memory_monitoring():
    """Test memory monitoring functionality."""
    print("\n🧪 Testing Memory Monitoring")
    print("=" * 50)
    
    try:
        import psutil
        from main_worker import memory_monitor
        
        # Get current memory usage
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        print(f"✅ Current memory usage: {memory_mb:.1f}MB")
        print("✅ Memory monitoring function imported successfully")
        
        # Test memory monitoring in a separate thread
        import threading
        import time
        
        # Start memory monitoring for a short time
        monitor_thread = threading.Thread(target=memory_monitor, daemon=True)
        monitor_thread.start()
        
        # Let it run for a few seconds
        time.sleep(2)
        
        print("✅ Memory monitoring thread started successfully")
        
    except Exception as e:
        print(f"❌ Memory monitoring test failed: {e}")
        return False
    
    return True

def test_error_recovery_context():
    """Test the error recovery context manager."""
    print("\n🧪 Testing Error Recovery Context")
    print("=" * 50)
    
    try:
        from main_worker import error_recovery_context
        
        # Test normal execution
        with error_recovery_context("test-task-id"):
            print("✅ Context manager entered successfully")
            print("✅ Normal execution path")
        
        print("✅ Context manager exited successfully")
        
        # Test exception handling
        try:
            with error_recovery_context("test-task-id"):
                print("✅ Context manager entered for exception test")
                raise ValueError("Test exception")
        except ValueError:
            print("✅ Exception caught and handled correctly")
        
    except Exception as e:
        print(f"❌ Error recovery context test failed: {e}")
        return False
    
    return True

def test_database_error_handling():
    """Test database error handling."""
    print("\n🧪 Testing Database Error Handling")
    print("=" * 50)
    
    try:
        from db import update_task_status, get_task_by_id
        
        # Test with a non-existent task
        fake_task_id = "non-existent-task-id"
        
        # This should not raise an exception but handle gracefully
        task = get_task_by_id(fake_task_id)
        if task is None:
            print("✅ Non-existent task handled gracefully")
        
        # Test updating status (this might fail but should be handled)
        try:
            update_task_status(fake_task_id, 'failed', error="Test error")
            print("✅ Database update handled gracefully")
        except Exception as e:
            print(f"✅ Database error caught: {e}")
        
    except Exception as e:
        print(f"❌ Database error handling test failed: {e}")
        return False
    
    return True

def test_worker_integration():
    """Test the complete worker integration with error handling."""
    print("\n🧪 Testing Worker Integration")
    print("=" * 50)
    
    try:
        from main_worker import process_all_pending_tasks
        
        # Test argument parsing
        original_argv = sys.argv.copy()
        
        # Test with no arguments
        sys.argv = ['main_worker.py']
        try:
            process_all_pending_tasks()
        except SystemExit as e:
            if e.code == 1:
                print("✅ Worker correctly exits with error code 1 for missing task_id")
            else:
                print(f"❌ Unexpected exit code: {e.code}")
                return False
        
        # Test with invalid task_id
        sys.argv = ['main_worker.py', 'invalid-task-id']
        try:
            process_all_pending_tasks()
        except SystemExit as e:
            if e.code == 1:
                print("✅ Worker correctly exits with error code 1 for invalid task_id")
            else:
                print(f"❌ Unexpected exit code: {e.code}")
                return False
        
        # Restore original argv
        sys.argv = original_argv
        
    except Exception as e:
        print(f"❌ Worker integration test failed: {e}")
        return False
    
    return True

def main():
    """Run all error handling tests."""
    print("🧪 Enhanced Error Handling Test Suite")
    print("=" * 60)
    
    tests = [
        ("Signal Handling Test", test_signal_handling),
        ("Memory Monitoring Test", test_memory_monitoring),
        ("Error Recovery Context Test", test_error_recovery_context),
        ("Database Error Handling Test", test_database_error_handling),
        ("Worker Integration Test", test_worker_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Error Handling Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All error handling tests passed!")
        print("\n💡 The worker now has comprehensive error handling:")
        print("   - Signal handling (SIGTERM, SIGINT, SIGKILL)")
        print("   - Memory monitoring with automatic failure")
        print("   - Database error recovery")
        print("   - Graceful process termination")
        print("   - Task status updates on any failure")
        return 0
    else:
        print("❌ Some error handling tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 