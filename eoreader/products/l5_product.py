""" Landsat-5 products """
from eoreader.exceptions import InvalidProductError
from eoreader.bands import OpticalBandNames as obn
from eoreader.products.landsat_product import LandsatProduct, LandsatProductType


class L5Product(LandsatProduct):
    """ Class of Landsat-5 Products """

    def get_product_type(self) -> None:
        """ Get products type """
        if "L1" in self.name:
            if "LT05" in self.name:
                self.product_type = LandsatProductType.L1_TM
                self.band_names.map_bands({
                    obn.BLUE: '1',
                    obn.GREEN: '2',
                    obn.RED: '3',
                    obn.NIR: '4',
                    obn.NNIR: '4',
                    obn.SWIR_1: '5',
                    obn.SWIR_2: '7',
                    obn.TIR_1: '6',
                    obn.TIR_2: '6'
                })
            elif "LM05" in self.name:
                self.product_type = LandsatProductType.L1_MSS
                self.band_names.map_bands({
                    obn.GREEN: '1',
                    obn.RED: '2',
                    obn.VRE_1: '3',
                    obn.VRE_2: '3',
                    obn.VRE_3: '3',
                    obn.NIR: '4',
                    obn.NNIR: '4'
                })
            else:
                raise InvalidProductError(f"Invalid Landsat-5 name: {self.name}")
        else:
            raise InvalidProductError(f"Invalid Landsat-5 name: {self.name}")

    def get_condensed_name(self) -> str:
        """
        Get products condensed name ({date}_L5_{tile}_{product_type}).

        Returns:
            str: Condensed L5 name
        """
        return f"{self.get_datetime()}_L5_{self.tile_name}_{self.product_type.value}"
