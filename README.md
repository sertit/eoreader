# EOReader

This project allows you to read and open satellite data.
This software relies on satellite's name to open them, so please du not modify them !

```python
>>> from eoreader.eoreader import EOReader
>>> from eoreader import index
>>> from eoreader.bands import OpticalBandNames as obn

>>> # Your variables
>>> opt_path = "path\to\your\satellite"
>>> resolution = 20  # in meters

>>> # Create the reader object and open satellite data
>>> eoreader = EOReader()
>>> prod = eoreader.open(opt_path)

>>> # Load some bands and index
>>> idx, meta = prod.load(index_list=[index.NDVI, index.MNDWI], band_list=[obn.GREEN],resolution=resolution)
>>> ndvi = idx[index.NDVI]
>>> mndwi = idx[index.MNDWI]
>>> green = idx[obn.GREEN]
```

Index and bands are opened as `numpy.ma.maskedarrays` 
(see [here](https://numpy.org/doc/stable/reference/maskedarray.generic.html) to learn more about it) and converted to float.
The mask corresponds to the nodata of your product, that is set to 0 by convention.

## Optical data

Accepted optical satellites are:

- `Sentinel-2`: **L2A** and **L1C**
- `Sentinel-2 Theia`: **L2A**
- `Sentinel-3`: **OLCI** and **SLSTR**
- `Landsat-1`: **MSS**
- `Landsat-2`: **MSS**
- `Landsat-3`: **MSS**
- `Landsat-4`: **TM** and **MSS**
- `Landsat-5`: **TM** and **MSS**
- `Landsat-7`: **ETM**
- `Landsat-8`: **OLCI**

Please look at this [WIKI page](https://code.sertit.unistra.fr/extracteo/extracteo/-/wikis/Satellites/Optical) to learn more about that.

## SAR data

Accepted SAR satellites are:

- `Sentinel-1` **GRD** + **SLC**
- `COSMO-SkyMed` **DGM** + **SCS**
- `TerraSAR-X` **MGD** (+ **SSC**, :warning: not tested, use it at your own risk)
- `RADARSAT-2` **SGF** (+ **SLC**, :warning: not tested, use it at your own risk)

Please look at this [WIKI page](https://code.sertit.unistra.fr/extracteo/extracteo/-/wikis/Satellites/SAR) to learn more about that.

## Available index:

- `AFRI_1_6`
- `AFRI_2_1`
- `AWEInsh`
- `AWEIsh`
- `BAI`
- `BSI`
- `CIG`
- `DSWI`
- `GLI`
- `GNDVI`
- `LWCI`
- `MNDWI`
- `NBR`
- `NDGRI`
- `NDMI`
- `NDRE2`
- `NDRE3`
- `NDVI`
- `NDWI`
- `PGR`
- `RDI`
- `RGI`
- `RI`
- `SRSWIR`
- `TCBRI`
- `TCGRE`
- `TCWET`
- `WI`

See [here](https://extracteo.pages.sertit.unistra.fr/extracteo/products/index.m.html) for more info.