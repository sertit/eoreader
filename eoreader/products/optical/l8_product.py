""" Landsat-8 products """
from eoreader.products.optical.landsat_product import LandsatProduct


class L8Product(LandsatProduct):
    """Class of Landsat-8 Products"""

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        # DO NOT TAKE INTO ACCOUNT PAN AND TIRS RES
        return 30.0

    def _set_product_type(self) -> None:
        """Get products type"""
        self._set_olci_product_type()
