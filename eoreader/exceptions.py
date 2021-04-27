""" EOReader exceptions """


class EoReaderError(Exception):
    """ EOReader error """

    pass


class InvalidBandError(EoReaderError):
    """ Invalid Band error, thrown when a non existing band is asked to a product. """

    pass


class InvalidIndexError(InvalidBandError):
    """ Invalid Index error, thrown when a non existing band is asked to a produc. """

    pass


class InvalidProductError(EoReaderError):
    """ Invalid Product error, thrown when satellite product is not as expected. """

    pass


class InvalidTypeError(EoReaderError, TypeError):
    """ Tile Name error, thrown when an unknown type is given (shouldn't never happen). """

    pass
