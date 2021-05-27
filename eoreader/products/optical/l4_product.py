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
""" Landsat-4 products """
from eoreader.exceptions import InvalidProductError
from eoreader.products.optical.landsat_product import LandsatProduct, LandsatProductType


class L4Product(LandsatProduct):
    """Class of Landsat-4 Products"""

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        if self.product_type == LandsatProductType.L1_MSS:
            def_res = 60.0
        else:
            # DO NOT TAKE INTO ACCOUNT TIRS RES
            def_res = 30.0
        return def_res

    def _set_product_type(self) -> None:
        """Set products type"""
        if "LT04" in self.name:
            self._set_tm_product_type()
        elif "LM04" in self.name:
            self._set_mss_product_type(version=4)
        else:
            raise InvalidProductError(f"Invalid Landsat-4 name: {self.name}")
