"""
Centralized Logging Configuration for JARVIS
Sets up consistent logging across all modules with proper formatting
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    console_output: bool = True
):
    """
    Configure centralized logging for the entire application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        console_output: Whether to output logs to console
    
    Example:
        # Development (verbose)
        setup_logging(level=logging.DEBUG)
        
        # Production (minimal)
        setup_logging(level=logging.WARNING, log_file="jarvis.log")
    """
    # Root logger
    root = logging.getLogger()
    root.setLevel(level)
    
    # Clear existing handlers
    root.handlers.clear()
    
    # Formatter with timestamp, module, level, and message
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)
    
    # File handler
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    
    # Suppress noisy third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("google.auth").setLevel(logging.WARNING)
    logging.getLogger("google.genai").setLevel(logging.INFO)  # Keep Gemini logs
    logging.getLogger("groq").setLevel(logging.WARNING)
    
    # Log startup message
    root.info("🚀 JARVIS logging initialized")
    root.debug(f"Log level: {logging.getLevelName(level)}")
    if log_file:
        root.debug(f"Log file: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Args:
        name: Module name (usually __name__)
    
    Returns:
        Configured logger instance
    
    Example:
        logger = get_logger(__name__)
        logger.info("Module initialized")
    """
    return logging.getLogger(name)


# Convenience functions for common patterns
def log_api_call(
    logger: logging.Logger,
    provider: str,
    model: str,
    success: bool,
    response_time: Optional[float] = None
):
    """
    Log API calls with consistent formatting.
    
    Args:
        logger: Logger instance
        provider: API provider name (Groq, Gemini, etc.)
        model: Model name
        success: Whether call succeeded
        response_time: Optional response time in seconds
    """
    status = "✓" if success else "✗"
    msg = f"{status} {provider}/{model}"
    
    if response_time:
        msg += f" ({response_time:.2f}s)"
    
    if success:
        logger.info(msg)
    else:
        logger.error(msg)


def log_tool_execution(
    logger: logging.Logger,
    tool_name: str,
    success: bool,
    result: Optional[str] = None,
    error: Optional[str] = None
):
    """
    Log tool executions with consistent formatting.
    
    Args:
        logger: Logger instance
        tool_name: Name of the tool
        success: Whether execution succeeded
        result: Optional result summary
        error: Optional error message
    """
    status = "✓" if success else "✗"
    msg = f"{status} Tool: {tool_name}"
    
    if result:
        msg += f" → {result[:100]}"
    if error:
        msg += f" (Error: {error})"
    
    if success:
        logger.info(msg)
    else:
        logger.error(msg)
