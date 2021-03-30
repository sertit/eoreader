""" Landsat-3 products """
from eoreader.products.optical.landsat_product import LandsatProduct


class L3Product(LandsatProduct):
    """ Class of Landsat-3 Products """

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        # DO NOT TAKE INTO ACCOUNT TIRS RES
        return 60.

    def _set_product_type(self) -> None:
        """ Get products type """
        self._set_mss_product_type(version=3)

    def _get_condensed_name(self) -> str:
        """
        Get products condensed name ({date}_L3_{tile}_{product_type}).

        Returns:
            str: Condensed L3 name
        """
        return self._get_landsat_condensed_name(version=3)
