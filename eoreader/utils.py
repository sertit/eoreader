""" Utils: mostly getting directories relative to the project """
import logging
import os

EOREADER_NAME = "eoreader"
DATETIME_FMT = "%Y%m%dT%H%M%S"
LOGGER = logging.getLogger(EOREADER_NAME)


def get_src_dir() -> str:
    """
    Get src directory.

    Returns:
        str: Root directory
    """
    return os.path.abspath(os.path.dirname(__file__))


def get_root_dir() -> str:
    """
    Get root directory.

    Returns:
        str: Root directory
    """
    return os.path.abspath(os.path.join(get_src_dir(), ".."))


def get_data_dir() -> str:
    """
    Get data directory.

    Returns:
        str: Data directory
    """
    return os.path.abspath(os.path.join(get_src_dir(), 'data'))


def get_db_dir() -> str:
    """
    Get database directory in the DS2

    Returns:
        str: Database directory
    """
    db_dir = os.path.join(r'\\ds2', 'database02', 'BASES_DE_DONNEES')

    if not os.path.isdir(db_dir):
        db_dir = os.path.join("/home", "ds2_db2", 'BASES_DE_DONNEES')

    return db_dir
