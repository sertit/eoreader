""" Utils module for scripts """
import os
import logging
from eoreader.reader import Reader
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)
READER = Reader()


def get_ci_dir() -> str:
    """
    Get CI DATA directory
    Returns:
        str: CI DATA directory
    """
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def get_ci_data_dir() -> str:
    """
    Get CI DATA directory
    Returns:
        str: CI DATA directory
    """
    return os.path.join(get_ci_dir(), 'DATA')
