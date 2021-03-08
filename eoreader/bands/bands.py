""" Optical Bands """
# Lines too long
# pylint: disable=C0301
from enum import unique
from collections.abc import MutableMapping

from sertit.misc import ListEnum

from eoreader.exceptions import InvalidTypeError


class Bands(MutableMapping):
    """ Super bands class, used as a dict """

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
    """ Super class for band names """

    @classmethod
    def get_band_names(cls) -> list:
        """
        Get all band names

        Returns:
            list: List of names

        """
        return cls.list_names()

    @classmethod
    def from_list(cls, name_list: list) -> list:
        """
        Get the band enums from list of band names

        Args:
            name_list (list): List of names

        Returns:
            list: List of enums

        """
        try:
            band_names = [cls(name) for name in name_list]
        except ValueError as ex:
            raise InvalidTypeError(f"Band names ({name_list}) should be chosen among: {cls.get_band_names()}") from ex

        return band_names

    @classmethod
    def tolist(cls, name_list: list = None) -> list:
        """
        Get a list from the values of the bands

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
                elif isinstance(key, Bands):
                    out_list.append(cls[key])
                else:
                    raise InvalidTypeError("The list should either contain strings or SarBandNames")
        else:
            out_list = cls.list_values()

        return out_list


# ---------------------- SAR ----------------------
@unique
class SarBandNames(BandNames):
    """ SAR Band names """
    VV = 'VV'
    VV_DSPK = 'DESPK_VV'
    HH = 'HH'
    HH_DSPK = 'DESPK_HH'
    VH = 'VH'
    VH_DSPK = 'DESPK_VH'
    HV = 'HV'
    HV_DSPK = 'DESPK_HV'

    @classmethod
    def corresponding_despeckle(cls, band: "SarBandNames"):
        if cls.is_despeckle(band):
            dspk = band
        else:
            dspk = cls.from_value(f"DESPK_{band.name}")

        return dspk

    @classmethod
    def corresponding_speckle(cls, band: "SarBandNames"):
        return cls.from_value(f"{band.name[:2]}")

    @classmethod
    def is_despeckle(cls, band: "SarBandNames"):
        return "DSPK" in band.name


# too many ancestors
# pylint: disable=R0901
class SarBands(Bands):
    """ SAR bands class """

    def __init__(self) -> None:
        super().__init__({band_name: band_name.value for band_name in SarBandNames})


# ---------------------- OPTICAL ----------------------
class OpticalBandNames(BandNames):
    """
    This class aims to regroup equivalent bands under the same nomenclature.
    Each products will set their band number in regard to their corresponding name.

    More information can be retrieved here:

    - overall: http://blog.imagico.de/wp-content/uploads/2016/11/sat_spectra_full4a.png
    - L8/S2:
       - https://reader.elsevier.com/reader/sd/pii/S0034425718301883
       - https://landsat.gsfc.nasa.gov/wp-content/uploads/2015/06/Landsat.v.Sentinel-2.png
    - L4/L5, MSS-TM: https://landsat.gsfc.nasa.gov/the-multispectral-scanner-system/
    - All Landsats: https://landsat.gsfc.nasa.gov/wp-content/uploads/2016/10/all_Landsat_bands.png
    - S2: https://discovery.creodias.eu/dataset/72181b08-a577-4d55-8ece-d8485167beb7/resource/d8f5dd92-b35c-46ee-98a2-0879dad03fce/download/res_band_s2_1.png
    - S3 OLCI: https://discovery.creodias.eu/dataset/a0960a9b-c9c4-46db-bca5-ec79d0dda32b/resource/de8300a4-08cd-41aa-96ec-d9813115cc08/download/s3_res_band_ol.png
    - S3 SLSTR: https://discovery.creodias.eu/dataset/ea8f247e-d193-4368-8cf6-8687a03a5306/resource/8e5c485a-d832-42be-ad9c-af500b468f29/download/s3_slcs.png
    - Index consistency: https://www.indexdatabase.de/

    This classification allows index computation and algorithms to run without knowing the band nb of every satellite.
    If None, then the band does not exist for the satellite.
    """
    # Coastal aerosol
    CA = 'COASTAL_AEROSOL'

    # Blue
    BLUE = "BLUE"

    # Green
    GREEN = "GREEN"

    # Red
    RED = "RED"

    # Vegetation red edge
    VRE_1 = "VEGETATION_RED_EDGE_1"

    # Vegetation red edge
    VRE_2 = "VEGETATION_RED_EDGE_2"

    # Vegetation red edge
    VRE_3 = "VEGETATION_RED_EDGE_3"

    # NIR
    NIR = "NIR"

    # Narrow NIR
    NNIR = "NARROW_NIR"

    # Water vapour
    WV = "WATER_VAPOUR"

    # Far NIR /!\ WARNING -> For satellites that don't have any SWIR, do not use it in index !
    FNIR = "FAR_NIR"

    # Cirrus
    CIRRUS = "CIRRUS"

    # SWIR
    SWIR_1 = "SWIR_1"

    # SWIR
    SWIR_2 = "SWIR_2"

    # MIR
    MIR = "MIR"

    # Thermal IR
    TIR_1 = "THERMAL_IR_1"

    # Thermal IR
    TIR_2 = "THERMAL_IR_2"

    # Panchromatic
    PAN = "PANCHROMATIC"


# too many ancestors
# pylint: disable=R0901
class OpticalBands(Bands):
    """ Optical bands class """

    def __init__(self) -> None:
        super().__init__({band_name: None for band_name in OpticalBandNames})

    def map_bands(self, band_map: dict) -> None:
        """
        Set band map (only useful values)

        Args:
            band_map (dict): Band mapping as {OpticalBandNames: Band number for loading band}
        """
        for band_name, band_nb in band_map.items():
            if band_name not in self._band_map or not isinstance(band_name, OpticalBandNames):
                raise InvalidTypeError(f"{band_name} should be an OpticalBandNames object")

            # Set number
            self._band_map[band_name] = band_nb
