""" Utils module for scripts """
import os
import logging

from sertit import ci

from eoreader.reader import Reader
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)
READER = Reader()
try:
    # CI
    CI_PATH = os.path.join(ci.get_db3_path(), "CI", "eoreader")
except NotADirectoryError:
    # Windows
    CI_PATH = os.path.join(r'\\ds2', 'database03', "CI", "eoreader")

OPT_PATH = os.path.join(CI_PATH, "optical")
SAR_PATH = os.path.join(CI_PATH, "sar")


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
