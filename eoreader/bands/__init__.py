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
"""
Band module containing:

- wrapper for SAR and optical bands
- Index definitions
- Aliases for all these useful variables

To use it, simply type:

.. code-block:: python

    >>> from eoreader.bands.alias import *
    >>> GREEN
    <OpticalBandNames.GREEN: 'GREEN'>
    >>> HH
    <SarBandNames.HH: 'HH'>
    >>> NDVI
    <function NDVI at 0x00000261F6FFA950>
"""
