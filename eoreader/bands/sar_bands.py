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
"""SAR Bands"""

from eoreader.bands.band_names import SarBandNames
from eoreader.bands.bands import Band, BandMap
from eoreader.bands.mappings import EOREADER_TO_SPYNDEX_DICT
from eoreader.exceptions import InvalidTypeError


class SarBand(Band):
    """
    SAR Band object.
    Based on STAC band object.
    See `here <https://github.com/stac-extensions/eo/#band-object>`_ for more information, without useless information.
    """

    def __init__(self, eoreader_name, **kwargs):
        # Initialization from the super class
        super().__init__(eoreader_name, **kwargs)

        # Set names
        try:
            self.eoreader_name = SarBandNames.convert_from(eoreader_name)[0]
        except TypeError as exc:
            raise InvalidTypeError from exc

    def _to_repr_constellation_specific(self) -> list:
        """
        Representation specific to the constellation

        Returns:
            list: Representation list (constellation specific)
        """

        return []


# too many ancestors
# pylint: disable=R0901
class SarBandMap(BandMap):
    """SAR band map class"""

    def __init__(self) -> None:
        super().__init__({band_name: None for band_name in SarBandNames})

    def map_bands(self, band_map: dict) -> None:
        """
        Mapping band names to specific satellite band numbers, as strings.

        .. code-block:: python

            >>> sb = SarBandMap()
            >>> sb.map_bands({
                    VV: 1,
                })

        Args:
            band_map (dict): Band mapping as {SarBandNames: Band number for loading band}
        """
        for band_name, band in band_map.items():
            if not isinstance(band, SarBand):
                spyndex_name = (EOREADER_TO_SPYNDEX_DICT.get(band_name),)
                band = SarBand(
                    eoreader_name=band_name,
                    name=band,
                    id=band,
                    spyndex_name=spyndex_name,
                )

            if band_name not in self._band_map or not isinstance(
                band_name, SarBandNames
            ):
                raise InvalidTypeError(f"{band_name} should be a SarBandNames object")

            # Set number
            self._band_map[band_name] = band
