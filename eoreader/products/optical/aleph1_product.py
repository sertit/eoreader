# Copyright 2026, SERTIT-ICube - France, https://sertit.unistra.fr/
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
"""
Aleph-1 (Satellogic) products https://developers.satellogic.com/imagery-products/introduction.html
"""

import json
import logging
from datetime import datetime
from enum import unique

import geopandas as gpd
import numpy as np
import xarray as xr
from dicttoxml import dicttoxml
from lxml import etree
from sertit import files, path, vectors
from sertit.misc import ListEnum
from sertit.types import AnyPathType

from eoreader import DATETIME_FMT, EOREADER_NAME, cache
from eoreader.bands import (
    ALL_CLOUDS,
    BLUE,
    CIRRUS,
    CLOUDS,
    GREEN,
    NARROW_NIR,
    NIR,
    RAW_CLOUDS,
    RED,
    BandNames,
    SpectralBand,
    to_str,
)
from eoreader.bands.band_names import Aleph1MaskBandNames
from eoreader.exceptions import InvalidProductError, InvalidTypeError
from eoreader.products import VhrProduct
from eoreader.products.optical.optical_product import RawUnits
from eoreader.stac import GSD, ID, NAME, WV_MAX, WV_MIN
from eoreader.utils import qck_wrapper, simplify

LOGGER = logging.getLogger(EOREADER_NAME)


@unique
class Aleph1ProductType(ListEnum):
    """Aleph-1 (Satellogic) product types (processing levels)"""

    L0 = "Raw"
    """
    The L0 Product is the rawest product from Satellogic’s products family. 
    It is composed by the raw frames coming directly from the sensor of the payloads without any modification or processing, along with the necessary metadata. 
    The frames are simple packaged in a standardized format to create the L0 product. The units of each raster are in DNs directly from the sensor.
    
    See: https://developers.satellogic.com/imagery-products/l0.html
    
    **Not handled by EOReader**
    """

    L1A = "Raw corrected"
    """
    The L1A Product is a raw, but corrected product from Satellogic’s products family. 
    It is composed by the raw frames that have been radiometrically corrected along with the necessary metadata.

    The algorithms applied to the L0 data to convert it into L1A are: 
    
    - Artifacts removals 
    - PSF Deconvolution 
    - Radiometric correction to Top of the atosmphere units 
    - HDR (combining 2 L0 frames with different exposures, only on Mark V) 
    - Stray light correction 
    - NO-data and cloud mask calculation
    
    See: https://developers.satellogic.com/imagery-products/l1a.html
    
    **Not handled by EOReader**    
    """

    L1B = "L1 Basic"
    """
    The L1 Basic (aka L1B and QuickView) product is a 4-band (RGB and Near infrared) product characterised by its low processing time and that can be generated from Mark IV and Mark V satellites raw imagery. 
    It is geolocated and projected to the ground but not orthorectified and it is presented at native resolution. 
    This implies that different captures may have different pixel sizes depending on the altitude and the off-nadir angle of the satellite at capture time. 
    This imagery product is currently used in Rapid Response products, as well as the base collection to browse the archive. 
    
    See: https://developers.satellogic.com/imagery-products/l1basic.html
    
    ✅ **Handled by EOReader**    
    """

    L1C = "Ortho ready"
    """
    The Ortho Ready (L1C) product is a 4-band imagery dataset designed for users who wish to perform their own orthorectification using a Digital Elevation Model (DEM) of their choice. 
    The 16-bit, 4-band rasters (visual and near-infrared) are provided with Rational Polynomial Coefficients (RPCs). 
    By combining the imagery, the RPCs, and a DEM, users can generate their own geometrically corrected, orthorectified images. 
    
    See: https://developers.satellogic.com/imagery-products/ortho_ready.html
    
    **Not handled by EOReader**    
    """

    L1D = "Ortho"
    """
    The L1D and L1D_SR imagery products are 4-band (RGB and Near infrared) product designed for accuracy and best of class image quality. 
    It is delivered to customers after going through radiometric and geometric correction process.
    
    See: https://developers.satellogic.com/imagery-products/ortho.html
    
    ✅ **Handled by EOReader**    
    """

    L1D_SR = "Ortho Super Resolution"
    """
    The L1D and L1D_SR imagery products are 4-band (RGB and Near infrared) product designed for accuracy and best of class image quality. 
    It is delivered to customers after going through radiometric and geometric correction process.
    
    See: https://developers.satellogic.com/imagery-products/ortho.html
    
    ✅ **Handled by EOReader**    
    """


@unique
class Aleph1Instrument(ListEnum):
    """Aleph-1 (Satellogic) instrument
    See `Satellogic documentation <https://developers.satellogic.com/imagery-products/msi_payload_specifications.html>`_ for more information.
    """

    MARKIV = "MarkIV"
    """
    Mark IV satellite generation
    """

    MARKV = "MarkV"
    """
    Mark V satellite generation
    """

    UNKOWN = "Unknown"
    """
    Missing instrument in mtd (older versions)
    """


class Aleph1Product(VhrProduct):
    """
    Class for Aleph-1 (Satellogic) products
    """

    def _pre_init(self, **kwargs) -> None:
        """
        Function used to pre_init the products
        (setting needs_extraction and so on)
        """
        self._raw_units = RawUnits.REFL
        self._has_cloud_cover = True
        self._use_filename = True
        self.needs_extraction = False

        # Pre init done by the super class
        super()._pre_init(**kwargs)

    def _set_pixel_size(self) -> None:
        """
        Set product default pixel size (in meters)
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        gsd = root.findtext(".//gsd")
        if not gsd:
            raise InvalidProductError("'gsd' not found in metadata!")

        # GSD varies according to the product type
        self.pixel_size = np.round(float(gsd), 2)

        # Images are captured with approximately 1m native resolution at nadir for all spectral bands
        # https://developers.satellogic.com/imagery-products/msi_payload_specifications.html#spatial-resolution
        self.resolution = 1.0

    @cache
    @simplify
    def footprint(self) -> gpd.GeoDataFrame:
        """
        Get real footprint in UTM of the products (without nodata, in french == emprise utile)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"LC08_L1GT_023030_20200518_20200527_01_T2"
            >>> prod = Reader().open(path)
            >>> prod.footprint
               index                                           geometry
            0      0  POLYGON ((366165.000 4899735.000, 366165.000 4...

        Overload of the generic function because landsat nodata seems to be different in QA than in regular bands.
        Indeed, nodata pixels vary according to the band sensor footprint,
        whereas QA nodata is where at least one band has nodata.

        We chose to keep QA nodata values for the footprint in order to show where all bands are valid.

        **TL;DR: We use the QA nodata value to determine the product's footprint**.

        Returns:
            gpd.GeoDataFrame: Footprint as a GeoDataFrame
        """
        return self._read_stac_mtd().to_crs(self.crs())

    @cache
    def extent(self) -> gpd.GeoDataFrame:
        """
        Get UTM extent of the tile, managing the case with not orthorectified bands.

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = "S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3"
            >>> prod = Reader().open(path)
            >>> prod.utm_extent()
                                                        geometry
            0  POLYGON ((1488846.028 6121896.451, 1488846.028...

        Returns:
            gpd.GeoDataFrame: Extent in UTM
        """
        extent = self.footprint().copy()
        extent.geometry = extent.envelope

        return extent

    def _set_product_type(self) -> None:
        """
        Set product type.
        """
        # Processing level
        prod_type = "L1D_SR" if "L1D_SR" in self.name else self.split_name[3]

        try:
            self.product_type = getattr(Aleph1ProductType, prod_type)
        except AttributeError as exc:
            raise InvalidProductError(
                f"Product type '{prod_type}' not handled by EOReader."
            ) from exc

        if self.product_type in [
            Aleph1ProductType.L0,
            Aleph1ProductType.L1A,
            Aleph1ProductType.L1C,
        ]:
            raise NotImplementedError(
                f"Satellogic {prod_type} products are not handled by EOReader yet."
            )

    def _set_instrument(self) -> None:
        """
        Set instrument
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        instrument = root.findtext(".//satellite_generation")
        if not instrument:
            version = root.findtext(".//product_version")
            LOGGER.warning(
                f"'satellite_generation' not found in metadata (maybe old product version: {version}). 'Unknown' instrument set by default."
            )
            instrument = "Unknown"

        self.instrument = Aleph1Instrument.from_value(instrument)

    def _map_bands(self) -> None:
        """
        Map bands
        """

        blue = SpectralBand(
            eoreader_name=BLUE,
            **{NAME: "BLUE", ID: 1, GSD: self.pixel_size, WV_MIN: 450, WV_MAX: 510},
        )

        green = SpectralBand(
            eoreader_name=GREEN,
            **{NAME: "GREEN", ID: 2, GSD: self.pixel_size, WV_MIN: 510, WV_MAX: 580},
        )

        red = SpectralBand(
            eoreader_name=RED,
            **{NAME: "RED", ID: 3, GSD: self.pixel_size, WV_MIN: 590, WV_MAX: 690},
        )

        nir = SpectralBand(
            eoreader_name=NIR,
            **{NAME: "NIR", ID: 4, GSD: self.pixel_size, WV_MIN: 750, WV_MAX: 900},
        )
        self.bands.map_bands(
            {
                BLUE: blue.update(id=3),
                GREEN: green.update(id=2),
                RED: red.update(id=1),
                NARROW_NIR: nir.update(id=4),
                NIR: nir.update(id=4),
            }
        )

    def get_datetime(self, as_datetime: bool = False) -> str | datetime:
        """
        Get the product's acquisition datetime, with format :code:`YYYYMMDDTHHMMSS` <-> :code:`%Y%m%dT%H%M%S`

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"LC08_L1GT_023030_20200518_20200527_01_T2"
            >>> prod = Reader().open(path)
            >>> prod.get_datetime(as_datetime=True)
            datetime.datetime(2020, 5, 18, 16, 34, 7)
            >>> prod.get_datetime(as_datetime=False)
            '20200518T163407'

        Args:
            as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string.

        Returns:
             str | dt.datetime: Its acquisition datetime
        """
        if self.datetime is None:
            # Get MTD XML file
            root, _ = self.read_mtd()

            # Open datetime
            acq_date = root.findtext(".//datetime")
            if not acq_date:
                raise InvalidProductError("'datetime' not found in metadata!")

            # Convert to datetime
            date = datetime.strptime(acq_date, "%Y-%m-%dT%H:%M:%S.%fZ")

        else:
            date = self.datetime

        if not as_datetime:
            date = date.strftime(DATETIME_FMT)

        return date

    def _get_name_constellation_specific(self) -> str:
        """
        Set product real name from metadata

        Returns:
            str: True name of the product (from metadata)
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open identifier
        return root.findtext(".//id")

    @cache
    def get_mean_sun_angles(self) -> (float, float):
        """
        Get Mean Sun angles (Azimuth and Zenith angles)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"IMG_PHR1A_PMS_001"
            >>> prod = Reader().open(path)
            >>> prod.get_mean_sun_angles()
            (45.6624568841367, 30.219881316357643)

        Returns:
            (float, float): Mean Azimuth and Zenith angle
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open zenith and azimuth angle
        zenith_angle = 90 - float(root.findtext(".//sun_elevation"))
        azimuth_angle = float(root.findtext(".//sun_azimuth"))

        return azimuth_angle, zenith_angle

    @cache
    def get_mean_viewing_angles(self) -> (float, float, float):
        """
        Get Mean Viewing angles (azimuth, off-nadir and incidence angles)

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_mean_viewing_angles()

        Returns:
            (float, float, float): Mean azimuth, off-nadir and incidence angles
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Open zenith and azimuth angle
        try:
            az = float(root.findtext(".//azimuth"))
            off_nadir = float(root.findtext(".//off_nadir"))
            incidence_angle = float(root.findtext(".//incidence_angle"))
        except TypeError as exc:
            raise InvalidProductError(
                "azimuth, off_nadir or incidence_angle not found in metadata!"
            ) from exc

        return az, off_nadir, incidence_angle

    @cache
    def get_cloud_cover(self) -> float:
        """
        Get cloud cover as given in the metadata

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.get_cloud_cover()
            55.5

        Returns:
            float: Cloud cover as given in the metadata
        """
        # Get MTD XML file
        root, _ = self.read_mtd()

        # Get the cloud cover
        try:
            try:
                cc = float(root.findtext(".//cloud_cover"))
            except TypeError as exc:
                raise InvalidProductError(
                    "'cloud_cover' not found in metadata!"
                ) from exc

        except (InvalidProductError, TypeError) as ex:
            LOGGER.warning(ex)
            cc = 0

        return cc

    def _to_reflectance(
        self,
        band_arr: xr.DataArray,
        band_path: AnyPathType,
        band: BandNames,
        **kwargs,
    ) -> xr.DataArray:
        """
        Converts band to reflectance

        Args:
            band_arr (xr.DataArray): Band array to convert
            band_path (AnyPathType): Band path
            band (BandNames): Band to read
            **kwargs: Other keywords

        Returns:
            xr.DataArray: Band in reflectance
        """
        # Delivered in uint16
        # Compute the correct radiometry of the band for raw band
        if path.get_filename(band_path).endswith("TOA"):
            band_arr *= 0.0001

        # To float32
        if band_arr.dtype != np.float32:
            band_arr = band_arr.astype(np.float32)

        return band_arr

    @cache
    def _get_stac_regex(self):
        """Get STAC regex, either if archived or not."""
        return r".*_stac\.geojson" if self.is_archived else "*_stac.geojson"

    @cache
    def _read_stac_mtd(self) -> gpd.GeoDataFrame:
        """Read STAC metadata (also geojson footprint of the image)"""
        regex = self._get_stac_regex()
        if self.is_archived:
            mtd = self._read_archived_vector(archive_regex=regex)
        else:
            try:
                mtd = vectors.read(next(self.path.glob(regex)))
            except StopIteration as exc:
                raise FileNotFoundError(
                    f"Non existing file *_stac.geojson in {self.path}"
                ) from exc

        return mtd

    @cache
    def _read_mtd_dict(self) -> dict:
        """Return metadata as a dict"""
        regex = self._get_stac_regex()
        if self.is_archived:
            mtd = json.loads(self._read_archived_file(regex))
        else:
            mtd = files.read_json(next(self.path.glob(regex)), print_file=False)

        return mtd

    @cache
    def _read_mtd(self) -> (etree._Element, dict):
        """
        Read Satellogic metadata.

        Returns:
            (etree._Element, dict): Metadata XML root and its namespaces
        """
        # MTD are JSON
        try:
            mtd = self._read_mtd_dict()

            # Sanitize STAC mtd (remove STAC prefixes with ':' that break XML keys)
            def __sanitize_recursive(d):
                for key in d.copy():
                    k = key.split(":")[-1]
                    d[k] = d.pop(key)
                    if isinstance(d[k], dict):
                        __sanitize_recursive(d[k])

            mtd.pop("assets", None)
            mtd.pop("links", None)
            mtd.pop("stac_extensions", None)
            mtd.pop("stac_version", None)
            mtd.pop("type", None)
            __sanitize_recursive(mtd)
            root = etree.fromstring(dicttoxml(mtd, attr_type=False))
        except etree.XMLSyntaxError as exc:
            raise InvalidProductError(
                f"Cannot convert metadata to XML for {self.path}!"
            ) from exc

        return root, {}

    def _has_mask(self, mask: BandNames) -> bool:
        """
        Can the specified mask be loaded from this product?

        .. code-block:: python

            >>> from eoreader.reader import Reader
            >>> from eoreader.bands import *
            >>> path = r"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip"
            >>> prod = Reader().open(path)
            >>> prod.has_index(DETFOO)
            True

        Args:
            mask (BandNames): Mask

        Returns:
            bool: True if the specified mask is provided by the current product
        """
        return mask in [Aleph1MaskBandNames.CLOUD]

    def _open_masks(
        self,
        bands: list,
        pixel_size: float = None,
        size: list | tuple = None,
        **kwargs,
    ) -> dict:
        """
        Open a list of mask files as xarrays.

        Args:
            bands (list): List of the wanted bands
            pixel_size (int): Band pixel size in meters
            size (tuple | list): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}

        for band in bands:
            band_name = band.name
            mask_path = self._get_path(band_name, "vrt")

            band_arr = self._read_band(
                mask_path,
                band=band,
                pixel_size=pixel_size,
                size=size,
                **kwargs,
            )
            band_arr.attrs["long_name"] = band_name
            band_dict[band] = band_arr.rename(band_name)

        return band_dict

    def _has_cloud_band(self, band: BandNames) -> bool:
        """
        Does this product has the specified cloud band?
        """
        return band in [RAW_CLOUDS, CLOUDS, CIRRUS, ALL_CLOUDS]

    def _open_clouds(
        self,
        bands: list,
        pixel_size: float = None,
        size: list | tuple = None,
        **kwargs,
    ) -> dict:
        """
        Load cloud files as xarrays.

        Args:
            bands (list): List of the wanted bands
            pixel_size (int): Band pixel size in meters
            size (tuple | list): Size of the array (width, height). Not used if pixel_size is provided.
            kwargs: Additional arguments
        Returns:
            dict: Dictionary {band_name, band_xarray}
        """
        band_dict = {}

        if bands:
            cld_arr = self._open_masks(
                [Aleph1MaskBandNames.CLOUD], pixel_size=pixel_size, size=size
            )[Aleph1MaskBandNames.CLOUD]

            nodata = cld_arr == 0

            for band in bands:
                if band == ALL_CLOUDS:
                    cloud = self._create_mask(cld_arr, cld_arr >= 2, nodata)
                elif band == CIRRUS:
                    cloud = self._create_mask(cld_arr, cld_arr == 2, nodata)
                elif band == CLOUDS:
                    cloud = self._create_mask(cld_arr, cld_arr == 3, nodata)
                elif band == RAW_CLOUDS:
                    cloud = cld_arr
                else:
                    raise InvalidTypeError(
                        f"Non existing cloud band for Satellogic: {band}"
                    )

                # Rename
                band_name = to_str(band)[0]
                cloud.attrs["long_name"] = band_name
                band_dict[band] = cloud.rename(band_name).astype(np.float32)

        return band_dict

    def _get_tile_path(self, **kwargs) -> AnyPathType:
        """
        Get the VHR tile path

        Returns:
            AnyPathType: VHR filepath
        """
        return self._get_path("TOA", "vrt")

    @qck_wrapper
    def get_quicklook_path(self) -> str:
        """
        Get quicklook path if existing.

        Returns:
            str: Quicklook path
        """
        if self.is_archived:
            quicklook_path = self.path / self._get_archived_path(
                regex=r".*preview\.png"
            )
        else:
            quicklook_path = next(self.path.glob("*preview.png"))

        return quicklook_path

    def _get_job_id(self) -> str:
        """
        Get VHR job ID

        Returns:
            str: VHR product ID
        """
        return self.split_name[-1]

    def _get_condensed_name(self) -> str:
        """
        Get VHR products condensed name ({date}_{constellation}_{product_type}_{job_id}).

        Returns:
            str: Condensed name
        """
        return f"{self.get_datetime()}_{self.constellation.name}_{self.product_type.name}_{self._job_id}"
