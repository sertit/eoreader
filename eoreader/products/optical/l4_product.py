""" Landsat-4 products """
from eoreader.exceptions import InvalidProductError
from eoreader.products.optical.landsat_product import LandsatProduct, LandsatProductType


class L4Product(LandsatProduct):
    """ Class of Landsat-4 Products """

    def _set_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        if self.product_type == LandsatProductType.L1_TM:
            def_res = 60.0
        else:
            # DO NOT TAKE INTO ACCOUNT TIRS RES
            def_res = 30.0
        return def_res

    def _set_product_type(self) -> None:
        """ Get products type """
        if "LT04" in self.name:
            self._set_tm_product_type()
        elif "LM04" in self.name:
            self._set_mss_product_type(version=4)
        else:
            raise InvalidProductError(f"Invalid Landsat-4 name: {self.name}")
