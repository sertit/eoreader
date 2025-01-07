# Copyright 2025, SERTIT-ICube - France, https://sertit.unistra.fr/
# This file is part of eoreader project
#     https://github.com/sertit/eoreader
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
**EOReader** library
"""

# flake8: noqa
from functools import wraps
from typing import Callable

EOREADER_NAME = "eoreader"
DATETIME_FMT = "%Y%m%dT%H%M%S"

try:
    from methodtools import lru_cache

    def cache(func: Callable) -> Callable:
        @lru_cache()
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

except ImportError:
    print(
        "WARNING!\n"
        "Without the methodtools library, caches are not limited to object instances!\n"
        "Caches may be shared between similar products!\n"
        "Please install methodtools through pip (pip install methodtools)"
    )
    from functools import cache


from .__meta__ import (
    __version__,
)
