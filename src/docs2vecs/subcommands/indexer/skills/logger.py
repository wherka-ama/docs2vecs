import logging
from pathlib import Path
from typing import Optional


def get_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name (str): The name of the logger.
        log_file (str, optional): Path to the log file. If None, logs will only go to console.

    Returns:
        logging.Logger: A logger with the given name.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Clear any existing handlers to avoid duplicate logging
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    # File handler (if log_file is specified)
    if log_file:
        # Create directory if it doesn't exist
        log_dir = Path(log_file).parent
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

    return logger
