import os

import setuptools

from eoreader import __version__

BASEDIR = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
with open(os.path.join(BASEDIR, "README.md"), "r") as f:
    readme = f.read()

setuptools.setup(
    name="eoreader",
    version=__version__,
    author="Rémi BRAUN",
    author_email="dev-sertit@unistra.fr",
    description="Multi satellite reader allowing you to load bands and index and stack them.",
    long_description=readme,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    install_requires=[
        "lxml",
        "netCDF4",
        "rioxarray",
        "geopandas",
        "sertit[full]",
        "rtree",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: GIS",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    package_data={"": ["LICENSE", "NOTICE"], "eoreader.data": ["*.xml"]},
    include_package_data=True,
    python_requires=">=3.7",
    project_urls={
        "Bug Tracker": "https://github.com/sertit/eoreader/issues/",
        "Documentation": "https://sertit.github.io/eoreader/sertit/",
        "Source Code": "https://github.com/sertit/eoreader",
    },
)
