""" Landsat-8 products """
from eoreader.exceptions import InvalidProductError
from eoreader.bands.bands import OpticalBandNames as obn
from eoreader.products.optical.landsat_product import LandsatProduct, LandsatProductType


class L8Product(LandsatProduct):
    """ Class of Landsat-8 Products """

    def _set_product_type(self) -> None:
        """ Get products type """
        if "L1" in self.name:
            self.product_type = LandsatProductType.L1_OLCI
            self.band_names.map_bands({
                obn.CA: '1',
                obn.BLUE: '2',
                obn.GREEN: '3',
                obn.RED: '4',
                obn.NIR: '5',
                obn.NNIR: '5',
                obn.SWIR_1: '6',
                obn.SWIR_2: '7',
                obn.PAN: '8',
                obn.CIRRUS: '9',
                obn.TIR_1: '10',
                obn.TIR_2: '11'
            })
        else:
            raise InvalidProductError(f"Invalid Landsat-8 name: {self.name}")

    def _get_condensed_name(self) -> str:
        """
        Get products condensed name ({date}_L8_{tile}_{product_type}).

        Returns:
            str: Condensed L8 name
        """
        return f"{self.get_datetime()}_L8_{self.tile_name}_{self.product_type.value}"
