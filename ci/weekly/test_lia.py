import shutil

import pytest

from ci.on_push.test_lia import test_lia as on_push_test_lia
from ci.scripts_utils import dask_env, reduce_verbosity, s3_env

WRITE_ON_DISK = True


reduce_verbosity()


@pytest.mark.skipif(
    shutil.which("gpt") is None, reason="Only works if SNAP GPT's exe can be found."
)
@s3_env
@dask_env
def test_lia(tmp_path):
    """Function testing the correct loading of LIA"""
    on_push_test_lia(tmp_path)
