""" Landsat-1 products """
from eoreader.exceptions import InvalidProductError
from eoreader.bands.bands import OpticalBandNames as obn
from eoreader.products.optical.landsat_product import LandsatProduct, LandsatProductType


class L1Product(LandsatProduct):
    """ Class of Landsat-1 Products """

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
            raise InvalidProductError(f"Invalid Landsat-1 name: {self.name}")

    def _get_condensed_name(self) -> str:
        """
        Get products condensed name ({date}_L1_{tile}_{product_type}).

        ```python
        >>> prod.get_condensed_name()
        19771228T151759_L1_033031_MSS
        ```

        Returns:
            str: Condensed L1 name
        """
        return f"{self.get_datetime()}_L1_{self.tile_name}_{self.product_type.value}"
