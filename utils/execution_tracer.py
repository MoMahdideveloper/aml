import os
import traceback
import logging
from functools import wraps

# Set up logger for execution tracing
tracer_logger = logging.getLogger('execution_tracer')
tracer_logger.setLevel(logging.DEBUG)

# Create handler if not exists (to avoid duplicate handlers)
if not tracer_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    tracer_logger.addHandler(handler)
    tracer_logger.propagate = False  # Prevent duplicate logs

# Check if tracing is enabled via environment variable
TRACING_ENABLED = os.environ.get("ENABLE_EXECUTION_TRACE", "0").lower() in ("1", "true", "yes")

def log_execution(func):
    """
    Decorator to log function execution details including call stack.
    Only active when ENABLE_EXECUTION_TRACE environment variable is set to '1', 'true', or 'yes'.

    Logs:
    - Function name, module, and line number
    - Full call stack to show execution path

    Usage:
        @log_execution
        def my_function():
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if TRACING_ENABLED:
            # Get the frame_info
            func_name = func.__name__
            func_module = func.__module__
            # Try to get line number from function's code object
            try:
                lineno = func.__code__.co_firstlineno
            except AttributeError:
                lineno = 'unknown'

            # Log function entry
            tracer_logger.debug(
                f"ENTERING FUNCTION: {func_module}.{func_name} (line {lineno})"
            )

            # Log the call stack to show execution path
            stack = traceback.extract_stack()
            # Remove the last two frames (this wrapper and the log_execution call)
            if len(stack) > 2:
                stack = stack[:-2]

            tracer_logger.debug("CALL STACK:")
            for frame in stack:
                tracer_logger.debug(
                    f"  File \"{frame.filename}\", line {frame.lineno}, in {frame.name}"
                    f"\n    {frame.line}"
                )

            # Execute the function
            try:
                result = func(*args, **kwargs)
                tracer_logger.debug(
                    f"EXITING FUNCTION: {func_module}.{func_name} (returned)"
                )
                return result
            except Exception as e:
                tracer_logger.debug(
                    f"EXITING FUNCTION: {func_module}.{func_name} (exception: {type(e).__name__})"
                )
                raise
        else:
            # Tracing disabled - just call the function normally
            return func(*args, **kwargs)

    return wrapper

# Convenience function to enable/disable tracing at runtime
def set_tracing_enabled(enabled):
    """Enable or disable execution tracing at runtime."""
    global TRACING_ENABLED
    TRACING_ENABLED = enabled
    tracer_logger.debug(f"Execution tracing {'enabled' if enabled else 'disabled'}")

# Convenience function to check tracing status
def is_tracing_enabled():
    """Return current tracing status."""
    return TRACING_ENABLED