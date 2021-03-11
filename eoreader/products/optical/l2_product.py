""" Landsat-2 products """
from eoreader.exceptions import InvalidProductError
from eoreader.bands.bands import OpticalBandNames as obn
from eoreader.products.optical.landsat_product import LandsatProduct, LandsatProductType


class L2Product(LandsatProduct):
    """ Class of Landsat-2 Products """

    def _set_default_resolution(self) -> float:
        """
        Set product default resolution (in meters)
        """
        return 60.

    def _set_product_type(self) -> None:
        """ Get products type """
        if "L1" in self.name:
            self.product_type = LandsatProductType.L1_MSS
            self.band_names.map_bands({
                obn.GREEN: '4',
                obn.RED: '5',
                obn.VRE_1: '6',
                obn.VRE_2: '6',
                obn.VRE_3: '6',
                obn.NIR: '7',
                obn.NNIR: '7'
            })
        else:
            raise InvalidProductError(f"Invalid Landsat-2 name: {self.name}")

    def _set_condensed_name(self) -> str:
        """
        Get products condensed name (L2_{date}_{tile}_{product_type}).

        Returns:
            str: Condensed L2 name
        """
        return f"{self.get_datetime()}_L2_{self.tile_name}_{self.product_type.value}"
