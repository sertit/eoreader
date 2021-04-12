""" Landsat-7 products """
from eoreader.products.optical.landsat_product import LandsatProduct


class L7Product(LandsatProduct):
    """ Class of Landsat-7 Products """

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        # DO NOT TAKE INTO ACCOUNT PAN AND TIRS RES
        return 30.

    def _set_product_type(self) -> None:
        """ Get products type """
        self._set_etm_product_type()
