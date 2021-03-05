""" Landsat-7 products """
from eoreader.exceptions import InvalidProductError
from eoreader.bands import OpticalBandNames as obn
from eoreader.products.landsat_product import LandsatProduct, LandsatProductType


class L7Product(LandsatProduct):
    """ Class of Landsat-7 Products """

    def get_product_type(self) -> None:
        """ Get products type """
        if "L1" in self.name:
            self.product_type = LandsatProductType.L1_ETM
            self.band_names.map_bands({
                obn.BLUE: '1',
                obn.GREEN: '2',
                obn.RED: '3',
                obn.NIR: '4',
                obn.NNIR: '4',
                obn.SWIR_1: '5',
                obn.SWIR_2: '7',
                obn.PAN: '8',
                obn.TIR_1: '6_VCID_1',
                obn.TIR_2: '6_VCID_2'
            })
        else:
            raise InvalidProductError(f"Invalid Landsat-7 name: {self.name}")

    def get_condensed_name(self) -> str:
        """
        Get products condensed name ({date}_L7_{tile}_{product_type}).

        Returns:
            str: Condensed L7 name
        """
        return f"{self.get_datetime()}_L7_{self.tile_name}_{self.product_type.value}"
