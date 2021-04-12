""" Landsat-2 products """
from eoreader.products.optical.landsat_product import LandsatProduct


class L2Product(LandsatProduct):
    """ Class of Landsat-2 Products """

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        return 60.

    def _set_product_type(self) -> None:
        """ Get products type """
        self._set_mss_product_type(version=2)
