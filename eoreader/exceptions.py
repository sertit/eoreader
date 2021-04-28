# -*- coding: utf-8 -*-
# Copyright 2021, SERTIT-ICube - France, https://sertit.unistra.fr/
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
""" EOReader exceptions """


class EoReaderError(Exception):
    """EOReader error"""

    pass


class InvalidBandError(EoReaderError):
    """Invalid Band error, thrown when a non existing band is asked to a product."""

    pass


class InvalidIndexError(InvalidBandError):
    """Invalid Index error, thrown when a non existing band is asked to a product."""

    pass


class InvalidProductError(EoReaderError):
    """Invalid Product error, thrown when satellite product is not as expected."""

    pass


class InvalidTypeError(EoReaderError, TypeError):
    """Tile Name error, thrown when an unknown type is given (shouldn't never happen)."""

    pass
