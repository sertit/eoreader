import datetime
import logging
from collections import defaultdict
from enum import unique
from functools import reduce

import geopandas as gpd
import numpy as np
import xarray as xr
from lxml import etree
from rasterio.enums import Resampling
from sertit import geometry, path, rasters, types
from sertit.misc import ListEnum
from sertit.types import AnyPathStrType, AnyPathType

from eoreader import DATETIME_FMT, EOREADER_NAME, cache, utils
from eoreader.bands import (
    BLUE,
    GREEN,
    NARROW_NIR,
    NIR,
    RED,
    VRE_1,
    VRE_2,
    VRE_3,
    BandNames,
    SpectralBand,
    is_mask,
    to_band,
    to_str,
)
from eoreader.bands.band_names import (
    ALL_CLOUDS,
    CA,
    CIRRUS,
    CLOUDS,
    DEEP_BLUE,
    RAW_CLOUDS,
    SHADOWS,
    WV,
    YELLOW,
    VenusMaskBandNames,
)
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.keywords import ASSOCIATED_BANDS
from eoreader.products import OpticalProduct
from eoreader.products.optical.optical_product import RawUnits
from eoreader.stac import CENTER_WV, FWHM, GSD, ID, NAME
from eoreader.utils import simplify

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class VenusProductType(ListEnum):
    """Venus products types (L2A)"""

    L2A = "VSC"
    """Level-2A: https://www.mdpi.com/2072-4292/14/14/3281"""


class VenusProduct(OpticalProduct):
    def __init__(
        self,
        product_path: AnyPathStrType,
        archive_path: AnyPathStrType = None,
        output_path: AnyPathStrType = None,
        remove_tmp: bool = False,
        **kwargs,
    ) -> None:
        # Initialization from the super class
        super().__init__(product_path, archive_path, output_path, remove_tmp, **kwargs)

    def _pre_init(self, **kwargs) -> None:
        """
        TODO : same as s2_theia_product
        """
        self._has_cloud_cover = True
        self.needs_extraction = False
        self._use_filename = True
        self._raw_units = RawUnits.REFL

        # Pre init done by the super class
        super()._pre_init(**kwargs)

    def _post_init(self, **kwargs) -> None:
        """
        TODO : same as s2_theia_product
        """
        self.tile_name = self._get_tile_name()

        # Post init done by the super class
        super()._post_init(**kwargs)

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        """
        self.pixel_size = 5.0

    def _get_tile_name(self) -> str:
        """
        TODO : same as s2_theia_product
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        tile = root.findtext(".//GEOGRAPHICAL_ZONE")
        if not tile:
            raise InvalidProductError("GEOGRAPHICAL_ZONE not found in metadata!")
        return tile

    def _set_product_type(self) -> None:
        """Set products type"""
        self.product_type = VenusProductType.L2A

    def _set_instrument(self) -> None:
        """
        Set instrument

        VENµS : https://database.eohandbook.com/database/missionsummary.aspx?missionID=601&utm_source=eoportal&utm_content=venus
        """
        self.instrument = "VSC"

    def _map_bands(self) -> None:
        """
        Map bands
        """
        venus_bands = {
            DEEP_BLUE: SpectralBand(
                eoreader_name=DEEP_BLUE,
                **{NAME: "B1", ID: "1", GSD: 5, CENTER_WV: 420, FWHM: 40},
            ),
            CA: SpectralBand(
                eoreader_name=CA,
                **{NAME: "B2", ID: "2", GSD: 5, CENTER_WV: 443, FWHM: 40},
            ),
            BLUE: SpectralBand(
                eoreader_name=BLUE,
                **{NAME: "B3", ID: "3", GSD: 5, CENTER_WV: 490, FWHM: 40},
            ),
            GREEN: SpectralBand(
                eoreader_name=GREEN,
                **{NAME: "B4", ID: "4", GSD: 5, CENTER_WV: 555, FWHM: 40},
            ),
            YELLOW: SpectralBand(
                eoreader_name=YELLOW,
                **{NAME: "B5", ID: "5", GSD: 5, CENTER_WV: 620, FWHM: 40},
            ),
            RED: SpectralBand(
                eoreader_name=RED,
                **{NAME: "B7", ID: "7", GSD: 5, CENTER_WV: 667, FWHM: 30},
            ),
            VRE_1: SpectralBand(
                eoreader_name=VRE_1,
                **{NAME: "B8", ID: "8", GSD: 5, CENTER_WV: 702, FWHM: 24},
            ),
            VRE_2: SpectralBand(
                eoreader_name=VRE_2,
                **{NAME: "B9", ID: "9", GSD: 5, CENTER_WV: 742, FWHM: 16},
            ),
            VRE_3: SpectralBand(
                eoreader_name=VRE_3,
                **{NAME: "B10", ID: "10", GSD: 5, CENTER_WV: 782, FWHM: 16},
            ),
            NIR: SpectralBand(
                eoreader_name=NIR,
                **{NAME: "B11", ID: "11", GSD: 5, CENTER_WV: 865, FWHM: 40},
            ),
            NARROW_NIR: SpectralBand(
                eoreader_name=NARROW_NIR,
                **{NAME: "B11", ID: "11", GSD: 5, CENTER_WV: 865, FWHM: 40},
            ),
            WV: SpectralBand(
                eoreader_name=WV,
                **{NAME: "B12", ID: "12", GSD: 5, CENTER_WV: 910, FWHM: 20},
            ),
        }
        self.bands.map_bands(venus_bands)

    @cache
    @simplify
    def footprint(self) -> gpd.GeoDataFrame:
        """
        TODO : almost the same as s2_theia_product
        """
        edg_path = self._get_mask_path(
            VenusMaskBandNames.EDG.name
        )  # there is no additional parameters
        mask = utils.read(edg_path, masked=False)

        # Vectorize the nodata band
        footprint = rasters.vectorize(mask, values=0, default_nodata=1)
        footprint = geometry.get_wider_exterior(footprint)
        footprint.geometry = footprint.geometry.convex_hull

        return footprint

    def get_datetime(self, as_datetime: bool = False) -> str | datetime.datetime:
        """
        # TODO : almost the same as S2TheiaProduct
        """
        if self.datetime is None:
            # Get MTD XML file
            root, _ = self.read_mtd()

            # Open identifier
            acq_date = root.findtext(".//ACQUISITION_DATE")
            if not acq_date:
                raise InvalidProductError("ACQUISITION_DATE not found in metadata!")

            # Convert to datetime
            date = datetime.datetime.strptime(
                acq_date, "%Y-%m-%dT%H:%M:%S.%f"
            )  # no 'Z' at the end
        else:
            date = self.datetime

        if not as_datetime:
            date = date.strftime(DATETIME_FMT)
        return date

    def _get_name_constellation_specific(self) -> str:
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        name = path.get_filename(root.findtext(".//IDENTIFIER"))
        if not name:
            raise InvalidProductError("IDENTIFIER not found in metadata!")

        return name

    def get_band_paths(
        self, band_list: list, pixel_size: float = None, **kwargs
    ) -> dict:
        """
        TODO : same as s2_theia
        TODO : FRE vs SRE, optionnal ?
        TODO : not mandatory ?
        """
        band_paths = {}
        for band in band_list:  # Get clean band path
            clean_band = self.get_band_path(band, pixel_size=pixel_size, **kwargs)
            if clean_band.is_file():
                band_paths[band] = clean_band
            else:
                band_id = self.bands[band].id
                try:
                    if self.is_archived:
                        band_paths[band] = self._get_archived_rio_path(
                            rf".*FRE_B{band_id}\.tif"
                        )
                    else:
                        band_paths[band] = path.get_file_in_dir(
                            self.path, f"FRE_B{band_id}.tif"
                        )
                except (FileNotFoundError, IndexError) as ex:
                    raise InvalidProductError(
                        f"Non existing {band.name} ({band_id}) band for {self.path}"
                    ) from ex

        return band_paths

    def _read_band(
        self,
        band_path: AnyPathType,
        band: BandNames = None,
        pixel_size: tuple | list | float = None,
        size: list | tuple = None,
        **kwargs,
    ) -> xr.DataArray:
        """
        TODO : same as s2_theia_product
        """
        band_arr = utils.read(
            band_path,
            pixel_size=pixel_size,
            size=size,
            resampling=kwargs.pop("resampling", self.band_resampling),
            **kwargs,
        )

        # Convert type if needed
        if band_arr.dtype != np.float32:
            band_arr = band_arr.astype(np.float32)

        return band_arr

    def _to_reflectance(
        self,
        band_arr: xr.DataArray,
        band_path: AnyPathType,
        band: BandNames,
        **kwargs,
    ) -> xr.DataArray:
        """
        TODO : almost the same as s2_theia_product
        """
        # Compute the correct radiometry of the band for raw band
        if path.get_filename(band_path).startswith("VENUS"):
            band_arr /= 10000.0

        # Convert type if needed
        if band_arr.dtype != np.float32:
            band_arr = band_arr.astype(np.float32)

        return band_arr

    def _manage_invalid_pixels(
        self,
        band_arr: xr.DataArray,
        band: BandNames,
        pixel_size: float = None,
        **kwargs,
    ) -> xr.DataArray:
        """
        TODO : Almost the same as s2_theia_product
        TODO : EDG, SAT and invalid pixels as parameters ?
        """
        # -- Manage nodata from Theia band array
        # Theia nodata is already processed
        no_data_mask = np.where(
            band_arr.data == self._raw_nodata, self._mask_true, self._mask_false
        ).astype(np.uint8)

        # Open NODATA pixels mask
        edg_mask = self._open_mask(
            VenusMaskBandNames.EDG,
            pixel_size=pixel_size,
            size=(band_arr.rio.width, band_arr.rio.height),
            **kwargs,
        )
        sat_mask = self._open_mask(
            VenusMaskBandNames.SAT,
            associated_band=band,
            pixel_size=pixel_size,
            size=(band_arr.rio.width, band_arr.rio.height),
            **kwargs,
        )

        # Combine masks
        mask = no_data_mask | edg_mask.data | sat_mask.data

        # Open defective pixels (optional mask)
        try:
            def_mask = self._open_mask(
                VenusMaskBandNames.PIX,
                associated_band=band,
                pixel_size=pixel_size,
                size=(band_arr.rio.width, band_arr.rio.height),
                **kwargs,
            )
            mask = mask | def_mask.data
        except InvalidProductError:
            pass

        # -- Merge masks
        return self._set_nodata_mask(band_arr, mask)

    def _manage_nodata(
        self,
        band_arr: xr.DataArray,
        band: BandNames,
        pixel_size: float = None,
        **kwargs,
    ) -> xr.DataArray:
        """
        TODO : Same as s2_theia_product
        """
        # -- Manage nodata from Theia band array
        # Theia nodata is already processed
        no_data_mask = np.where(
            band_arr.data == self._raw_nodata, self._mask_true, self._mask_false
        ).astype(np.uint8)

        # -- Merge masks
        return self._set_nodata_mask(band_arr, no_data_mask)

    def _reorder_loaded_bands_like_input(
        self, bands: list, bands_dict: dict, **kwargs
    ) -> dict:
        """
        TODO : Same as s2_theia_product
        """
        reordered_dict = {}
        associated_bands = self._sanitized_associated_bands(
            bands, kwargs.get(ASSOCIATED_BANDS)
        )

        for band in bands:
            if associated_bands and band in associated_bands:
                for associated_band in associated_bands[band]:
                    key = self._get_band_key(band, associated_band, **kwargs)
                    reordered_dict[key] = bands_dict[key]
            else:
                key = self._get_band_key(band, associated_band=None, **kwargs)
                reordered_dict[key] = bands_dict[key]

        return reordered_dict

    def _sanitized_associated_bands(self, bands: list, associated_bands: dict) -> dict:
        """
        Sanitizes the associated bands
        -> convert all inputs to BandNames

        Args:
            bands (list): Band wanted
            associated_bands (dict): Associated bands

        Returns:
            dict: Sanitized associated bands
        """
        sanitized_associated_bands = {}

        if associated_bands:
            for key, val in associated_bands.items():
                if val != [None]:
                    sanitized_associated_bands[to_band(key, as_list=False)] = to_band(
                        val
                    )

        for band in bands:
            if is_mask(band) and band not in sanitized_associated_bands:
                if band in [VenusMaskBandNames.SAT, VenusMaskBandNames.PIX]:
                    raise ValueError(
                        f"Associated spectral band not given to the {band.name} mask. "
                        f"{[VenusMaskBandNames.SAT.name, VenusMaskBandNames.PIX.name]} masks are band-specific so giving an associated band is mandatory."
                    )
                else:
                    sanitized_associated_bands[band] = [None]
        return sanitized_associated_bands

    def _get_mask_path(self, mask_id: str) -> AnyPathType:
        """
        TODO : almost the same as s2_theia_product
        """
        mask_regex = f"*{mask_id}_XS.tif"  # XS
        try:
            if self.is_archived:
                mask_path = self._get_archived_rio_path(mask_regex.replace("*", ".*"))
            else:
                mask_path = path.get_file_in_dir(
                    self.path.joinpath("MASKS"), mask_regex, exact_name=True
                )
        except (FileNotFoundError, IndexError) as ex:
            raise InvalidProductError(
                f"Non existing mask {mask_regex} in {self.name}"
            ) from ex

        return mask_path

    def _has_mask(self, mask: BandNames) -> bool:
        """
        TODO : almost the same as s2_theia_product
        """
        return mask in [
            VenusMaskBandNames.PIX,  # Venus specific
            VenusMaskBandNames.EDG,
            VenusMaskBandNames.SAT,
            VenusMaskBandNames.MG2,
            VenusMaskBandNames.IAB,
            VenusMaskBandNames.CLM,
            VenusMaskBandNames.USI,  # Venus specific
        ]

    def _load_masks(
        self,
        bands: list,
        pixel_size: float = None,
        size: list | tuple = None,
        **kwargs,
    ) -> dict:
        """
        TODO : same as s2_theia_product
        """
        band_dict = {}
        if bands:
            # First, try to open the cloud band written on disk
            bands_to_load = []
            associated_bands_to_load = defaultdict(list)

            # Sanitize associated bands
            associated_bands = self._sanitized_associated_bands(
                bands, kwargs.get(ASSOCIATED_BANDS)
            )
            # Update kwargs with sanitized associated bands
            if associated_bands:
                kwargs[ASSOCIATED_BANDS] = associated_bands_to_load

            for band in bands:
                for associated_band in associated_bands[band]:
                    key = self._get_band_key(band, associated_band, **kwargs)
                    mask_path = self.get_band_path(
                        key,
                        pixel_size,
                        size,
                        writable=False,
                        **kwargs,
                    )
                    if mask_path.is_file():
                        band_dict[key] = utils.read(mask_path)
                    else:
                        bands_to_load.append(band)
                        associated_bands_to_load[band].append(associated_band)

            # Then load other bands that haven't been loaded before
            loaded_bands = self._open_masks(
                bands_to_load,
                pixel_size,
                size,
                **kwargs,
            )

            # Write them on disk
            for band_id, band_arr in loaded_bands.items():
                mask_path = self.get_band_path(
                    band_id, pixel_size, size, writable=True, **kwargs
                )
                band_arr = utils.write_path_in_attrs(band_arr, mask_path)
                utils.write(
                    band_arr,
                    mask_path,
                    dtype=band_arr.encoding["dtype"],  # This field is mandatory
                    nodata=band_arr.encoding.get("_FillValue"),
                )

            # Merge the dict
            band_dict.update(loaded_bands)

        return band_dict

    def _open_masks(
        self,
        bands: list,
        pixel_size: float = None,
        size: list | tuple = None,
        **kwargs,
    ) -> dict:
        """
        TODO : same as s2_theia_product
        """
        band_dict = {}

        associated_bands = self._sanitized_associated_bands(
            bands, kwargs.get(ASSOCIATED_BANDS)
        )

        for band in bands:
            for associated_band in associated_bands[band]:
                # Create the key for the output dict
                key = self._get_band_key(band, associated_band, **kwargs)

                # Open mask
                LOGGER.debug(f"Loading {to_str(key, as_list=False)} mask")
                band_arr = self._open_mask(
                    band, associated_band, pixel_size, size, **kwargs
                )

                # Get the dict key (manage SAT and DFP masks with associated spectral bands)
                band_dict[key] = band_arr

        return band_dict

    def _open_mask(
        self,
        band: BandNames,
        associated_band: BandNames = None,
        pixel_size: float = None,
        size: list | tuple = None,
        **kwargs,
    ) -> xr.DataArray:
        """
        TODO : almost the same as s2_theia_product
        """
        # Just to choose between R1 and R2 here -> take R1
        if associated_band is None:
            associated_band = self.get_default_band()

        mask_path = self._get_mask_path(band.name)

        # Open SAT band
        mask = utils.read(
            mask_path,
            pixel_size=pixel_size,
            size=size,
            resampling=Resampling.nearest,  # Nearest to keep the flags
            masked=False,
            as_type=np.uint8,
            **kwargs,
        )

        if band in [VenusMaskBandNames.SAT, VenusMaskBandNames.PIX]:
            mask = mask.copy(data=utils.read_bit_array(mask, 0))  # TODO : check 0

        band_name = self._get_band_key(band, associated_band, as_str=True, **kwargs)
        mask.attrs["long_name"] = band_name
        return mask.rename(band_name)

    def _load_bands(
        self,
        bands: list,
        pixel_size: float = None,
        size: list | tuple = None,
        **kwargs,
    ) -> dict:
        """
        TODO : same as s2_theia_product
        """
        # Return empty if no band are specified
        if not bands:
            return {}

        # Get band paths
        band_paths = self.get_band_paths(bands, pixel_size=pixel_size, **kwargs)

        # Open bands and get array (resampled if needed)
        band_arrays = self._open_bands(
            band_paths, pixel_size=pixel_size, size=size, **kwargs
        )

        return band_arrays

    def _get_condensed_name(self) -> str:
        """
        Get products condensed name ({date}_VENUS_{tile]_{product_type}).

        Returns:
            str: Condensed name
        """
        return f"{self.get_datetime()}_VENUS_{self.tile_name}_{self.product_type.name}"

    @cache
    def get_mean_sun_angles(self) -> (float, float):
        """
        TODO : same as s2_theia_product
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        try:
            mean_sun_angles = root.find(".//Sun_Angles")
            zenith_angle = float(mean_sun_angles.findtext("ZENITH_ANGLE"))
            azimuth_angle = float(mean_sun_angles.findtext("AZIMUTH_ANGLE"))
        except TypeError as exc:
            raise InvalidProductError(
                "Azimuth or Zenith angles not found in metadata!"
            ) from exc

        return azimuth_angle, zenith_angle

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read metadata and outputs the metadata XML root and its namespaces as a dict

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"VENUS-XS_20201029-105210-000_L2A_SUDOUE-1_C_V3-1.zip"
            >>> prod = Reader().open(path)
            >>> prod.read_mtd()
            (<Element Muscate_Metadata_Document at 0x252d2071e88>, {})

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces
        """

        # TODO : same as S2TheiaProduct
        mtd_from_path = "MTD_ALL.xml"
        mtd_archived = r"MTD_ALL\.xml"

        return self._read_mtd_xml(mtd_from_path, mtd_archived)

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this product has the specified cloud band?
        """
        return True

    def _open_clouds(
        self,
        bands: list,
        pixel_size: float = None,
        size: list | tuple = None,
        **kwargs,
    ) -> dict:
        """
        Load cloud files as xarrays.

        Read VENUS cloud mask:
        https://www.cesbio.cnrs.fr/multitemp/format-of-ven%c2%b5s-l2a-produced-by-muscate/

        > cloud mask
            bit 0 (1) : all clouds except the thinnest and all shadows
            bit 1 (2) : all clouds (except the thinnest)
            bit 2 (4) : cloud shadows cast by a detected cloud
            bit 3 (8) : cloud shadows cast by a cloud outside image
            bit 4 (16) : clouds detected via mono-temporal thresholds
            bit 5 (32) : clouds detected via multi-temporal thresholds
            bit 6 (64) : thinnest clouds
            bit 7 (128) : high clouds detected by stereoscopy

        Args:
            bands (list): List of the wanted bands
            pixel_size (int): Band pixel size in meters
            size (Union[tuple, list]): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}

        if bands:
            # Get nodata mask
            masks = self._load_masks(
                [VenusMaskBandNames.EDG, VenusMaskBandNames.CLM],
                pixel_size=pixel_size,
                size=size,
            )
            nodata = masks[VenusMaskBandNames.EDG]
            clouds_mask = masks[VenusMaskBandNames.CLM]

            # Bit ids
            clouds_shadows_id = 0
            clouds_id = 1
            cirrus_id = 6
            shadows_in_id = 2
            shadows_out_id = 3

            for band in bands:
                if band == ALL_CLOUDS:
                    cloud = self._create_mask(
                        clouds_mask, [clouds_shadows_id, cirrus_id], nodata
                    )
                elif band == SHADOWS:
                    cloud = self._create_mask(
                        clouds_mask, [shadows_in_id, shadows_out_id], nodata
                    )
                elif band == CLOUDS:
                    cloud = self._create_mask(clouds_mask, clouds_id, nodata)
                elif band == CIRRUS:
                    cloud = self._create_mask(clouds_mask, cirrus_id, nodata)
                elif band == RAW_CLOUDS:
                    cloud = clouds_mask
                else:
                    raise InvalidTypeError(
                        "Non-existing cloud band for Sentinel-2 THEIA."
                    )

                # Rename
                band_name = to_str(band)[0]

                # Multi bands -> do not change long name
                if band != RAW_CLOUDS:
                    cloud.attrs["long_name"] = band_name
                band_dict[band] = cloud.rename(band_name).astype(np.float32)

        return band_dict

    def _create_mask(
        self, bit_array: xr.DataArray, bit_ids: int | list, nodata: np.ndarray
    ) -> xr.DataArray:
        """
        # TODO : same as S2TheiaProduct
        """
        bit_ids = types.make_iterable(bit_ids)
        conds = utils.read_bit_array(bit_array.astype(np.uint8), bit_ids)
        cond = reduce(lambda x, y: x | y, conds)  # Use every condition (bitwise or)

        return super()._create_mask(bit_array, cond, nodata)

    def get_quicklook_path(self) -> str:
        """
        TODO : same as s2_theia_product
        """
        quicklook_path = None
        try:
            if self.is_archived:
                quicklook_path = self.path / self._get_archived_path(
                    regex=r".*QKL_ALL\.jpg"
                )
            else:
                quicklook_path = next(self.path.glob("**/*QKL_ALL.jpg"))
            quicklook_path = str(quicklook_path)
        except (StopIteration, FileNotFoundError):
            LOGGER.warning(f"No quicklook found in {self.condensed_name}")

        return quicklook_path

    @cache
    def get_cloud_cover(self) -> float:
        """
        TODO : same as s2_theia_product
        """
        # Get MTD XML file
        root, nsmap = self.read_mtd()

        # Get the cloud cover
        try:
            cc = float(root.findtext(".//QUALITY_INDEX[@name='CloudPercent']"))
        except (InvalidProductError, TypeError):
            LOGGER.warning(
                "'QUALITY_INDEXQUALITY_INDEX name='CloudPercent'' not found in metadata!"
            )
            cc = 0

        return cc
