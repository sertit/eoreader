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
""" Landsat-8 products """
from eoreader.products.optical.landsat_product import LandsatProduct


class L8Product(LandsatProduct):
    """Class of Landsat-8 Products"""

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        # DO NOT TAKE INTO ACCOUNT PAN AND TIRS RES
        return 30.0

    def _set_product_type(self) -> None:
        """Set products type"""
        self._set_olci_product_type()
