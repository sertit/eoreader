import setuptools
from eoreader.version import __version__

setuptools.setup(
    name='eoreader',
    version=__version__,  # Semantic Versioning (see https://semver.org/)
    author="Rémi BRAUN",
    author_email="remi.braun@unistra.fr",
    description="SERTIT python library for extracting data on satellite products",
    long_description=
    '''
        SERTIT python library for extracting data on satellite products.
        For more information please see http://code.sertit.unistra.fr/SERTIT/eoreader/blob/master/README.md"
    ''',
    url="http://code.sertit.unistra.fr/SERTIT/eoreader",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Operating System :: OS Independent"
    ],
    install_requires=[
        "psutil",
        "lxml",
        "netCDF4",
        "rasterio",
        "geopandas",
        # "sertit",
    ],
    package_data={'eoreader.data': ['*.xml']},
    include_package_data=True
)
