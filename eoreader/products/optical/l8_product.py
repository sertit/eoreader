""" Landsat-8 products """
from eoreader.products.optical.landsat_product import LandsatProduct


class L8Product(LandsatProduct):
    """ Class of Landsat-8 Products """

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        # DO NOT TAKE INTO ACCOUNT PAN AND TIRS RES
        return 30.

    def _set_product_type(self) -> None:
        """ Get products type """
        self._set_olci_product_type()

    def _get_condensed_name(self) -> str:
        """
        Get products condensed name ({date}_L8_{tile}_{product_type}).

        Returns:
            str: Condensed L8 name
        """
        return self._get_landsat_condensed_name(version=8)
