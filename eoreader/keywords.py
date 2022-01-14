# -*- coding: utf-8 -*-
# Copyright 2022, SERTIT-ICube - France, https://sertit.unistra.fr/
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
""" Additional keywords for EOReader used in :code:`load` or  :code:`stack`"""
import sys

__all__ = ["SLSTR_RAD_ADJUST", "SLSTR_STRIPE", "SLSTR_VIEW", "CLEAN_OPTICAL"]

SLSTR_RAD_ADJUST = "slstr_radiance_adjustment"
""" SLSTR radiance adjustment, please see  :code:`eoreader.products.optical.s3_slstr_product.SlstrRadAdjust`"""

SLSTR_STRIPE = "slstr_stripe"
""" SLSTR stripe, please see  :code:`eoreader.products.optical.s3_slstr_product.SlstrStripe`"""

SLSTR_VIEW = "slstr_view"
""" SLSTR view, please see  :code:`eoreader.products.optical.s3_slstr_product.SlstrView`"""

CLEAN_OPTICAL = "clean_optical"
"""
Method to clean optical band (manage invalid pixels, only nodata or directly raw data).
This can speed up the process.
"""

SAR_INTERP_NA = "sar_interpolate_na"
"""
Interpolate nodata pixels that can be found inside the footprint
(coming from null values that are not really nodata but that are not processed by the Terrain Correction step)
"""


def prune_keywords(**kwargs) -> dict:
    """
    Prune EOReader keywords from kwargs in order to avoid the GDAL warning
    CPLE_NotSupported in driver GTiff does not support open option XXX

    Args:
        kwargs: Kwargs to prune

    Returns: Prune kwargs
    """
    if kwargs:
        prune_kwargs = kwargs.copy()
        for keyword in __all__:
            keyword_val = getattr(sys.modules[__name__], keyword)
            if keyword_val in prune_kwargs:
                prune_kwargs.pop(keyword_val)
        return prune_kwargs
    else:
        return kwargs
