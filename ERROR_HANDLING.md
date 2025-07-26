# Enhanced Error Handling for ProtoVideo Worker

## Overview

The ProtoVideo worker has been enhanced with comprehensive error handling to ensure that any task failure or process termination results in proper task status updates and error logging.

## Features

### 1. Signal Handling
- **SIGTERM**: Graceful termination signal
- **SIGINT**: Interrupt signal (Ctrl+C)
- **SIGKILL**: Force kill signal

When any of these signals are received, the worker will:
- Log the signal event
- Update the task status to "failed"
- Include the signal information in the error message
- Exit gracefully

### 2. Memory Monitoring
- **Background monitoring**: Runs in a separate thread
- **Warning threshold**: 1GB memory usage
- **Critical threshold**: 2GB memory usage
- **Automatic failure**: Tasks are marked as failed if memory exceeds 2GB

### 3. Database Error Recovery
- **Graceful handling**: Database errors don't crash the worker
- **Status updates**: Task status is always updated, even on database errors
- **Error logging**: All database errors are logged with full context

### 4. Context Manager
- **Error recovery context**: Wraps task processing with comprehensive error handling
- **Resource cleanup**: Ensures proper cleanup of resources
- **Signal restoration**: Restores original signal handlers after task completion

### 5. Process Monitoring
- **Garbage collection**: Forces garbage collection before starting tasks
- **Memory cleanup**: Monitors and logs memory usage
- **Resource tracking**: Tracks temporary files and cleanup

## Implementation Details

### Signal Handler
```python
def signal_handler(signum, frame):
    """Handle process termination signals."""
    global current_task_id, task_failed, failure_reason
    
    signal_name = signal.Signals(signum).name
    failure_reason = f"Process terminated by signal: {signal_name} (SIG{signum})"
    task_failed = True
    
    if current_task_id:
        update_task_status(current_task_id, 'failed', error=failure_reason)
    
    sys.exit(1)
```

### Memory Monitor
```python
def memory_monitor():
    """Monitor memory usage and log warnings."""
    process = psutil.Process()
    while not task_failed:
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb > 1000:  # Warning at 1GB
            logger.warning(f"[MEMORY] High memory usage: {memory_mb:.1f}MB")
        
        if memory_mb > 2000:  # Critical at 2GB
            failure_reason = f"Memory limit exceeded: {memory_mb:.1f}MB"
            task_failed = True
            break
```

### Error Recovery Context
```python
@contextmanager
def error_recovery_context(task_id):
    """Context manager for comprehensive error handling."""
    # Set up signal handlers
    # Start memory monitoring
    # Process task
    # Clean up resources
    # Restore signal handlers
```

## Usage

### Normal Operation
```bash
python main_worker.py <task_id>
```

### Signal Testing
```bash
# Start worker
python main_worker.py <task_id> &
WORKER_PID=$!

# Send termination signal
kill -TERM $WORKER_PID

# Check task status in database
```

### Memory Testing
```bash
# Monitor memory usage
python -c "
import psutil
p = psutil.Process()
print(f'Memory: {p.memory_info().rss / 1024 / 1024:.1f}MB')
"
```

## Error Scenarios Handled

### 1. Process Termination
- **Cause**: SIGTERM, SIGINT, SIGKILL signals
- **Action**: Update task status to "failed"
- **Error Message**: "Process terminated by signal: SIGTERM (SIG15)"

### 2. Memory Exhaustion
- **Cause**: Memory usage exceeds 2GB
- **Action**: Mark task as failed
- **Error Message**: "Memory limit exceeded: 2048.5MB"

### 3. Database Errors
- **Cause**: Connection issues, constraint violations
- **Action**: Log error and continue processing
- **Error Message**: Original database error with context

### 4. Video Generation Errors
- **Cause**: API failures, file system errors, encoding issues
- **Action**: Update task status to "failed"
- **Error Message**: Full stack trace with context

### 5. Unexpected Exceptions
- **Cause**: Any unhandled exception
- **Action**: Catch, log, and update task status
- **Error Message**: Full exception details with stack trace

## Configuration

### Environment Variables
```bash
# Memory limits (in MB)
MEMORY_WARNING_THRESHOLD=1000  # 1GB
MEMORY_CRITICAL_THRESHOLD=2000 # 2GB

# Signal handling
ENABLE_SIGNAL_HANDLING=true

# Database retry settings
DB_RETRY_ATTEMPTS=3
DB_RETRY_DELAY=5
```

### Logging
All error events are logged with structured JSON format:
```json
{
  "message": "Task processing failed",
  "level": "ERROR",
  "time": "2025-07-26 22:44:27,419",
  "task_id": "test-task-id",
  "error_type": "ValueError",
  "error_message": "Test exception"
}
```

## Testing

### Run Error Handling Tests
```bash
# Simple tests (no actual signals)
PYTHONPATH=. python tests/test_error_handling_simple.py

# Full tests (includes signal testing)
PYTHONPATH=. python tests/test_error_handling.py
```

### Test Categories
1. **Module Imports**: Verify all required modules can be imported
2. **Configuration**: Check global variables and settings
3. **Memory Usage**: Monitor memory consumption
4. **Database Functions**: Test database error handling
5. **Error Recovery Context**: Test context manager functionality
6. **Signal Handling**: Test signal handler registration
7. **Worker Integration**: Test complete worker functionality

## Monitoring

### Health Checks
```bash
# Check worker process
ps aux | grep main_worker.py

# Check memory usage
python -c "import psutil; p=psutil.Process(); print(f'{p.memory_info().rss/1024/1024:.1f}MB')"

# Check task status
python -c "from db import get_task_by_id; print(get_task_by_id('task-id').status)"
```

### Log Analysis
```bash
# Filter error logs
grep "ERROR" worker.log

# Filter signal logs
grep "SIGNAL" worker.log

# Filter memory logs
grep "MEMORY" worker.log
```

## Benefits

1. **Reliability**: Tasks are never left in an unknown state
2. **Debugging**: Comprehensive error messages with full context
3. **Resource Management**: Automatic cleanup and memory monitoring
4. **Graceful Degradation**: Worker continues operating even with partial failures
5. **Observability**: Structured logging for monitoring and alerting

## Troubleshooting

### Common Issues

1. **Task stuck in "inprogress"**
   - Check worker logs for error messages
   - Verify database connectivity
   - Check memory usage

2. **Memory warnings**
   - Monitor memory usage over time
   - Consider increasing memory limits
   - Optimize video generation parameters

3. **Signal handling not working**
   - Verify signal handlers are registered
   - Check if process is being killed with SIGKILL
   - Review system logs for process termination

4. **Database errors**
   - Check database connectivity
   - Verify database permissions
   - Review database logs

### Debug Commands
```bash
# Check worker status
ps aux | grep main_worker

# Monitor memory
watch -n 1 'ps -o pid,ppid,cmd,%mem,%cpu --sort=-%mem | head -10'

# Check task status
python -c "from db import get_task_by_id; t=get_task_by_id('task-id'); print(f'Status: {t.status}, Error: {t.error}')"
``` 