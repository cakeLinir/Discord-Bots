import logging
import os

# Logger konfigurieren
def setup_logger(name, log_file, level=logging.INFO):
    """
    Richtet einen Logger ein.
    :param name: Name des Loggers
    :param log_file: Pfad zur Log-Datei
    :param level: Logging-Level
    """
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

# Logger für shared-Bereich
LOG_FILE_PATH = os.path.join(os.getcwd(), 'shared.log')
shared_logger = setup_logger('shared', LOG_FILE_PATH)
