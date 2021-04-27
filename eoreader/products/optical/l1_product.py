""" Landsat-1 products """
from eoreader.products.optical.landsat_product import LandsatProduct


class L1Product(LandsatProduct):
    """Class of Landsat-1 Products"""

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        return 60.0

    def _set_product_type(self) -> None:
        """Get products type"""
        self._set_mss_product_type(version=1)
