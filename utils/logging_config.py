import logging
import os

def setup_logging(log_name=None):
    """Sets up logging to log only to a file."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    if log_name:
        log_file = os.path.join(log_dir, f"{log_name}.log")
    else:
        log_file = os.path.join(log_dir, "app.log")

    # Create a custom logger
    logger = logging.getLogger(log_name)
    if not logger.hasHandlers():  # Avoid adding duplicate handlers
        logger.setLevel(logging.DEBUG)

        # Create a file handler
        file_handler = logging.FileHandler(log_file, mode='w')
        file_handler.setLevel(logging.DEBUG)

        # Create a formatter and add it to the file handler
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # Add the file handler to the logger
        logger.addHandler(file_handler)

        # Disable propagation to avoid duplicate logs
        logger.propagate = False

    # Remove any handlers added by third-party libraries to the root logger
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    return logger
