#!/usr/bin/env python3
"""Setup proper logging configuration for Othello Coach"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path

def setup_logging():
    """Configure logging with proper rotation and error handling"""
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler with INFO level
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation (max 5 files, 1MB each)
    log_file = log_dir / "othello-coach.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=1024*1024,  # 1MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Error handler for critical errors
    error_log_file = log_dir / "othello-coach-errors.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=1024*1024,  # 1MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    error_handler.setFormatter(error_formatter)
    root_logger.addHandler(error_handler)
    
    # Set specific logger levels
    logging.getLogger('othello_coach.engine.search').setLevel(logging.WARNING)
    logging.getLogger('othello_coach.engine.eval').setLevel(logging.WARNING)
    logging.getLogger('othello_coach.insights.features').setLevel(logging.WARNING)
    
    # Test logging
    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized successfully")
    logger.info(f"Log files: {log_file}, {error_log_file}")
    
    return logger

def test_logging():
    """Test that logging works correctly"""
    logger = logging.getLogger("test")
    
    logger.debug("This is a debug message (should not appear)")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    try:
        # Simulate an error
        raise ValueError("Test error for logging")
    except Exception as e:
        logger.exception("Caught exception during test")
    
    print("✓ Logging test completed. Check the log files.")

if __name__ == "__main__":
    logger = setup_logging()
    test_logging()
    print("✓ Logging setup completed successfully!")
