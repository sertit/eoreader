from typing import Union

from sertit import misc, types

from eoreader.exceptions import InvalidTypeError
from eoreader.stac import StacCommonNames


class BandNames(misc.ListEnum):
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
        name_list = types.make_iterable(name_list)

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

    def __gt__(self, other) -> bool:
        """
        Overload greater than for BandNames -> compare the names in string.

        Args:
            other (BandNames): Other products to be compared with this one

        Returns:
            bool: True if this product has been acquired after the other

        """
        try:
            return self.name > other.name
        except AttributeError:
            return str(self) > str(other)

    def __ge__(self, other) -> bool:
        """
        Overload greater than for BandNames -> compare the names in string.

        Args:
            other (Product): Other products to be compared with this one

        Returns:
            bool: True if this product has been acquired after or in the same time as the other

        """
        try:
            return self.name >= other.name
        except AttributeError:
            return str(self) >= str(other)

    def __le__(self, other) -> bool:
        """
        Overload greater than for BandNames -> compare the names in string.

        Args:
            other (BandNames): Other products to be compared with this one

        Returns:
            bool: True if this product has been acquired before or in the same time as the other

        """
        try:
            return self.name <= other.name
        except AttributeError:
            return str(self) <= str(other)

    def __lt__(self, other) -> bool:
        """
        Overload greater than for BandNames -> compare the names in string.

        Args:
            other (BandNames): Other products to be compared with this one

        Returns:
            bool: True if this product has been acquired before the other

        """
        try:
            return self.name < other.name
        except AttributeError:
            return str(self) < str(other)


class SpectralBandNames(BandNames):
    """
    This class aims to regroup equivalent bands under the same nomenclature.
    Each product will set their band number in regard to their corresponding name.

    **Note**: The mapping is based on Sentinel-2 spectral bands.

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

    YELLOW = "YELLOW"
    """Yellow"""

    RED = "RED"
    """Red"""

    VRE_1 = "VEGETATION_RED_EDGE_1"
    """Vegetation red edge, Band 1"""

    VRE_2 = "VEGETATION_RED_EDGE_2"
    """Vegetation red edge, Band 2"""

    VRE_3 = "VEGETATION_RED_EDGE_3"
    """Vegetation red edge, Band 3"""

    NIR = "NIR"
    """NIR (B8 for Sentinel-2)"""

    NARROW_NIR = "NARROW_NIR"
    """Narrow NIR, spectrally narrow NIR band, equivalent to B8A (gsd 20m) for Sentinel-2 products, equivalent to NIR band for other products"""

    WV = "WATER_VAPOUR"
    """Water vapour"""

    SWIR_CIRRUS = "SWIR_CIRRUS"
    """SWIR Cirrus"""

    SWIR_1 = "SWIR_1"
    """SWIR, Band 1"""

    SWIR_2 = "SWIR_2"
    """SWIR, Band 2"""

    TIR_1 = "THERMAL_IR_1"
    """Thermal IR, Band 1"""

    TIR_2 = "THERMAL_IR_2"
    """Thermal IR, Band 2"""

    PAN = "PANCHROMATIC"
    """Panchromatic"""

    # SLSTR additional band names
    S7 = "S7"
    """
    S7
    """

    F1 = "F1"
    """
    F1
    """

    F2 = "F2"
    """
    F2
    """

    # S3-OLCI additional band names
    Oa01 = "Oa01"
    """
    Oa01
    """

    Oa02 = "Oa02"
    """
    Oa02
    """

    Oa09 = "Oa09"
    """
    Oa09
    """

    Oa10 = "Oa10"
    """
    Oa10
    """

    Oa13 = "Oa13"
    """
    Oa13
    """

    Oa14 = "Oa14"
    """
    Oa14
    """

    Oa15 = "Oa15"
    """
    Oa15
    """

    Oa18 = "Oa18"
    """
    Oa18
    """

    Oa19 = "Oa19"
    """
    Oa01
    """

    Oa21 = "Oa21"
    """
    Oa01
    """

    # -- PlanetScope PSB.SD instrument additional band --
    GREEN_1 = "GREEN_I"
    """
    GREEN I
    """

    # old alias, to be deprecated
    GREEN1 = "GREEN_I"
    """
    GREEN I
    """

    @classmethod
    def stac_to_eoreader(cls, common_name: str, name: str) -> "SpectralBandNames":
        """
        Convert STAC common names or name to EOReader bands

        Args:
            common_name (str): STAC common name
            name (str): STAC name

        Returns:
            SpectralBandNames: EOReader name
        """
        # Try directly from raw name (especially for Sentinel-3 raw bands etc.)
        try:
            return cls.from_value(name)
        except ValueError:
            eoreader_name = None

        stac_common_name = StacCommonNames.from_value(common_name)

        for key, val in EOREADER_STAC_MAP.items():
            if val == stac_common_name:
                eoreader_name = key
                break

        return eoreader_name

    @classmethod
    def eoreader_to_stac(cls, eoreader_name: "SpectralBandNames") -> StacCommonNames:
        """
        Convert EOReader bands to STAC common names

        Args:
            eoreader_name (SpectralBandNames): EOReader name

        Returns:
            StacCommonNames: STAC common name
        """
        return EOREADER_STAC_MAP.get(eoreader_name, "")


# -- SPECTRAL BANDS --
CA = SpectralBandNames.CA  # Coastal aerosol
BLUE = SpectralBandNames.BLUE
GREEN = SpectralBandNames.GREEN
YELLOW = SpectralBandNames.YELLOW
RED = SpectralBandNames.RED
VRE_1 = SpectralBandNames.VRE_1
VRE_2 = SpectralBandNames.VRE_2
VRE_3 = SpectralBandNames.VRE_3
NIR = SpectralBandNames.NIR
NARROW_NIR = SpectralBandNames.NARROW_NIR
WV = SpectralBandNames.WV  # Water vapour
SWIR_CIRRUS = SpectralBandNames.SWIR_CIRRUS  # Spectral band based on cirrus
SWIR_1 = SpectralBandNames.SWIR_1
SWIR_2 = SpectralBandNames.SWIR_2
TIR_1 = SpectralBandNames.TIR_1
TIR_2 = SpectralBandNames.TIR_2
PAN = SpectralBandNames.PAN

# -- S3-SLSTR Additional bands --
S7 = SpectralBandNames.S7
F1 = SpectralBandNames.F1
F2 = SpectralBandNames.F2

# -- S3-OCLI Additional bands --
Oa01 = SpectralBandNames.Oa01
Oa02 = SpectralBandNames.Oa02
Oa09 = SpectralBandNames.Oa09
Oa10 = SpectralBandNames.Oa10
Oa13 = SpectralBandNames.Oa13
Oa14 = SpectralBandNames.Oa14
Oa15 = SpectralBandNames.Oa15
Oa18 = SpectralBandNames.Oa18
Oa19 = SpectralBandNames.Oa19
Oa21 = SpectralBandNames.Oa21

# -- PlanetScope PSB.SD instrument additional band --
GREEN_1 = SpectralBandNames.GREEN_1
GREEN1 = SpectralBandNames.GREEN_1  # To be deprecated

EOREADER_STAC_MAP = {
    CA: StacCommonNames.COASTAL,
    BLUE: StacCommonNames.BLUE,
    GREEN: StacCommonNames.GREEN,
    RED: StacCommonNames.RED,
    YELLOW: StacCommonNames.YELLOW,
    PAN: StacCommonNames.PAN,
    VRE_1: StacCommonNames.RE,
    VRE_2: StacCommonNames.RE,
    VRE_3: StacCommonNames.RE,
    NIR: StacCommonNames.NIR,
    NARROW_NIR: StacCommonNames.NIR08,
    WV: StacCommonNames.NIR09,
    SWIR_CIRRUS: StacCommonNames.CIRRUS,
    SWIR_1: StacCommonNames.SWIR16,
    SWIR_2: StacCommonNames.SWIR22,
    TIR_1: StacCommonNames.LWIR11,
    TIR_2: StacCommonNames.LWIR12,
}


class SarBandNames(BandNames):
    """SAR Band names"""

    VV = "VV"
    """ Vertical Transmit-Vertical Receive Polarisation """

    VV_DSPK = "VV_DSPK"
    """ Vertical Transmit-Vertical Receive Polarisation (Despeckled) """

    HH = "HH"
    """ Horizontal Transmit-Horizontal Receive Polarisation """

    HH_DSPK = "HH_DSPK"
    """ Horizontal Transmit-Horizontal Receive Polarisation (Despeckled) """

    VH = "VH"
    """ Vertical Transmit-Horizontal Receive Polarisation """

    VH_DSPK = "VH_DSPK"
    """ Vertical Transmit-Horizontal Receive Polarisation (Despeckled) """

    HV = "HV"
    """ Horizontal Transmit-Vertical Receive Polarisation """

    HV_DSPK = "HV_DSPK"
    """ Horizontal Transmit-Vertical Receive Polarisation (Despeckled) """

    RH = "RH"
    """ Compact polarization: right circular transmit, horizontal receive """

    RH_DSPK = "RH_DSPK"
    """ Compact polarization: right circular transmit, horizontal receive """

    RV = "RV"
    """ Compact polarization: right circular transmit, vertical receive (Despeckled) """

    RV_DSPK = "RV_DSPK"
    """ Compact polarization: right circular transmit, horizontal receive (Despeckled) """

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
        return band if cls.is_despeckle(band) else cls.from_value(f"{band.name}_DSPK")

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
        return "DSPK" in band.name

    @classmethod
    def speckle_list(cls):
        return [band for band in cls if not cls.is_despeckle(band)]


VV = SarBandNames.VV
VV_DSPK = SarBandNames.VV_DSPK
HH = SarBandNames.HH
HH_DSPK = SarBandNames.HH_DSPK
VH = SarBandNames.VH
VH_DSPK = SarBandNames.VH_DSPK
HV = SarBandNames.HV
HV_DSPK = SarBandNames.HV_DSPK
RH = SarBandNames.RH
RH_DSPK = SarBandNames.RH_DSPK
RV = SarBandNames.RV
RV_DSPK = SarBandNames.RV_DSPK


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


RAW_CLOUDS = CloudsBandNames.RAW_CLOUDS
CLOUDS = CloudsBandNames.CLOUDS
SHADOWS = CloudsBandNames.SHADOWS
CIRRUS = CloudsBandNames.CIRRUS  # Cirrus detected
ALL_CLOUDS = CloudsBandNames.ALL_CLOUDS


class DemBandNames(BandNames):
    """DEM Band names"""

    DEM = "DEM"
    """ DEM """

    SLOPE = "SLOPE"
    """ Slope """

    HILLSHADE = "HILLSHADE"
    """ Hillshade """


DEM = DemBandNames.DEM
SLOPE = DemBandNames.SLOPE
HILLSHADE = DemBandNames.HILLSHADE
