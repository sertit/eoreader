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
""" Bands """
# Lines too long
# pylint: disable=C0301
import copy
from abc import abstractmethod
from collections.abc import MutableMapping
from typing import Union

from sertit import misc
from sertit.misc import ListEnum

from eoreader.exceptions import InvalidTypeError
from eoreader.stac import ASSET_ROLE, DESCRIPTION, GSD, ID, NAME, REFLECTANCE


# ---------------------- BAND OBJECTS ----------------------
class Band:
    """
    Band object. Based on STAC band object.
    See `here <https://github.com/stac-extensions/eo/#band-object>`_ for more information.
    """

    def __init__(self, eoreader_name=None, **kwargs):
        misc.check_mandatory_keys(kwargs, [NAME, ID])

        self.name = kwargs.get(NAME)
        """
        STAC :code:`name`.
        This is typically the name the data provider uses for the band.
        It should be treated like an 'id', to identify that a particular band used in several assets represents the same band (all the other fields should be the same as well).
        It is also recommended that clients use this name for display, potentially in conjunction with the common name.
        """

        self.id = kwargs.get(ID)
        """
        ID of the band, used to retrieve the band file or the band number in the stack.
        """

        self.eoreader_name = None
        """
        Mapping between EOReader names and STAC common names
        """

        self.common_name = None
        """
        STAC :code:`common_name`.
        The band's common_name is the name that is commonly used to refer to that band's spectral properties.
        None if not existing.
        """

        self.description = kwargs.get(DESCRIPTION, "")
        """
        STAC :code:`description`.
        Description to fully explain the band. CommonMark 0.29 syntax MAY be used for rich text representation.
        """

        self.gsd = kwargs.get(GSD)
        """
        GSD of the band (in meters)
        """

        self.asset_role = kwargs.get(ASSET_ROLE, REFLECTANCE)
        """
        Asset role, as described in the best-practices paragraph.
        """

    def _to_repr(self) -> list:
        """
        Returns a representation of the product as a list

        Returns:
            list: Representation of the product
        """
        # Mandatory fields
        repr = [
            f"eoreader.{self.__class__.__name__} '{self.name}'",
            "Attributes:",
            f"\tid: {self.id}",
        ]

        # Optional fields
        for attr in ["eoreader_name", "common_name", "gsd", "asset_role"]:
            if getattr(self, attr) is not None:
                attr_str = getattr(self, attr)
                if isinstance(attr_str, ListEnum):
                    attr_str = attr_str.value
                if attr == "gsd":
                    repr.append(f"\t{attr} (m): {attr_str}")
                else:
                    repr.append(f"\t{attr}: {attr_str}")

        # Specific to constellation
        repr += self._to_repr_constellation_specific()

        # Final: description
        if self.description:
            repr.append(f"\tdescription: {self.description}")

        return repr

    @abstractmethod
    def _to_repr_constellation_specific(self) -> list:
        """
        Representation specific to the constellation

        Returns:
            list: Representation list (constellation specific)
        """
        raise NotImplementedError

    def __repr__(self):
        return "\n".join(self._to_repr())

    def update(self, **kwargs) -> "Band":
        new_band = copy.copy(self)

        for key, val in kwargs.items():
            if hasattr(new_band, key):
                setattr(new_band, key, val)
        return new_band


# ---------------------- BAND MAP OBJECTS ----------------------
class BandMap(MutableMapping):
    """Super bands class, used as a dict"""

    def __init__(self, *args, **kwargs):
        self._band_map = dict()
        self.update(dict(*args, **kwargs))  # use the free update to set keys

    def __getitem__(self, key):
        return self._band_map[key]

    def __setitem__(self, key, value):
        self._band_map[key] = value

    def __delitem__(self, key):
        del self._band_map[key]

    def __iter__(self):
        return iter(self._band_map)

    def __len__(self):
        return len(self._band_map)

    def __repr__(self):
        band_repr = [
            band.__repr__() for band in self._band_map.values() if band is not None
        ]
        return "\n".join(band_repr)


# ---------------------- BAND NAMES ----------------------


class BandNames(ListEnum):
    """Super class for band names, **do not use it**."""

    @classmethod
    def from_list(cls, name_list: Union[list, str]) -> list:
        """
        Get the band enums from list of band names

        .. code-block:: python

            >>> SarBandNames.from_list("VV")
            [<SarBandNames.VV: 'VV'>]

        Args:
            name_list (Union[list, str]): List of names

        Returns:
            list: List of enums
        """
        if not isinstance(name_list, list):
            name_list = [name_list]
        try:
            band_names = [cls(name) for name in name_list]
        except ValueError as ex:
            raise InvalidTypeError(
                f"Band names ({name_list}) should be chosen among: {cls.list_names()}"
            ) from ex

        return band_names

    @classmethod
    def to_value_list(cls, name_list: list = None) -> list:
        """
        Get a list from the values of the bands

        .. code-block:: python

             >>> SarBandNames.to_name_list([SarBandNames.HV_DSPK, SarBandNames.VV])
            ['HV_DSPK', 'VV']
            >>> SarBandNames.to_name_list()
            ['VV', 'VV_DSPK', 'HH', 'HH_DSPK', 'VH', 'VH_DSPK', 'HV', 'HV_DSPK']

        Args:
            name_list (list): List of band names

        Returns:
            list: List of band values

        """
        if name_list:
            out_list = []
            for key in name_list:
                if isinstance(key, str):
                    out_list.append(getattr(cls, key).value)
                elif isinstance(key, cls):
                    out_list.append(key.value)
                else:
                    raise InvalidTypeError(
                        "The list should either contain strings or BandNames"
                    )
        else:
            out_list = cls.list_values()

        return out_list
