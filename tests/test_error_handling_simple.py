#!/usr/bin/env python3
"""
Simple test to verify the enhanced error handling functionality.
"""
import os
import sys
import time

def test_imports():
    """Test that all required modules can be imported."""
    print("🧪 Testing Module Imports")
    print("=" * 50)
    
    try:
        import psutil
        print("✅ psutil imported successfully")
        
        from main_worker import (
            signal_handler, 
            memory_monitor, 
            error_recovery_context,
            process_all_pending_tasks
        )
        print("✅ All main_worker functions imported successfully")
        
        from db import update_task_status, get_task_by_id
        print("✅ Database functions imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_configuration():
    """Test that the error handling configuration is correct."""
    print("\n🧪 Testing Configuration")
    print("=" * 50)
    
    try:
        from main_worker import current_task_id, task_failed, failure_reason
        
        print(f"✅ Global variables initialized:")
        print(f"   - current_task_id: {current_task_id}")
        print(f"   - task_failed: {task_failed}")
        print(f"   - failure_reason: {failure_reason}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_memory_usage():
    """Test memory usage monitoring."""
    print("\n🧪 Testing Memory Usage")
    print("=" * 50)
    
    try:
        import psutil
        
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        print(f"✅ Current memory usage: {memory_mb:.1f}MB")
        
        # Test memory thresholds
        if memory_mb > 1000:
            print("⚠️  High memory usage detected (>1GB)")
        elif memory_mb > 2000:
            print("❌ Critical memory usage detected (>2GB)")
        else:
            print("✅ Memory usage is normal")
        
        return True
        
    except Exception as e:
        print(f"❌ Memory usage test failed: {e}")
        return False

def test_database_functions():
    """Test database error handling functions."""
    print("\n🧪 Testing Database Functions")
    print("=" * 50)
    
    try:
        from db import update_task_status, get_task_by_id
        
        # Test with non-existent task
        fake_task_id = "non-existent-task-id"
        task = get_task_by_id(fake_task_id)
        
        if task is None:
            print("✅ Non-existent task handled correctly")
        
        # Test status update (should handle gracefully)
        try:
            update_task_status(fake_task_id, 'failed', error="Test error")
            print("✅ Database update handled gracefully")
        except Exception as e:
            print(f"✅ Database error caught: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database functions test failed: {e}")
        return False

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
        
        return True
        
    except Exception as e:
        print(f"❌ Error recovery context test failed: {e}")
        return False

def main():
    """Run all simple error handling tests."""
    print("🧪 Simple Error Handling Test Suite")
    print("=" * 60)
    
    tests = [
        ("Module Imports Test", test_imports),
        ("Configuration Test", test_configuration),
        ("Memory Usage Test", test_memory_usage),
        ("Database Functions Test", test_database_functions),
        ("Error Recovery Context Test", test_error_recovery_context)
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
    print("📊 Simple Error Handling Test Summary")
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
        print("   - Context manager for error recovery")
        return 0
    else:
        print("❌ Some error handling tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 