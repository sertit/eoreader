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
""" Optical Bands """
# Lines too long
# pylint: disable=C0301
from collections.abc import MutableMapping
from enum import unique
from typing import Union

from eoreader.exceptions import InvalidTypeError
from sertit.misc import ListEnum


class _Bands(MutableMapping):
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
                        "The list should either contain strings or SarBandNames"
                    )
        else:
            out_list = cls.list_values()

        return out_list


# ---------------------- SAR ----------------------
@unique
class SarBandNames(BandNames):
    """SAR Band names"""

    VV = "VV"
    """ Vertical Transmit-Vertical Receive Polarisation """

    VV_DSPK = "VV_DSPK"
    """ Vertical Transmit-Vertical Receive Polarisation Despeckled """

    HH = "HH"
    """ Horizontal Transmit-Horizontal Receive Polarisation """

    HH_DSPK = "HH_DSPK"
    """ Horizontal Transmit-Horizontal Receive Polarisation Despeckled """

    VH = "VH"
    """ Vertical Transmit-Horizontal Receive Polarisation """

    VH_DSPK = "VH_DSPK"
    """ Vertical Transmit-Horizontal Receive Polarisatio Despeckled """

    HV = "HV"
    """ Horizontal Transmit-Vertical Receive Polarisation """

    HV_DSPK = "HV_DSPK"
    """ Horizontal Transmit-Vertical Receive Polarisation Despeckled """

    @classmethod
    def corresponding_despeckle(cls, band: "SarBandNames"):
        """
        Corresponding despeckled band.

        .. code-block:: python

            >>> SarBandNames.corresponding_despeckle(SarBandNames.VV)
            <SarBandNames.VV_DSPK: 'VV_DSPK'>
            >>> SarBandNames.corresponding_despeckle(SarBandNames.VV_DSPK)
            <SarBandNames.VV_DSPK: 'VV_DSPK'>

        Args:
            band (SarBandNames): Noisy (speckle) band

        Returns:
            SarBandNames: Despeckled band
        """
        if cls.is_despeckle(band):
            dspk = band
        else:
            dspk = cls.from_value(f"{band.name}_DSPK")

        return dspk

    @classmethod
    def corresponding_speckle(cls, band: "SarBandNames"):
        """
        Corresponding speckle (noisy) band.

        .. code-block:: python

            >>> SarBandNames.corresponding_speckle(SarBandNames.VV)
            <SarBandNames.VV: 'VV'>
            >>> SarBandNames.corresponding_speckle(SarBandNames.VV_DSPK)
            <SarBandNames.VV: 'VV'>

        Args:
            band (SarBandNames): Noisy (speckle) band

        Returns:
            SarBandNames: Despeckled band
        """
        return cls.from_value(f"{band.name[:2]}")

    @classmethod
    def is_despeckle(cls, band: "SarBandNames"):
        """
        Returns True if the band corresponds to a despeckled one.

        .. code-block:: python

            >>> SarBandNames.is_despeckle(SarBandNames.VV)
            False
            >>> SarBandNames.is_despeckle(SarBandNames.VV_DSPK)
            True

        Args:
            band (SarBandNames): Band to test

        Returns:
            SarBandNames: Despeckled band
        """
        """"""
        return "DSPK" in band.name


# too many ancestors
# pylint: disable=R0901
class SarBands(_Bands):
    """SAR bands class"""

    def __init__(self) -> None:
        super().__init__({band_name: band_name.value for band_name in SarBandNames})


# ---------------------- OPTICAL ----------------------
class OpticalBandNames(BandNames):
    """
    This class aims to regroup equivalent bands under the same nomenclature.
    Each products will set their band number in regard to their corresponding name.

    **Note**: The mapping is based on Sentinel-2 bands.
    Satellites can have not mapped bands (such as Sentinel-3)

    More information can be retrieved here:

    - `Overall comparison <http://blog.imagico.de/wp-content/uploads/2016/11/sat_spectra_full4a.png>`_
    - L8/S2:
        - `Resource 1 <https://reader.elsevier.com/reader/sd/pii/S0034425718301883>`_
        - `Resource 2 <https://landsat.gsfc.nasa.gov/wp-content/uploads/2015/06/Landsat.v.Sentinel-2.png>`_
    - `L4/L5, MSS-TM <https://landsat.gsfc.nasa.gov/the-multispectral-scanner-system/>`_
    - `All Landsats <https://landsat.gsfc.nasa.gov/wp-content/uploads/2016/10/all_Landsat_bands.png>`_
    - `S2 <https://discovery.creodias.eu/dataset/72181b08-a577-4d55-8ece-d8485167beb7/resource/d8f5dd92-b35c-46ee-98a2-0879dad03fce/download/res_band_s2_1.png>`_
    - `S3 OLCI <https://discovery.creodias.eu/dataset/a0960a9b-c9c4-46db-bca5-ec79d0dda32b/resource/de8300a4-08cd-41aa-96ec-d9813115cc08/download/s3_res_band_ol.png>`_
    - `S3 SLSTR <https://discovery.creodias.eu/dataset/ea8f247e-d193-4368-8cf6-8687a03a5306/resource/8e5c485a-d832-42be-ad9c-af500b468f29/download/s3_slcs.png>`_
    - `Index consistency <https://www.indexdatabase.de/>`_

    This classification allows index computation and algorithms to run without knowing the band nb of every satellite.
    If None, then the band does not exist for the satellite.
    """

    CA = "COASTAL_AEROSOL"
    """Coastal aerosol"""

    BLUE = "BLUE"
    """Blue"""

    GREEN = "GREEN"
    """Green"""

    RED = "RED"
    """Red"""

    VRE_1 = "VEGETATION_RED_EDGE_1"
    """Vegetation red edge, Band 1"""

    VRE_2 = "VEGETATION_RED_EDGE_2"
    """Vegetation red edge, Band 2"""

    VRE_3 = "VEGETATION_RED_EDGE_3"
    """Vegetation red edge, Band 3"""

    NIR = "NIR"
    """NIR"""

    NARROW_NIR = "NARROW_NIR"
    """Narrow NIR"""

    WV = "WATER_VAPOUR"
    """Water vapour"""

    FAR_NIR = "FAR_NIR"
    """Far NIR"""

    SWIR_CIRRUS = "CIRRUS"
    """Cirrus"""

    SWIR_1 = "SWIR_1"
    """SWIR, Band 1"""

    SWIR_2 = "SWIR_2"
    """SWIR, Band 2"""

    MIR = "MIR"
    """MIR"""

    TIR_1 = "THERMAL_IR_1"
    """Thermal IR, Band 1"""

    TIR_2 = "THERMAL_IR_2"
    """Thermal IR, Band 2"""

    PAN = "PANCHROMATIC"
    """Panchromatic"""


# too many ancestors
# pylint: disable=R0901
class OpticalBands(_Bands):
    """Optical bands class"""

    def __init__(self) -> None:
        super().__init__({band_name: None for band_name in OpticalBandNames})

    def map_bands(self, band_map: dict) -> None:
        """
        Mapping band names to specific satellite band numbers, as strings.

        .. code-block:: python

            >>> # Example for Sentinel-2 L1C data
            >>> ob = OpticalBands()
            >>> ob.map_bands({
                    CA: '01',
                    BLUE: '02',
                    GREEN: '03',
                    RED: '04',
                    VRE_1: '05',
                    VRE_2: '06',
                    VRE_3: '07',
                    NIR: '08',
                    NNIR: '8A',
                    WV: '09',
                    SWIR_1: '11',
                    SWIR_2: '12'
                })

        Args:
            band_map (dict): Band mapping as {OpticalBandNames: Band number for loading band}
        """
        for band_name, band_nb in band_map.items():
            if band_name not in self._band_map or not isinstance(
                band_name, OpticalBandNames
            ):
                raise InvalidTypeError(
                    f"{band_name} should be an OpticalBandNames object"
                )

            # Set number
            self._band_map[band_name] = band_nb


# ---------------------- DEM ----------------------
@unique
class DemBandNames(BandNames):
    """DEM Band names"""

    DEM = "DEM"
    """ DEM """

    SLOPE = "SLOPE"
    """ Slope """

    HILLSHADE = "HILLSHADE"
    """ Hillshade """


# too many ancestors
# pylint: disable=R0901
class DemBands(_Bands):
    """DEM bands class"""

    def __init__(self) -> None:
        super().__init__({band_name: band_name.value for band_name in DemBandNames})


# ---------------------- DEM ----------------------
@unique
class CloudsBandNames(BandNames):
    """Clouds Band names"""

    RAW_CLOUDS = "RAW CLOUDS"
    """ Raw cloud raster (can be either QA raster, rasterized cloud vectors...) """

    CLOUDS = "CLOUDS"
    """ Binary mask of clouds (High confidence) """

    SHADOWS = "SHADOWS"
    """ Binary mask of shadows (High confidence) """

    CIRRUS = "CIRRUS"
    """ Binary mask of cirrus (High confidence) """

    ALL_CLOUDS = "ALL CLOUDS"
    """ All clouds (Including all high confidence clouds, shadows and cirrus) """


# too many ancestors
# pylint: disable=R0901
class CloudsBands(_Bands):
    """Clouds bands class"""

    def __init__(self) -> None:
        super().__init__({band_name: band_name.value for band_name in CloudsBandNames})
