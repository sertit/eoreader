import setuptools
import os
from eoreader.version import __version__

BASEDIR = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
with open(os.path.join(BASEDIR, "README.md"), "r") as f:
    readme = f.read()

setuptools.setup(
    name='eoreader',
    version=__version__,  # Semantic Versioning (see https://semver.org/)
    author="Rémi BRAUN",
    author_email="remi.braun@unistra.fr",
    description="SERTIT python library for reading and stacking satellite data",
    long_description=readme,
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
