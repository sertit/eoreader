""" Landsat-3 products """
from eoreader.products.optical.landsat_product import LandsatProduct


class L3Product(LandsatProduct):
    """Class of Landsat-3 Products"""

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        # DO NOT TAKE INTO ACCOUNT TIRS RES
        return 60.0

    def _set_product_type(self) -> None:
        """Get products type"""
        self._set_mss_product_type(version=3)
