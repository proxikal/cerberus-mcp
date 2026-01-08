"""
Performance tracing decorator for critical functions.

Part of the Aegis Robustness Model - Layer 3: Performance Tracing.
"""

import time
import functools
from typing import Callable, Any
from cerberus.logging_config import logger


def trace(func: Callable) -> Callable:
    """
    Decorator that logs function entry, exit, and execution time.

    Usage:
        @trace
        def my_function(arg1, arg2):
            # function body
            pass

    Logs:
        - Entry with function name and arguments
        - Exit with function name and execution duration
        - Any exceptions raised during execution
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        func_name = func.__qualname__

        # Log entry
        logger.debug(f"TRACE_ENTER: {func_name}")

        start_time = time.perf_counter()

        try:
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            duration = end_time - start_time

            # Log successful exit with duration
            logger.info(
                f"TRACE_EXIT: {func_name} completed in {duration:.4f}s",
                extra={
                    "function": func_name,
                    "duration_seconds": duration,
                    "status": "success"
                }
            )

            return result

        except Exception as e:
            end_time = time.perf_counter()
            duration = end_time - start_time

            # Log exit with exception
            logger.error(
                f"TRACE_EXIT: {func_name} failed after {duration:.4f}s with {type(e).__name__}: {str(e)}",
                extra={
                    "function": func_name,
                    "duration_seconds": duration,
                    "status": "error",
                    "exception_type": type(e).__name__,
                    "exception_message": str(e)
                }
            )

            raise

    return wrapper
