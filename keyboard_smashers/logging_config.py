import logging
import logging.handlers
import os


def setup_logging(log_level=logging.INFO, log_dir="logs"):

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s'
        ' - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')

    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    root_logger.handlers.clear()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    all_logs_file = os.path.join(log_dir, 'app.log')
    file_handler = logging.handlers.RotatingFileHandler(
        all_logs_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    error_file = os.path.join(log_dir, 'errors.log')
    error_handler = logging.handlers.RotatingFileHandler(
        error_file,
        maxBytes=10 * 1024 * 1024,
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)

    review_file = os.path.join(log_dir, 'review_activity.log')
    review_handler = logging.handlers.RotatingFileHandler(
        review_file,
        maxBytes=10 * 1024 * 1024,
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    review_handler.setLevel(logging.INFO)
    review_handler.setFormatter(detailed_formatter)

    review_logger = logging.getLogger('review_activity')
    review_logger.addHandler(review_handler)
    review_logger.setLevel(logging.INFO)

    logging.info("Logging system initialized")

    return root_logger
