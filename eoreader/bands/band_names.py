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

    DEEP_BLUE = "DEEP_BLUE"
    """Deep Blue"""

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
DEEP_BLUE = SpectralBandNames.DEEP_BLUE
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
    def is_speckle(cls, band: "SarBandNames"):
        """
        Returns True if the band corresponds to a speckle one.

        .. code-block:: python

            >>> SarBandNames.is_despeckle(SarBandNames.VV)
            True
            >>> SarBandNames.is_despeckle(SarBandNames.VV_DSPK)
            False

        Args:
            band (SarBandNames): Band to test

        Returns:
            SarBandNames: Despeckled band
        """
        return not cls.is_despeckle(band)

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


class MaskBandNames(BandNames):
    """
    Mask Band names: Base class to make isinstance work
    -> nothing mapped here, to be done per product I suppose...

    Only single band masks will be managed.
    """

    #

    # -- DIMAP v1 --
    # None

    # -- Maxar --
    # None

    # -- Sentinel-3 --
    # TODO: Sentinel-3 masks not implemented yet (write an issue on GitHub if needed!)
    # More complex than for other products because of the an/in/... suffixes

    # -- SV1 --
    # None

    pass


class DimapV2MaskBandNames(MaskBandNames):
    """DIMAP v2 Mask Band names"""

    CLD = "CLD"
    """ DIMAP v2 mask - Cloud vector mask """

    DET = "DET"
    """ DIMAP v2 mask - Out of order detectors vector mask """

    QTE = "QTE"
    """ DIMAP v2 mask - Synthetic technical quality vector mask """

    ROI = "ROI"
    """ DIMAP v2 mask - Region of Interest vector mask """

    SLT = "SLT"
    """ DIMAP v2 mask - Straylight vector mask """

    SNW = "SNW"
    """ DIMAP v2 mask - Snow vector mask """

    VIS = "VIS"
    """ DIMAP v2 mask - Hidden area vector mask (optional) """


class HlsMaskBandNames(MaskBandNames):
    """HLS Mask Band names"""

    FMASK = "Fmask"
    """ HLS mask - Fmask """

    SAA = "SAA"
    """ HLS and Landsat (collection 2) mask - SAA """

    SZA = "SZA"
    """ HLS and Landsat (collection 2) mask - SZA """

    VAA = "VAA"
    """ HLS and Landsat (collection 2) mask - VAA """

    VZA = "VZA"
    """ HLS and Landsat (collection 2) mask - VZA """


class LandsatMaskBandNames(MaskBandNames):
    """Landsat Mask Band names"""

    # COL_1
    BQA = "BQA"
    """ Landsat mask (collection 1) - BQA """

    # COL_2
    QA_PIXEL = "QA_PIXEL"
    """ Landsat mask (collection 2) - Quality Assessment pixel """

    QA_RADSAT = "QA_RADSAT"
    """ Landsat mask (collection 2) - QA_RADSAT """

    # Level 1
    SAA = "SAA"
    """ Landsat (collection 2) mask - SAA """

    SZA = "SZA"
    """ Landsat (collection 2) mask - SZA """

    VAA = "VAA"
    """ Landsat (collection 2) mask - VAA """

    VZA = "VZA"
    """ Landsat (collection 2) mask - VZA """

    # Level 2
    SR_QA_AEROSOL = "SR_QA_AEROSOL"
    """ Landsat mask (collection 2, level 2) - SR_QA_AEROSOL """

    ST_QA = "ST_QA"
    """ Landsat mask (collection 2, level 2) - ST_QA """


class PlanetMaskBandNames(MaskBandNames):
    """Planet Mask Band names"""

    # -- Planet --
    # https://developers.planet.com/docs/data/udm-2/#udm21-bands
    # UDM2 = "UDM2"
    # """ Planet mask - Usable Data Mask - 8 bands """
    # Not implemented (multi band mask)

    CLEAR = "CLEAR"
    """ Planet mask - Usable Data Mask - First band - Clear map """

    SNOW = "SNOW"
    """ Planet mask - Usable Data Mask - 2nd band - Snow map """

    SHADOW = "SHADOW"
    """ Planet mask - Usable Data Mask - 3rd band - Shadow map """

    LIGHT_HAZE = "LIGHT_HAZE"
    """ Planet mask - Usable Data Mask - 4th band - Light haze map """

    HEAVY_HAZE = "HEAVY_HAZE"
    """ Planet mask - Usable Data Mask - 5th band - Heavy haze map (not supported by UDM 2.1 onward) """

    CLOUD = "CLOUD"
    """ Planet mask - Usable Data Mask - 6th band - Cloud map """

    CONFIDENCE = "CONFIDENCE"
    """ Planet mask - Usable Data Mask - 7th band - Confidence map """

    UNUSABLE = "UNUSABLE"
    """ Planet mask - Usable Data Mask - 8th band - Unusable pixels (Equivalent to the UDM asset)"""

    UDM = "UDM"
    """ Planet mask - Unusable Data Mask (Legacy) """


class S2MaskBandNames(MaskBandNames):
    """Sentinel-2 Mask Band names"""

    DETFOO = "DETFOO"
    """ Sentinel-2 mask - Detectors footprint (Legacy) """

    # Processing baseline < 04.00
    TECQUA = "TECQUA"
    """ Sentinel-2 mask - Technical quality mask """

    DEFECT = "DEFECT"
    """ Sentinel-2 mask (band 5 in MSK_QUALIT for processing baseline >= 04.00) - Defective pixels """

    NODATA = "NODATA"
    """ Sentinel-2 mask (band 6 and 7 in MSK_QUALIT for processing baseline >= 04.00) - Pixel nodata (inside the detectors) """

    SATURA = "SATURA"
    """ Sentinel-2 mask (band 8 in MSK_QUALIT for processing baseline >= 04.00) - Saturated Pixels mask """

    # Processing baseline >= 04.00
    # https://sentiwiki.copernicus.eu/__attachments/1692737/S2-PDGS-CS-DI-PSD%20-%20S2%20Product%20Specification%20Document%202024%20-%2015.0.pdf
    # table 107
    # MSK_QUALIT
    ANC_LOST = "MSK_QUALIT_ANC_LOST"
    """ Sentinel-2 mask (band 1 in MSK_QUALIT for processing baseline >= 04.00) - Ancillary lost data """

    ANC_DEG = "MSK_QUALIT_ANC_DEG"
    """ Sentinel-2 mask (band 2 in MSK_QUALIT for processing baseline >= 04.00) - Ancillary degraded data  """

    MSI_LOST = "MSK_QUALIT_MSI_LOST"
    """ Sentinel-2 mask (band 3 in MSK_QUALIT for processing baseline >= 04.00) - MSI lost data """

    MSI_DEG = "MSK_QUALIT_MSI_DEG"
    """ Sentinel-2 mask (band 4 in MSK_QUALIT for processing baseline >= 04.00) - MSI degraded data """

    QT_DEFECTIVE_PIXELS = "MSK_QUALIT_QT_DEFECTIVE_PIXELS"
    """ Sentinel-2 mask (band 5 in MSK_QUALIT for processing baseline >= 04.00) - Defective pixels (matching defective columns) """

    QT_NODATA_PIXELS = "MSK_QUALIT_QT_NODATA_PIXELS"
    """ Sentinel-2 mask (band 6 in MSK_QUALIT for processing baseline >= 04.00) - No–data pixels """

    QT_PARTIALLY_CORRECTED_PIXELS = "MSK_QUALIT_QT_PARTIALLY_CORRECTED_PIXELS"
    """ Sentinel-2 mask (band 7 in MSK_QUALIT for processing baseline >= 04.00) - Pixels partially corrected during cross-talk processing."""

    QT_SATURATED_PIXELS = "MSK_QUALIT_QT_SATURATED_PIXELS"
    """
    Sentinel-2 mask (band 8 in MSK_QUALIT for processing baseline >= 04.00) - Saturated pixels"""

    # Only for L1B and L1A
    # CLOUD_INV = "MSK_QUALIT_CLOUD_INV"
    # """ Sentinel-2 mask (band 9 in MSK_QUALIT for processing baseline >= 04.00) - Coarse cloud masks """

    # MSK_CLASSI
    OPAQUE = "MSK_CLASSI_OPAQUE"
    """ Sentinel-2 mask (band 1 in MSK_CLASSI for processing baseline >= 04.00) - Opaque clouds """

    CIRRUS = "MSK_CLASSI_CIRRUS"
    """ Sentinel-2 mask (band 2 in MSK_CLASSI for processing baseline >= 04.00) - Cirrus clouds """

    SNOW_ICE = "MSK_CLASSI_SNOW_ICE"
    """ Sentinel-2 mask (band 3 in MSK_CLASSI for processing baseline >= 04.00) - Snow and Ice areas """

    # L2A
    CLDPRB = "CLDPRB"
    """ Sentinel-2 mask (L2A only) - Clouds probability (equals 'CLOUDS_RAW')"""

    SNWPRB = "SNWPRB"
    """ Sentinel-2 mask (L2A only) - Snow probability """


class S2TheiaMaskBandNames(MaskBandNames):
    """Sentinel-2 Theia Mask Band names"""

    # THEIA
    DFP = "DFP"
    """ Sentinel-2 THEIA mask - Defective pixels """

    EDG = "EDG"
    """ Sentinel-2 THEIA mask - Nodata pixels """

    SAT = "SAT"
    """ Sentinel-2 THEIA mask - Saturated pixels """

    MG2 = "MG2"
    """ Sentinel-2 THEIA mask - Geophysical mask (classification) """

    IAB = "IAB"
    """ Sentinel-2 THEIA mask - Mask where water vapor and TOA pixels have been interpolated """

    CLM = "CLM"
    """ Sentinel-2 THEIA mask - Cloud masks """


class VenusMaskBandNames(MaskBandNames):
    """Venus Theia Mask Band names"""

    CLM = "CLM"
    """ Venus mask - Cloud masks """

    EDG = "EDG"
    """ Venus mask - Nodata pixels """

    SAT = "SAT"
    """ Venus mask - Saturated pixels """

    MG2 = "MG2"
    """ Venus mask - Geophysical mask (classification) """

    IAB = "IAB"
    """ Venus mask - Mask where water vapor and TOA pixels have been interpolated """

    PIX = "PIX"
    """ Venus mask - Aberrant_Pixels """

    USI = "USI"
    """ Venus mask - Useful Image """


# Mask bands are not exposed as other bands (great risks of overlap between names!)


class Sentinel2L2ABands(BandNames):
    """Sentinel-2 L2A specific Band names"""

    AOT = "AOT"
    """ Sentinel-2 L2A specific band - Aerosol Optical Thickness (Quality assurance band) """

    WVP = "WVP"
    """ Sentinel-2 L2A specific band - Water Vapour (Quality assurance band) """

    SCL = "SCL"
    """ Sentinel-2 L2A specific band - Scene Classification Layer (Quality assurance band) """

    # TCI = "TCI"
    # """ Sentinel-2 L2A specific band - True Color Image """
    # Not implemented (multi-band band, how to solve that? TCI-R, TCI-G, TCI-B?) -> Open a GitHub issue if needed!


AOT = Sentinel2L2ABands.AOT
WVP = Sentinel2L2ABands.WVP
SCL = Sentinel2L2ABands.SCL
# TCI = Sentinel2L2ABands.TCI
