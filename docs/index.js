URLS=[
"eoreader/index.html",
"eoreader/bands/index.html",
"eoreader/bands/alias.html",
"eoreader/bands/bands.html",
"eoreader/bands/index.m.html",
"eoreader/env_vars.html",
"eoreader/examples/index.html",
"eoreader/exceptions.html",
"eoreader/products/index.html",
"eoreader/products/optical/index.html",
"eoreader/products/optical/l1_product.html",
"eoreader/products/optical/landsat_product.html",
"eoreader/products/optical/optical_product.html",
"eoreader/products/product.html",
"eoreader/products/optical/l2_product.html",
"eoreader/products/optical/l3_product.html",
"eoreader/products/optical/l4_product.html",
"eoreader/products/optical/l5_product.html",
"eoreader/products/optical/l7_product.html",
"eoreader/products/optical/l8_product.html",
"eoreader/products/optical/s2_product.html",
"eoreader/products/optical/s2_theia_product.html",
"eoreader/products/optical/s3_product.html",
"eoreader/products/sar/index.html",
"eoreader/products/sar/csk_product.html",
"eoreader/products/sar/sar_product.html",
"eoreader/products/sar/rs2_product.html",
"eoreader/products/sar/s1_product.html",
"eoreader/products/sar/tsx_product.html",
"eoreader/reader.html",
"eoreader/utils.html"
];
INDEX=[
{
"ref":"eoreader",
"url":0,
"doc":" Source Code : https: github.com/sertit/eoreader  EOReader This project is a multi-satellite  reader allowing you to open [optical](https: sertit.github.io/eoreader/eoreader implemented-optical-satellites) and [SAR](https: sertit.github.io/eoreader/eoreader implemented-sar-satellites) data. It also implements two additional features, non depending on the sensor: -  eoreader.products.product.Product.load : Load many band types: - satellite bands ([optical](https: sertit.github.io/eoreader/eoreader band-mapping) or [SAR](https: sertit.github.io/eoreader/eoreader sar-bands - [index](https: sertit.github.io/eoreader/eoreader available-index) - [cloud bands](https: sertit.github.io/eoreader/eoreader cloud-bands) - [DEM bands](https: sertit.github.io/eoreader/eoreader dem-bands) -  eoreader.products.product.Product.stack : Stack all these type of bands It allows you to focus on the science instead of worrying how to access to the data, especially if you have to work with multiple sensors !  Python Quickstart The main features of EOReader are gathered hereunder:   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>>  Your variables >>> path = r\"path/to/your/satellite/product\"  Optical in this example >>>  WARNING: you can leave the output_path empty, but EOReader will create a temporary output directory >>>  and you won't be able to retrieve what's has been written on disk >>> output = r\"path/to/your/output\" >>>  Create the reader object and open satellite data >>> eoreader = Reader()  This is a singleton >>> prod = eoreader.open(path, output_path=output)  The Reader will recognize the satellite type from its name >>>  Get the footprint of the product (usable data) and its extent (envelope of the tile) >>> footprint = prod.footprint >>> extent = prod.extent >>>  Load some bands and index: they will all share the same metadata >>> bands = prod.load([NDVI, GREEN, HILLSHADE, CLOUDS])  Resolution not specified: use product resolution >>> ndvi = bands[NDVI] >>> green = bands[GREEN] >>> hillshade = bands[HILLSHADE] >>> clouds = bands[CLOUDS] >>>  NOTE: every array that comes out  load are collocated, which isn't the case if you load arrays separately >>>  (important for DEM data as they may have different grids) >>>  Create a stack with some other bands >>> stack = prod.stack([NDVI, MNDWI, GREEN, SLOPE, CIRRUS])  Resolution not specified: use product resolution >>>  Read Metadata >>> mtd, namespace = prod.read_mtd()    WARNING - Sentinel-3 and SAR products need [ SNAP gpt ](https: senbox.atlassian.net/wiki/spaces/SNAP/pages/70503590/Creating+a+GPF+Graph) to be geocoded. Ensure that you have the folder containing your  gpt.exe in your  PATH .  Installation  pip install eoreader  WARNING  EOReader depends mainly on  geopandas and  rasterio . (with GDAL installation issues on Windows, so please install them from wheels that you can find [here](https: www.lfd.uci.edu/~gohlke/pythonlibs/ rasterio . _____  Main features  Read The reader singleton is your unique entry. It will create for you the product object corresponding to your satellite data.   >>> import os >>> from eoreader.reader import Reader >>>  Path to your satellite data, ie. Sentinel-2 >>> path = r'S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.zip'  You can work with the archive for S2 data >>>  Path to your output directory (if not set, it will work in a temp directory) >>> output = os.path.abspath('.') >>>  Create the reader singleton >>> eoreader = Reader() >>> prod = eoreader.open(path, output_path=output) >>>  NOTE: you can set the output directory after the creation, that allows you to use the product condensed name >>> prod.output = os.path.join(output, prod.condensed_name)  It will automatically create it if needed   From there you have access to a lot of information on your product:   >>>  Product CRS (always in UTM) >>> prod.crs CRS.from_epsg(32630) >>>  Full extent of the bands as a geopandas GeoDataFrame (always in UTM) >>> prod.extent() geometry 0 POLYGON 309780.000 4390200.000, 309780.000 4 . >>>  Footprint: extent of the useful pixels (minus nodata) as a geopandas GeoDataFrame (always in UTM) >>> prod.footprint() index geometry 0 0 POLYGON  199980.000 4500000.000, 199980.000 4 . >>>  Default resolution (20m for S2) >>> prod.resolution 20. >>>  Acquisition date and datetime >>> prod.date datetime.date(2020, 8, 24) >>> prod.datetime datetime.datetime(2020, 8, 24, 11, 6, 31) >>>  Access the raw metadata as an lxml.etree._Element: >>> prod.read_mtd()   See the difference between footprint and extent hereunder: |Without nodata | With nodata| | - |  -| | ![without_nodata](https: zupimages.net/up/21/14/69i6.gif) | ![with_nodata](https: zupimages.net/up/21/14/vg6w.gif) |  Load  eoreader.products.product.Product.load is the function for accessing to product-related bands. It can load satellite bands, index, DEM bands and cloud bands according to this workflow: ![load_workflow](https: zupimages.net/up/21/14/vtnc.png)   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.zip\" >>> prod = Reader().open(path) >>>  Get the wanted bands and check if the product can produce them >>> band_list = [GREEN, NDVI, TIR_1, SHADOWS, HILLSHADE] >>> ok_bands = [band for band in band_list if prod.has_band(band)] [GREEN, NDVI, HILLSHADE] >>>  Sentinel-2 cannot produce satellite band TIR_1 and cloud band SHADOWS >>>  Load bands >>> bands = prod.load(ok_bands) >>> bands  \" { :  array( [0.94786006, 0.92717856, 0.92240528,  ., 1.73572724, 1.55314477, 1.63242706], [1.04147187, 0.93668633, 0.91499688,  ., 1.59941784, 1.52895995, 1.51386761], [2.86996677, 1.69360304, 1.2413562 ,  ., 1.61172353, 1.55742907, 1.50568275],  ., [1.45807257, 1.61071344, 1.64620751,  ., 1.25498441, 1.42998927, 1.70447076], [1.57802352, 1.77086658, 1.69901482,  ., 1.19999853, 1.27813254, 1.52287237], [1.63569594, 1.66751277, 1.63474646,  ., 1.27617084, 1.22456033, 1.27022877 ]) Coordinates:  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  band (band) int32 1 spatial_ref int32 0,  :  array( [0.06146327, 0.06141786, 0.06100179,  ., 0.11880179, 0.12087143, 0.11468571], [0.06123214, 0.06071094, 0.06029063,  ., 0.11465781, 0.11858906, 0.11703929], [0.06494643, 0.06226562, 0.06169219,  ., 0.11174062, 0.11434844, 0.11491964],  ., [0.1478125 , 0.13953906, 0.13751719,  ., 0.15949688, 0.14200781, 0.12982321], [0.14091429, 0.12959531, 0.13144844,  ., 0.17246719, 0.156175 , 0.13453036], [0.13521429, 0.13274286, 0.13084821,  ., 0.16064821, 0.16847143, 0.16009592 ]) Coordinates:  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  band (band) int32 1 spatial_ref int32 0,  :  array( [220., 221., 221.,  ., 210., 210., 210.], [222., 222., 221.,  ., 210., 210., 210.], [221., 221., 220.,  ., 210., 210., 210.],  ., [215., 214., 212.,  ., 207., 207., 207.], [214., 212., 211.,  ., 206., 205., 205.], [213., 211., 209.,  ., 205., 204., 205. ]) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0 Attributes: grid_mapping: spatial_ref original_dtype: uint8}  \"    NOTE Index and bands are opened as [ xarrays ](http: xarray.pydata.org/en/stable/) with [ rioxarray ](https: corteva.github.io/rioxarray/stable/), in  float with the nodata set to  np.nan . The nodata written back on disk is -9999 by convention (for now the rasters will be written in float)  Stack  eoreader.products.product.Product.stack is the function stacking all possible bands. It is based on the load function and then just stacks the bands and write it on disk if needed.   >>>  Create a stack with the previous OK bands >>> stack = prod.stack(ok_bands, resolution=300., stack_path=os.path.join(prod.output, \"stack.tif\")  \"  array( [9.47860062e-01, 9.27178562e-01, 9.22405303e-01,  ., 1.73572719e+00, 1.55314481e+00, 1.63242710e+00], [1.04147184e+00, 9.36686337e-01, 9.14996862e-01,  ., 1.59941781e+00, 1.52895999e+00, 1.51386762e+00], [2.86996675e+00, 1.69360304e+00, 1.24135625e+00,  ., 1.61172354e+00, 1.55742908e+00, 1.50568271e+00],  ., [1.45807254e+00, 1.61071348e+00, 1.64620745e+00,  ., 1.25498438e+00, 1.42998922e+00, 1.70447075e+00], [1.57802355e+00, 1.77086663e+00, 1.69901478e+00,  ., 1.19999850e+00, 1.27813256e+00, 1.52287233e+00], [1.63569593e+00, 1.66751277e+00, 1.63474643e+00,  ., 1.27617085e+00, 1.22456038e+00, 1.27022874e+00 ,  6.14632666e-02, 6.14178553e-02, 6.10017851e-02,  ., 1.18801787e-01, 1.20871432e-01, 1.14685714e-01], [6.12321422e-02, 6.07109368e-02, 6.02906235e-02,  ., 1.14657812e-01, 1.18589066e-01, 1.17039286e-01], [6.49464279e-02, 6.22656234e-02, 6.16921857e-02,  ., 1.11740626e-01, 1.14348434e-01, 1.14919640e-01], [1.47812501e-01, 1.39539063e-01, 1.37517184e-01,  ., 1.59496874e-01, 1.42007813e-01, 1.29823208e-01], [1.40914291e-01, 1.29595309e-01, 1.31448433e-01,  ., 1.72467187e-01, 1.56175002e-01, 1.34530351e-01], [1.35214284e-01, 1.32742852e-01, 1.30848214e-01,  ., 1.60648212e-01, 1.68471426e-01, 1.60095915e-01 ,  2.20000000e+02, 2.21000000e+02, 2.21000000e+02,  ., 2.10000000e+02, 2.10000000e+02, 2.10000000e+02], [2.22000000e+02, 2.22000000e+02, 2.21000000e+02,  ., 2.10000000e+02, 2.10000000e+02, 2.10000000e+02], [2.21000000e+02, 2.21000000e+02, 2.20000000e+02,  ., 2.10000000e+02, 2.10000000e+02, 2.10000000e+02],  ., [2.15000000e+02, 2.14000000e+02, 2.12000000e+02,  ., 2.07000000e+02, 2.07000000e+02, 2.07000000e+02], [2.14000000e+02, 2.12000000e+02, 2.11000000e+02,  ., 2.06000000e+02, 2.05000000e+02, 2.05000000e+02], [2.13000000e+02, 2.11000000e+02, 2.09000000e+02,  ., 2.05000000e+02, 2.04000000e+02, 2.05000000e+02 ], dtype=float32) Coordinates:  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06 spatial_ref int32 0  z (z) MultiIndex - variable (z) object 'NDVI' 'GREEN' 'HILLSHADE' - band (z) int64 1 1 1 Attributes: long_name: ['NDVI', 'GREEN', 'HILLSHADE']  \"   _____  Optical data  Implemented optical satellites |Satellites | Class | Product Types | Use archive | Default Resolution | | - |  - |  - |  - |  -| |Sentinel-2 |  eoreader.products.optical.s2_product.S2Product | L1C & L2A | Yes | 20m| |Sentinel-2 Theia |  eoreader.products.optical.s2_theia_product.S2TheiaProduct | L2A | Yes | 20m| |Sentinel-3 SLSTR |  eoreader.products.optical.s3_product.S3Product | RBT | No | 300m| |Sentinel-3 OLCI |  eoreader.products.optical.s3_product.S3Product | EFR | No | 500m| |Landsat-8 OLCI |  eoreader.products.optical.l8_product.L8Product | Level 1 | Collection 1: No, Collection 2: Yes | 30m| |Landsat-7 ETM |  eoreader.products.optical.l7_product.L7Product | Level 1 | Collection 1: No, Collection 2: Yes | 30m| |Landsat-5 TM |  eoreader.products.optical.l5_product.L5Product | Level 1 | Collection 1: No, Collection 2: Yes | 30m| |Landsat-4 TM |  eoreader.products.optical.l4_product.L4Product | Level 1 | Collection 1: No, Collection 2: Yes | 30m| |Landsat-5 MSS |  eoreader.products.optical.l5_product.L5Product | Level 1 | Collection 1: No, Collection 2: Yes | 60m| |Landsat-4 MSS |  eoreader.products.optical.l4_product.L4Product | Level 1 | Collection 1: No, Collection 2: Yes | 60m| |Landsat-3 MSS |  eoreader.products.optical.l3_product.L3Product | Level 1 | Collection 1: No, Collection 2: Yes | 60m| |Landsat-2 MSS |  eoreader.products.optical.l2_product.L2Product | Level 1 | Collection 1: No, Collection 2: Yes | 60m| |Landsat-1 MSS |  eoreader.products.optical.l1_product.L1Product | Level 1 | Collection 1: No, Collection 2: Yes | 60m| Satellites products that cannot be used as archived have to be extracted before use.  Optical bands The following bands are available in  EOReader , but may not be available for all sensors.  Satellite bands These bands are mainly based on Sentinel-2 bands with some additions: -  CA : Coastal Aerosol -  BLUE -  GREEN -  RED -  VRE_1 : Vegetation Red Edge 1 -  VRE_2 : Vegetation Red Edge 2 -  VRE_3 : Vegetation Red Edge 3 -  NIR : Near Infrared -  NARROW_NIR : Narrow Near Infrared (band  8A for  Sentinel-2 ) -  WP : Water vapour -  SWIR_CIRRUS -  SWIR_1 -  SWIR_2 -  PAN : Panchromatic -  TIR_1 : Thermal Infrared 1 -  TIR_2 : Thermal Infrared 2 See [here]() for more information.  Index -  AFRI_1_6 -  AFRI_2_1 -  AWEInsh -  AWEIsh -  BAI -  BSI -  CIG -  DSWI -  GLI -  GNDVI -  MNDWI -  NBR -  NDGRI -  NDMI -  NDRE2 -  NDRE3 -  NDVI -  NDWI -  RDI -  RGI -  RI -  SRSWIR -  TCBRI -  TCGRE -  TCWET -  WI See [here]() for more information.  Cloud bands Maximum 5 cloud bands are available, according to the files provided in the data. All the bands are rasterized and orthorectified if needed (for Sentinel-2 or 3 data for example), ready to be stacked. -  RAW_CLOUDS : Raw Cloud file as provided (the only changes are the orthorectification and rasterization). Can provide other flags, or cloud probability. -  CLOUDS : Cloud presence (1) or absence (0). -  CIRRUS : Cirrus presence (1) or absence (0). -  SHADOWS : Shadows presence (1) or absence (0). -  ALL_CLOUDS : Cloud  OR Cirrus  OR Shadows presence (1) or absence (0). Do not take into account missing bands ( ie. for Landsat MSS sensors,  ALL_CLOUDS   CLOUDS ) See [here]() for more information.  DEM bands These bands need a valid worldwide DEM path positioned thanks to the environment variable  EOREADER_SAR_DEFAULT_RES -  DEM -  SLOPE -  HILLSHADE See [here]() for more information. _____  SAR data  Implemented SAR satellites |Satellites | Class | Product Types | Use archive| | - |  - |  - |  -| |Sentinel-1 |  eoreader.products.sar.s1_product.S1Product | SLC & GRD | Yes| |COSMO-Skymed |  eoreader.products.sar.csk_product.CskProduct | DGM & SCS, (others should also be OK) | No| |TerraSAR-X |  eoreader.products.sar.tsx_product.TsxProduct | MGD (SSC should be OK) | No| |RADARSAT-2 |  eoreader.products.sar.rs2_product.Rs2Product | SGF (SLC should be OK) | Yes|  WARNING Satellites products that cannot be used as archived have to be extracted before use.  SAR Bands According to what contains the products, allowed SAR bands are: -  VV ( eoreader.bands.bands.SarBandNames.VV ) -  VH ( eoreader.bands.bands.SarBandNames.VH ) -  HH ( eoreader.bands.bands.SarBandNames.HH ) -  HV ( eoreader.bands.bands.SarBandNames.HV ) You also can load despeckled bands: -  VV_DSPK ( eoreader.bands.bands.SarBandNames.VV_DSPK ) -  VH_DSPK ( eoreader.bands.bands.SarBandNames.VH_DSPK ) -  HH_DSPK ( eoreader.bands.bands.SarBandNames.HH_DSPK ) -  HV_DSPK ( eoreader.bands.bands.SarBandNames.HV_DSPK )  DEM bands These bands need a valid worldwide DEM path positioned thanks to the environment variable  EOREADER_SAR_DEFAULT_RES -  DEM -  SLOPE See [here]() for more information."
},
{
"ref":"eoreader.bands",
"url":1,
"doc":"Band module containing: - wrapper for SAR and optical bands - Index definitions - Aliases for all these useful variables To use it, simply type:   >>> from eoreader.bands.alias import  >>> GREEN  >>> HH  >>> NDVI   "
},
{
"ref":"eoreader.bands.alias",
"url":2,
"doc":"Aliases for bands and index, created in order to import just this file and not  OpticalBandNames ,  SarBandNames and  index . To use it, simply type:   >>> from eoreader.bands.alias import  >>> GREEN  >>> HH  >>> NDVI   "
},
{
"ref":"eoreader.bands.alias.is_clouds",
"url":2,
"doc":"Returns True if we have a Clouds-related keyword   >>> from eoreader.bands.alias import  >>> is_clouds(NDVI) False >>> is_clouds(HH) False >>> is_clouds(GREEN) False >>> is_clouds(SLOPE) False >>> is_clouds(CLOUDS) True  ",
"func":1
},
{
"ref":"eoreader.bands.alias.is_dem",
"url":2,
"doc":"Returns True if we have a DEM-related keyword   >>> from eoreader.bands.alias import  >>> is_dem(NDVI) False >>> is_dem(HH) False >>> is_dem(GREEN) False >>> is_dem(SLOPE) True >>> is_dem(CLOUDS) False  ",
"func":1
},
{
"ref":"eoreader.bands.alias.is_index",
"url":2,
"doc":"Returns True if is an index function from the  bands.index module   >>> from eoreader.bands.alias import  >>> is_index(NDVI) True >>> is_index(HH) False >>> is_index(GREEN) False >>> is_index(SLOPE) False >>> is_index(CLOUDS) False   Args: idx (Any): Anything that could be an index Returns: bool: True if the index asked is an index function (such as  index.NDVI )",
"func":1
},
{
"ref":"eoreader.bands.alias.is_optical_band",
"url":2,
"doc":"Returns True if is an optical band (from  OpticalBandNames )   >>> from eoreader.bands.alias import  >>> is_optical_band(NDVI) False >>> is_optical_band(HH) False >>> is_optical_band(GREEN) True >>> is_optical_band(SLOPE) False >>> is_optical_band(CLOUDS) False   Args: band (Any): Anything that could be an optical band Returns: bool: True if the band asked is an optical band",
"func":1
},
{
"ref":"eoreader.bands.alias.is_sar_band",
"url":2,
"doc":"Returns True if is a SAR band (from  SarBandNames )   >>> from eoreader.bands.alias import  >>> is_sar_band(NDVI) False >>> is_sar_band(HH) True >>> is_sar_band(GREEN) False >>> is_sar_band(SLOPE) False >>> is_sar_band(CLOUDS) False   Args: band (Any): Anything that could be a SAR band Returns: bool: True if the band asked is a SAR band",
"func":1
},
{
"ref":"eoreader.bands.alias.is_band",
"url":2,
"doc":"Returns True if is a band (from both  SarBandNames or  OpticalBandNames )   >>> from eoreader.bands.alias import  >>> is_band(NDVI) False >>> is_band(HH) True >>> is_band(GREEN) True >>> is_band(SLOPE) False >>> is_band(CLOUDS) False   Args: band (Any): Anything that could be a band Returns: bool: True if the band asked is a band",
"func":1
},
{
"ref":"eoreader.bands.alias.to_band",
"url":2,
"doc":"Convert a string (or real value) to any alias, band or index. You can pass the name or the value of the bands.   >>> to_band([\"NDVI\", \"GREEN\", RED, \"VH_DSPK\", \"SLOPE\", DEM, \"CLOUDS\", CLOUDS]) [ ,  ,  ,  ,  ,  ,  ,  ]   Args: to_convert (list): Values to convert into band objects Returns: list: converted values",
"func":1
},
{
"ref":"eoreader.bands.alias.to_str",
"url":2,
"doc":"Convert a string (or real value) to any alias, band or index. You can pass the name or the value of the bands.   >>> to_str([\"NDVI\", \"GREEN\", RED, \"VH_DSPK\", \"SLOPE\", DEM, \"CLOUDS\", CLOUDS]) ['NDVI', 'GREEN', 'RED', 'VH_DSPK', 'SLOPE', 'DEM', 'CLOUDS', 'CLOUDS']   Args: to_convert (list): Values to convert into str Returns: list: str bands",
"func":1
},
{
"ref":"eoreader.bands.bands",
"url":3,
"doc":"Optical Bands"
},
{
"ref":"eoreader.bands.bands.BandNames",
"url":3,
"doc":"Super class for band names,  do not use it ."
},
{
"ref":"eoreader.bands.bands.BandNames.from_list",
"url":3,
"doc":"Get the band enums from list of band names   >>> SarBandNames.from_list(\"VV\") [ ]   Args: name_list (Union[list, str]): List of names Returns: list: List of enums",
"func":1
},
{
"ref":"eoreader.bands.bands.BandNames.to_value_list",
"url":3,
"doc":"Get a list from the values of the bands   >>> SarBandNames.to_name_list([SarBandNames.HV_DSPK, SarBandNames.VV]) ['HV_DSPK', 'VV'] >>> SarBandNames.to_name_list() ['VV', 'VV_DSPK', 'HH', 'HH_DSPK', 'VH', 'VH_DSPK', 'HV', 'HV_DSPK']   Args: name_list (list): List of band names Returns: list: List of band values",
"func":1
},
{
"ref":"eoreader.bands.bands.SarBandNames",
"url":3,
"doc":"SAR Band names"
},
{
"ref":"eoreader.bands.bands.SarBandNames.corresponding_despeckle",
"url":3,
"doc":"Corresponding despeckled band.   >>> SarBandNames.corresponding_despeckle(SarBandNames.VV)  >>> SarBandNames.corresponding_despeckle(SarBandNames.VV_DSPK)    Args: band (SarBandNames): Noisy (speckle) band Returns: SarBandNames: Despeckled band",
"func":1
},
{
"ref":"eoreader.bands.bands.SarBandNames.corresponding_speckle",
"url":3,
"doc":"Corresponding speckle (noisy) band.   >>> SarBandNames.corresponding_speckle(SarBandNames.VV)  >>> SarBandNames.corresponding_speckle(SarBandNames.VV_DSPK)    Args: band (SarBandNames): Noisy (speckle) band Returns: SarBandNames: Despeckled band",
"func":1
},
{
"ref":"eoreader.bands.bands.SarBandNames.is_despeckle",
"url":3,
"doc":"Returns True if the band corresponds to a despeckled one.   >>> SarBandNames.is_despeckle(SarBandNames.VV) False >>> SarBandNames.is_despeckle(SarBandNames.VV_DSPK) True   Args: band (SarBandNames): Band to test Returns: SarBandNames: Despeckled band",
"func":1
},
{
"ref":"eoreader.bands.bands.SarBandNames.VV",
"url":3,
"doc":"Vertical Transmit-Vertical Receive Polarisation"
},
{
"ref":"eoreader.bands.bands.SarBandNames.VV_DSPK",
"url":3,
"doc":"Vertical Transmit-Vertical Receive Polarisation Despeckled"
},
{
"ref":"eoreader.bands.bands.SarBandNames.HH",
"url":3,
"doc":"Horizontal Transmit-Horizontal Receive Polarisation"
},
{
"ref":"eoreader.bands.bands.SarBandNames.HH_DSPK",
"url":3,
"doc":"Horizontal Transmit-Horizontal Receive Polarisation Despeckled"
},
{
"ref":"eoreader.bands.bands.SarBandNames.VH",
"url":3,
"doc":"Vertical Transmit-Horizontal Receive Polarisation"
},
{
"ref":"eoreader.bands.bands.SarBandNames.VH_DSPK",
"url":3,
"doc":"Vertical Transmit-Horizontal Receive Polarisatio Despeckled"
},
{
"ref":"eoreader.bands.bands.SarBandNames.HV",
"url":3,
"doc":"Horizontal Transmit-Vertical Receive Polarisation"
},
{
"ref":"eoreader.bands.bands.SarBandNames.HV_DSPK",
"url":3,
"doc":"Horizontal Transmit-Vertical Receive Polarisation Despeckled"
},
{
"ref":"eoreader.bands.bands.SarBandNames.from_list",
"url":3,
"doc":"Get the band enums from list of band names   >>> SarBandNames.from_list(\"VV\") [ ]   Args: name_list (Union[list, str]): List of names Returns: list: List of enums",
"func":1
},
{
"ref":"eoreader.bands.bands.SarBandNames.to_value_list",
"url":3,
"doc":"Get a list from the values of the bands   >>> SarBandNames.to_name_list([SarBandNames.HV_DSPK, SarBandNames.VV]) ['HV_DSPK', 'VV'] >>> SarBandNames.to_name_list() ['VV', 'VV_DSPK', 'HH', 'HH_DSPK', 'VH', 'VH_DSPK', 'HV', 'HV_DSPK']   Args: name_list (list): List of band names Returns: list: List of band values",
"func":1
},
{
"ref":"eoreader.bands.bands.SarBands",
"url":3,
"doc":"SAR bands class"
},
{
"ref":"eoreader.bands.bands.OpticalBandNames",
"url":3,
"doc":"This class aims to regroup equivalent bands under the same nomenclature. Each products will set their band number in regard to their corresponding name.  Note : The mapping is based on Sentinel-2 bands. Satellites can have not mapped bands (such as Sentinel-3) More information can be retrieved here: - [Overall comparison](http: blog.imagico.de/wp-content/uploads/2016/11/sat_spectra_full4a.png) - L8/S2: - [Resource 1](https: reader.elsevier.com/reader/sd/pii/S0034425718301883) - [Resource 2](https: landsat.gsfc.nasa.gov/wp-content/uploads/2015/06/Landsat.v.Sentinel-2.png) - [L4/L5, MSS-TM](https: landsat.gsfc.nasa.gov/the-multispectral-scanner-system/) - [All Landsats](https: landsat.gsfc.nasa.gov/wp-content/uploads/2016/10/all_Landsat_bands.png) - [S2](https: discovery.creodias.eu/dataset/72181b08-a577-4d55-8ece-d8485167beb7/resource/d8f5dd92-b35c-46ee-98a2-0879dad03fce/download/res_band_s2_1.png) - [S3 OLCI](https: discovery.creodias.eu/dataset/a0960a9b-c9c4-46db-bca5-ec79d0dda32b/resource/de8300a4-08cd-41aa-96ec-d9813115cc08/download/s3_res_band_ol.png) - [S3 SLSTR](https: discovery.creodias.eu/dataset/ea8f247e-d193-4368-8cf6-8687a03a5306/resource/8e5c485a-d832-42be-ad9c-af500b468f29/download/s3_slcs.png) - [Index consistency](https: www.indexdatabase.de/) This classification allows index computation and algorithms to run without knowing the band nb of every satellite. If None, then the band does not exist for the satellite."
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.CA",
"url":3,
"doc":"Coastal aerosol"
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.BLUE",
"url":3,
"doc":"Blue"
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.GREEN",
"url":3,
"doc":"Green"
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.RED",
"url":3,
"doc":"Red"
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.VRE_1",
"url":3,
"doc":"Vegetation red edge, Band 1"
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.VRE_2",
"url":3,
"doc":"Vegetation red edge, Band 2"
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.VRE_3",
"url":3,
"doc":"Vegetation red edge, Band 3"
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.NIR",
"url":3,
"doc":"NIR"
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.NARROW_NIR",
"url":3,
"doc":"Narrow NIR"
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.WV",
"url":3,
"doc":"Water vapour"
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.FAR_NIR",
"url":3,
"doc":"Far NIR"
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.SWIR_CIRRUS",
"url":3,
"doc":"Cirrus"
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.SWIR_1",
"url":3,
"doc":"SWIR, Band 1"
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.SWIR_2",
"url":3,
"doc":"SWIR, Band 2"
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.MIR",
"url":3,
"doc":"MIR"
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.TIR_1",
"url":3,
"doc":"Thermal IR, Band 1"
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.TIR_2",
"url":3,
"doc":"Thermal IR, Band 2"
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.PAN",
"url":3,
"doc":"Panchromatic"
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.from_list",
"url":3,
"doc":"Get the band enums from list of band names   >>> SarBandNames.from_list(\"VV\") [ ]   Args: name_list (Union[list, str]): List of names Returns: list: List of enums",
"func":1
},
{
"ref":"eoreader.bands.bands.OpticalBandNames.to_value_list",
"url":3,
"doc":"Get a list from the values of the bands   >>> SarBandNames.to_name_list([SarBandNames.HV_DSPK, SarBandNames.VV]) ['HV_DSPK', 'VV'] >>> SarBandNames.to_name_list() ['VV', 'VV_DSPK', 'HH', 'HH_DSPK', 'VH', 'VH_DSPK', 'HV', 'HV_DSPK']   Args: name_list (list): List of band names Returns: list: List of band values",
"func":1
},
{
"ref":"eoreader.bands.bands.OpticalBands",
"url":3,
"doc":"Optical bands class"
},
{
"ref":"eoreader.bands.bands.OpticalBands.map_bands",
"url":3,
"doc":"Mapping band names to specific satellite band numbers, as strings.   >>>  Example for Sentinel-2 L1C data >>> ob = OpticalBands() >>> ob.map_bands({ CA: '01', BLUE: '02', GREEN: '03', RED: '04', VRE_1: '05', VRE_2: '06', VRE_3: '07', NIR: '08', NNIR: '8A', WV: '09', SWIR_1: '11', SWIR_2: '12' })   Args: band_map (dict): Band mapping as {OpticalBandNames: Band number for loading band}",
"func":1
},
{
"ref":"eoreader.bands.bands.DemBandNames",
"url":3,
"doc":"DEM Band names"
},
{
"ref":"eoreader.bands.bands.DemBandNames.DEM",
"url":3,
"doc":"DEM"
},
{
"ref":"eoreader.bands.bands.DemBandNames.SLOPE",
"url":3,
"doc":"Slope"
},
{
"ref":"eoreader.bands.bands.DemBandNames.HILLSHADE",
"url":3,
"doc":"Hillshade"
},
{
"ref":"eoreader.bands.bands.DemBandNames.from_list",
"url":3,
"doc":"Get the band enums from list of band names   >>> SarBandNames.from_list(\"VV\") [ ]   Args: name_list (Union[list, str]): List of names Returns: list: List of enums",
"func":1
},
{
"ref":"eoreader.bands.bands.DemBandNames.to_value_list",
"url":3,
"doc":"Get a list from the values of the bands   >>> SarBandNames.to_name_list([SarBandNames.HV_DSPK, SarBandNames.VV]) ['HV_DSPK', 'VV'] >>> SarBandNames.to_name_list() ['VV', 'VV_DSPK', 'HH', 'HH_DSPK', 'VH', 'VH_DSPK', 'HV', 'HV_DSPK']   Args: name_list (list): List of band names Returns: list: List of band values",
"func":1
},
{
"ref":"eoreader.bands.bands.DemBands",
"url":3,
"doc":"DEM bands class"
},
{
"ref":"eoreader.bands.bands.CloudsBandNames",
"url":3,
"doc":"Clouds Band names"
},
{
"ref":"eoreader.bands.bands.CloudsBandNames.RAW_CLOUDS",
"url":3,
"doc":"Raw cloud raster (can be either QA raster, rasterized cloud vectors .)"
},
{
"ref":"eoreader.bands.bands.CloudsBandNames.CLOUDS",
"url":3,
"doc":"Binary mask of clouds (High confidence)"
},
{
"ref":"eoreader.bands.bands.CloudsBandNames.SHADOWS",
"url":3,
"doc":"Binary mask of shadows (High confidence)"
},
{
"ref":"eoreader.bands.bands.CloudsBandNames.CIRRUS",
"url":3,
"doc":"Binary mask of cirrus (High confidence)"
},
{
"ref":"eoreader.bands.bands.CloudsBandNames.ALL_CLOUDS",
"url":3,
"doc":"All clouds (Including all high confidence clouds, shadows and cirrus)"
},
{
"ref":"eoreader.bands.bands.CloudsBandNames.from_list",
"url":3,
"doc":"Get the band enums from list of band names   >>> SarBandNames.from_list(\"VV\") [ ]   Args: name_list (Union[list, str]): List of names Returns: list: List of enums",
"func":1
},
{
"ref":"eoreader.bands.bands.CloudsBandNames.to_value_list",
"url":3,
"doc":"Get a list from the values of the bands   >>> SarBandNames.to_name_list([SarBandNames.HV_DSPK, SarBandNames.VV]) ['HV_DSPK', 'VV'] >>> SarBandNames.to_name_list() ['VV', 'VV_DSPK', 'HH', 'HH_DSPK', 'VH', 'VH_DSPK', 'HV', 'HV_DSPK']   Args: name_list (list): List of band names Returns: list: List of band values",
"func":1
},
{
"ref":"eoreader.bands.bands.CloudsBands",
"url":3,
"doc":"Clouds bands class"
},
{
"ref":"eoreader.bands.index",
"url":4,
"doc":"Set of usual optical index.  Note : The nodata is always consideobn.RED to be set to 0. If this changes, it will become mandatory to use the NODATA mask everywhere !  Note 2 : This is easier to manage index as raw functions in a file rather than stoobn.RED in a class"
},
{
"ref":"eoreader.bands.index.RGI",
"url":4,
"doc":"Relative Greenness Index: https: www.indexdatabase.de/db/i-single.php?id=326 Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.NDVI",
"url":4,
"doc":"Normalized Difference Vegetation Index: https: www.indexdatabase.de/db/i-single.php?id=59 Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.TCBRI",
"url":4,
"doc":"Tasseled Cap Brightness: https: en.wikipedia.org/wiki/Tasseled_cap_transformation https: www.indexdatabase.de/db/r-single.php?id=723 Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.TCGRE",
"url":4,
"doc":"Tasseled Cap Greenness: https: en.wikipedia.org/wiki/Tasseled_cap_transformation https: www.indexdatabase.de/db/r-single.php?id=723 Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.TCWET",
"url":4,
"doc":"Tasseled Cap Wetness: https: en.wikipedia.org/wiki/Tasseled_cap_transformation https: www.indexdatabase.de/db/r-single.php?id=723 Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.NDRE2",
"url":4,
"doc":"Normalized Difference Red-Edge: https: www.indexdatabase.de/db/i-single.php?id=223 Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.NDRE3",
"url":4,
"doc":"Normalized Difference Red-Edge: https: www.indexdatabase.de/db/i-single.php?id=223 Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.GLI",
"url":4,
"doc":"Green leaf index: https: www.indexdatabase.de/db/i-single.php?id=375 Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.GNDVI",
"url":4,
"doc":"Green NDVI: https: www.indexdatabase.de/db/i-single.php?id=401 Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.RI",
"url":4,
"doc":"Normalized Difference RED/GREEN Redness Index: https: www.indexdatabase.de/db/i-single.php?id=74 Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.NDGRI",
"url":4,
"doc":"Normalized Difference GREEN/RED Index: https: www.indexdatabase.de/db/i-single.php?id=390 Also known as NDGR. Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.CIG",
"url":4,
"doc":"Chlorophyll Index Green: https: www.indexdatabase.de/db/i-single.php?id=128 Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.NDMI",
"url":4,
"doc":"Normalized Difference Moisture Index: https: www.indexdatabase.de/db/i-single.php?id=56 Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.DSWI",
"url":4,
"doc":"Disease water stress index: https: www.indexdatabase.de/db/i-single.php?id=106 Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.SRSWIR",
"url":4,
"doc":"Simple Ratio SWIR_1/SWIR_2 Clay Minerals: https: www.indexdatabase.de/db/i-single.php?id=204 Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.RDI",
"url":4,
"doc":"Ratio Drought Index: https: www.indexdatabase.de/db/i-single.php?id=71 Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.NDWI",
"url":4,
"doc":"Simple Ratio MIR/NIR Ratio Drought Index: https: www.indexdatabase.de/db/i-single.php?id=71 Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.BAI",
"url":4,
"doc":"Burn Area Index: https: www.harrisgeospatial.com/docs/BackgroundBurnIndices.html Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.NBR",
"url":4,
"doc":"Normalized Burn Ratio: https: www.indexdatabase.de/db/i-single.php?id=53 Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.MNDWI",
"url":4,
"doc":"Modified Normalised Difference Water Index : https: wiki.orfeo-toolbox.org/index.php/MNDWI Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.AWEInsh",
"url":4,
"doc":"Automated Water Extraction Index not shadow: Feyisa et al. (2014) Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.AWEIsh",
"url":4,
"doc":"Automated Water Extraction Index shadow: Feyisa et al. (2014) Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.WI",
"url":4,
"doc":"Water Index (2015): Fisher et al. (2016) Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.AFRI_1_6",
"url":4,
"doc":"Aerosol free vegetation index 1600: https: www.indexdatabase.de/db/i-single.php?id=393 Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.AFRI_2_1",
"url":4,
"doc":"Aerosol free vegetation index 2100: https: www.indexdatabase.de/db/i-single.php?id=395  WARNING There is an error in the formula, go see the papers to get the right one (0.56 instead of 0.5): https: core.ac.uk/download/pdf/130673386.pdf Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.BSI",
"url":4,
"doc":"Barren Soil Index: Rikimaru et al., 2002. Tropical forest cover density mapping. http: tropecol.com/pdf/open/PDF_43_1/43104.pdf BSI =  RED+SWIR) \u2013 (NIR+BLUE /  RED+SWIR) + (NIR+BLUE Args: bands (dict): Bands as {band_name: xr.DataArray} Returns: xr.DataArray: Computed index",
"func":1
},
{
"ref":"eoreader.bands.index.get_all_index_names",
"url":4,
"doc":"Get all index names contained in this file   >>> from eoreader.bands import index >>> index.get_all_index_names() ['AFRI_1_6', 'AFRI_2_1', 'AWEInsh', 'AWEIsh', 'BAI',  ., 'WI']   Returns: list: Index names",
"func":1
},
{
"ref":"eoreader.bands.index.get_all_index",
"url":4,
"doc":"Get all index functions contained in this file   >>> from eoreader.bands import index >>> index.get_all_index() [ ,  .,  ]   Returns: list: Index functions",
"func":1
},
{
"ref":"eoreader.bands.index.get_needed_bands",
"url":4,
"doc":"Gather all the needed bands for the specified index function   >>> index.get_needed_bands(NDVI) [ ,  ]   Returns: list: Needed bands for the index function",
"func":1
},
{
"ref":"eoreader.bands.index.get_all_needed_bands",
"url":4,
"doc":"Gather all the needed bands for all index functions   >>> index.get_all_needed_bands() {  : [ ,  ],  .  : [ ,  ] } >>>  Or written in a more readable fashion: >>> {idx.__name__: [band.value for band in bands] for idx, bands in index.get_all_needed_bands().items()} { 'AFRI_1_6': ['NIR', 'SWIR_2'],  ., 'WI': ['NIR', 'SWIR_1'] }   Returns: dict: Needed bands for all index functions",
"func":1
},
{
"ref":"eoreader.env_vars",
"url":5,
"doc":"Environment variables that can change the processes"
},
{
"ref":"eoreader.env_vars.PP_GRAPH",
"url":5,
"doc":"Environment variables for overriding default pre-processing graph path"
},
{
"ref":"eoreader.env_vars.DSPK_GRAPH",
"url":5,
"doc":"Environment variables for overriding default despeckling graph path"
},
{
"ref":"eoreader.env_vars.SAR_DEF_RES",
"url":5,
"doc":"Environment variables for SAR default resolution, used for SNAP orthorectification to override default resolution."
},
{
"ref":"eoreader.env_vars.S3_DEF_RES",
"url":5,
"doc":"Environment variables for S3 default resolution, used for SNAP orthorectification to override default resolution."
},
{
"ref":"eoreader.env_vars.DEM_PATH",
"url":5,
"doc":"Environment variables for overriding default DEM path"
},
{
"ref":"eoreader.env_vars.CI_EOREADER_BAND_FOLDER",
"url":5,
"doc":"Environment variables used in CI to override the existing band path in order to bypass SNAP process and DEM reprojection."
},
{
"ref":"eoreader.examples",
"url":6,
"doc":"EOReader examples. - []()"
},
{
"ref":"eoreader.exceptions",
"url":7,
"doc":"EOReader exceptions"
},
{
"ref":"eoreader.exceptions.EoReaderError",
"url":7,
"doc":"EOReader error"
},
{
"ref":"eoreader.exceptions.InvalidBandError",
"url":7,
"doc":"Invalid Band error, thrown when a non existing band is asked to a product."
},
{
"ref":"eoreader.exceptions.InvalidIndexError",
"url":7,
"doc":"Invalid Index error, thrown when a non existing band is asked to a produc."
},
{
"ref":"eoreader.exceptions.InvalidProductError",
"url":7,
"doc":"Invalid Product error, thrown when satellite product is not as expected."
},
{
"ref":"eoreader.exceptions.InvalidTypeError",
"url":7,
"doc":"Tile Name error, thrown when an unknown type is given (shouldn't never happen)."
},
{
"ref":"eoreader.products",
"url":8,
"doc":"SAR and Optical products  Optical data  Implemented optical satellites |Satellites | Class | Product Types | Use archive | Default Resolution | | - |  - |  - |  - |  -| |Sentinel-2 |  eoreader.products.optical.s2_product.S2Product | L1C & L2A | Yes | 20m| |Sentinel-2 Theia |  eoreader.products.optical.s2_theia_product.S2TheiaProduct | L2A | Yes | 20m| |Sentinel-3 SLSTR |  eoreader.products.optical.s3_product.S3Product | RBT | No | 300m| |Sentinel-3 OLCI |  eoreader.products.optical.s3_product.S3Product | EFR | No | 500m| |Landsat-8 OLCI |  eoreader.products.optical.l8_product.L8Product | Level 1 | Collection 1: No, Collection 2: Yes | 30m| |Landsat-7 ETM |  eoreader.products.optical.l7_product.L7Product | Level 1 | Collection 1: No, Collection 2: Yes | 30m| |Landsat-5 TM |  eoreader.products.optical.l5_product.L5Product | Level 1 | Collection 1: No, Collection 2: Yes | 30m| |Landsat-4 TM |  eoreader.products.optical.l4_product.L4Product | Level 1 | Collection 1: No, Collection 2: Yes | 30m| |Landsat-5 MSS |  eoreader.products.optical.l5_product.L5Product | Level 1 | Collection 1: No, Collection 2: Yes | 60m| |Landsat-4 MSS |  eoreader.products.optical.l4_product.L4Product | Level 1 | Collection 1: No, Collection 2: Yes | 60m| |Landsat-3 MSS |  eoreader.products.optical.l3_product.L3Product | Level 1 | Collection 1: No, Collection 2: Yes | 60m| |Landsat-2 MSS |  eoreader.products.optical.l2_product.L2Product | Level 1 | Collection 1: No, Collection 2: Yes | 60m| |Landsat-1 MSS |  eoreader.products.optical.l1_product.L1Product | Level 1 | Collection 1: No, Collection 2: Yes | 60m| Satellites products that cannot be used as archived have to be extracted before use.  Optical bands The following bands are available in  EOReader , but may not be available for all sensors.  Satellite bands These bands are mainly based on Sentinel-2 bands with some additions: -  CA : Coastal Aerosol -  BLUE -  GREEN -  RED -  VRE_1 : Vegetation Red Edge 1 -  VRE_2 : Vegetation Red Edge 2 -  VRE_3 : Vegetation Red Edge 3 -  NIR : Near Infrared -  NARROW_NIR : Narrow Near Infrared (band  8A for  Sentinel-2 ) -  WP : Water vapour -  SWIR_CIRRUS -  SWIR_1 -  SWIR_2 -  PAN : Panchromatic -  TIR_1 : Thermal Infrared 1 -  TIR_2 : Thermal Infrared 2 See [here]() for more information.  Index -  AFRI_1_6 -  AFRI_2_1 -  AWEInsh -  AWEIsh -  BAI -  BSI -  CIG -  DSWI -  GLI -  GNDVI -  MNDWI -  NBR -  NDGRI -  NDMI -  NDRE2 -  NDRE3 -  NDVI -  NDWI -  RDI -  RGI -  RI -  SRSWIR -  TCBRI -  TCGRE -  TCWET -  WI See [here]() for more information.  Cloud bands Maximum 5 cloud bands are available, according to the files provided in the data. All the bands are rasterized and orthorectified if needed (for Sentinel-2 or 3 data for example), ready to be stacked. -  RAW_CLOUDS : Raw Cloud file as provided (the only changes are the orthorectification and rasterization). Can provide other flags, or cloud probability. -  CLOUDS : Cloud presence (1) or absence (0). -  CIRRUS : Cirrus presence (1) or absence (0). -  SHADOWS : Shadows presence (1) or absence (0). -  ALL_CLOUDS : Cloud  OR Cirrus  OR Shadows presence (1) or absence (0). Do not take into account missing bands ( ie. for Landsat MSS sensors,  ALL_CLOUDS   CLOUDS ) See [here]() for more information.  DEM bands These bands need a valid worldwide DEM path positioned thanks to the environment variable  EOREADER_SAR_DEFAULT_RES -  DEM -  SLOPE -  HILLSHADE See [here]() for more information.  SAR data  Implemented SAR satellites |Satellites | Class | Product Types | Use archive| | - |  - |  - |  -| |Sentinel-1 |  eoreader.products.sar.s1_product.S1Product | SLC & GRD | Yes| |COSMO-Skymed |  eoreader.products.sar.csk_product.CskProduct | DGM & SCS, (others should also be OK) | No| |TerraSAR-X |  eoreader.products.sar.tsx_product.TsxProduct | MGD (SSC should be OK) | No| |RADARSAT-2 |  eoreader.products.sar.rs2_product.Rs2Product | SGF (SLC should be OK) | Yes|  WARNING Satellites products that cannot be used as archived have to be extracted before use.  SAR Bands According to what contains the products, allowed SAR bands are: -  VV ( eoreader.bands.bands.SarBandNames.VV ) -  VH ( eoreader.bands.bands.SarBandNames.VH ) -  HH ( eoreader.bands.bands.SarBandNames.HH ) -  HV ( eoreader.bands.bands.SarBandNames.HV ) You also can load despeckled bands: -  VV_DSPK ( eoreader.bands.bands.SarBandNames.VV_DSPK ) -  VH_DSPK ( eoreader.bands.bands.SarBandNames.VH_DSPK ) -  HH_DSPK ( eoreader.bands.bands.SarBandNames.HH_DSPK ) -  HV_DSPK ( eoreader.bands.bands.SarBandNames.HV_DSPK )  DEM bands These bands need a valid worldwide DEM path positioned thanks to the environment variable  EOREADER_SAR_DEFAULT_RES -  DEM -  SLOPE See [here]() for more information."
},
{
"ref":"eoreader.products.optical",
"url":9,
"doc":"Optical products.  Optical data  Implemented optical satellites |Satellites | Class | Product Types | Use archive | Default Resolution | | - |  - |  - |  - |  -| |Sentinel-2 |  eoreader.products.optical.s2_product.S2Product | L1C & L2A | Yes | 20m| |Sentinel-2 Theia |  eoreader.products.optical.s2_theia_product.S2TheiaProduct | L2A | Yes | 20m| |Sentinel-3 SLSTR |  eoreader.products.optical.s3_product.S3Product | RBT | No | 300m| |Sentinel-3 OLCI |  eoreader.products.optical.s3_product.S3Product | EFR | No | 500m| |Landsat-8 OLCI |  eoreader.products.optical.l8_product.L8Product | Level 1 | Collection 1: No, Collection 2: Yes | 30m| |Landsat-7 ETM |  eoreader.products.optical.l7_product.L7Product | Level 1 | Collection 1: No, Collection 2: Yes | 30m| |Landsat-5 TM |  eoreader.products.optical.l5_product.L5Product | Level 1 | Collection 1: No, Collection 2: Yes | 30m| |Landsat-4 TM |  eoreader.products.optical.l4_product.L4Product | Level 1 | Collection 1: No, Collection 2: Yes | 30m| |Landsat-5 MSS |  eoreader.products.optical.l5_product.L5Product | Level 1 | Collection 1: No, Collection 2: Yes | 60m| |Landsat-4 MSS |  eoreader.products.optical.l4_product.L4Product | Level 1 | Collection 1: No, Collection 2: Yes | 60m| |Landsat-3 MSS |  eoreader.products.optical.l3_product.L3Product | Level 1 | Collection 1: No, Collection 2: Yes | 60m| |Landsat-2 MSS |  eoreader.products.optical.l2_product.L2Product | Level 1 | Collection 1: No, Collection 2: Yes | 60m| |Landsat-1 MSS |  eoreader.products.optical.l1_product.L1Product | Level 1 | Collection 1: No, Collection 2: Yes | 60m| Satellites products that cannot be used as archived have to be extracted before use.  Optical bands The following bands are available in  EOReader , but may not be available for all sensors.  Satellite bands These bands are mainly based on Sentinel-2 bands with some additions: -  CA : Coastal Aerosol -  BLUE -  GREEN -  RED -  VRE_1 : Vegetation Red Edge 1 -  VRE_2 : Vegetation Red Edge 2 -  VRE_3 : Vegetation Red Edge 3 -  NIR : Near Infrared -  NARROW_NIR : Narrow Near Infrared (band  8A for  Sentinel-2 ) -  WP : Water vapour -  SWIR_CIRRUS -  SWIR_1 -  SWIR_2 -  PAN : Panchromatic -  TIR_1 : Thermal Infrared 1 -  TIR_2 : Thermal Infrared 2 See [here]() for more information.  Index -  AFRI_1_6 -  AFRI_2_1 -  AWEInsh -  AWEIsh -  BAI -  BSI -  CIG -  DSWI -  GLI -  GNDVI -  MNDWI -  NBR -  NDGRI -  NDMI -  NDRE2 -  NDRE3 -  NDVI -  NDWI -  RDI -  RGI -  RI -  SRSWIR -  TCBRI -  TCGRE -  TCWET -  WI See [here]() for more information.  Cloud bands Maximum 5 cloud bands are available, according to the files provided in the data. All the bands are rasterized and orthorectified if needed (for Sentinel-2 or 3 data for example), ready to be stacked. -  RAW_CLOUDS : Raw Cloud file as provided (the only changes are the orthorectification and rasterization). Can provide other flags, or cloud probability. -  CLOUDS : Cloud presence (1) or absence (0). -  CIRRUS : Cirrus presence (1) or absence (0). -  SHADOWS : Shadows presence (1) or absence (0). -  ALL_CLOUDS : Cloud  OR Cirrus  OR Shadows presence (1) or absence (0). Do not take into account missing bands ( ie. for Landsat MSS sensors,  ALL_CLOUDS   CLOUDS ) See [here]() for more information.  DEM bands These bands need a valid worldwide DEM path positioned thanks to the environment variable  EOREADER_SAR_DEFAULT_RES -  DEM -  SLOPE -  HILLSHADE See [here]() for more information.  Specifications  Optical band mapping between sensors |Bands (names) | Coastal aerosol | Blue | Green | Red | Vegetation red edge | Vegetation red edge | Vegetation red edge | NIR | Narrow NIR | Water vapor | SWIR \u2013 Cirrus | SWIR | SWIR | Panchromatic | Thermal IR | Thermal IR| | - |  - |  - |  - |  - |  - |  - |  - |  - |  - |  - |  - |  - |  - |  - |  - |  -| | Band alias |  CA |  BLUE |  GREEN |  RED |  VRE_1 |  VRE_2 |  VRE_3 |  NIR |  NARROW_NIR |  WP |  SWIR_CIRRUS |  SWIR_1 |  SWIR_2 |  PAN |  TIR_1 |  TIR_2 | |Sentinel-2 |  1 (60m) |  2 (10m) |  3 (10m) |  4 (10m) |  5 (20m) | 6 (20m) | 7 (20m) | 8 (10m) |  8A (20m) | 9 (60m) | 10 (60m) | 11 (20m) | 12 (20m) | | | | |Sentinel-2 Theia |  Not available |  2 (10m) | 3 (10m) |  4 (10m) |  5 (20m) | 6 (20m) | 7 (20m) | 8 (10m) |  8A (20m) |  Not available | 10 (60m) | 11 (20m) | 12 (20m) | | | | |Sentinel-3 OLCI |  2 (300m) |  3 (300m) | 6 (300m) | 8 (300m) | 11 (300m) | 12 (300m) |  16 (300m) |  17 (300m) |  17 (300m) |  20 (300m) | | | | | | | |Sentinel-3 SLSTR | | |  1 (500m) |  2 (500m) | | | | 3 (500m) | 3 (500m) | |  4 (500m) |  5 (500m) | 6 (500m) | | 8 (1km) | 9 (1km)| |Landsat OLCI (8) |  1 (30m) |  2 (30m) |  3 (30m) |  4 (30m) | | | |  5 (30m) |  5 (30m) | | 9 (30m) | 6 (30m) | 7 (30m) | 8 (15m) | 10 (100m) | 11 (100m)| |Landsat ETM (7)| |  1 (30m) |  2 (30m) |  3 (30m) | | | |  4 (30m) |  4 (30m) | | |  5 (30m) | 7 (30m) | 8 (15m) | 6 (60m) | 6 (60m)| |Landsat TM (5-4)| |  1 (30m) |  2 (30m) |  3 (30m) | | | |  4 (30m) |  4 (30m) | | |  5 (30m) | 7 (30m) | | 6 (120m) | 6 (120m)| |Landsat MSS (5-4)| | |  1 (60m) |  2 (60m) |  3 (60m) |  3 (60m) |  3 (60m) |  4 (60m) |  4 (60m) | | | | | | | | |Landsat MSS (1-3)| | |  4 (60m) |  5 (60m) |  6 (60m) |  6 (60m) |  6 (60m) |  7 (60m) |  7 (60m) | | | | | | 8 (240m)  only for Landsat-3 | 8 (240m)  only for Landsat-3 | \\ Not all bands of this satellite are used in EOReader  Cloud bands specifications Maximum 5 cloud bands are available, according to the files provided in the data. All the bands are rasterized and orthorectified if needed (for Sentinel-2 or 3 data for example), ready to be stacked. The only difference with the other bands is that the cloud bands are provided in  uint8 and have a nodata equal to 255. -  eoreader.bands.bands.CloudsBandNames.RAW_CLOUDS : Raw Cloud file as provided (the only changes are the orthorectification and rasterization). Can provide other flags, or cloud probability. -  eoreader.bands.bands.CloudsBandNames.CLOUDS : Cloud presence (1) or absence (0). If clouds are provided in probabilities, their presence is determined according to Landsat definition (proba> 67%) -  eoreader.bands.bands.CloudsBandNames.CIRRUS : Cirrus presence (1) or absence (0). If clouds are provided in probabilities, their presence is determined according to Landsat definition (proba> 67%) -  eoreader.bands.bands.CloudsBandNames.SHADOWS : Shadows presence (1) or absence (0). If clouds are provided in probabilities, their presence is determined according to Landsat definition (proba> 67%) -  eoreader.bands.bands.CloudsBandNames.ALL_CLOUDS : Cloud  OR Cirrus  OR Shadows presence (1) or absence (0). Do not take into account missing bands (ie. for Landsat MSS sensors,  ALL_CLOUDS   CLOUDS ) |Satellites | Clouds Bands| | - |  -| |Sentinel-2 |  RAW_CLOUDS ,  CLOUDS ,  CIRRUS ,  ALL_CLOUDS | |Sentinel-2 Theia |  RAW_CLOUDS ,  CLOUDS ,  SHADOWS ,  CIRRUS ,  ALL_CLOUDS | |Sentinel-3 OLCI |  No cloud file available for S3-OLCI data | |Sentinel-3 SLSTR |  RAW_CLOUDS ,  CLOUDS ,  CIRRUS ,  ALL_CLOUDS | |Landsat-8 |  RAW_CLOUDS ,  CLOUDS ,  SHADOWS ,  CIRRUS ,  ALL_CLOUDS | |Landsat-7 |  RAW_CLOUDS ,  CLOUDS ,  SHADOWS ,  ALL_CLOUDS | |Landsat-5 TM |  RAW_CLOUDS ,  CLOUDS ,  SHADOWS ,  ALL_CLOUDS | |Landsat-4 TM |  RAW_CLOUDS ,  CLOUDS ,  SHADOWS ,  ALL_CLOUDS | |Landsat-5 MSS |  RAW_CLOUDS ,  CLOUDS ,  ALL_CLOUDS | |Landsat-4 MSS |  RAW_CLOUDS ,  CLOUDS ,  ALL_CLOUDS | |Landsat-3 |  RAW_CLOUDS ,  CLOUDS ,  ALL_CLOUDS | |Landsat-2 |  RAW_CLOUDS ,  CLOUDS ,  ALL_CLOUDS | |Landsat-1 |  RAW_CLOUDS ,  CLOUDS ,  ALL_CLOUDS |  DEM bands specifications Optical satellites can all load  eoreader.bands.bands.DemBandNames.DEM ,  eoreader.bands.bands.DemBandNames.SLOPE and  eoreader.bands.bands.DemBandNames.HILLSHADE bands. The  SLOPE and  HILLSHADE bands are computed with the [ gdaldem ](https: gdal.org/programs/gdaldem.html) tool. Use the environment variable  EOREADER_SAR_DEFAULT_RES to position your worldwide DEM.  Available index |Index | Needed bands | Accepted satellites| | - |  - |  -| | eoreader.bands.index.AFRI_1_6 |  NIR ,  SWIR_1 | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM| | eoreader.bands.index.AFRI_2_1 |  NIR ,  SWIR_2 | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM| | eoreader.bands.index.AWEInsh |  BLUE ,  GREEN ,  NIR ,  SWIR_1 ,  SWIR_2 | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM| | eoreader.bands.index.AWEIsh |  GREEN ,  NIR ,  SWIR_1 ,  SWIR_2 | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM| | eoreader.bands.index.BAI |  RED ,  NIR | All optical satellites| | eoreader.bands.index.BSI |  BLUE ,  RED ,  NIR ,  SWIR_1 | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM| | eoreader.bands.index.CIG |  GREEN ,  NIR | All optical satellites| | eoreader.bands.index.DSWI |  GREEN ,  RED ,  NIR ,  SWIR_1 | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM| | eoreader.bands.index.GLI |  GREEN ,  RED ,  BLUE | Sentinel-2, Sentinel-3 OLCI, Landsat OLCI, (E)TM| | eoreader.bands.index.GNDVI |  GREEN ,  NIR | All optical satellites| | eoreader.bands.index.MNDWI |  GREEN ,  SWIR_1 | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM| | eoreader.bands.index.NBR |  NNIR ,  SWIR_2 | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM| | eoreader.bands.index.NDGRI |  GREEN ,  RED | All optical satellites| | eoreader.bands.index.NDMI |  NIR ,  SWIR_1 | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM| | eoreader.bands.index.NDRE2 |  NIR ,  VRE_1 | Sentinel-2, Sentinel-3 OLCI, Landsat MSS| | eoreader.bands.index.NDRE3 |  NIR ,  VRE_2 | Sentinel-2, Sentinel-3 OLCI, Landsat MSS| | eoreader.bands.index.NDVI |  RED ,  NIR | All optical satellites| | eoreader.bands.index.NDWI |  GREEN ,  NIR | All optical satellites| | eoreader.bands.index.RDI |  NNIR ,  SWIR_2 | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM| | eoreader.bands.index.RGI |  GREEN ,  RED | All optical satellites| | eoreader.bands.index.RI |  GREEN ,  VRE_1 | Sentinel-2, Sentinel-3 OLCI, Landsat MSS| | eoreader.bands.index.SRSWIR |  SWIR_1 ,  SWIR_2 | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM| | eoreader.bands.index.TCBRI |  BLUE ,  GREEN ,  RED ,  NIR ,  SWIR_1 ,  SWIR_2 | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM| | eoreader.bands.index.TCGRE |  BLUE ,  GREEN ,  RED ,  NIR ,  SWIR_1 ,  SWIR_2 | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM| | eoreader.bands.index.TCWET |  BLUE ,  GREEN ,  RED ,  NIR ,  SWIR_1 ,  SWIR_2 | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM| | eoreader.bands.index.WI |  GREEN ,  RED ,  NIR ,  SWIR_1 ,  SWIR_2 | Sentinel-2, Sentinel-3 SLSTR, Landsat OLCI, (E)TM|  Default SNAP resolution You can override default SNAP resolution (in meters) when orthorecifying SAR and S3 bands by setting the following environment variables: -  EOREADER_S3_DEFAULT_RES (500m for SLSTR and 300m for OLCI data by default)  Documentary Sources  Optical data  Landsat - [Collection 1 vs Collection 2](https: www.usgs.gov/media/files/landsat-collection-1-vs-collection-2-summary) - [Quality assessment Collection 1](https: www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-1-level-1-quality-assessment-band) - [Quality assessment Collection 2](https: www.usgs.gov/core-science-systems/nli/landsat/landsat-collection-2-quality-assessment-bands) - [MSS Collection 2 Data Format](https: www.usgs.gov/media/files/landsat-1-5-mss-collection-2-level-1-data-format-control-book) - [TM Collection 2 Data Format](https: www.usgs.gov/media/files/landsat-4-5-tm-collection-2-level-1-data-format-control-book) - [ETM Collection 2 Data Format](https: www.usgs.gov/media/files/landsat-7-etm-collection-2-level-1-data-format-control-book) - [OLCI Collection 2 Data Format](https: www.usgs.gov/media/files/landsat-8-level-1-data-format-control-book)  Sentinel-2 - [Cloud masks](https: sentinels.copernicus.eu/web/sentinel/technical-guides/sentinel-2-msi/level-1c/cloud-masks) - [Product Specification](https: sentinel.esa.int/documents/247904/349490/S2_MSI_Product_Specification.pdf)  Sentinel-2 Theia - [Product Format](https: labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/)  Sentinel-3 - [OLCI Product Format](https: sentinel.esa.int/documents/247904/1872756/Sentinel-3-OLCI-Product-Data-Format-Specification-OLCI-Level-1) - [SLSTR Clouds](https: sentinels.copernicus.eu/web/sentinel/technical-guides/sentinel-3-slstr/level-1/cloud-identification)  PlanetScope - [Product Specification](https: earth.esa.int/eogateway/documents/20142/37627/Planet-combined-imagery-product-specs-2020.pdf) - [On Medium](https: medium.com/geoplexing/getting-started-with-planet-imagery-part-3-items-and-ordering-476a1a21618c)  Band mapping - You can find a magnificent band comparison chart on the [Imagico](http: blog.imagico.de/satellite-comparison-update/) blog. - [L8-S2](https: reader.elsevier.com/reader/sd/pii/S0034425718301883) - [L8-S2](https: landsat.gsfc.nasa.gov/wp-content/uploads/2015/06/Landsat.v.Sentinel-2.png) - [L4/L5, MSS-TM](https: landsat.gsfc.nasa.gov/the-multispectral-scanner-system/) - [All Landsats](https: landsat.gsfc.nasa.gov/wp-content/uploads/2016/10/all_Landsat_bands.png) - [S2](https: discovery.creodias.eu/dataset/72181b08-a577-4d55-8ece-d8485167beb7/resource/d8f5dd92-b35c-46ee-98a2-0879dad03fce/download/res_band_s2_1.png) - [S3 OLCI](https: discovery.creodias.eu/dataset/a0960a9b-c9c4-46db-bca5-ec79d0dda32b/resource/de8300a4-08cd-41aa-96ec-d9813115cc08/download/s3_res_band_ol.png) - [S3 SLSTR](https: discovery.creodias.eu/dataset/ea8f247e-d193-4368-8cf6-8687a03a5306/resource/8e5c485a-d832-42be-ad9c-af500b468f29/download/s3_slcs.png)  Index - [Index consistency](https: www.indexdatabase.de/) - Specific sources inside the index function documentation in  eoreader.bands.index "
},
{
"ref":"eoreader.products.optical.l1_product",
"url":10,
"doc":"Landsat-1 products"
},
{
"ref":"eoreader.products.optical.l1_product.L1Product",
"url":10,
"doc":"Class of Landsat-1 Products"
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.footprint",
"url":11,
"doc":"Get real footprint of the products (without nodata, in french  emprise utile)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>> prod.footprint() index geometry 0 0 POLYGON  366165.000 4899735.000, 366165.000 4 .   Overload of the generic function because landsat nodata seems to be different in QA than in regular bands. Indeed, nodata pixels vary according to the band sensor footprint, whereas QA nodata is where at least one band has nodata. We chose to keep QA nodata values for the footprint in order to show where all bands are valid.  TL;DR: We use the QA nodata value to determine the product's footprint . Returns: gpd.GeoDataFrame: Footprint as a GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.get_datetime",
"url":11,
"doc":"Get the product's acquisition datetime, with format  YYYYMMDDTHHMMSS   %Y%m%dT%H%M%S   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>> prod.get_datetime(as_datetime=True) datetime.datetime(2020, 5, 18, 16, 34, 7) >>> prod.get_datetime(as_datetime=False) '20200518T163407'   Args: as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string. Returns: Union[str, datetime.datetime]: Its acquisition datetime",
"func":1
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.get_band_paths",
"url":11,
"doc":"Return the paths of required bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_band_paths([GREEN, RED]) {  : 'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B3.TIF',  : 'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B4.TIF' }   Args: band_list (list): List of the wanted bands resolution (float): Useless here Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.read_mtd",
"url":11,
"doc":"Read Landsat metadata as: - a  pandas.DataFrame whatever its collection is (by default for collection 1) - a XML root + its namespace if the product is retrieved from the 2nd collection (by default for collection 2)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>>  COLLECTION 1 : Open metadata as panda DataFrame >>> prod.read_mtd() NAME ORIGIN  . RESAMPLING_OPTION value \"Image courtesy of the U.S. Geological Survey\"  . \"CUBIC_CONVOLUTION\" [1 rows x 197 columns] >>>  COLLECTION 2 : Open metadata as XML >>> path = r\"LC08_L1TP_200030_20201220_20210310_02_T1\"  Collection 2 >>> prod = Reader().open(path) >>> prod.read_mtd() ( ,  ) >>>  COLLECTION 2 : Force to pandas.DataFrame >>> prod.read_mtd(force_pd=True) NAME ORIGIN  . RESAMPLING_OPTION value \"Image courtesy of the U.S. Geological Survey\"  . \"CUBIC_CONVOLUTION\" [1 rows x 263 columns]   Args: force_pd (bool): If collection 2, return a pandas.DataFrame instead of a XML root + namespace Returns: pd.DataFrame: Metadata as a Pandas DataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.get_mean_sun_angles",
"url":11,
"doc":"Get Mean Sun angles (Azimuth and Zenith angles)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_mean_sun_angles() (140.80752656, 61.93065805)   Returns: (float, float): Mean Azimuth and Zenith angle",
"func":1
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.get_default_band",
"url":12,
"doc":"Get default band:  GREEN for optical data as every optical satellite has a GREEN band.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band()    Returns: str: Default band",
"func":1
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.get_default_band_path",
"url":12,
"doc":"Get default band ( GREEN for optical data) path.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band_path() 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2'   Returns: str: Default band path",
"func":1
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.crs",
"url":12,
"doc":"Get UTM projection of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_crs() CRS.from_epsg(32630)   Returns: rasterio.crs.CRS: CRS object",
"func":1
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.extent",
"url":12,
"doc":"Get UTM extent of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_extent() geometry 0 POLYGON  309780.000 4390200.000, 309780.000 4 .   Returns: gpd.GeoDataFrame: Footprint in UTM",
"func":1
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.get_existing_bands",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_bands() [ ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ]   Returns: list: List of existing bands in the products",
"func":1
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.get_existing_band_paths",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_band_paths() {  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B01.jp2',  .,  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B12.jp2' }   Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.get_date",
"url":13,
"doc":"Get the product's acquisition date.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_date(as_date=True) datetime.datetime(2020, 8, 24, 0, 0) >>> prod.get_date(as_date=False) '20200824'   Args: as_date (bool): Return the date as a datetime.date. If false, returns a string. Returns: str: Its acquisition date",
"func":1
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.load",
"url":13,
"doc":"Open the bands and compute the wanted index. The bands will be purged of nodata and invalid pixels, the nodata will be set to 0 and the bands will be masked arrays in float. Bands that come out this function at the same time are collocated and therefore have the same shapes. This can be broken if you load data separately. Its is best to always load DEM data with some real bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> bands = prod.load([GREEN, NDVI], resolution=20) >>> bands  ' {  :  array( [0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0,  :  array( [0.0615 , 0.061625, 0.061 ,  ., 0.12085 , 0.120225, 0.113575], [0.061075, 0.06045 , 0.06025 ,  ., 0.114625, 0.119625, 0.117625], [0.06475 , 0.06145 , 0.060925,  ., 0.111475, 0.114925, 0.115175],  ., [0.1516 , 0.14195 , 0.1391 ,  ., 0.159975, 0.14145 , 0.127075], [0.140325, 0.125975, 0.131875,  ., 0.18245 , 0.1565 , 0.13015 ], [0.133475, 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675, 0.16405  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0 }  '   Args: bands (Union[list, BandNames, Callable]): Band list resolution (float): Resolution of the band, in meters size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided. Returns: dict: {band_name, band xarray}",
"func":1
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.has_band",
"url":13,
"doc":"Does this products has the specified band ? By band, we mean: - satellite band - index - DEM band - cloud band   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.has_band(GREEN) True >>> prod.has_band(TIR_2) False >>> prod.has_band(NDVI) True >>> prod.has_band(SHADOWS) False >>> prod.has_band(HILLSHADE) True   Args: band (Union[obn, sbn]): Optical or SAR band Returns: bool: True if the products has the specified band",
"func":1
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.output",
"url":13,
"doc":"Output directory of the product, to write orthorectified data for example."
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.stack",
"url":13,
"doc":"Stack bands and index of a products.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> stack = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  In meters >>> stack  '  array( [ 0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [ 0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [ 2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [ 1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [ 1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [ 1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ,  0.27066118, 0.23466069, 0.18792598,  ., -0.4611526 , -0.49751845, -0.4865216 ], [ 0.22425456, 0.28004232, 0.27851456,  ., -0.5032771 , -0.501796 , -0.502669 ], [-0.07466951, 0.06360884, 0.1207174 ,  ., -0.50617427, -0.50219285, -0.5034222 ], [-0.47076276, -0.4705828 , -0.4747971 ,  ., -0.32138503, -0.36619243, -0.37428448], [-0.4826967 , -0.5032287 , -0.48544118,  ., -0.278925 , -0.31404778, -0.36052078], [-0.488381 , -0.48253912, -0.4697526 ,  ., -0.38105175, -0.30813277, -0.27739233 ,  0.0615 , 0.061625 , 0.061 ,  ., 0.12085 , 0.120225 , 0.113575 ], [ 0.061075 , 0.06045 , 0.06025 ,  ., 0.114625 , 0.119625 , 0.117625 ], [ 0.06475 , 0.06145 , 0.060925 ,  ., 0.111475 , 0.114925 , 0.115175 ],  ., [ 0.1516 , 0.14195 , 0.1391 ,  ., 0.159975 , 0.14145 , 0.127075 ], [ 0.140325 , 0.125975 , 0.131875 ,  ., 0.18245 , 0.1565 , 0.13015 ], [ 0.133475 , 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675 , 0.16405  ], dtype=float32) Coordinates:  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0  z (z) MultiIndex - variable (z) object 'NDVI' 'MNDWI' 'GREEN' - band (z) int64 1 1 1 Attributes: long_name: ['NDVI', 'MNDWI', 'GREEN']  '   Args: bands (list): Bands and index combination resolution (float): Stack resolution. . If not specified, use the product resolution. stack_path (str): Stack path save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000) Returns: xr.DataArray: Stack as a DataArray",
"func":1
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.name",
"url":13,
"doc":"Product name (its filename without any extension)."
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.split_name",
"url":13,
"doc":"Split name, to retrieve every information from its filename (dates, tile, product type .)."
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.archive_path",
"url":13,
"doc":"Archive path, same as the product path if not specified. Useful when you want to know where both the extracted and archived version of your product are stored."
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.path",
"url":13,
"doc":"Usable path to the product, either extracted or archived path, according to the satellite."
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.is_archived",
"url":13,
"doc":"Is the archived product is processed (a products is considered as archived if its products path is a directory)."
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.needs_extraction",
"url":13,
"doc":"Does this products needs to be extracted to be processed ? ( True by default)."
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.date",
"url":13,
"doc":"Acquisition date."
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.datetime",
"url":13,
"doc":"Acquisition datetime."
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.tile_name",
"url":13,
"doc":"Tile if possible (for data that can be piled, for example S2 and Landsats)."
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.sensor_type",
"url":13,
"doc":"Sensor type, SAR or optical."
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.product_type",
"url":13,
"doc":"Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.band_names",
"url":13,
"doc":"Band mapping between band wrapping names such as  GREEN and band real number such as  03 for Sentinel-2."
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.is_reference",
"url":13,
"doc":"If the product is a reference, used for algorithms that need pre and post data, such as fire detection."
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.corresponding_ref",
"url":13,
"doc":"The corresponding reference products to the current one (if the product is not a reference but has a reference data corresponding to it). A list because of multiple ref in case of non-stackable products (S3, S1 .)"
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.nodata",
"url":13,
"doc":"Product nodata, set to 0 by default. Please do not touch this or all index will fail."
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.platform",
"url":13,
"doc":"Product platform, such as Sentinel-2"
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.resolution",
"url":13,
"doc":"Default resolution in meters of the current product. For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles."
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.condensed_name",
"url":13,
"doc":"Condensed name, the filename with only useful data to keep the name unique (ie.  20191215T110441_S2_30TXP_L2A_122756 ). Used to shorten names and paths."
},
{
"ref":"eoreader.products.optical.l1_product.L1Product.sat_id",
"url":13,
"doc":"Satellite ID, i.e.  S2 for Sentinel-2"
},
{
"ref":"eoreader.products.optical.l2_product",
"url":14,
"doc":"Landsat-2 products"
},
{
"ref":"eoreader.products.optical.l2_product.L2Product",
"url":14,
"doc":"Class of Landsat-2 Products"
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.footprint",
"url":11,
"doc":"Get real footprint of the products (without nodata, in french  emprise utile)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>> prod.footprint() index geometry 0 0 POLYGON  366165.000 4899735.000, 366165.000 4 .   Overload of the generic function because landsat nodata seems to be different in QA than in regular bands. Indeed, nodata pixels vary according to the band sensor footprint, whereas QA nodata is where at least one band has nodata. We chose to keep QA nodata values for the footprint in order to show where all bands are valid.  TL;DR: We use the QA nodata value to determine the product's footprint . Returns: gpd.GeoDataFrame: Footprint as a GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.get_datetime",
"url":11,
"doc":"Get the product's acquisition datetime, with format  YYYYMMDDTHHMMSS   %Y%m%dT%H%M%S   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>> prod.get_datetime(as_datetime=True) datetime.datetime(2020, 5, 18, 16, 34, 7) >>> prod.get_datetime(as_datetime=False) '20200518T163407'   Args: as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string. Returns: Union[str, datetime.datetime]: Its acquisition datetime",
"func":1
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.get_band_paths",
"url":11,
"doc":"Return the paths of required bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_band_paths([GREEN, RED]) {  : 'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B3.TIF',  : 'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B4.TIF' }   Args: band_list (list): List of the wanted bands resolution (float): Useless here Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.read_mtd",
"url":11,
"doc":"Read Landsat metadata as: - a  pandas.DataFrame whatever its collection is (by default for collection 1) - a XML root + its namespace if the product is retrieved from the 2nd collection (by default for collection 2)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>>  COLLECTION 1 : Open metadata as panda DataFrame >>> prod.read_mtd() NAME ORIGIN  . RESAMPLING_OPTION value \"Image courtesy of the U.S. Geological Survey\"  . \"CUBIC_CONVOLUTION\" [1 rows x 197 columns] >>>  COLLECTION 2 : Open metadata as XML >>> path = r\"LC08_L1TP_200030_20201220_20210310_02_T1\"  Collection 2 >>> prod = Reader().open(path) >>> prod.read_mtd() ( ,  ) >>>  COLLECTION 2 : Force to pandas.DataFrame >>> prod.read_mtd(force_pd=True) NAME ORIGIN  . RESAMPLING_OPTION value \"Image courtesy of the U.S. Geological Survey\"  . \"CUBIC_CONVOLUTION\" [1 rows x 263 columns]   Args: force_pd (bool): If collection 2, return a pandas.DataFrame instead of a XML root + namespace Returns: pd.DataFrame: Metadata as a Pandas DataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.get_mean_sun_angles",
"url":11,
"doc":"Get Mean Sun angles (Azimuth and Zenith angles)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_mean_sun_angles() (140.80752656, 61.93065805)   Returns: (float, float): Mean Azimuth and Zenith angle",
"func":1
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.get_default_band",
"url":12,
"doc":"Get default band:  GREEN for optical data as every optical satellite has a GREEN band.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band()    Returns: str: Default band",
"func":1
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.get_default_band_path",
"url":12,
"doc":"Get default band ( GREEN for optical data) path.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band_path() 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2'   Returns: str: Default band path",
"func":1
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.crs",
"url":12,
"doc":"Get UTM projection of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_crs() CRS.from_epsg(32630)   Returns: rasterio.crs.CRS: CRS object",
"func":1
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.extent",
"url":12,
"doc":"Get UTM extent of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_extent() geometry 0 POLYGON  309780.000 4390200.000, 309780.000 4 .   Returns: gpd.GeoDataFrame: Footprint in UTM",
"func":1
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.get_existing_bands",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_bands() [ ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ]   Returns: list: List of existing bands in the products",
"func":1
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.get_existing_band_paths",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_band_paths() {  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B01.jp2',  .,  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B12.jp2' }   Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.get_date",
"url":13,
"doc":"Get the product's acquisition date.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_date(as_date=True) datetime.datetime(2020, 8, 24, 0, 0) >>> prod.get_date(as_date=False) '20200824'   Args: as_date (bool): Return the date as a datetime.date. If false, returns a string. Returns: str: Its acquisition date",
"func":1
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.load",
"url":13,
"doc":"Open the bands and compute the wanted index. The bands will be purged of nodata and invalid pixels, the nodata will be set to 0 and the bands will be masked arrays in float. Bands that come out this function at the same time are collocated and therefore have the same shapes. This can be broken if you load data separately. Its is best to always load DEM data with some real bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> bands = prod.load([GREEN, NDVI], resolution=20) >>> bands  ' {  :  array( [0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0,  :  array( [0.0615 , 0.061625, 0.061 ,  ., 0.12085 , 0.120225, 0.113575], [0.061075, 0.06045 , 0.06025 ,  ., 0.114625, 0.119625, 0.117625], [0.06475 , 0.06145 , 0.060925,  ., 0.111475, 0.114925, 0.115175],  ., [0.1516 , 0.14195 , 0.1391 ,  ., 0.159975, 0.14145 , 0.127075], [0.140325, 0.125975, 0.131875,  ., 0.18245 , 0.1565 , 0.13015 ], [0.133475, 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675, 0.16405  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0 }  '   Args: bands (Union[list, BandNames, Callable]): Band list resolution (float): Resolution of the band, in meters size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided. Returns: dict: {band_name, band xarray}",
"func":1
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.has_band",
"url":13,
"doc":"Does this products has the specified band ? By band, we mean: - satellite band - index - DEM band - cloud band   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.has_band(GREEN) True >>> prod.has_band(TIR_2) False >>> prod.has_band(NDVI) True >>> prod.has_band(SHADOWS) False >>> prod.has_band(HILLSHADE) True   Args: band (Union[obn, sbn]): Optical or SAR band Returns: bool: True if the products has the specified band",
"func":1
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.output",
"url":13,
"doc":"Output directory of the product, to write orthorectified data for example."
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.stack",
"url":13,
"doc":"Stack bands and index of a products.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> stack = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  In meters >>> stack  '  array( [ 0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [ 0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [ 2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [ 1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [ 1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [ 1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ,  0.27066118, 0.23466069, 0.18792598,  ., -0.4611526 , -0.49751845, -0.4865216 ], [ 0.22425456, 0.28004232, 0.27851456,  ., -0.5032771 , -0.501796 , -0.502669 ], [-0.07466951, 0.06360884, 0.1207174 ,  ., -0.50617427, -0.50219285, -0.5034222 ], [-0.47076276, -0.4705828 , -0.4747971 ,  ., -0.32138503, -0.36619243, -0.37428448], [-0.4826967 , -0.5032287 , -0.48544118,  ., -0.278925 , -0.31404778, -0.36052078], [-0.488381 , -0.48253912, -0.4697526 ,  ., -0.38105175, -0.30813277, -0.27739233 ,  0.0615 , 0.061625 , 0.061 ,  ., 0.12085 , 0.120225 , 0.113575 ], [ 0.061075 , 0.06045 , 0.06025 ,  ., 0.114625 , 0.119625 , 0.117625 ], [ 0.06475 , 0.06145 , 0.060925 ,  ., 0.111475 , 0.114925 , 0.115175 ],  ., [ 0.1516 , 0.14195 , 0.1391 ,  ., 0.159975 , 0.14145 , 0.127075 ], [ 0.140325 , 0.125975 , 0.131875 ,  ., 0.18245 , 0.1565 , 0.13015 ], [ 0.133475 , 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675 , 0.16405  ], dtype=float32) Coordinates:  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0  z (z) MultiIndex - variable (z) object 'NDVI' 'MNDWI' 'GREEN' - band (z) int64 1 1 1 Attributes: long_name: ['NDVI', 'MNDWI', 'GREEN']  '   Args: bands (list): Bands and index combination resolution (float): Stack resolution. . If not specified, use the product resolution. stack_path (str): Stack path save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000) Returns: xr.DataArray: Stack as a DataArray",
"func":1
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.name",
"url":13,
"doc":"Product name (its filename without any extension)."
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.split_name",
"url":13,
"doc":"Split name, to retrieve every information from its filename (dates, tile, product type .)."
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.archive_path",
"url":13,
"doc":"Archive path, same as the product path if not specified. Useful when you want to know where both the extracted and archived version of your product are stored."
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.path",
"url":13,
"doc":"Usable path to the product, either extracted or archived path, according to the satellite."
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.is_archived",
"url":13,
"doc":"Is the archived product is processed (a products is considered as archived if its products path is a directory)."
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.needs_extraction",
"url":13,
"doc":"Does this products needs to be extracted to be processed ? ( True by default)."
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.date",
"url":13,
"doc":"Acquisition date."
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.datetime",
"url":13,
"doc":"Acquisition datetime."
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.tile_name",
"url":13,
"doc":"Tile if possible (for data that can be piled, for example S2 and Landsats)."
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.sensor_type",
"url":13,
"doc":"Sensor type, SAR or optical."
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.product_type",
"url":13,
"doc":"Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.band_names",
"url":13,
"doc":"Band mapping between band wrapping names such as  GREEN and band real number such as  03 for Sentinel-2."
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.is_reference",
"url":13,
"doc":"If the product is a reference, used for algorithms that need pre and post data, such as fire detection."
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.corresponding_ref",
"url":13,
"doc":"The corresponding reference products to the current one (if the product is not a reference but has a reference data corresponding to it). A list because of multiple ref in case of non-stackable products (S3, S1 .)"
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.nodata",
"url":13,
"doc":"Product nodata, set to 0 by default. Please do not touch this or all index will fail."
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.platform",
"url":13,
"doc":"Product platform, such as Sentinel-2"
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.resolution",
"url":13,
"doc":"Default resolution in meters of the current product. For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles."
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.condensed_name",
"url":13,
"doc":"Condensed name, the filename with only useful data to keep the name unique (ie.  20191215T110441_S2_30TXP_L2A_122756 ). Used to shorten names and paths."
},
{
"ref":"eoreader.products.optical.l2_product.L2Product.sat_id",
"url":13,
"doc":"Satellite ID, i.e.  S2 for Sentinel-2"
},
{
"ref":"eoreader.products.optical.l3_product",
"url":15,
"doc":"Landsat-3 products"
},
{
"ref":"eoreader.products.optical.l3_product.L3Product",
"url":15,
"doc":"Class of Landsat-3 Products"
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.footprint",
"url":11,
"doc":"Get real footprint of the products (without nodata, in french  emprise utile)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>> prod.footprint() index geometry 0 0 POLYGON  366165.000 4899735.000, 366165.000 4 .   Overload of the generic function because landsat nodata seems to be different in QA than in regular bands. Indeed, nodata pixels vary according to the band sensor footprint, whereas QA nodata is where at least one band has nodata. We chose to keep QA nodata values for the footprint in order to show where all bands are valid.  TL;DR: We use the QA nodata value to determine the product's footprint . Returns: gpd.GeoDataFrame: Footprint as a GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.get_datetime",
"url":11,
"doc":"Get the product's acquisition datetime, with format  YYYYMMDDTHHMMSS   %Y%m%dT%H%M%S   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>> prod.get_datetime(as_datetime=True) datetime.datetime(2020, 5, 18, 16, 34, 7) >>> prod.get_datetime(as_datetime=False) '20200518T163407'   Args: as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string. Returns: Union[str, datetime.datetime]: Its acquisition datetime",
"func":1
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.get_band_paths",
"url":11,
"doc":"Return the paths of required bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_band_paths([GREEN, RED]) {  : 'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B3.TIF',  : 'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B4.TIF' }   Args: band_list (list): List of the wanted bands resolution (float): Useless here Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.read_mtd",
"url":11,
"doc":"Read Landsat metadata as: - a  pandas.DataFrame whatever its collection is (by default for collection 1) - a XML root + its namespace if the product is retrieved from the 2nd collection (by default for collection 2)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>>  COLLECTION 1 : Open metadata as panda DataFrame >>> prod.read_mtd() NAME ORIGIN  . RESAMPLING_OPTION value \"Image courtesy of the U.S. Geological Survey\"  . \"CUBIC_CONVOLUTION\" [1 rows x 197 columns] >>>  COLLECTION 2 : Open metadata as XML >>> path = r\"LC08_L1TP_200030_20201220_20210310_02_T1\"  Collection 2 >>> prod = Reader().open(path) >>> prod.read_mtd() ( ,  ) >>>  COLLECTION 2 : Force to pandas.DataFrame >>> prod.read_mtd(force_pd=True) NAME ORIGIN  . RESAMPLING_OPTION value \"Image courtesy of the U.S. Geological Survey\"  . \"CUBIC_CONVOLUTION\" [1 rows x 263 columns]   Args: force_pd (bool): If collection 2, return a pandas.DataFrame instead of a XML root + namespace Returns: pd.DataFrame: Metadata as a Pandas DataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.get_mean_sun_angles",
"url":11,
"doc":"Get Mean Sun angles (Azimuth and Zenith angles)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_mean_sun_angles() (140.80752656, 61.93065805)   Returns: (float, float): Mean Azimuth and Zenith angle",
"func":1
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.get_default_band",
"url":12,
"doc":"Get default band:  GREEN for optical data as every optical satellite has a GREEN band.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band()    Returns: str: Default band",
"func":1
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.get_default_band_path",
"url":12,
"doc":"Get default band ( GREEN for optical data) path.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band_path() 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2'   Returns: str: Default band path",
"func":1
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.crs",
"url":12,
"doc":"Get UTM projection of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_crs() CRS.from_epsg(32630)   Returns: rasterio.crs.CRS: CRS object",
"func":1
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.extent",
"url":12,
"doc":"Get UTM extent of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_extent() geometry 0 POLYGON  309780.000 4390200.000, 309780.000 4 .   Returns: gpd.GeoDataFrame: Footprint in UTM",
"func":1
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.get_existing_bands",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_bands() [ ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ]   Returns: list: List of existing bands in the products",
"func":1
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.get_existing_band_paths",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_band_paths() {  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B01.jp2',  .,  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B12.jp2' }   Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.get_date",
"url":13,
"doc":"Get the product's acquisition date.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_date(as_date=True) datetime.datetime(2020, 8, 24, 0, 0) >>> prod.get_date(as_date=False) '20200824'   Args: as_date (bool): Return the date as a datetime.date. If false, returns a string. Returns: str: Its acquisition date",
"func":1
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.load",
"url":13,
"doc":"Open the bands and compute the wanted index. The bands will be purged of nodata and invalid pixels, the nodata will be set to 0 and the bands will be masked arrays in float. Bands that come out this function at the same time are collocated and therefore have the same shapes. This can be broken if you load data separately. Its is best to always load DEM data with some real bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> bands = prod.load([GREEN, NDVI], resolution=20) >>> bands  ' {  :  array( [0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0,  :  array( [0.0615 , 0.061625, 0.061 ,  ., 0.12085 , 0.120225, 0.113575], [0.061075, 0.06045 , 0.06025 ,  ., 0.114625, 0.119625, 0.117625], [0.06475 , 0.06145 , 0.060925,  ., 0.111475, 0.114925, 0.115175],  ., [0.1516 , 0.14195 , 0.1391 ,  ., 0.159975, 0.14145 , 0.127075], [0.140325, 0.125975, 0.131875,  ., 0.18245 , 0.1565 , 0.13015 ], [0.133475, 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675, 0.16405  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0 }  '   Args: bands (Union[list, BandNames, Callable]): Band list resolution (float): Resolution of the band, in meters size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided. Returns: dict: {band_name, band xarray}",
"func":1
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.has_band",
"url":13,
"doc":"Does this products has the specified band ? By band, we mean: - satellite band - index - DEM band - cloud band   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.has_band(GREEN) True >>> prod.has_band(TIR_2) False >>> prod.has_band(NDVI) True >>> prod.has_band(SHADOWS) False >>> prod.has_band(HILLSHADE) True   Args: band (Union[obn, sbn]): Optical or SAR band Returns: bool: True if the products has the specified band",
"func":1
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.output",
"url":13,
"doc":"Output directory of the product, to write orthorectified data for example."
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.stack",
"url":13,
"doc":"Stack bands and index of a products.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> stack = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  In meters >>> stack  '  array( [ 0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [ 0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [ 2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [ 1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [ 1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [ 1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ,  0.27066118, 0.23466069, 0.18792598,  ., -0.4611526 , -0.49751845, -0.4865216 ], [ 0.22425456, 0.28004232, 0.27851456,  ., -0.5032771 , -0.501796 , -0.502669 ], [-0.07466951, 0.06360884, 0.1207174 ,  ., -0.50617427, -0.50219285, -0.5034222 ], [-0.47076276, -0.4705828 , -0.4747971 ,  ., -0.32138503, -0.36619243, -0.37428448], [-0.4826967 , -0.5032287 , -0.48544118,  ., -0.278925 , -0.31404778, -0.36052078], [-0.488381 , -0.48253912, -0.4697526 ,  ., -0.38105175, -0.30813277, -0.27739233 ,  0.0615 , 0.061625 , 0.061 ,  ., 0.12085 , 0.120225 , 0.113575 ], [ 0.061075 , 0.06045 , 0.06025 ,  ., 0.114625 , 0.119625 , 0.117625 ], [ 0.06475 , 0.06145 , 0.060925 ,  ., 0.111475 , 0.114925 , 0.115175 ],  ., [ 0.1516 , 0.14195 , 0.1391 ,  ., 0.159975 , 0.14145 , 0.127075 ], [ 0.140325 , 0.125975 , 0.131875 ,  ., 0.18245 , 0.1565 , 0.13015 ], [ 0.133475 , 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675 , 0.16405  ], dtype=float32) Coordinates:  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0  z (z) MultiIndex - variable (z) object 'NDVI' 'MNDWI' 'GREEN' - band (z) int64 1 1 1 Attributes: long_name: ['NDVI', 'MNDWI', 'GREEN']  '   Args: bands (list): Bands and index combination resolution (float): Stack resolution. . If not specified, use the product resolution. stack_path (str): Stack path save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000) Returns: xr.DataArray: Stack as a DataArray",
"func":1
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.name",
"url":13,
"doc":"Product name (its filename without any extension)."
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.split_name",
"url":13,
"doc":"Split name, to retrieve every information from its filename (dates, tile, product type .)."
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.archive_path",
"url":13,
"doc":"Archive path, same as the product path if not specified. Useful when you want to know where both the extracted and archived version of your product are stored."
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.path",
"url":13,
"doc":"Usable path to the product, either extracted or archived path, according to the satellite."
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.is_archived",
"url":13,
"doc":"Is the archived product is processed (a products is considered as archived if its products path is a directory)."
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.needs_extraction",
"url":13,
"doc":"Does this products needs to be extracted to be processed ? ( True by default)."
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.date",
"url":13,
"doc":"Acquisition date."
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.datetime",
"url":13,
"doc":"Acquisition datetime."
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.tile_name",
"url":13,
"doc":"Tile if possible (for data that can be piled, for example S2 and Landsats)."
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.sensor_type",
"url":13,
"doc":"Sensor type, SAR or optical."
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.product_type",
"url":13,
"doc":"Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.band_names",
"url":13,
"doc":"Band mapping between band wrapping names such as  GREEN and band real number such as  03 for Sentinel-2."
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.is_reference",
"url":13,
"doc":"If the product is a reference, used for algorithms that need pre and post data, such as fire detection."
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.corresponding_ref",
"url":13,
"doc":"The corresponding reference products to the current one (if the product is not a reference but has a reference data corresponding to it). A list because of multiple ref in case of non-stackable products (S3, S1 .)"
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.nodata",
"url":13,
"doc":"Product nodata, set to 0 by default. Please do not touch this or all index will fail."
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.platform",
"url":13,
"doc":"Product platform, such as Sentinel-2"
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.resolution",
"url":13,
"doc":"Default resolution in meters of the current product. For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles."
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.condensed_name",
"url":13,
"doc":"Condensed name, the filename with only useful data to keep the name unique (ie.  20191215T110441_S2_30TXP_L2A_122756 ). Used to shorten names and paths."
},
{
"ref":"eoreader.products.optical.l3_product.L3Product.sat_id",
"url":13,
"doc":"Satellite ID, i.e.  S2 for Sentinel-2"
},
{
"ref":"eoreader.products.optical.l4_product",
"url":16,
"doc":"Landsat-4 products"
},
{
"ref":"eoreader.products.optical.l4_product.L4Product",
"url":16,
"doc":"Class of Landsat-4 Products"
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.footprint",
"url":11,
"doc":"Get real footprint of the products (without nodata, in french  emprise utile)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>> prod.footprint() index geometry 0 0 POLYGON  366165.000 4899735.000, 366165.000 4 .   Overload of the generic function because landsat nodata seems to be different in QA than in regular bands. Indeed, nodata pixels vary according to the band sensor footprint, whereas QA nodata is where at least one band has nodata. We chose to keep QA nodata values for the footprint in order to show where all bands are valid.  TL;DR: We use the QA nodata value to determine the product's footprint . Returns: gpd.GeoDataFrame: Footprint as a GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.get_datetime",
"url":11,
"doc":"Get the product's acquisition datetime, with format  YYYYMMDDTHHMMSS   %Y%m%dT%H%M%S   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>> prod.get_datetime(as_datetime=True) datetime.datetime(2020, 5, 18, 16, 34, 7) >>> prod.get_datetime(as_datetime=False) '20200518T163407'   Args: as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string. Returns: Union[str, datetime.datetime]: Its acquisition datetime",
"func":1
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.get_band_paths",
"url":11,
"doc":"Return the paths of required bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_band_paths([GREEN, RED]) {  : 'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B3.TIF',  : 'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B4.TIF' }   Args: band_list (list): List of the wanted bands resolution (float): Useless here Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.read_mtd",
"url":11,
"doc":"Read Landsat metadata as: - a  pandas.DataFrame whatever its collection is (by default for collection 1) - a XML root + its namespace if the product is retrieved from the 2nd collection (by default for collection 2)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>>  COLLECTION 1 : Open metadata as panda DataFrame >>> prod.read_mtd() NAME ORIGIN  . RESAMPLING_OPTION value \"Image courtesy of the U.S. Geological Survey\"  . \"CUBIC_CONVOLUTION\" [1 rows x 197 columns] >>>  COLLECTION 2 : Open metadata as XML >>> path = r\"LC08_L1TP_200030_20201220_20210310_02_T1\"  Collection 2 >>> prod = Reader().open(path) >>> prod.read_mtd() ( ,  ) >>>  COLLECTION 2 : Force to pandas.DataFrame >>> prod.read_mtd(force_pd=True) NAME ORIGIN  . RESAMPLING_OPTION value \"Image courtesy of the U.S. Geological Survey\"  . \"CUBIC_CONVOLUTION\" [1 rows x 263 columns]   Args: force_pd (bool): If collection 2, return a pandas.DataFrame instead of a XML root + namespace Returns: pd.DataFrame: Metadata as a Pandas DataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.get_mean_sun_angles",
"url":11,
"doc":"Get Mean Sun angles (Azimuth and Zenith angles)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_mean_sun_angles() (140.80752656, 61.93065805)   Returns: (float, float): Mean Azimuth and Zenith angle",
"func":1
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.get_default_band",
"url":12,
"doc":"Get default band:  GREEN for optical data as every optical satellite has a GREEN band.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band()    Returns: str: Default band",
"func":1
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.get_default_band_path",
"url":12,
"doc":"Get default band ( GREEN for optical data) path.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band_path() 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2'   Returns: str: Default band path",
"func":1
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.crs",
"url":12,
"doc":"Get UTM projection of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_crs() CRS.from_epsg(32630)   Returns: rasterio.crs.CRS: CRS object",
"func":1
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.extent",
"url":12,
"doc":"Get UTM extent of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_extent() geometry 0 POLYGON  309780.000 4390200.000, 309780.000 4 .   Returns: gpd.GeoDataFrame: Footprint in UTM",
"func":1
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.get_existing_bands",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_bands() [ ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ]   Returns: list: List of existing bands in the products",
"func":1
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.get_existing_band_paths",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_band_paths() {  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B01.jp2',  .,  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B12.jp2' }   Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.get_date",
"url":13,
"doc":"Get the product's acquisition date.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_date(as_date=True) datetime.datetime(2020, 8, 24, 0, 0) >>> prod.get_date(as_date=False) '20200824'   Args: as_date (bool): Return the date as a datetime.date. If false, returns a string. Returns: str: Its acquisition date",
"func":1
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.load",
"url":13,
"doc":"Open the bands and compute the wanted index. The bands will be purged of nodata and invalid pixels, the nodata will be set to 0 and the bands will be masked arrays in float. Bands that come out this function at the same time are collocated and therefore have the same shapes. This can be broken if you load data separately. Its is best to always load DEM data with some real bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> bands = prod.load([GREEN, NDVI], resolution=20) >>> bands  ' {  :  array( [0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0,  :  array( [0.0615 , 0.061625, 0.061 ,  ., 0.12085 , 0.120225, 0.113575], [0.061075, 0.06045 , 0.06025 ,  ., 0.114625, 0.119625, 0.117625], [0.06475 , 0.06145 , 0.060925,  ., 0.111475, 0.114925, 0.115175],  ., [0.1516 , 0.14195 , 0.1391 ,  ., 0.159975, 0.14145 , 0.127075], [0.140325, 0.125975, 0.131875,  ., 0.18245 , 0.1565 , 0.13015 ], [0.133475, 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675, 0.16405  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0 }  '   Args: bands (Union[list, BandNames, Callable]): Band list resolution (float): Resolution of the band, in meters size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided. Returns: dict: {band_name, band xarray}",
"func":1
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.has_band",
"url":13,
"doc":"Does this products has the specified band ? By band, we mean: - satellite band - index - DEM band - cloud band   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.has_band(GREEN) True >>> prod.has_band(TIR_2) False >>> prod.has_band(NDVI) True >>> prod.has_band(SHADOWS) False >>> prod.has_band(HILLSHADE) True   Args: band (Union[obn, sbn]): Optical or SAR band Returns: bool: True if the products has the specified band",
"func":1
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.output",
"url":13,
"doc":"Output directory of the product, to write orthorectified data for example."
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.stack",
"url":13,
"doc":"Stack bands and index of a products.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> stack = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  In meters >>> stack  '  array( [ 0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [ 0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [ 2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [ 1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [ 1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [ 1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ,  0.27066118, 0.23466069, 0.18792598,  ., -0.4611526 , -0.49751845, -0.4865216 ], [ 0.22425456, 0.28004232, 0.27851456,  ., -0.5032771 , -0.501796 , -0.502669 ], [-0.07466951, 0.06360884, 0.1207174 ,  ., -0.50617427, -0.50219285, -0.5034222 ], [-0.47076276, -0.4705828 , -0.4747971 ,  ., -0.32138503, -0.36619243, -0.37428448], [-0.4826967 , -0.5032287 , -0.48544118,  ., -0.278925 , -0.31404778, -0.36052078], [-0.488381 , -0.48253912, -0.4697526 ,  ., -0.38105175, -0.30813277, -0.27739233 ,  0.0615 , 0.061625 , 0.061 ,  ., 0.12085 , 0.120225 , 0.113575 ], [ 0.061075 , 0.06045 , 0.06025 ,  ., 0.114625 , 0.119625 , 0.117625 ], [ 0.06475 , 0.06145 , 0.060925 ,  ., 0.111475 , 0.114925 , 0.115175 ],  ., [ 0.1516 , 0.14195 , 0.1391 ,  ., 0.159975 , 0.14145 , 0.127075 ], [ 0.140325 , 0.125975 , 0.131875 ,  ., 0.18245 , 0.1565 , 0.13015 ], [ 0.133475 , 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675 , 0.16405  ], dtype=float32) Coordinates:  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0  z (z) MultiIndex - variable (z) object 'NDVI' 'MNDWI' 'GREEN' - band (z) int64 1 1 1 Attributes: long_name: ['NDVI', 'MNDWI', 'GREEN']  '   Args: bands (list): Bands and index combination resolution (float): Stack resolution. . If not specified, use the product resolution. stack_path (str): Stack path save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000) Returns: xr.DataArray: Stack as a DataArray",
"func":1
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.name",
"url":13,
"doc":"Product name (its filename without any extension)."
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.split_name",
"url":13,
"doc":"Split name, to retrieve every information from its filename (dates, tile, product type .)."
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.archive_path",
"url":13,
"doc":"Archive path, same as the product path if not specified. Useful when you want to know where both the extracted and archived version of your product are stored."
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.path",
"url":13,
"doc":"Usable path to the product, either extracted or archived path, according to the satellite."
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.is_archived",
"url":13,
"doc":"Is the archived product is processed (a products is considered as archived if its products path is a directory)."
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.needs_extraction",
"url":13,
"doc":"Does this products needs to be extracted to be processed ? ( True by default)."
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.date",
"url":13,
"doc":"Acquisition date."
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.datetime",
"url":13,
"doc":"Acquisition datetime."
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.tile_name",
"url":13,
"doc":"Tile if possible (for data that can be piled, for example S2 and Landsats)."
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.sensor_type",
"url":13,
"doc":"Sensor type, SAR or optical."
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.product_type",
"url":13,
"doc":"Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.band_names",
"url":13,
"doc":"Band mapping between band wrapping names such as  GREEN and band real number such as  03 for Sentinel-2."
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.is_reference",
"url":13,
"doc":"If the product is a reference, used for algorithms that need pre and post data, such as fire detection."
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.corresponding_ref",
"url":13,
"doc":"The corresponding reference products to the current one (if the product is not a reference but has a reference data corresponding to it). A list because of multiple ref in case of non-stackable products (S3, S1 .)"
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.nodata",
"url":13,
"doc":"Product nodata, set to 0 by default. Please do not touch this or all index will fail."
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.platform",
"url":13,
"doc":"Product platform, such as Sentinel-2"
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.resolution",
"url":13,
"doc":"Default resolution in meters of the current product. For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles."
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.condensed_name",
"url":13,
"doc":"Condensed name, the filename with only useful data to keep the name unique (ie.  20191215T110441_S2_30TXP_L2A_122756 ). Used to shorten names and paths."
},
{
"ref":"eoreader.products.optical.l4_product.L4Product.sat_id",
"url":13,
"doc":"Satellite ID, i.e.  S2 for Sentinel-2"
},
{
"ref":"eoreader.products.optical.l5_product",
"url":17,
"doc":"Landsat-5 products"
},
{
"ref":"eoreader.products.optical.l5_product.L5Product",
"url":17,
"doc":"Class of Landsat-5 Products"
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.footprint",
"url":11,
"doc":"Get real footprint of the products (without nodata, in french  emprise utile)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>> prod.footprint() index geometry 0 0 POLYGON  366165.000 4899735.000, 366165.000 4 .   Overload of the generic function because landsat nodata seems to be different in QA than in regular bands. Indeed, nodata pixels vary according to the band sensor footprint, whereas QA nodata is where at least one band has nodata. We chose to keep QA nodata values for the footprint in order to show where all bands are valid.  TL;DR: We use the QA nodata value to determine the product's footprint . Returns: gpd.GeoDataFrame: Footprint as a GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.get_datetime",
"url":11,
"doc":"Get the product's acquisition datetime, with format  YYYYMMDDTHHMMSS   %Y%m%dT%H%M%S   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>> prod.get_datetime(as_datetime=True) datetime.datetime(2020, 5, 18, 16, 34, 7) >>> prod.get_datetime(as_datetime=False) '20200518T163407'   Args: as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string. Returns: Union[str, datetime.datetime]: Its acquisition datetime",
"func":1
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.get_band_paths",
"url":11,
"doc":"Return the paths of required bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_band_paths([GREEN, RED]) {  : 'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B3.TIF',  : 'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B4.TIF' }   Args: band_list (list): List of the wanted bands resolution (float): Useless here Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.read_mtd",
"url":11,
"doc":"Read Landsat metadata as: - a  pandas.DataFrame whatever its collection is (by default for collection 1) - a XML root + its namespace if the product is retrieved from the 2nd collection (by default for collection 2)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>>  COLLECTION 1 : Open metadata as panda DataFrame >>> prod.read_mtd() NAME ORIGIN  . RESAMPLING_OPTION value \"Image courtesy of the U.S. Geological Survey\"  . \"CUBIC_CONVOLUTION\" [1 rows x 197 columns] >>>  COLLECTION 2 : Open metadata as XML >>> path = r\"LC08_L1TP_200030_20201220_20210310_02_T1\"  Collection 2 >>> prod = Reader().open(path) >>> prod.read_mtd() ( ,  ) >>>  COLLECTION 2 : Force to pandas.DataFrame >>> prod.read_mtd(force_pd=True) NAME ORIGIN  . RESAMPLING_OPTION value \"Image courtesy of the U.S. Geological Survey\"  . \"CUBIC_CONVOLUTION\" [1 rows x 263 columns]   Args: force_pd (bool): If collection 2, return a pandas.DataFrame instead of a XML root + namespace Returns: pd.DataFrame: Metadata as a Pandas DataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.get_mean_sun_angles",
"url":11,
"doc":"Get Mean Sun angles (Azimuth and Zenith angles)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_mean_sun_angles() (140.80752656, 61.93065805)   Returns: (float, float): Mean Azimuth and Zenith angle",
"func":1
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.get_default_band",
"url":12,
"doc":"Get default band:  GREEN for optical data as every optical satellite has a GREEN band.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band()    Returns: str: Default band",
"func":1
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.get_default_band_path",
"url":12,
"doc":"Get default band ( GREEN for optical data) path.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band_path() 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2'   Returns: str: Default band path",
"func":1
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.crs",
"url":12,
"doc":"Get UTM projection of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_crs() CRS.from_epsg(32630)   Returns: rasterio.crs.CRS: CRS object",
"func":1
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.extent",
"url":12,
"doc":"Get UTM extent of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_extent() geometry 0 POLYGON  309780.000 4390200.000, 309780.000 4 .   Returns: gpd.GeoDataFrame: Footprint in UTM",
"func":1
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.get_existing_bands",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_bands() [ ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ]   Returns: list: List of existing bands in the products",
"func":1
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.get_existing_band_paths",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_band_paths() {  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B01.jp2',  .,  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B12.jp2' }   Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.get_date",
"url":13,
"doc":"Get the product's acquisition date.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_date(as_date=True) datetime.datetime(2020, 8, 24, 0, 0) >>> prod.get_date(as_date=False) '20200824'   Args: as_date (bool): Return the date as a datetime.date. If false, returns a string. Returns: str: Its acquisition date",
"func":1
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.load",
"url":13,
"doc":"Open the bands and compute the wanted index. The bands will be purged of nodata and invalid pixels, the nodata will be set to 0 and the bands will be masked arrays in float. Bands that come out this function at the same time are collocated and therefore have the same shapes. This can be broken if you load data separately. Its is best to always load DEM data with some real bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> bands = prod.load([GREEN, NDVI], resolution=20) >>> bands  ' {  :  array( [0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0,  :  array( [0.0615 , 0.061625, 0.061 ,  ., 0.12085 , 0.120225, 0.113575], [0.061075, 0.06045 , 0.06025 ,  ., 0.114625, 0.119625, 0.117625], [0.06475 , 0.06145 , 0.060925,  ., 0.111475, 0.114925, 0.115175],  ., [0.1516 , 0.14195 , 0.1391 ,  ., 0.159975, 0.14145 , 0.127075], [0.140325, 0.125975, 0.131875,  ., 0.18245 , 0.1565 , 0.13015 ], [0.133475, 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675, 0.16405  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0 }  '   Args: bands (Union[list, BandNames, Callable]): Band list resolution (float): Resolution of the band, in meters size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided. Returns: dict: {band_name, band xarray}",
"func":1
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.has_band",
"url":13,
"doc":"Does this products has the specified band ? By band, we mean: - satellite band - index - DEM band - cloud band   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.has_band(GREEN) True >>> prod.has_band(TIR_2) False >>> prod.has_band(NDVI) True >>> prod.has_band(SHADOWS) False >>> prod.has_band(HILLSHADE) True   Args: band (Union[obn, sbn]): Optical or SAR band Returns: bool: True if the products has the specified band",
"func":1
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.output",
"url":13,
"doc":"Output directory of the product, to write orthorectified data for example."
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.stack",
"url":13,
"doc":"Stack bands and index of a products.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> stack = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  In meters >>> stack  '  array( [ 0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [ 0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [ 2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [ 1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [ 1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [ 1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ,  0.27066118, 0.23466069, 0.18792598,  ., -0.4611526 , -0.49751845, -0.4865216 ], [ 0.22425456, 0.28004232, 0.27851456,  ., -0.5032771 , -0.501796 , -0.502669 ], [-0.07466951, 0.06360884, 0.1207174 ,  ., -0.50617427, -0.50219285, -0.5034222 ], [-0.47076276, -0.4705828 , -0.4747971 ,  ., -0.32138503, -0.36619243, -0.37428448], [-0.4826967 , -0.5032287 , -0.48544118,  ., -0.278925 , -0.31404778, -0.36052078], [-0.488381 , -0.48253912, -0.4697526 ,  ., -0.38105175, -0.30813277, -0.27739233 ,  0.0615 , 0.061625 , 0.061 ,  ., 0.12085 , 0.120225 , 0.113575 ], [ 0.061075 , 0.06045 , 0.06025 ,  ., 0.114625 , 0.119625 , 0.117625 ], [ 0.06475 , 0.06145 , 0.060925 ,  ., 0.111475 , 0.114925 , 0.115175 ],  ., [ 0.1516 , 0.14195 , 0.1391 ,  ., 0.159975 , 0.14145 , 0.127075 ], [ 0.140325 , 0.125975 , 0.131875 ,  ., 0.18245 , 0.1565 , 0.13015 ], [ 0.133475 , 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675 , 0.16405  ], dtype=float32) Coordinates:  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0  z (z) MultiIndex - variable (z) object 'NDVI' 'MNDWI' 'GREEN' - band (z) int64 1 1 1 Attributes: long_name: ['NDVI', 'MNDWI', 'GREEN']  '   Args: bands (list): Bands and index combination resolution (float): Stack resolution. . If not specified, use the product resolution. stack_path (str): Stack path save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000) Returns: xr.DataArray: Stack as a DataArray",
"func":1
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.name",
"url":13,
"doc":"Product name (its filename without any extension)."
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.split_name",
"url":13,
"doc":"Split name, to retrieve every information from its filename (dates, tile, product type .)."
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.archive_path",
"url":13,
"doc":"Archive path, same as the product path if not specified. Useful when you want to know where both the extracted and archived version of your product are stored."
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.path",
"url":13,
"doc":"Usable path to the product, either extracted or archived path, according to the satellite."
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.is_archived",
"url":13,
"doc":"Is the archived product is processed (a products is considered as archived if its products path is a directory)."
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.needs_extraction",
"url":13,
"doc":"Does this products needs to be extracted to be processed ? ( True by default)."
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.date",
"url":13,
"doc":"Acquisition date."
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.datetime",
"url":13,
"doc":"Acquisition datetime."
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.tile_name",
"url":13,
"doc":"Tile if possible (for data that can be piled, for example S2 and Landsats)."
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.sensor_type",
"url":13,
"doc":"Sensor type, SAR or optical."
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.product_type",
"url":13,
"doc":"Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.band_names",
"url":13,
"doc":"Band mapping between band wrapping names such as  GREEN and band real number such as  03 for Sentinel-2."
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.is_reference",
"url":13,
"doc":"If the product is a reference, used for algorithms that need pre and post data, such as fire detection."
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.corresponding_ref",
"url":13,
"doc":"The corresponding reference products to the current one (if the product is not a reference but has a reference data corresponding to it). A list because of multiple ref in case of non-stackable products (S3, S1 .)"
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.nodata",
"url":13,
"doc":"Product nodata, set to 0 by default. Please do not touch this or all index will fail."
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.platform",
"url":13,
"doc":"Product platform, such as Sentinel-2"
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.resolution",
"url":13,
"doc":"Default resolution in meters of the current product. For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles."
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.condensed_name",
"url":13,
"doc":"Condensed name, the filename with only useful data to keep the name unique (ie.  20191215T110441_S2_30TXP_L2A_122756 ). Used to shorten names and paths."
},
{
"ref":"eoreader.products.optical.l5_product.L5Product.sat_id",
"url":13,
"doc":"Satellite ID, i.e.  S2 for Sentinel-2"
},
{
"ref":"eoreader.products.optical.l7_product",
"url":18,
"doc":"Landsat-7 products"
},
{
"ref":"eoreader.products.optical.l7_product.L7Product",
"url":18,
"doc":"Class of Landsat-7 Products"
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.footprint",
"url":11,
"doc":"Get real footprint of the products (without nodata, in french  emprise utile)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>> prod.footprint() index geometry 0 0 POLYGON  366165.000 4899735.000, 366165.000 4 .   Overload of the generic function because landsat nodata seems to be different in QA than in regular bands. Indeed, nodata pixels vary according to the band sensor footprint, whereas QA nodata is where at least one band has nodata. We chose to keep QA nodata values for the footprint in order to show where all bands are valid.  TL;DR: We use the QA nodata value to determine the product's footprint . Returns: gpd.GeoDataFrame: Footprint as a GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.get_datetime",
"url":11,
"doc":"Get the product's acquisition datetime, with format  YYYYMMDDTHHMMSS   %Y%m%dT%H%M%S   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>> prod.get_datetime(as_datetime=True) datetime.datetime(2020, 5, 18, 16, 34, 7) >>> prod.get_datetime(as_datetime=False) '20200518T163407'   Args: as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string. Returns: Union[str, datetime.datetime]: Its acquisition datetime",
"func":1
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.get_band_paths",
"url":11,
"doc":"Return the paths of required bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_band_paths([GREEN, RED]) {  : 'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B3.TIF',  : 'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B4.TIF' }   Args: band_list (list): List of the wanted bands resolution (float): Useless here Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.read_mtd",
"url":11,
"doc":"Read Landsat metadata as: - a  pandas.DataFrame whatever its collection is (by default for collection 1) - a XML root + its namespace if the product is retrieved from the 2nd collection (by default for collection 2)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>>  COLLECTION 1 : Open metadata as panda DataFrame >>> prod.read_mtd() NAME ORIGIN  . RESAMPLING_OPTION value \"Image courtesy of the U.S. Geological Survey\"  . \"CUBIC_CONVOLUTION\" [1 rows x 197 columns] >>>  COLLECTION 2 : Open metadata as XML >>> path = r\"LC08_L1TP_200030_20201220_20210310_02_T1\"  Collection 2 >>> prod = Reader().open(path) >>> prod.read_mtd() ( ,  ) >>>  COLLECTION 2 : Force to pandas.DataFrame >>> prod.read_mtd(force_pd=True) NAME ORIGIN  . RESAMPLING_OPTION value \"Image courtesy of the U.S. Geological Survey\"  . \"CUBIC_CONVOLUTION\" [1 rows x 263 columns]   Args: force_pd (bool): If collection 2, return a pandas.DataFrame instead of a XML root + namespace Returns: pd.DataFrame: Metadata as a Pandas DataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.get_mean_sun_angles",
"url":11,
"doc":"Get Mean Sun angles (Azimuth and Zenith angles)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_mean_sun_angles() (140.80752656, 61.93065805)   Returns: (float, float): Mean Azimuth and Zenith angle",
"func":1
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.get_default_band",
"url":12,
"doc":"Get default band:  GREEN for optical data as every optical satellite has a GREEN band.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band()    Returns: str: Default band",
"func":1
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.get_default_band_path",
"url":12,
"doc":"Get default band ( GREEN for optical data) path.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band_path() 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2'   Returns: str: Default band path",
"func":1
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.crs",
"url":12,
"doc":"Get UTM projection of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_crs() CRS.from_epsg(32630)   Returns: rasterio.crs.CRS: CRS object",
"func":1
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.extent",
"url":12,
"doc":"Get UTM extent of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_extent() geometry 0 POLYGON  309780.000 4390200.000, 309780.000 4 .   Returns: gpd.GeoDataFrame: Footprint in UTM",
"func":1
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.get_existing_bands",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_bands() [ ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ]   Returns: list: List of existing bands in the products",
"func":1
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.get_existing_band_paths",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_band_paths() {  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B01.jp2',  .,  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B12.jp2' }   Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.get_date",
"url":13,
"doc":"Get the product's acquisition date.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_date(as_date=True) datetime.datetime(2020, 8, 24, 0, 0) >>> prod.get_date(as_date=False) '20200824'   Args: as_date (bool): Return the date as a datetime.date. If false, returns a string. Returns: str: Its acquisition date",
"func":1
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.load",
"url":13,
"doc":"Open the bands and compute the wanted index. The bands will be purged of nodata and invalid pixels, the nodata will be set to 0 and the bands will be masked arrays in float. Bands that come out this function at the same time are collocated and therefore have the same shapes. This can be broken if you load data separately. Its is best to always load DEM data with some real bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> bands = prod.load([GREEN, NDVI], resolution=20) >>> bands  ' {  :  array( [0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0,  :  array( [0.0615 , 0.061625, 0.061 ,  ., 0.12085 , 0.120225, 0.113575], [0.061075, 0.06045 , 0.06025 ,  ., 0.114625, 0.119625, 0.117625], [0.06475 , 0.06145 , 0.060925,  ., 0.111475, 0.114925, 0.115175],  ., [0.1516 , 0.14195 , 0.1391 ,  ., 0.159975, 0.14145 , 0.127075], [0.140325, 0.125975, 0.131875,  ., 0.18245 , 0.1565 , 0.13015 ], [0.133475, 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675, 0.16405  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0 }  '   Args: bands (Union[list, BandNames, Callable]): Band list resolution (float): Resolution of the band, in meters size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided. Returns: dict: {band_name, band xarray}",
"func":1
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.has_band",
"url":13,
"doc":"Does this products has the specified band ? By band, we mean: - satellite band - index - DEM band - cloud band   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.has_band(GREEN) True >>> prod.has_band(TIR_2) False >>> prod.has_band(NDVI) True >>> prod.has_band(SHADOWS) False >>> prod.has_band(HILLSHADE) True   Args: band (Union[obn, sbn]): Optical or SAR band Returns: bool: True if the products has the specified band",
"func":1
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.output",
"url":13,
"doc":"Output directory of the product, to write orthorectified data for example."
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.stack",
"url":13,
"doc":"Stack bands and index of a products.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> stack = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  In meters >>> stack  '  array( [ 0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [ 0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [ 2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [ 1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [ 1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [ 1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ,  0.27066118, 0.23466069, 0.18792598,  ., -0.4611526 , -0.49751845, -0.4865216 ], [ 0.22425456, 0.28004232, 0.27851456,  ., -0.5032771 , -0.501796 , -0.502669 ], [-0.07466951, 0.06360884, 0.1207174 ,  ., -0.50617427, -0.50219285, -0.5034222 ], [-0.47076276, -0.4705828 , -0.4747971 ,  ., -0.32138503, -0.36619243, -0.37428448], [-0.4826967 , -0.5032287 , -0.48544118,  ., -0.278925 , -0.31404778, -0.36052078], [-0.488381 , -0.48253912, -0.4697526 ,  ., -0.38105175, -0.30813277, -0.27739233 ,  0.0615 , 0.061625 , 0.061 ,  ., 0.12085 , 0.120225 , 0.113575 ], [ 0.061075 , 0.06045 , 0.06025 ,  ., 0.114625 , 0.119625 , 0.117625 ], [ 0.06475 , 0.06145 , 0.060925 ,  ., 0.111475 , 0.114925 , 0.115175 ],  ., [ 0.1516 , 0.14195 , 0.1391 ,  ., 0.159975 , 0.14145 , 0.127075 ], [ 0.140325 , 0.125975 , 0.131875 ,  ., 0.18245 , 0.1565 , 0.13015 ], [ 0.133475 , 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675 , 0.16405  ], dtype=float32) Coordinates:  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0  z (z) MultiIndex - variable (z) object 'NDVI' 'MNDWI' 'GREEN' - band (z) int64 1 1 1 Attributes: long_name: ['NDVI', 'MNDWI', 'GREEN']  '   Args: bands (list): Bands and index combination resolution (float): Stack resolution. . If not specified, use the product resolution. stack_path (str): Stack path save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000) Returns: xr.DataArray: Stack as a DataArray",
"func":1
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.name",
"url":13,
"doc":"Product name (its filename without any extension)."
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.split_name",
"url":13,
"doc":"Split name, to retrieve every information from its filename (dates, tile, product type .)."
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.archive_path",
"url":13,
"doc":"Archive path, same as the product path if not specified. Useful when you want to know where both the extracted and archived version of your product are stored."
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.path",
"url":13,
"doc":"Usable path to the product, either extracted or archived path, according to the satellite."
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.is_archived",
"url":13,
"doc":"Is the archived product is processed (a products is considered as archived if its products path is a directory)."
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.needs_extraction",
"url":13,
"doc":"Does this products needs to be extracted to be processed ? ( True by default)."
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.date",
"url":13,
"doc":"Acquisition date."
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.datetime",
"url":13,
"doc":"Acquisition datetime."
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.tile_name",
"url":13,
"doc":"Tile if possible (for data that can be piled, for example S2 and Landsats)."
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.sensor_type",
"url":13,
"doc":"Sensor type, SAR or optical."
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.product_type",
"url":13,
"doc":"Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.band_names",
"url":13,
"doc":"Band mapping between band wrapping names such as  GREEN and band real number such as  03 for Sentinel-2."
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.is_reference",
"url":13,
"doc":"If the product is a reference, used for algorithms that need pre and post data, such as fire detection."
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.corresponding_ref",
"url":13,
"doc":"The corresponding reference products to the current one (if the product is not a reference but has a reference data corresponding to it). A list because of multiple ref in case of non-stackable products (S3, S1 .)"
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.nodata",
"url":13,
"doc":"Product nodata, set to 0 by default. Please do not touch this or all index will fail."
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.platform",
"url":13,
"doc":"Product platform, such as Sentinel-2"
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.resolution",
"url":13,
"doc":"Default resolution in meters of the current product. For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles."
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.condensed_name",
"url":13,
"doc":"Condensed name, the filename with only useful data to keep the name unique (ie.  20191215T110441_S2_30TXP_L2A_122756 ). Used to shorten names and paths."
},
{
"ref":"eoreader.products.optical.l7_product.L7Product.sat_id",
"url":13,
"doc":"Satellite ID, i.e.  S2 for Sentinel-2"
},
{
"ref":"eoreader.products.optical.l8_product",
"url":19,
"doc":"Landsat-8 products"
},
{
"ref":"eoreader.products.optical.l8_product.L8Product",
"url":19,
"doc":"Class of Landsat-8 Products"
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.footprint",
"url":11,
"doc":"Get real footprint of the products (without nodata, in french  emprise utile)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>> prod.footprint() index geometry 0 0 POLYGON  366165.000 4899735.000, 366165.000 4 .   Overload of the generic function because landsat nodata seems to be different in QA than in regular bands. Indeed, nodata pixels vary according to the band sensor footprint, whereas QA nodata is where at least one band has nodata. We chose to keep QA nodata values for the footprint in order to show where all bands are valid.  TL;DR: We use the QA nodata value to determine the product's footprint . Returns: gpd.GeoDataFrame: Footprint as a GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.get_datetime",
"url":11,
"doc":"Get the product's acquisition datetime, with format  YYYYMMDDTHHMMSS   %Y%m%dT%H%M%S   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>> prod.get_datetime(as_datetime=True) datetime.datetime(2020, 5, 18, 16, 34, 7) >>> prod.get_datetime(as_datetime=False) '20200518T163407'   Args: as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string. Returns: Union[str, datetime.datetime]: Its acquisition datetime",
"func":1
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.get_band_paths",
"url":11,
"doc":"Return the paths of required bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_band_paths([GREEN, RED]) {  : 'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B3.TIF',  : 'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B4.TIF' }   Args: band_list (list): List of the wanted bands resolution (float): Useless here Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.read_mtd",
"url":11,
"doc":"Read Landsat metadata as: - a  pandas.DataFrame whatever its collection is (by default for collection 1) - a XML root + its namespace if the product is retrieved from the 2nd collection (by default for collection 2)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>>  COLLECTION 1 : Open metadata as panda DataFrame >>> prod.read_mtd() NAME ORIGIN  . RESAMPLING_OPTION value \"Image courtesy of the U.S. Geological Survey\"  . \"CUBIC_CONVOLUTION\" [1 rows x 197 columns] >>>  COLLECTION 2 : Open metadata as XML >>> path = r\"LC08_L1TP_200030_20201220_20210310_02_T1\"  Collection 2 >>> prod = Reader().open(path) >>> prod.read_mtd() ( ,  ) >>>  COLLECTION 2 : Force to pandas.DataFrame >>> prod.read_mtd(force_pd=True) NAME ORIGIN  . RESAMPLING_OPTION value \"Image courtesy of the U.S. Geological Survey\"  . \"CUBIC_CONVOLUTION\" [1 rows x 263 columns]   Args: force_pd (bool): If collection 2, return a pandas.DataFrame instead of a XML root + namespace Returns: pd.DataFrame: Metadata as a Pandas DataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.get_mean_sun_angles",
"url":11,
"doc":"Get Mean Sun angles (Azimuth and Zenith angles)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_mean_sun_angles() (140.80752656, 61.93065805)   Returns: (float, float): Mean Azimuth and Zenith angle",
"func":1
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.get_default_band",
"url":12,
"doc":"Get default band:  GREEN for optical data as every optical satellite has a GREEN band.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band()    Returns: str: Default band",
"func":1
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.get_default_band_path",
"url":12,
"doc":"Get default band ( GREEN for optical data) path.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band_path() 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2'   Returns: str: Default band path",
"func":1
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.crs",
"url":12,
"doc":"Get UTM projection of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_crs() CRS.from_epsg(32630)   Returns: rasterio.crs.CRS: CRS object",
"func":1
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.extent",
"url":12,
"doc":"Get UTM extent of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_extent() geometry 0 POLYGON  309780.000 4390200.000, 309780.000 4 .   Returns: gpd.GeoDataFrame: Footprint in UTM",
"func":1
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.get_existing_bands",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_bands() [ ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ]   Returns: list: List of existing bands in the products",
"func":1
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.get_existing_band_paths",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_band_paths() {  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B01.jp2',  .,  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B12.jp2' }   Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.get_date",
"url":13,
"doc":"Get the product's acquisition date.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_date(as_date=True) datetime.datetime(2020, 8, 24, 0, 0) >>> prod.get_date(as_date=False) '20200824'   Args: as_date (bool): Return the date as a datetime.date. If false, returns a string. Returns: str: Its acquisition date",
"func":1
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.load",
"url":13,
"doc":"Open the bands and compute the wanted index. The bands will be purged of nodata and invalid pixels, the nodata will be set to 0 and the bands will be masked arrays in float. Bands that come out this function at the same time are collocated and therefore have the same shapes. This can be broken if you load data separately. Its is best to always load DEM data with some real bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> bands = prod.load([GREEN, NDVI], resolution=20) >>> bands  ' {  :  array( [0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0,  :  array( [0.0615 , 0.061625, 0.061 ,  ., 0.12085 , 0.120225, 0.113575], [0.061075, 0.06045 , 0.06025 ,  ., 0.114625, 0.119625, 0.117625], [0.06475 , 0.06145 , 0.060925,  ., 0.111475, 0.114925, 0.115175],  ., [0.1516 , 0.14195 , 0.1391 ,  ., 0.159975, 0.14145 , 0.127075], [0.140325, 0.125975, 0.131875,  ., 0.18245 , 0.1565 , 0.13015 ], [0.133475, 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675, 0.16405  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0 }  '   Args: bands (Union[list, BandNames, Callable]): Band list resolution (float): Resolution of the band, in meters size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided. Returns: dict: {band_name, band xarray}",
"func":1
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.has_band",
"url":13,
"doc":"Does this products has the specified band ? By band, we mean: - satellite band - index - DEM band - cloud band   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.has_band(GREEN) True >>> prod.has_band(TIR_2) False >>> prod.has_band(NDVI) True >>> prod.has_band(SHADOWS) False >>> prod.has_band(HILLSHADE) True   Args: band (Union[obn, sbn]): Optical or SAR band Returns: bool: True if the products has the specified band",
"func":1
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.output",
"url":13,
"doc":"Output directory of the product, to write orthorectified data for example."
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.stack",
"url":13,
"doc":"Stack bands and index of a products.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> stack = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  In meters >>> stack  '  array( [ 0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [ 0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [ 2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [ 1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [ 1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [ 1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ,  0.27066118, 0.23466069, 0.18792598,  ., -0.4611526 , -0.49751845, -0.4865216 ], [ 0.22425456, 0.28004232, 0.27851456,  ., -0.5032771 , -0.501796 , -0.502669 ], [-0.07466951, 0.06360884, 0.1207174 ,  ., -0.50617427, -0.50219285, -0.5034222 ], [-0.47076276, -0.4705828 , -0.4747971 ,  ., -0.32138503, -0.36619243, -0.37428448], [-0.4826967 , -0.5032287 , -0.48544118,  ., -0.278925 , -0.31404778, -0.36052078], [-0.488381 , -0.48253912, -0.4697526 ,  ., -0.38105175, -0.30813277, -0.27739233 ,  0.0615 , 0.061625 , 0.061 ,  ., 0.12085 , 0.120225 , 0.113575 ], [ 0.061075 , 0.06045 , 0.06025 ,  ., 0.114625 , 0.119625 , 0.117625 ], [ 0.06475 , 0.06145 , 0.060925 ,  ., 0.111475 , 0.114925 , 0.115175 ],  ., [ 0.1516 , 0.14195 , 0.1391 ,  ., 0.159975 , 0.14145 , 0.127075 ], [ 0.140325 , 0.125975 , 0.131875 ,  ., 0.18245 , 0.1565 , 0.13015 ], [ 0.133475 , 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675 , 0.16405  ], dtype=float32) Coordinates:  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0  z (z) MultiIndex - variable (z) object 'NDVI' 'MNDWI' 'GREEN' - band (z) int64 1 1 1 Attributes: long_name: ['NDVI', 'MNDWI', 'GREEN']  '   Args: bands (list): Bands and index combination resolution (float): Stack resolution. . If not specified, use the product resolution. stack_path (str): Stack path save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000) Returns: xr.DataArray: Stack as a DataArray",
"func":1
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.name",
"url":13,
"doc":"Product name (its filename without any extension)."
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.split_name",
"url":13,
"doc":"Split name, to retrieve every information from its filename (dates, tile, product type .)."
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.archive_path",
"url":13,
"doc":"Archive path, same as the product path if not specified. Useful when you want to know where both the extracted and archived version of your product are stored."
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.path",
"url":13,
"doc":"Usable path to the product, either extracted or archived path, according to the satellite."
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.is_archived",
"url":13,
"doc":"Is the archived product is processed (a products is considered as archived if its products path is a directory)."
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.needs_extraction",
"url":13,
"doc":"Does this products needs to be extracted to be processed ? ( True by default)."
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.date",
"url":13,
"doc":"Acquisition date."
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.datetime",
"url":13,
"doc":"Acquisition datetime."
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.tile_name",
"url":13,
"doc":"Tile if possible (for data that can be piled, for example S2 and Landsats)."
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.sensor_type",
"url":13,
"doc":"Sensor type, SAR or optical."
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.product_type",
"url":13,
"doc":"Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.band_names",
"url":13,
"doc":"Band mapping between band wrapping names such as  GREEN and band real number such as  03 for Sentinel-2."
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.is_reference",
"url":13,
"doc":"If the product is a reference, used for algorithms that need pre and post data, such as fire detection."
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.corresponding_ref",
"url":13,
"doc":"The corresponding reference products to the current one (if the product is not a reference but has a reference data corresponding to it). A list because of multiple ref in case of non-stackable products (S3, S1 .)"
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.nodata",
"url":13,
"doc":"Product nodata, set to 0 by default. Please do not touch this or all index will fail."
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.platform",
"url":13,
"doc":"Product platform, such as Sentinel-2"
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.resolution",
"url":13,
"doc":"Default resolution in meters of the current product. For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles."
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.condensed_name",
"url":13,
"doc":"Condensed name, the filename with only useful data to keep the name unique (ie.  20191215T110441_S2_30TXP_L2A_122756 ). Used to shorten names and paths."
},
{
"ref":"eoreader.products.optical.l8_product.L8Product.sat_id",
"url":13,
"doc":"Satellite ID, i.e.  S2 for Sentinel-2"
},
{
"ref":"eoreader.products.optical.landsat_product",
"url":11,
"doc":"Landsat products"
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProductType",
"url":11,
"doc":"Landsat products types"
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProductType.L1_OLCI",
"url":11,
"doc":"OLCI Product Type, for Landsat-8 platform"
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProductType.L1_ETM",
"url":11,
"doc":"ETM Product Type, for Landsat-7 platform"
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProductType.L1_TM",
"url":11,
"doc":"TM Product Type, for Landsat-5 and 4 platforms"
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProductType.L1_MSS",
"url":11,
"doc":"MSS Product Type, for Landsat-5, 4, 3, 2, 1 platforms"
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatCollection",
"url":11,
"doc":"Landsat collection number. See [here](https: www.usgs.gov/media/files/landsat-collection-1-vs-collection-2-summary) for more information"
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatCollection.COL_1",
"url":11,
"doc":"Collection 1"
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatCollection.COL_2",
"url":11,
"doc":"Collection 2"
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct",
"url":11,
"doc":"Super Class of Landsat Products You can use directly the .tar file in case of collection 2 products."
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.footprint",
"url":11,
"doc":"Get real footprint of the products (without nodata, in french  emprise utile)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>> prod.footprint() index geometry 0 0 POLYGON  366165.000 4899735.000, 366165.000 4 .   Overload of the generic function because landsat nodata seems to be different in QA than in regular bands. Indeed, nodata pixels vary according to the band sensor footprint, whereas QA nodata is where at least one band has nodata. We chose to keep QA nodata values for the footprint in order to show where all bands are valid.  TL;DR: We use the QA nodata value to determine the product's footprint . Returns: gpd.GeoDataFrame: Footprint as a GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.get_datetime",
"url":11,
"doc":"Get the product's acquisition datetime, with format  YYYYMMDDTHHMMSS   %Y%m%dT%H%M%S   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>> prod.get_datetime(as_datetime=True) datetime.datetime(2020, 5, 18, 16, 34, 7) >>> prod.get_datetime(as_datetime=False) '20200518T163407'   Args: as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string. Returns: Union[str, datetime.datetime]: Its acquisition datetime",
"func":1
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.get_band_paths",
"url":11,
"doc":"Return the paths of required bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_band_paths([GREEN, RED]) {  : 'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B3.TIF',  : 'LC08_L1GT_023030_20200518_20200527_01_T2\\LC08_L1GT_023030_20200518_20200527_01_T2_B4.TIF' }   Args: band_list (list): List of the wanted bands resolution (float): Useless here Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.read_mtd",
"url":11,
"doc":"Read Landsat metadata as: - a  pandas.DataFrame whatever its collection is (by default for collection 1) - a XML root + its namespace if the product is retrieved from the 2nd collection (by default for collection 2)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>>  COLLECTION 1 : Open metadata as panda DataFrame >>> prod.read_mtd() NAME ORIGIN  . RESAMPLING_OPTION value \"Image courtesy of the U.S. Geological Survey\"  . \"CUBIC_CONVOLUTION\" [1 rows x 197 columns] >>>  COLLECTION 2 : Open metadata as XML >>> path = r\"LC08_L1TP_200030_20201220_20210310_02_T1\"  Collection 2 >>> prod = Reader().open(path) >>> prod.read_mtd() ( ,  ) >>>  COLLECTION 2 : Force to pandas.DataFrame >>> prod.read_mtd(force_pd=True) NAME ORIGIN  . RESAMPLING_OPTION value \"Image courtesy of the U.S. Geological Survey\"  . \"CUBIC_CONVOLUTION\" [1 rows x 263 columns]   Args: force_pd (bool): If collection 2, return a pandas.DataFrame instead of a XML root + namespace Returns: pd.DataFrame: Metadata as a Pandas DataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.get_mean_sun_angles",
"url":11,
"doc":"Get Mean Sun angles (Azimuth and Zenith angles)   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_mean_sun_angles() (140.80752656, 61.93065805)   Returns: (float, float): Mean Azimuth and Zenith angle",
"func":1
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.get_default_band",
"url":12,
"doc":"Get default band:  GREEN for optical data as every optical satellite has a GREEN band.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band()    Returns: str: Default band",
"func":1
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.get_default_band_path",
"url":12,
"doc":"Get default band ( GREEN for optical data) path.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band_path() 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2'   Returns: str: Default band path",
"func":1
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.crs",
"url":12,
"doc":"Get UTM projection of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_crs() CRS.from_epsg(32630)   Returns: rasterio.crs.CRS: CRS object",
"func":1
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.extent",
"url":12,
"doc":"Get UTM extent of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_extent() geometry 0 POLYGON  309780.000 4390200.000, 309780.000 4 .   Returns: gpd.GeoDataFrame: Footprint in UTM",
"func":1
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.get_existing_bands",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_bands() [ ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ]   Returns: list: List of existing bands in the products",
"func":1
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.get_existing_band_paths",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_band_paths() {  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B01.jp2',  .,  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B12.jp2' }   Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.get_date",
"url":13,
"doc":"Get the product's acquisition date.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_date(as_date=True) datetime.datetime(2020, 8, 24, 0, 0) >>> prod.get_date(as_date=False) '20200824'   Args: as_date (bool): Return the date as a datetime.date. If false, returns a string. Returns: str: Its acquisition date",
"func":1
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.load",
"url":13,
"doc":"Open the bands and compute the wanted index. The bands will be purged of nodata and invalid pixels, the nodata will be set to 0 and the bands will be masked arrays in float. Bands that come out this function at the same time are collocated and therefore have the same shapes. This can be broken if you load data separately. Its is best to always load DEM data with some real bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> bands = prod.load([GREEN, NDVI], resolution=20) >>> bands  ' {  :  array( [0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0,  :  array( [0.0615 , 0.061625, 0.061 ,  ., 0.12085 , 0.120225, 0.113575], [0.061075, 0.06045 , 0.06025 ,  ., 0.114625, 0.119625, 0.117625], [0.06475 , 0.06145 , 0.060925,  ., 0.111475, 0.114925, 0.115175],  ., [0.1516 , 0.14195 , 0.1391 ,  ., 0.159975, 0.14145 , 0.127075], [0.140325, 0.125975, 0.131875,  ., 0.18245 , 0.1565 , 0.13015 ], [0.133475, 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675, 0.16405  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0 }  '   Args: bands (Union[list, BandNames, Callable]): Band list resolution (float): Resolution of the band, in meters size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided. Returns: dict: {band_name, band xarray}",
"func":1
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.has_band",
"url":13,
"doc":"Does this products has the specified band ? By band, we mean: - satellite band - index - DEM band - cloud band   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.has_band(GREEN) True >>> prod.has_band(TIR_2) False >>> prod.has_band(NDVI) True >>> prod.has_band(SHADOWS) False >>> prod.has_band(HILLSHADE) True   Args: band (Union[obn, sbn]): Optical or SAR band Returns: bool: True if the products has the specified band",
"func":1
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.output",
"url":13,
"doc":"Output directory of the product, to write orthorectified data for example."
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.stack",
"url":13,
"doc":"Stack bands and index of a products.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> stack = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  In meters >>> stack  '  array( [ 0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [ 0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [ 2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [ 1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [ 1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [ 1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ,  0.27066118, 0.23466069, 0.18792598,  ., -0.4611526 , -0.49751845, -0.4865216 ], [ 0.22425456, 0.28004232, 0.27851456,  ., -0.5032771 , -0.501796 , -0.502669 ], [-0.07466951, 0.06360884, 0.1207174 ,  ., -0.50617427, -0.50219285, -0.5034222 ], [-0.47076276, -0.4705828 , -0.4747971 ,  ., -0.32138503, -0.36619243, -0.37428448], [-0.4826967 , -0.5032287 , -0.48544118,  ., -0.278925 , -0.31404778, -0.36052078], [-0.488381 , -0.48253912, -0.4697526 ,  ., -0.38105175, -0.30813277, -0.27739233 ,  0.0615 , 0.061625 , 0.061 ,  ., 0.12085 , 0.120225 , 0.113575 ], [ 0.061075 , 0.06045 , 0.06025 ,  ., 0.114625 , 0.119625 , 0.117625 ], [ 0.06475 , 0.06145 , 0.060925 ,  ., 0.111475 , 0.114925 , 0.115175 ],  ., [ 0.1516 , 0.14195 , 0.1391 ,  ., 0.159975 , 0.14145 , 0.127075 ], [ 0.140325 , 0.125975 , 0.131875 ,  ., 0.18245 , 0.1565 , 0.13015 ], [ 0.133475 , 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675 , 0.16405  ], dtype=float32) Coordinates:  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0  z (z) MultiIndex - variable (z) object 'NDVI' 'MNDWI' 'GREEN' - band (z) int64 1 1 1 Attributes: long_name: ['NDVI', 'MNDWI', 'GREEN']  '   Args: bands (list): Bands and index combination resolution (float): Stack resolution. . If not specified, use the product resolution. stack_path (str): Stack path save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000) Returns: xr.DataArray: Stack as a DataArray",
"func":1
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.name",
"url":13,
"doc":"Product name (its filename without any extension)."
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.split_name",
"url":13,
"doc":"Split name, to retrieve every information from its filename (dates, tile, product type .)."
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.archive_path",
"url":13,
"doc":"Archive path, same as the product path if not specified. Useful when you want to know where both the extracted and archived version of your product are stored."
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.path",
"url":13,
"doc":"Usable path to the product, either extracted or archived path, according to the satellite."
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.is_archived",
"url":13,
"doc":"Is the archived product is processed (a products is considered as archived if its products path is a directory)."
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.needs_extraction",
"url":13,
"doc":"Does this products needs to be extracted to be processed ? ( True by default)."
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.date",
"url":13,
"doc":"Acquisition date."
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.datetime",
"url":13,
"doc":"Acquisition datetime."
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.tile_name",
"url":13,
"doc":"Tile if possible (for data that can be piled, for example S2 and Landsats)."
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.sensor_type",
"url":13,
"doc":"Sensor type, SAR or optical."
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.product_type",
"url":13,
"doc":"Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.band_names",
"url":13,
"doc":"Band mapping between band wrapping names such as  GREEN and band real number such as  03 for Sentinel-2."
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.is_reference",
"url":13,
"doc":"If the product is a reference, used for algorithms that need pre and post data, such as fire detection."
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.corresponding_ref",
"url":13,
"doc":"The corresponding reference products to the current one (if the product is not a reference but has a reference data corresponding to it). A list because of multiple ref in case of non-stackable products (S3, S1 .)"
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.nodata",
"url":13,
"doc":"Product nodata, set to 0 by default. Please do not touch this or all index will fail."
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.platform",
"url":13,
"doc":"Product platform, such as Sentinel-2"
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.resolution",
"url":13,
"doc":"Default resolution in meters of the current product. For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles."
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.condensed_name",
"url":13,
"doc":"Condensed name, the filename with only useful data to keep the name unique (ie.  20191215T110441_S2_30TXP_L2A_122756 ). Used to shorten names and paths."
},
{
"ref":"eoreader.products.optical.landsat_product.LandsatProduct.sat_id",
"url":13,
"doc":"Satellite ID, i.e.  S2 for Sentinel-2"
},
{
"ref":"eoreader.products.optical.optical_product",
"url":12,
"doc":"Super class for optical products"
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct",
"url":12,
"doc":"Super class for optical products"
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.get_default_band",
"url":12,
"doc":"Get default band:  GREEN for optical data as every optical satellite has a GREEN band.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band()    Returns: str: Default band",
"func":1
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.get_default_band_path",
"url":12,
"doc":"Get default band ( GREEN for optical data) path.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band_path() 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2'   Returns: str: Default band path",
"func":1
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.crs",
"url":12,
"doc":"Get UTM projection of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_crs() CRS.from_epsg(32630)   Returns: rasterio.crs.CRS: CRS object",
"func":1
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.extent",
"url":12,
"doc":"Get UTM extent of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_extent() geometry 0 POLYGON  309780.000 4390200.000, 309780.000 4 .   Returns: gpd.GeoDataFrame: Footprint in UTM",
"func":1
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.get_existing_bands",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_bands() [ ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ]   Returns: list: List of existing bands in the products",
"func":1
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.get_existing_band_paths",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_band_paths() {  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B01.jp2',  .,  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B12.jp2' }   Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.get_mean_sun_angles",
"url":12,
"doc":"Get Mean Sun angles (Azimuth and Zenith angles)   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_mean_sun_angles() (149.148155074489, 32.6627897525474)   Returns: (float, float): Mean Azimuth and Zenith angle",
"func":1
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.footprint",
"url":13,
"doc":"Get UTM footprint of the products (without nodata,  in french  emprise utile )   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.footprint() index geometry 0 0 POLYGON  199980.000 4500000.000, 199980.000 4 .   Returns: gpd.GeoDataFrame: Footprint as a GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.get_datetime",
"url":13,
"doc":"Get the product's acquisition datetime, with format  YYYYMMDDTHHMMSS   %Y%m%dT%H%M%S   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_datetime(as_datetime=True) datetime.datetime(2020, 8, 24, 11, 6, 31) >>> prod.get_datetime(as_datetime=False) '20200824T110631'   Args: as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string. Returns: Union[str, datetime.datetime]: Its acquisition datetime",
"func":1
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.get_date",
"url":13,
"doc":"Get the product's acquisition date.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_date(as_date=True) datetime.datetime(2020, 8, 24, 0, 0) >>> prod.get_date(as_date=False) '20200824'   Args: as_date (bool): Return the date as a datetime.date. If false, returns a string. Returns: str: Its acquisition date",
"func":1
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.get_band_paths",
"url":13,
"doc":"Return the paths of required bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_band_paths([GREEN, RED]) {  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2',  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B04.jp2' }   Args: band_list (list): List of the wanted bands resolution (float): Band resolution Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.read_mtd",
"url":13,
"doc":"Read metadata and outputs the metadata XML root and its namespace most of the time, except from L8-collection 1 data which outputs a pandas DataFrame   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.read_mtd() ( ,  )   Returns: Any: Metadata XML root and its namespace or pd.DataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.load",
"url":13,
"doc":"Open the bands and compute the wanted index. The bands will be purged of nodata and invalid pixels, the nodata will be set to 0 and the bands will be masked arrays in float. Bands that come out this function at the same time are collocated and therefore have the same shapes. This can be broken if you load data separately. Its is best to always load DEM data with some real bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> bands = prod.load([GREEN, NDVI], resolution=20) >>> bands  ' {  :  array( [0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0,  :  array( [0.0615 , 0.061625, 0.061 ,  ., 0.12085 , 0.120225, 0.113575], [0.061075, 0.06045 , 0.06025 ,  ., 0.114625, 0.119625, 0.117625], [0.06475 , 0.06145 , 0.060925,  ., 0.111475, 0.114925, 0.115175],  ., [0.1516 , 0.14195 , 0.1391 ,  ., 0.159975, 0.14145 , 0.127075], [0.140325, 0.125975, 0.131875,  ., 0.18245 , 0.1565 , 0.13015 ], [0.133475, 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675, 0.16405  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0 }  '   Args: bands (Union[list, BandNames, Callable]): Band list resolution (float): Resolution of the band, in meters size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided. Returns: dict: {band_name, band xarray}",
"func":1
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.has_band",
"url":13,
"doc":"Does this products has the specified band ? By band, we mean: - satellite band - index - DEM band - cloud band   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.has_band(GREEN) True >>> prod.has_band(TIR_2) False >>> prod.has_band(NDVI) True >>> prod.has_band(SHADOWS) False >>> prod.has_band(HILLSHADE) True   Args: band (Union[obn, sbn]): Optical or SAR band Returns: bool: True if the products has the specified band",
"func":1
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.output",
"url":13,
"doc":"Output directory of the product, to write orthorectified data for example."
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.stack",
"url":13,
"doc":"Stack bands and index of a products.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> stack = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  In meters >>> stack  '  array( [ 0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [ 0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [ 2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [ 1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [ 1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [ 1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ,  0.27066118, 0.23466069, 0.18792598,  ., -0.4611526 , -0.49751845, -0.4865216 ], [ 0.22425456, 0.28004232, 0.27851456,  ., -0.5032771 , -0.501796 , -0.502669 ], [-0.07466951, 0.06360884, 0.1207174 ,  ., -0.50617427, -0.50219285, -0.5034222 ], [-0.47076276, -0.4705828 , -0.4747971 ,  ., -0.32138503, -0.36619243, -0.37428448], [-0.4826967 , -0.5032287 , -0.48544118,  ., -0.278925 , -0.31404778, -0.36052078], [-0.488381 , -0.48253912, -0.4697526 ,  ., -0.38105175, -0.30813277, -0.27739233 ,  0.0615 , 0.061625 , 0.061 ,  ., 0.12085 , 0.120225 , 0.113575 ], [ 0.061075 , 0.06045 , 0.06025 ,  ., 0.114625 , 0.119625 , 0.117625 ], [ 0.06475 , 0.06145 , 0.060925 ,  ., 0.111475 , 0.114925 , 0.115175 ],  ., [ 0.1516 , 0.14195 , 0.1391 ,  ., 0.159975 , 0.14145 , 0.127075 ], [ 0.140325 , 0.125975 , 0.131875 ,  ., 0.18245 , 0.1565 , 0.13015 ], [ 0.133475 , 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675 , 0.16405  ], dtype=float32) Coordinates:  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0  z (z) MultiIndex - variable (z) object 'NDVI' 'MNDWI' 'GREEN' - band (z) int64 1 1 1 Attributes: long_name: ['NDVI', 'MNDWI', 'GREEN']  '   Args: bands (list): Bands and index combination resolution (float): Stack resolution. . If not specified, use the product resolution. stack_path (str): Stack path save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000) Returns: xr.DataArray: Stack as a DataArray",
"func":1
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.name",
"url":13,
"doc":"Product name (its filename without any extension)."
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.split_name",
"url":13,
"doc":"Split name, to retrieve every information from its filename (dates, tile, product type .)."
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.archive_path",
"url":13,
"doc":"Archive path, same as the product path if not specified. Useful when you want to know where both the extracted and archived version of your product are stored."
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.path",
"url":13,
"doc":"Usable path to the product, either extracted or archived path, according to the satellite."
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.is_archived",
"url":13,
"doc":"Is the archived product is processed (a products is considered as archived if its products path is a directory)."
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.needs_extraction",
"url":13,
"doc":"Does this products needs to be extracted to be processed ? ( True by default)."
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.date",
"url":13,
"doc":"Acquisition date."
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.datetime",
"url":13,
"doc":"Acquisition datetime."
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.tile_name",
"url":13,
"doc":"Tile if possible (for data that can be piled, for example S2 and Landsats)."
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.sensor_type",
"url":13,
"doc":"Sensor type, SAR or optical."
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.product_type",
"url":13,
"doc":"Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.band_names",
"url":13,
"doc":"Band mapping between band wrapping names such as  GREEN and band real number such as  03 for Sentinel-2."
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.is_reference",
"url":13,
"doc":"If the product is a reference, used for algorithms that need pre and post data, such as fire detection."
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.corresponding_ref",
"url":13,
"doc":"The corresponding reference products to the current one (if the product is not a reference but has a reference data corresponding to it). A list because of multiple ref in case of non-stackable products (S3, S1 .)"
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.nodata",
"url":13,
"doc":"Product nodata, set to 0 by default. Please do not touch this or all index will fail."
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.platform",
"url":13,
"doc":"Product platform, such as Sentinel-2"
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.resolution",
"url":13,
"doc":"Default resolution in meters of the current product. For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles."
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.condensed_name",
"url":13,
"doc":"Condensed name, the filename with only useful data to keep the name unique (ie.  20191215T110441_S2_30TXP_L2A_122756 ). Used to shorten names and paths."
},
{
"ref":"eoreader.products.optical.optical_product.OpticalProduct.sat_id",
"url":13,
"doc":"Satellite ID, i.e.  S2 for Sentinel-2"
},
{
"ref":"eoreader.products.optical.s2_product",
"url":20,
"doc":"Sentinel-2 products"
},
{
"ref":"eoreader.products.optical.s2_product.S2ProductType",
"url":20,
"doc":"Sentinel-2 products types (L1C or L2A)"
},
{
"ref":"eoreader.products.optical.s2_product.S2ProductType.L1C",
"url":20,
"doc":""
},
{
"ref":"eoreader.products.optical.s2_product.S2ProductType.L2A",
"url":20,
"doc":""
},
{
"ref":"eoreader.products.optical.s2_product.S2Product",
"url":20,
"doc":"Class of Sentinel-2 Products You can use directly the .zip file"
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.get_datetime",
"url":20,
"doc":"Get the product's acquisition datetime, with format  YYYYMMDDTHHMMSS   %Y%m%dT%H%M%S   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_datetime(as_datetime=True) datetime.datetime(2020, 8, 24, 11, 6, 31) >>> prod.get_datetime(as_datetime=False) '20200824T110631'   Args: as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string. Returns: Union[str, datetime.datetime]: Its acquisition datetime",
"func":1
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.get_band_paths",
"url":20,
"doc":"Return the paths of required bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_band_paths([GREEN, RED]) {  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2',  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B04.jp2' }   Args: band_list (list): List of the wanted bands resolution (float): Band resolution Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.open_mask",
"url":20,
"doc":"Open S2 mask (GML files stored in QI_DATA) as  gpd.GeoDataFrame . Masks than can be called that way are: -  TECQUA : Technical quality mask -  SATURA : Saturated Pixels -  NODATA : Pixel nodata (inside the detectors) -  DETFOO : Detectors footprint -> used to process nodata outside the detectors -  DEFECT : Defective pixels -  CLOUDS ,  only with  00 as a band !   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod.open_mask(\"NODATA\", GREEN) Empty GeoDataFrame Columns: [geometry] Index: [] >>> prod.open_mask(\"SATURA\", GREEN) Empty GeoDataFrame Columns: [geometry] Index: [] >>> prod.open_mask(\"DETFOO\", GREEN) gml_id  . geometry 0 detector_footprint-B03-02-0  . POLYGON Z  199980.000 4500000.000 0.000, 1999 . 1 detector_footprint-B03-03-1  . POLYGON Z  222570.000 4500000.000 0.000, 2225 . 2 detector_footprint-B03-05-2  . POLYGON Z  273050.000 4500000.000 0.000, 2730 . 3 detector_footprint-B03-07-3  . POLYGON Z  309770.000 4453710.000 0.000, 3097 . 4 detector_footprint-B03-04-4  . POLYGON Z  248080.000 4500000.000 0.000, 2480 . 5 detector_footprint-B03-06-5  . POLYGON Z  297980.000 4500000.000 0.000, 2979 . [6 rows x 3 columns]   Args: mask_str (str): Mask name, such as DEFECT, NODATA, SATURA . band (Union[obn, str]): Band number as an OpticalBandNames or str (for clouds: 00) Returns: gpd.GeoDataFrame: Mask as a vector",
"func":1
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.get_mean_sun_angles",
"url":20,
"doc":"Get Mean Sun angles (Azimuth and Zenith angles)   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_mean_sun_angles() (149.148155074489, 32.6627897525474)   Returns: (float, float): Mean Azimuth and Zenith angle",
"func":1
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.read_mtd",
"url":20,
"doc":"Read metadata and outputs the metadata XML root and its namespace   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.read_mtd() ( , '{https: psd-14.sentinel2.eo.esa.int/PSD/S2_PDI_Level-2A_Tile_Metadata.xsd}')   Returns: (etree._Element, str): Metadata XML root and its namespace",
"func":1
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.get_default_band",
"url":12,
"doc":"Get default band:  GREEN for optical data as every optical satellite has a GREEN band.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band()    Returns: str: Default band",
"func":1
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.get_default_band_path",
"url":12,
"doc":"Get default band ( GREEN for optical data) path.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band_path() 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2'   Returns: str: Default band path",
"func":1
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.crs",
"url":12,
"doc":"Get UTM projection of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_crs() CRS.from_epsg(32630)   Returns: rasterio.crs.CRS: CRS object",
"func":1
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.extent",
"url":12,
"doc":"Get UTM extent of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_extent() geometry 0 POLYGON  309780.000 4390200.000, 309780.000 4 .   Returns: gpd.GeoDataFrame: Footprint in UTM",
"func":1
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.get_existing_bands",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_bands() [ ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ]   Returns: list: List of existing bands in the products",
"func":1
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.get_existing_band_paths",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_band_paths() {  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B01.jp2',  .,  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B12.jp2' }   Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.footprint",
"url":13,
"doc":"Get UTM footprint of the products (without nodata,  in french  emprise utile )   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.footprint() index geometry 0 0 POLYGON  199980.000 4500000.000, 199980.000 4 .   Returns: gpd.GeoDataFrame: Footprint as a GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.get_date",
"url":13,
"doc":"Get the product's acquisition date.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_date(as_date=True) datetime.datetime(2020, 8, 24, 0, 0) >>> prod.get_date(as_date=False) '20200824'   Args: as_date (bool): Return the date as a datetime.date. If false, returns a string. Returns: str: Its acquisition date",
"func":1
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.load",
"url":13,
"doc":"Open the bands and compute the wanted index. The bands will be purged of nodata and invalid pixels, the nodata will be set to 0 and the bands will be masked arrays in float. Bands that come out this function at the same time are collocated and therefore have the same shapes. This can be broken if you load data separately. Its is best to always load DEM data with some real bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> bands = prod.load([GREEN, NDVI], resolution=20) >>> bands  ' {  :  array( [0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0,  :  array( [0.0615 , 0.061625, 0.061 ,  ., 0.12085 , 0.120225, 0.113575], [0.061075, 0.06045 , 0.06025 ,  ., 0.114625, 0.119625, 0.117625], [0.06475 , 0.06145 , 0.060925,  ., 0.111475, 0.114925, 0.115175],  ., [0.1516 , 0.14195 , 0.1391 ,  ., 0.159975, 0.14145 , 0.127075], [0.140325, 0.125975, 0.131875,  ., 0.18245 , 0.1565 , 0.13015 ], [0.133475, 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675, 0.16405  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0 }  '   Args: bands (Union[list, BandNames, Callable]): Band list resolution (float): Resolution of the band, in meters size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided. Returns: dict: {band_name, band xarray}",
"func":1
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.has_band",
"url":13,
"doc":"Does this products has the specified band ? By band, we mean: - satellite band - index - DEM band - cloud band   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.has_band(GREEN) True >>> prod.has_band(TIR_2) False >>> prod.has_band(NDVI) True >>> prod.has_band(SHADOWS) False >>> prod.has_band(HILLSHADE) True   Args: band (Union[obn, sbn]): Optical or SAR band Returns: bool: True if the products has the specified band",
"func":1
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.output",
"url":13,
"doc":"Output directory of the product, to write orthorectified data for example."
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.stack",
"url":13,
"doc":"Stack bands and index of a products.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> stack = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  In meters >>> stack  '  array( [ 0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [ 0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [ 2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [ 1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [ 1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [ 1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ,  0.27066118, 0.23466069, 0.18792598,  ., -0.4611526 , -0.49751845, -0.4865216 ], [ 0.22425456, 0.28004232, 0.27851456,  ., -0.5032771 , -0.501796 , -0.502669 ], [-0.07466951, 0.06360884, 0.1207174 ,  ., -0.50617427, -0.50219285, -0.5034222 ], [-0.47076276, -0.4705828 , -0.4747971 ,  ., -0.32138503, -0.36619243, -0.37428448], [-0.4826967 , -0.5032287 , -0.48544118,  ., -0.278925 , -0.31404778, -0.36052078], [-0.488381 , -0.48253912, -0.4697526 ,  ., -0.38105175, -0.30813277, -0.27739233 ,  0.0615 , 0.061625 , 0.061 ,  ., 0.12085 , 0.120225 , 0.113575 ], [ 0.061075 , 0.06045 , 0.06025 ,  ., 0.114625 , 0.119625 , 0.117625 ], [ 0.06475 , 0.06145 , 0.060925 ,  ., 0.111475 , 0.114925 , 0.115175 ],  ., [ 0.1516 , 0.14195 , 0.1391 ,  ., 0.159975 , 0.14145 , 0.127075 ], [ 0.140325 , 0.125975 , 0.131875 ,  ., 0.18245 , 0.1565 , 0.13015 ], [ 0.133475 , 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675 , 0.16405  ], dtype=float32) Coordinates:  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0  z (z) MultiIndex - variable (z) object 'NDVI' 'MNDWI' 'GREEN' - band (z) int64 1 1 1 Attributes: long_name: ['NDVI', 'MNDWI', 'GREEN']  '   Args: bands (list): Bands and index combination resolution (float): Stack resolution. . If not specified, use the product resolution. stack_path (str): Stack path save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000) Returns: xr.DataArray: Stack as a DataArray",
"func":1
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.name",
"url":13,
"doc":"Product name (its filename without any extension)."
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.split_name",
"url":13,
"doc":"Split name, to retrieve every information from its filename (dates, tile, product type .)."
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.archive_path",
"url":13,
"doc":"Archive path, same as the product path if not specified. Useful when you want to know where both the extracted and archived version of your product are stored."
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.path",
"url":13,
"doc":"Usable path to the product, either extracted or archived path, according to the satellite."
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.is_archived",
"url":13,
"doc":"Is the archived product is processed (a products is considered as archived if its products path is a directory)."
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.needs_extraction",
"url":13,
"doc":"Does this products needs to be extracted to be processed ? ( True by default)."
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.date",
"url":13,
"doc":"Acquisition date."
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.datetime",
"url":13,
"doc":"Acquisition datetime."
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.tile_name",
"url":13,
"doc":"Tile if possible (for data that can be piled, for example S2 and Landsats)."
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.sensor_type",
"url":13,
"doc":"Sensor type, SAR or optical."
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.product_type",
"url":13,
"doc":"Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.band_names",
"url":13,
"doc":"Band mapping between band wrapping names such as  GREEN and band real number such as  03 for Sentinel-2."
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.is_reference",
"url":13,
"doc":"If the product is a reference, used for algorithms that need pre and post data, such as fire detection."
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.corresponding_ref",
"url":13,
"doc":"The corresponding reference products to the current one (if the product is not a reference but has a reference data corresponding to it). A list because of multiple ref in case of non-stackable products (S3, S1 .)"
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.nodata",
"url":13,
"doc":"Product nodata, set to 0 by default. Please do not touch this or all index will fail."
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.platform",
"url":13,
"doc":"Product platform, such as Sentinel-2"
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.resolution",
"url":13,
"doc":"Default resolution in meters of the current product. For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles."
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.condensed_name",
"url":13,
"doc":"Condensed name, the filename with only useful data to keep the name unique (ie.  20191215T110441_S2_30TXP_L2A_122756 ). Used to shorten names and paths."
},
{
"ref":"eoreader.products.optical.s2_product.S2Product.sat_id",
"url":13,
"doc":"Satellite ID, i.e.  S2 for Sentinel-2"
},
{
"ref":"eoreader.products.optical.s2_theia_product",
"url":21,
"doc":"Sentinel-2 Theia products See [here](https: labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/) for more information."
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct",
"url":21,
"doc":"Class of Sentinel-2 Theia Products. See [here](https: labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/) for more information."
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.get_datetime",
"url":21,
"doc":"Get the product's acquisition datetime, with format  YYYYMMDDTHHMMSS   %Y%m%dT%H%M%S   >>> from eoreader.reader import Reader >>> path = r\"SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2\" >>> prod = Reader().open(path) >>> prod.get_datetime(as_datetime=True) datetime.datetime(2019, 6, 25, 10, 57, 28, 756000), fetched from metadata, so we have the ms >>> prod.get_datetime(as_datetime=False) '20190625T105728'   Args: as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string. Returns: Union[str, datetime.datetime]: Its acquisition datetime",
"func":1
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.get_band_paths",
"url":21,
"doc":"Return the paths of required bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2\" >>> prod = Reader().open(path) >>> prod.get_band_paths([GREEN, RED]) {  : 'SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2\\SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2_FRE_B3.tif',  : 'SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2\\SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2_FRE_B4.tif' }   Args: band_list (list): List of the wanted bands resolution (float): Band resolution Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.open_mask",
"url":21,
"doc":"Get a Sentinel-2 THEIA mask path. See [here](https: labo.obs-mip.fr/multitemp/sentinel-2/theias-sentinel-2-l2a-product-format/) for more information. Accepted mask IDs: -  DFP : Defective pixels -  EDG : Nodata pixels mask -  SAT : Saturated pixels mask -  MG2 : Geophysical mask (classification) -  IAB : Mask where water vapor and TOA pixels have been interpolated -  CLM : Cloud mask   >>> from eoreader.bands.alias import  >>> from eoreader.reader import Reader >>> path = r\"SENTINEL2B_20190401-105726-885_L2A_T31UEQ_D_V2-0.zip\" >>> prod = Reader().open(path) >>> prod.open_mask(\"CLM\", GREEN) array( [0,  ., 0 ], dtype=uint8)   Args: mask_id: Mask ID band (obn): Band name as an OpticalBandNames resolution (float): Band resolution in meters size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided. Returns: np.ndarray: Mask array",
"func":1
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.get_mean_sun_angles",
"url":21,
"doc":"Get Mean Sun angles (Azimuth and Zenith angles)   >>> from eoreader.reader import Reader >>> path = r\"SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2\" >>> prod = Reader().open(path) >>> prod.get_mean_sun_angles() (154.554755774838, 27.5941391571236)   Returns: (float, float): Mean Azimuth and Zenith angle",
"func":1
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.read_mtd",
"url":21,
"doc":"Read metadata and outputs the metadata XML root and its namespace   >>> from eoreader.reader import Reader >>> path = r\"SENTINEL2B_20190401-105726-885_L2A_T31UEQ_D_V2-0.zip\" >>> prod = Reader().open(path) >>> prod.read_mtd() ( ,  )   Returns: (etree._Element, str): Metadata XML root and its namespace",
"func":1
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.get_default_band",
"url":12,
"doc":"Get default band:  GREEN for optical data as every optical satellite has a GREEN band.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band()    Returns: str: Default band",
"func":1
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.get_default_band_path",
"url":12,
"doc":"Get default band ( GREEN for optical data) path.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band_path() 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2'   Returns: str: Default band path",
"func":1
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.crs",
"url":12,
"doc":"Get UTM projection of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_crs() CRS.from_epsg(32630)   Returns: rasterio.crs.CRS: CRS object",
"func":1
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.extent",
"url":12,
"doc":"Get UTM extent of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_extent() geometry 0 POLYGON  309780.000 4390200.000, 309780.000 4 .   Returns: gpd.GeoDataFrame: Footprint in UTM",
"func":1
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.get_existing_bands",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_bands() [ ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ]   Returns: list: List of existing bands in the products",
"func":1
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.get_existing_band_paths",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_band_paths() {  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B01.jp2',  .,  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B12.jp2' }   Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.footprint",
"url":13,
"doc":"Get UTM footprint of the products (without nodata,  in french  emprise utile )   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.footprint() index geometry 0 0 POLYGON  199980.000 4500000.000, 199980.000 4 .   Returns: gpd.GeoDataFrame: Footprint as a GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.get_date",
"url":13,
"doc":"Get the product's acquisition date.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_date(as_date=True) datetime.datetime(2020, 8, 24, 0, 0) >>> prod.get_date(as_date=False) '20200824'   Args: as_date (bool): Return the date as a datetime.date. If false, returns a string. Returns: str: Its acquisition date",
"func":1
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.load",
"url":13,
"doc":"Open the bands and compute the wanted index. The bands will be purged of nodata and invalid pixels, the nodata will be set to 0 and the bands will be masked arrays in float. Bands that come out this function at the same time are collocated and therefore have the same shapes. This can be broken if you load data separately. Its is best to always load DEM data with some real bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> bands = prod.load([GREEN, NDVI], resolution=20) >>> bands  ' {  :  array( [0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0,  :  array( [0.0615 , 0.061625, 0.061 ,  ., 0.12085 , 0.120225, 0.113575], [0.061075, 0.06045 , 0.06025 ,  ., 0.114625, 0.119625, 0.117625], [0.06475 , 0.06145 , 0.060925,  ., 0.111475, 0.114925, 0.115175],  ., [0.1516 , 0.14195 , 0.1391 ,  ., 0.159975, 0.14145 , 0.127075], [0.140325, 0.125975, 0.131875,  ., 0.18245 , 0.1565 , 0.13015 ], [0.133475, 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675, 0.16405  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0 }  '   Args: bands (Union[list, BandNames, Callable]): Band list resolution (float): Resolution of the band, in meters size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided. Returns: dict: {band_name, band xarray}",
"func":1
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.has_band",
"url":13,
"doc":"Does this products has the specified band ? By band, we mean: - satellite band - index - DEM band - cloud band   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.has_band(GREEN) True >>> prod.has_band(TIR_2) False >>> prod.has_band(NDVI) True >>> prod.has_band(SHADOWS) False >>> prod.has_band(HILLSHADE) True   Args: band (Union[obn, sbn]): Optical or SAR band Returns: bool: True if the products has the specified band",
"func":1
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.output",
"url":13,
"doc":"Output directory of the product, to write orthorectified data for example."
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.stack",
"url":13,
"doc":"Stack bands and index of a products.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> stack = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  In meters >>> stack  '  array( [ 0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [ 0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [ 2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [ 1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [ 1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [ 1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ,  0.27066118, 0.23466069, 0.18792598,  ., -0.4611526 , -0.49751845, -0.4865216 ], [ 0.22425456, 0.28004232, 0.27851456,  ., -0.5032771 , -0.501796 , -0.502669 ], [-0.07466951, 0.06360884, 0.1207174 ,  ., -0.50617427, -0.50219285, -0.5034222 ], [-0.47076276, -0.4705828 , -0.4747971 ,  ., -0.32138503, -0.36619243, -0.37428448], [-0.4826967 , -0.5032287 , -0.48544118,  ., -0.278925 , -0.31404778, -0.36052078], [-0.488381 , -0.48253912, -0.4697526 ,  ., -0.38105175, -0.30813277, -0.27739233 ,  0.0615 , 0.061625 , 0.061 ,  ., 0.12085 , 0.120225 , 0.113575 ], [ 0.061075 , 0.06045 , 0.06025 ,  ., 0.114625 , 0.119625 , 0.117625 ], [ 0.06475 , 0.06145 , 0.060925 ,  ., 0.111475 , 0.114925 , 0.115175 ],  ., [ 0.1516 , 0.14195 , 0.1391 ,  ., 0.159975 , 0.14145 , 0.127075 ], [ 0.140325 , 0.125975 , 0.131875 ,  ., 0.18245 , 0.1565 , 0.13015 ], [ 0.133475 , 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675 , 0.16405  ], dtype=float32) Coordinates:  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0  z (z) MultiIndex - variable (z) object 'NDVI' 'MNDWI' 'GREEN' - band (z) int64 1 1 1 Attributes: long_name: ['NDVI', 'MNDWI', 'GREEN']  '   Args: bands (list): Bands and index combination resolution (float): Stack resolution. . If not specified, use the product resolution. stack_path (str): Stack path save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000) Returns: xr.DataArray: Stack as a DataArray",
"func":1
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.name",
"url":13,
"doc":"Product name (its filename without any extension)."
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.split_name",
"url":13,
"doc":"Split name, to retrieve every information from its filename (dates, tile, product type .)."
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.archive_path",
"url":13,
"doc":"Archive path, same as the product path if not specified. Useful when you want to know where both the extracted and archived version of your product are stored."
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.path",
"url":13,
"doc":"Usable path to the product, either extracted or archived path, according to the satellite."
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.is_archived",
"url":13,
"doc":"Is the archived product is processed (a products is considered as archived if its products path is a directory)."
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.needs_extraction",
"url":13,
"doc":"Does this products needs to be extracted to be processed ? ( True by default)."
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.date",
"url":13,
"doc":"Acquisition date."
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.datetime",
"url":13,
"doc":"Acquisition datetime."
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.tile_name",
"url":13,
"doc":"Tile if possible (for data that can be piled, for example S2 and Landsats)."
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.sensor_type",
"url":13,
"doc":"Sensor type, SAR or optical."
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.product_type",
"url":13,
"doc":"Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.band_names",
"url":13,
"doc":"Band mapping between band wrapping names such as  GREEN and band real number such as  03 for Sentinel-2."
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.is_reference",
"url":13,
"doc":"If the product is a reference, used for algorithms that need pre and post data, such as fire detection."
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.corresponding_ref",
"url":13,
"doc":"The corresponding reference products to the current one (if the product is not a reference but has a reference data corresponding to it). A list because of multiple ref in case of non-stackable products (S3, S1 .)"
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.nodata",
"url":13,
"doc":"Product nodata, set to 0 by default. Please do not touch this or all index will fail."
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.platform",
"url":13,
"doc":"Product platform, such as Sentinel-2"
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.resolution",
"url":13,
"doc":"Default resolution in meters of the current product. For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles."
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.condensed_name",
"url":13,
"doc":"Condensed name, the filename with only useful data to keep the name unique (ie.  20191215T110441_S2_30TXP_L2A_122756 ). Used to shorten names and paths."
},
{
"ref":"eoreader.products.optical.s2_theia_product.S2TheiaProduct.sat_id",
"url":13,
"doc":"Satellite ID, i.e.  S2 for Sentinel-2"
},
{
"ref":"eoreader.products.optical.s3_product",
"url":22,
"doc":"Sentinel-3 products"
},
{
"ref":"eoreader.products.optical.s3_product.S3ProductType",
"url":22,
"doc":"Sentinel-3 products types (not exhaustive, only L1)"
},
{
"ref":"eoreader.products.optical.s3_product.S3ProductType.OLCI_EFR",
"url":22,
"doc":"OLCI EFR Product Type"
},
{
"ref":"eoreader.products.optical.s3_product.S3ProductType.SLSTR_RBT",
"url":22,
"doc":"SLSTR RBT Product Type"
},
{
"ref":"eoreader.products.optical.s3_product.S3Instrument",
"url":22,
"doc":"Sentinel-3 products types"
},
{
"ref":"eoreader.products.optical.s3_product.S3Instrument.OLCI",
"url":22,
"doc":"OLCI Instrument"
},
{
"ref":"eoreader.products.optical.s3_product.S3Instrument.SLSTR",
"url":22,
"doc":"SLSTR Instrument"
},
{
"ref":"eoreader.products.optical.s3_product.S3DataTypes",
"url":22,
"doc":"Sentinel-3 data types -> only considering useful ones"
},
{
"ref":"eoreader.products.optical.s3_product.S3DataTypes.EFR",
"url":22,
"doc":"EFR Data Type, for OLCI instrument"
},
{
"ref":"eoreader.products.optical.s3_product.S3DataTypes.RBT",
"url":22,
"doc":"RBT Data Type, for SLSTR instrument"
},
{
"ref":"eoreader.products.optical.s3_product.S3Product",
"url":22,
"doc":"Class of Sentinel-3 Products  Note : All S3-OLCI bands won't be used in EOReader !  Note : We only use NADIR rasters for S3-SLSTR bands"
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.get_datetime",
"url":22,
"doc":"Get the product's acquisition datetime, with format  YYYYMMDDTHHMMSS   %Y%m%dT%H%M%S   >>> from eoreader.reader import Reader >>> path = \"S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3\" >>> prod = Reader().open(path) >>> prod.get_datetime(as_datetime=True) datetime.datetime(2019, 11, 15, 23, 37, 22) >>> prod.get_datetime(as_datetime=False) '20191115T233722'   Args: as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string. Returns: Union[str, datetime.datetime]: Its acquisition datetime",
"func":1
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.get_band_paths",
"url":22,
"doc":"Return the paths of required bands.  WARNING If not existing, this function will orthorectify your bands !   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = \"S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3\" >>> prod = Reader().open(path) >>> prod.get_band_paths([GREEN, RED]) Executing processing graph  .11% .21% .31% .42% .52% .62% .73% .83% . done. {  : '20191115T233722_S3_SLSTR_RBT\\S1_reflectance.tif',  : '20191115T233722_S3_SLSTR_RBT\\S2_reflectance.tif', }   Args: band_list (list): List of the wanted bands resolution (float): Useless here Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.extent",
"url":22,
"doc":"Get UTM extent of the tile, managing the case with not orthorectified bands.   >>> from eoreader.reader import Reader >>> path = \"S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3\" >>> prod = Reader().open(path) >>> prod.utm_extent() geometry 0 POLYGON  1488846.028 6121896.451, 1488846.028 .   Returns: gpd.GeoDataFrame: Footprint in UTM",
"func":1
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.get_mean_sun_angles",
"url":22,
"doc":"Get Mean Sun angles (Azimuth and Zenith angles)   >>> from eoreader.reader import Reader >>> path = \"S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3\" >>> prod = Reader().open(path) >>> prod.get_mean_sun_angles() (78.55043955912154, 31.172127033319388)   Returns: (float, float): Mean Azimuth and Zenith angle",
"func":1
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.read_mtd",
"url":22,
"doc":"Read metadata and outputs the metadata XML root and its namespace   >>> from eoreader.reader import Reader >>> path = \"S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3\" >>> prod = Reader().open(path) >>> prod.read_mtd() ( ,  )   Returns: (etree._Element, str): Metadata XML root and its namespace",
"func":1
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.get_default_band",
"url":12,
"doc":"Get default band:  GREEN for optical data as every optical satellite has a GREEN band.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band()    Returns: str: Default band",
"func":1
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.get_default_band_path",
"url":12,
"doc":"Get default band ( GREEN for optical data) path.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band_path() 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2'   Returns: str: Default band path",
"func":1
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.crs",
"url":12,
"doc":"Get UTM projection of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_crs() CRS.from_epsg(32630)   Returns: rasterio.crs.CRS: CRS object",
"func":1
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.get_existing_bands",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_bands() [ ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ]   Returns: list: List of existing bands in the products",
"func":1
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.get_existing_band_paths",
"url":12,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_band_paths() {  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B01.jp2',  .,  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B12.jp2' }   Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.footprint",
"url":13,
"doc":"Get UTM footprint of the products (without nodata,  in french  emprise utile )   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.footprint() index geometry 0 0 POLYGON  199980.000 4500000.000, 199980.000 4 .   Returns: gpd.GeoDataFrame: Footprint as a GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.get_date",
"url":13,
"doc":"Get the product's acquisition date.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_date(as_date=True) datetime.datetime(2020, 8, 24, 0, 0) >>> prod.get_date(as_date=False) '20200824'   Args: as_date (bool): Return the date as a datetime.date. If false, returns a string. Returns: str: Its acquisition date",
"func":1
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.load",
"url":13,
"doc":"Open the bands and compute the wanted index. The bands will be purged of nodata and invalid pixels, the nodata will be set to 0 and the bands will be masked arrays in float. Bands that come out this function at the same time are collocated and therefore have the same shapes. This can be broken if you load data separately. Its is best to always load DEM data with some real bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> bands = prod.load([GREEN, NDVI], resolution=20) >>> bands  ' {  :  array( [0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0,  :  array( [0.0615 , 0.061625, 0.061 ,  ., 0.12085 , 0.120225, 0.113575], [0.061075, 0.06045 , 0.06025 ,  ., 0.114625, 0.119625, 0.117625], [0.06475 , 0.06145 , 0.060925,  ., 0.111475, 0.114925, 0.115175],  ., [0.1516 , 0.14195 , 0.1391 ,  ., 0.159975, 0.14145 , 0.127075], [0.140325, 0.125975, 0.131875,  ., 0.18245 , 0.1565 , 0.13015 ], [0.133475, 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675, 0.16405  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0 }  '   Args: bands (Union[list, BandNames, Callable]): Band list resolution (float): Resolution of the band, in meters size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided. Returns: dict: {band_name, band xarray}",
"func":1
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.has_band",
"url":13,
"doc":"Does this products has the specified band ? By band, we mean: - satellite band - index - DEM band - cloud band   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.has_band(GREEN) True >>> prod.has_band(TIR_2) False >>> prod.has_band(NDVI) True >>> prod.has_band(SHADOWS) False >>> prod.has_band(HILLSHADE) True   Args: band (Union[obn, sbn]): Optical or SAR band Returns: bool: True if the products has the specified band",
"func":1
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.output",
"url":13,
"doc":"Output directory of the product, to write orthorectified data for example."
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.stack",
"url":13,
"doc":"Stack bands and index of a products.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> stack = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  In meters >>> stack  '  array( [ 0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [ 0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [ 2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [ 1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [ 1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [ 1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ,  0.27066118, 0.23466069, 0.18792598,  ., -0.4611526 , -0.49751845, -0.4865216 ], [ 0.22425456, 0.28004232, 0.27851456,  ., -0.5032771 , -0.501796 , -0.502669 ], [-0.07466951, 0.06360884, 0.1207174 ,  ., -0.50617427, -0.50219285, -0.5034222 ], [-0.47076276, -0.4705828 , -0.4747971 ,  ., -0.32138503, -0.36619243, -0.37428448], [-0.4826967 , -0.5032287 , -0.48544118,  ., -0.278925 , -0.31404778, -0.36052078], [-0.488381 , -0.48253912, -0.4697526 ,  ., -0.38105175, -0.30813277, -0.27739233 ,  0.0615 , 0.061625 , 0.061 ,  ., 0.12085 , 0.120225 , 0.113575 ], [ 0.061075 , 0.06045 , 0.06025 ,  ., 0.114625 , 0.119625 , 0.117625 ], [ 0.06475 , 0.06145 , 0.060925 ,  ., 0.111475 , 0.114925 , 0.115175 ],  ., [ 0.1516 , 0.14195 , 0.1391 ,  ., 0.159975 , 0.14145 , 0.127075 ], [ 0.140325 , 0.125975 , 0.131875 ,  ., 0.18245 , 0.1565 , 0.13015 ], [ 0.133475 , 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675 , 0.16405  ], dtype=float32) Coordinates:  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0  z (z) MultiIndex - variable (z) object 'NDVI' 'MNDWI' 'GREEN' - band (z) int64 1 1 1 Attributes: long_name: ['NDVI', 'MNDWI', 'GREEN']  '   Args: bands (list): Bands and index combination resolution (float): Stack resolution. . If not specified, use the product resolution. stack_path (str): Stack path save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000) Returns: xr.DataArray: Stack as a DataArray",
"func":1
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.name",
"url":13,
"doc":"Product name (its filename without any extension)."
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.split_name",
"url":13,
"doc":"Split name, to retrieve every information from its filename (dates, tile, product type .)."
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.archive_path",
"url":13,
"doc":"Archive path, same as the product path if not specified. Useful when you want to know where both the extracted and archived version of your product are stored."
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.path",
"url":13,
"doc":"Usable path to the product, either extracted or archived path, according to the satellite."
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.is_archived",
"url":13,
"doc":"Is the archived product is processed (a products is considered as archived if its products path is a directory)."
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.needs_extraction",
"url":13,
"doc":"Does this products needs to be extracted to be processed ? ( True by default)."
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.date",
"url":13,
"doc":"Acquisition date."
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.datetime",
"url":13,
"doc":"Acquisition datetime."
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.tile_name",
"url":13,
"doc":"Tile if possible (for data that can be piled, for example S2 and Landsats)."
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.sensor_type",
"url":13,
"doc":"Sensor type, SAR or optical."
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.product_type",
"url":13,
"doc":"Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.band_names",
"url":13,
"doc":"Band mapping between band wrapping names such as  GREEN and band real number such as  03 for Sentinel-2."
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.is_reference",
"url":13,
"doc":"If the product is a reference, used for algorithms that need pre and post data, such as fire detection."
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.corresponding_ref",
"url":13,
"doc":"The corresponding reference products to the current one (if the product is not a reference but has a reference data corresponding to it). A list because of multiple ref in case of non-stackable products (S3, S1 .)"
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.nodata",
"url":13,
"doc":"Product nodata, set to 0 by default. Please do not touch this or all index will fail."
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.platform",
"url":13,
"doc":"Product platform, such as Sentinel-2"
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.resolution",
"url":13,
"doc":"Default resolution in meters of the current product. For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles."
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.condensed_name",
"url":13,
"doc":"Condensed name, the filename with only useful data to keep the name unique (ie.  20191215T110441_S2_30TXP_L2A_122756 ). Used to shorten names and paths."
},
{
"ref":"eoreader.products.optical.s3_product.S3Product.sat_id",
"url":13,
"doc":"Satellite ID, i.e.  S2 for Sentinel-2"
},
{
"ref":"eoreader.products.product",
"url":13,
"doc":"Product, superclass of all EOReader satellites products"
},
{
"ref":"eoreader.products.product.path_or_dst",
"url":13,
"doc":"Path or dataset decorator: allows a function to ingest a path or a rasterio dataset   >>>  Create mock function >>> @path_or_dst >>> def fct(dst): >>> read(dst) >>> >>>  Test the two ways >>> read1 = fct(\"path\\to\\raster.tif\") >>> with rasterio.open(\"path\\to\\raster.tif\") as dst: >>> read2 = fct(dst) >>> >>>  Test >>> read1  read2 True   Args: method (Callable): Function to decorate Returns: Callable: decorated function",
"func":1
},
{
"ref":"eoreader.products.product.SensorType",
"url":13,
"doc":"Sensor type of the products, optical or SAR"
},
{
"ref":"eoreader.products.product.SensorType.OPTICAL",
"url":13,
"doc":"For optical data"
},
{
"ref":"eoreader.products.product.SensorType.SAR",
"url":13,
"doc":"For SAR data"
},
{
"ref":"eoreader.products.product.Product",
"url":13,
"doc":"Super class of EOReader Products"
},
{
"ref":"eoreader.products.product.Product.footprint",
"url":13,
"doc":"Get UTM footprint of the products (without nodata,  in french  emprise utile )   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.footprint() index geometry 0 0 POLYGON  199980.000 4500000.000, 199980.000 4 .   Returns: gpd.GeoDataFrame: Footprint as a GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.product.Product.extent",
"url":13,
"doc":"Get UTM extent of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_extent() geometry 0 POLYGON  309780.000 4390200.000, 309780.000 4 .   Returns: gpd.GeoDataFrame: Footprint in UTM",
"func":1
},
{
"ref":"eoreader.products.product.Product.crs",
"url":13,
"doc":"Get UTM projection of the tile   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.utm_crs() CRS.from_epsg(32630)   Returns: crs.CRS: CRS object",
"func":1
},
{
"ref":"eoreader.products.product.Product.get_datetime",
"url":13,
"doc":"Get the product's acquisition datetime, with format  YYYYMMDDTHHMMSS   %Y%m%dT%H%M%S   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_datetime(as_datetime=True) datetime.datetime(2020, 8, 24, 11, 6, 31) >>> prod.get_datetime(as_datetime=False) '20200824T110631'   Args: as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string. Returns: Union[str, datetime.datetime]: Its acquisition datetime",
"func":1
},
{
"ref":"eoreader.products.product.Product.get_date",
"url":13,
"doc":"Get the product's acquisition date.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_date(as_date=True) datetime.datetime(2020, 8, 24, 0, 0) >>> prod.get_date(as_date=False) '20200824'   Args: as_date (bool): Return the date as a datetime.date. If false, returns a string. Returns: str: Its acquisition date",
"func":1
},
{
"ref":"eoreader.products.product.Product.get_default_band_path",
"url":13,
"doc":"Get default band path (among the existing ones). Usually  GREEN band for optical data and the first existing one between  VV and  HH for SAR data.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band_path() 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2'   Returns: str: Default band path",
"func":1
},
{
"ref":"eoreader.products.product.Product.get_default_band",
"url":13,
"doc":"Get default band: Usually  GREEN band for optical data and the first existing one between  VV and  HH for SAR data.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band()    Returns: str: Default band",
"func":1
},
{
"ref":"eoreader.products.product.Product.get_existing_bands",
"url":13,
"doc":"Return the existing bands.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_bands() [ ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ,  ]   Returns: list: List of existing bands in the products",
"func":1
},
{
"ref":"eoreader.products.product.Product.get_existing_band_paths",
"url":13,
"doc":"Return the existing band paths.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_band_paths() {  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B01.jp2',  .,  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B12.jp2' }   Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.product.Product.get_band_paths",
"url":13,
"doc":"Return the paths of required bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_band_paths([GREEN, RED]) {  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B03.jp2',  : 'zip+file: S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip!/S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE/GRANULE/L1C_T30TTK_A027018_20200824T111345/IMG_DATA/T30TTK_20200824T110631_B04.jp2' }   Args: band_list (list): List of the wanted bands resolution (float): Band resolution Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.product.Product.read_mtd",
"url":13,
"doc":"Read metadata and outputs the metadata XML root and its namespace most of the time, except from L8-collection 1 data which outputs a pandas DataFrame   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.read_mtd() ( ,  )   Returns: Any: Metadata XML root and its namespace or pd.DataFrame",
"func":1
},
{
"ref":"eoreader.products.product.Product.load",
"url":13,
"doc":"Open the bands and compute the wanted index. The bands will be purged of nodata and invalid pixels, the nodata will be set to 0 and the bands will be masked arrays in float. Bands that come out this function at the same time are collocated and therefore have the same shapes. This can be broken if you load data separately. Its is best to always load DEM data with some real bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> bands = prod.load([GREEN, NDVI], resolution=20) >>> bands  ' {  :  array( [0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0,  :  array( [0.0615 , 0.061625, 0.061 ,  ., 0.12085 , 0.120225, 0.113575], [0.061075, 0.06045 , 0.06025 ,  ., 0.114625, 0.119625, 0.117625], [0.06475 , 0.06145 , 0.060925,  ., 0.111475, 0.114925, 0.115175],  ., [0.1516 , 0.14195 , 0.1391 ,  ., 0.159975, 0.14145 , 0.127075], [0.140325, 0.125975, 0.131875,  ., 0.18245 , 0.1565 , 0.13015 ], [0.133475, 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675, 0.16405  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0 }  '   Args: bands (Union[list, BandNames, Callable]): Band list resolution (float): Resolution of the band, in meters size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided. Returns: dict: {band_name, band xarray}",
"func":1
},
{
"ref":"eoreader.products.product.Product.has_band",
"url":13,
"doc":"Does this products has the specified band ? By band, we mean: - satellite band - index - DEM band - cloud band   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.has_band(GREEN) True >>> prod.has_band(TIR_2) False >>> prod.has_band(NDVI) True >>> prod.has_band(SHADOWS) False >>> prod.has_band(HILLSHADE) True   Args: band (Union[obn, sbn]): Optical or SAR band Returns: bool: True if the products has the specified band",
"func":1
},
{
"ref":"eoreader.products.product.Product.output",
"url":13,
"doc":"Output directory of the product, to write orthorectified data for example."
},
{
"ref":"eoreader.products.product.Product.stack",
"url":13,
"doc":"Stack bands and index of a products.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> stack = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  In meters >>> stack  '  array( [ 0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [ 0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [ 2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [ 1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [ 1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [ 1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ,  0.27066118, 0.23466069, 0.18792598,  ., -0.4611526 , -0.49751845, -0.4865216 ], [ 0.22425456, 0.28004232, 0.27851456,  ., -0.5032771 , -0.501796 , -0.502669 ], [-0.07466951, 0.06360884, 0.1207174 ,  ., -0.50617427, -0.50219285, -0.5034222 ], [-0.47076276, -0.4705828 , -0.4747971 ,  ., -0.32138503, -0.36619243, -0.37428448], [-0.4826967 , -0.5032287 , -0.48544118,  ., -0.278925 , -0.31404778, -0.36052078], [-0.488381 , -0.48253912, -0.4697526 ,  ., -0.38105175, -0.30813277, -0.27739233 ,  0.0615 , 0.061625 , 0.061 ,  ., 0.12085 , 0.120225 , 0.113575 ], [ 0.061075 , 0.06045 , 0.06025 ,  ., 0.114625 , 0.119625 , 0.117625 ], [ 0.06475 , 0.06145 , 0.060925 ,  ., 0.111475 , 0.114925 , 0.115175 ],  ., [ 0.1516 , 0.14195 , 0.1391 ,  ., 0.159975 , 0.14145 , 0.127075 ], [ 0.140325 , 0.125975 , 0.131875 ,  ., 0.18245 , 0.1565 , 0.13015 ], [ 0.133475 , 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675 , 0.16405  ], dtype=float32) Coordinates:  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0  z (z) MultiIndex - variable (z) object 'NDVI' 'MNDWI' 'GREEN' - band (z) int64 1 1 1 Attributes: long_name: ['NDVI', 'MNDWI', 'GREEN']  '   Args: bands (list): Bands and index combination resolution (float): Stack resolution. . If not specified, use the product resolution. stack_path (str): Stack path save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000) Returns: xr.DataArray: Stack as a DataArray",
"func":1
},
{
"ref":"eoreader.products.product.Product.name",
"url":13,
"doc":"Product name (its filename without any extension)."
},
{
"ref":"eoreader.products.product.Product.split_name",
"url":13,
"doc":"Split name, to retrieve every information from its filename (dates, tile, product type .)."
},
{
"ref":"eoreader.products.product.Product.archive_path",
"url":13,
"doc":"Archive path, same as the product path if not specified. Useful when you want to know where both the extracted and archived version of your product are stored."
},
{
"ref":"eoreader.products.product.Product.path",
"url":13,
"doc":"Usable path to the product, either extracted or archived path, according to the satellite."
},
{
"ref":"eoreader.products.product.Product.is_archived",
"url":13,
"doc":"Is the archived product is processed (a products is considered as archived if its products path is a directory)."
},
{
"ref":"eoreader.products.product.Product.needs_extraction",
"url":13,
"doc":"Does this products needs to be extracted to be processed ? ( True by default)."
},
{
"ref":"eoreader.products.product.Product.date",
"url":13,
"doc":"Acquisition date."
},
{
"ref":"eoreader.products.product.Product.datetime",
"url":13,
"doc":"Acquisition datetime."
},
{
"ref":"eoreader.products.product.Product.tile_name",
"url":13,
"doc":"Tile if possible (for data that can be piled, for example S2 and Landsats)."
},
{
"ref":"eoreader.products.product.Product.sensor_type",
"url":13,
"doc":"Sensor type, SAR or optical."
},
{
"ref":"eoreader.products.product.Product.product_type",
"url":13,
"doc":"Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."
},
{
"ref":"eoreader.products.product.Product.band_names",
"url":13,
"doc":"Band mapping between band wrapping names such as  GREEN and band real number such as  03 for Sentinel-2."
},
{
"ref":"eoreader.products.product.Product.is_reference",
"url":13,
"doc":"If the product is a reference, used for algorithms that need pre and post data, such as fire detection."
},
{
"ref":"eoreader.products.product.Product.corresponding_ref",
"url":13,
"doc":"The corresponding reference products to the current one (if the product is not a reference but has a reference data corresponding to it). A list because of multiple ref in case of non-stackable products (S3, S1 .)"
},
{
"ref":"eoreader.products.product.Product.nodata",
"url":13,
"doc":"Product nodata, set to 0 by default. Please do not touch this or all index will fail."
},
{
"ref":"eoreader.products.product.Product.platform",
"url":13,
"doc":"Product platform, such as Sentinel-2"
},
{
"ref":"eoreader.products.product.Product.resolution",
"url":13,
"doc":"Default resolution in meters of the current product. For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles."
},
{
"ref":"eoreader.products.product.Product.condensed_name",
"url":13,
"doc":"Condensed name, the filename with only useful data to keep the name unique (ie.  20191215T110441_S2_30TXP_L2A_122756 ). Used to shorten names and paths."
},
{
"ref":"eoreader.products.product.Product.sat_id",
"url":13,
"doc":"Satellite ID, i.e.  S2 for Sentinel-2"
},
{
"ref":"eoreader.products.sar",
"url":23,
"doc":"SAR products.  SAR data  Implemented SAR satellites |Satellites | Class | Product Types | Use archive| | - |  - |  - |  -| |Sentinel-1 |  eoreader.products.sar.s1_product.S1Product | SLC & GRD | Yes| |COSMO-Skymed |  eoreader.products.sar.csk_product.CskProduct | DGM & SCS, (others should also be OK) | No| |TerraSAR-X |  eoreader.products.sar.tsx_product.TsxProduct | MGD (SSC should be OK) | No| |RADARSAT-2 |  eoreader.products.sar.rs2_product.Rs2Product | SGF (SLC should be OK) | Yes|  WARNING Satellites products that cannot be used as archived have to be extracted before use.  SAR Bands According to what contains the products, allowed SAR bands are: -  VV ( eoreader.bands.bands.SarBandNames.VV ) -  VH ( eoreader.bands.bands.SarBandNames.VH ) -  HH ( eoreader.bands.bands.SarBandNames.HH ) -  HV ( eoreader.bands.bands.SarBandNames.HV ) You also can load despeckled bands: -  VV_DSPK ( eoreader.bands.bands.SarBandNames.VV_DSPK ) -  VH_DSPK ( eoreader.bands.bands.SarBandNames.VH_DSPK ) -  HH_DSPK ( eoreader.bands.bands.SarBandNames.HH_DSPK ) -  HV_DSPK ( eoreader.bands.bands.SarBandNames.HV_DSPK )  DEM bands These bands need a valid worldwide DEM path positioned thanks to the environment variable  EOREADER_SAR_DEFAULT_RES -  DEM -  SLOPE See [here]() for more information. SAR satellites can only load  eoreader.bands.bands.DemBandNames.DEM and  eoreader.bands.bands.DemBandNames.SLOPE bands as the sun position does not impact SAR data. The  SLOPE band is computed with the [ gdaldem ](https: gdal.org/programs/gdaldem.html) tool. These bands need a valid worldwide DEM path positioned thanks to the environment variable  EOREADER_SAR_DEFAULT_RES .  Default resolution The default resolution of SAR products depends on their type. Complex data are  always converted back to ground range to be used. The product resolution is read in the metadata file if possible, so the following values are given as hints:  Sentinel-1 |  Sentinel-1 | Single Look Complex (SLC) |Ground Range Detected (GRD) Full Resolution (FR) | Ground Range Detected (GRD) High Resolution (HR) | Ground Range Detected (GRD) Medium Resolution (MR)| | - |  - |  - |  - |  -| |StripMap (SM) | 1.5x3.6 m to 3.1x4.1 m | 3.5m | 10.0m | 40.0m| |Interferometric Wide swath (IW) | 2.3x14.1 m | | 10.0m | 40.0m| |Extra-Wide swath (EW) | 5.9x19.9 m | | 25.0m | 40.0m| |Wave (WV) | 1.7x4.1 m and 2.7x4.1 m | | | 25.0m|  COSMO-Skymed |  COSMO-Skymed | Single-look Complex Slant (SCS) | Detected Ground Multi-look (DGM) Geocoded Ellipsoid Corrected (GEC) Geocoded Terrain Corrected (GTC)| | - |  - |  -| | Spotlight  Mode-2 (S2) | 1.1-0.9x0.91m | 1.0m| | StripMap  Himage (HI) | 3.0-2.6x2.4-2.6m | 5.0m| | StripMap  PingPong (PP) | 11-10x9.7m | 20.0m| | ScanSAR  Wide Region (WR) | 13.5x23m | 30.0m| | ScanSAR  Huge Region (HR) | 13.5x38.0m | 100.0m|  TerraSAR-X | TerraSAR-X | Single-look Slant Range (SSC) | Multi Look Ground Range (MGD) Geocoded Ellipsoid Corrected (GEC) Enhanced Ellipsoid Corrected (EEC) Spatially enhanced  (high resolution, SE)| Multi Look Ground Range (MGD) Geocoded Ellipsoid Corrected (GEC) Enhanced Ellipsoid Corrected (EEC) Radiometrically enhanced (high radiometry, RE)| | - |  - |  - |  -| | StripMap (SM)  Single-Pol | 0.9x2.0m | 1.5m or 1.25m | 4.0m or 3.25m| | StripMap (SM)  Dual-Pol | 0.9x2.5m | 3.0m | 5.5m or 4.5m| | High Resolution Spotlight (HS)  Single-Pol | 0.9x0.8m | 1.5m or 0.5m | 2.0m or 1.5m| | High Resolution Spotlight (HS)  Dual-Pol | 0.9x1.5m | 1.5m or 1.0m | 3.0m or 2.0m| | Spotlight (SL)  Single-Pol | 0.9x1.3m | 1.5m or 0.75m | 3.0m or 1.75m| | Spotlight (SL)  Dual-Pol | 0.9x2.6m | 3.5m or 3.4m | 8.5m or 5.5m| | Staring Spotlight (ST)  Single-Pol | 0.5x0.2m | 0.4m or 0.2m | 0.8m or 0.4m| | ScanSAR (SC)  Four Beams | 0.9x13m | | 8.25m| | ScanSAR (SC)  Six Beams | 1.4x?m | | 15.0m|  RADARSAT-2 | RADARSAT-2 | Single-look complex (SLC) | SAR georeferenced extra(SGX) | SAR georeferenced fine (SGF) | SAR systematic geocorrected (SSG) | SAR precision geocorrected (SPG) | ScanSAR narrow beam (SCN) | ScanSAR wide beam (SCW) | ScanSAR fine (SCF) | ScanSAR sampled (SCS)| | - |  - |  - |  - |  - |  - |  - |  - |  - |  -| |Spotlight | 1.3x0.4m | 1.0 or 0.8x1/3m | 0.5m | 0.5m | 0.5m | | | | | |Ultra-Fine | 1.3x2.1m | 1.0x1.0 or 0.8x0.8m | 1.56m | 1.56m | 1.56m | | | | | |Wide Ultra-Fine | 1.3x2.1m | 1.0m | 1.56m | 1.56m | 1.56m | | | | | |Multi-Look Fine | 2.7x2.9m | 3.13m | 6.25m | 6.25m | 6.25m | | | | | |Wide Multi-Look Fine | 2.7x2.9m | 3.13m | 6.25m | 6.25m | 6.25m | | | | | |Extra-Fine | Full Res: 2.7x2.9m Fine Res: 4.3x5.8m Full Res: 7.1x5.8m Wide Res: 10.6x5.8m | 1 look: 2.0m 4 looks: 3.13m 28 looks: 5.0m | 1 look: 3.13m 4 looks: 6.25m 28 looks: 8.0m | 3.13m | 3.13m | | | | | |Fine | 4.7x5.1m | 3.13m | 6.25m | 6.25m | 6.25m | | | | | |Wide-Fine | 4.7x5.1m | 3.13m | 6.25m | 6.25m | 6.25m | | | | | |Standard | 8.0 or 11.8x5.1m | 8.0m | 12.5m | 12.5m | 12.5m | | | | | |Wide | 11.8x5.1m | 10.0m | 12.5m | 12.5m | 12.5m | | | | | |Extended High | 11.8x5.1m | 8.0m | 12.5m | 12.5m | 12.5m | | | | | |Extended Low | 8.0x5.1m | 10.0m | 12.5m | 12.5m | 12.5m | | | | | |Fine Quad-Pol | 4.7x5.1m | 3.13m | 3.13m | 3.13m | 3.13m | | | | | |Wide Quad-Pol | 4.7x5.1m | 3.13m | 3.13m | 3.13m | 3.13m | | | | | |Standard Quad-Pol | 8.0 or 11.8x5.1m | 8.0x3.13m | 8.0x3.13m | 8.0x3.13m | 8.0x3.13m | | | | | |Wide Standard Quad-Pol | 8.0 or 11.8x5.1m | 8.0x3.13m | 8.0x3.13m | 8.0x3.13m | 8.0x3.13m | | | | | |ScanSAR Narrow | | | | | | 25.0m | | 25.0m | 25.0m| |ScanSAR Wide | | | | | | | 50.0m | 50.0m | 50.0m| |Ship (Detection of vessels) | | | | | | | | 40.0m | 20.0m| |Ocean Surveillance | | | | | | | | 50.0m | 35.0x25.0m|  GPT graphs You can change the SAR GPT graphs used by setting the following environment variables: -  EOREADER_PP_GRAPH : Environment variables for pre-processing graph path. -  EOREADER_DSPK_GRAPH : Environment variables for despeckling graph path  WARNING For performance reasons, the  Terrain Correction step is done  before the  Despeckle step. Indeed this step is very time-consuming and better done one time on the raw image than two times on both the raw and the despeckled image. Even if this is not the regular way of handling SAR data, this shouldn't really affect the quality of any extraction done after that.  What to know if you are changing a graph Those graphs should have a reader and a writer on this model:     1.0   Read    $file     Write      $out  BEAM-DIMAP       WARNING Pay attention to set  $file and  $out and leave the  BEAM-DIMAP file format. The first graph must orthorectify your SAR data, but should not despeckle it. The second graph is precisely charged to do it. The pre-processing graph should also have a  Terrain Correction step with the following wildcards that are set automatically in the module: -  $res_m : Resolution in meters -  $res_deg : Resolution in degrees -  $crs : CRS - The nodata value should  always be set to 0. The default  Terrain Correction step is:     Terrain-Correction       GETASSE30   0.0  true  BILINEAR_INTERPOLATION  BILINEAR_INTERPOLATION  $res_m  $res_deg  $crs  false  0.0  0.0  true  false  false  false  false  false  true  false  false  false  false  false  Use projected local incidence angle from DEM  Use projected local incidence angle from DEM  Latest Auxiliary File       Default SNAP resolution You can override default SNAP resolution (in meters) when geocoding SAR bands by setting the following environment variable: -  EOREADER_SAR_DEFAULT_RES (0.0 by default, which means using the product's default resolution)  Documentary Sources  SAR data  Sentinel-1 - [Data Products](https: earth.esa.int/web/sentinel/missions/sentinel-1/data-products) - [Acquisition Mode](https: earth.esa.int/web/sentinel/user-guides/sentinel-1-sar/acquisition-modes)  Others - [COSMO-Skymed Product Description](https: earth.esa.int/documents/10174/465595/COSMO-SkyMed-Mission-Products-Description) - [TerraSAR-X Product Description](https: tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf) - [RADARSAT-2 Product Description](https: www.pcigeomatics.com/geomatica-help/references/gdb_r/RADARSAT-2.html)"
},
{
"ref":"eoreader.products.sar.csk_product",
"url":24,
"doc":"COSMO-SkyMed products. More info [here](https: earth.esa.int/documents/10174/465595/COSMO-SkyMed-Mission-Products-Description)."
},
{
"ref":"eoreader.products.sar.csk_product.CskProductType",
"url":24,
"doc":"COSMO-SkyMed products types. Take a look [here](https: earth.esa.int/documents/10174/465595/COSMO-SkyMed-Mission-Products-Description)."
},
{
"ref":"eoreader.products.sar.csk_product.CskProductType.RAW",
"url":24,
"doc":"Level 0"
},
{
"ref":"eoreader.products.sar.csk_product.CskProductType.SCS",
"url":24,
"doc":"Level 1A, Single-look Complex Slant, (un)balanced"
},
{
"ref":"eoreader.products.sar.csk_product.CskProductType.DGM",
"url":24,
"doc":"Level 1B, Detected Ground Multi-look"
},
{
"ref":"eoreader.products.sar.csk_product.CskProductType.GEC",
"url":24,
"doc":"Level 1C, Geocoded Ellipsoid Corrected"
},
{
"ref":"eoreader.products.sar.csk_product.CskProductType.GTC",
"url":24,
"doc":"Level 1D, Geocoded Terrain Corrected"
},
{
"ref":"eoreader.products.sar.csk_product.CskSensorMode",
"url":24,
"doc":"COSMO-SkyMed sensor mode. Take a look [here](https: earth.esa.int/documents/10174/465595/COSMO-SkyMed-Mission-Products-Description)"
},
{
"ref":"eoreader.products.sar.csk_product.CskSensorMode.HI",
"url":24,
"doc":"Himage"
},
{
"ref":"eoreader.products.sar.csk_product.CskSensorMode.PP",
"url":24,
"doc":"PingPong"
},
{
"ref":"eoreader.products.sar.csk_product.CskSensorMode.WR",
"url":24,
"doc":"Wide Region"
},
{
"ref":"eoreader.products.sar.csk_product.CskSensorMode.HR",
"url":24,
"doc":"Huge Region"
},
{
"ref":"eoreader.products.sar.csk_product.CskSensorMode.S2",
"url":24,
"doc":"Spotlight 2"
},
{
"ref":"eoreader.products.sar.csk_product.CskPolarization",
"url":24,
"doc":"COSMO-SkyMed polarizations used during the acquisition. Take a look [here](https: earth.esa.int/documents/10174/465595/COSMO-SkyMed-Mission-Products-Description)."
},
{
"ref":"eoreader.products.sar.csk_product.CskPolarization.HH",
"url":24,
"doc":"Horizontal Tx/Horizontal Rx for Himage, ScanSAR and Spotlight modes"
},
{
"ref":"eoreader.products.sar.csk_product.CskPolarization.VV",
"url":24,
"doc":"Vertical Tx/Vertical Rx for Himage, ScanSAR and Spotlight modes"
},
{
"ref":"eoreader.products.sar.csk_product.CskPolarization.HV",
"url":24,
"doc":"Horizontal Tx/Vertical Rx for Himage, ScanSAR"
},
{
"ref":"eoreader.products.sar.csk_product.CskPolarization.VH",
"url":24,
"doc":"Vertical Tx/Horizontal Rx for Himage, ScanSAR"
},
{
"ref":"eoreader.products.sar.csk_product.CskPolarization.CO",
"url":24,
"doc":"Co-polar acquisition (HH/VV) for PingPong mode"
},
{
"ref":"eoreader.products.sar.csk_product.CskPolarization.CH",
"url":24,
"doc":"Cross polar acquisition (HH/HV) with Horizontal Tx polarization for PingPong mode"
},
{
"ref":"eoreader.products.sar.csk_product.CskPolarization.CV",
"url":24,
"doc":"Cross polar acquisition (VV/VH) with Vertical Tx polarization for PingPong mode"
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct",
"url":24,
"doc":"Class for COSMO-SkyMed Products   >>> from eoreader.reader import Reader >>>  CSK products could have any folder but needs to have a .h5 file correctly formatted >>>  ie. \"CSKS1_SCS_B_HI_15_HH_RA_SF_20201028224625_20201028224632.h5\" >>> path = r\"1011117-766193\" >>> prod = Reader().open(path)  "
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.wgs84_extent",
"url":24,
"doc":"Get the WGS84 extent of the file before any reprojection. This is useful when the SAR pre-process has not been done yet.   >>> from eoreader.reader import Reader >>> path = r\"1011117-766193\" >>> prod = Reader().open(path) >>> prod.wgs84_extent() geometry 0 POLYGON  108.09797 15.61011, 108.48224 15.678 .   Returns: gpd.GeoDataFrame: WGS84 extent as a gpd.GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.get_datetime",
"url":24,
"doc":"Get the product's acquisition datetime, with format  YYYYMMDDTHHMMSS   %Y%m%dT%H%M%S   >>> from eoreader.reader import Reader >>> path = r\"1011117-766193\" >>> prod = Reader().open(path) >>> prod.get_datetime(as_datetime=True) datetime.datetime(2020, 10, 28, 22, 46, 25) >>> prod.get_datetime(as_datetime=False) '20201028T224625'   Args: as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string. Returns: Union[str, datetime.datetime]: Its acquisition datetime",
"func":1
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.read_mtd",
"url":24,
"doc":"Read metadata and outputs the metadata XML root and its namespace   >>> from eoreader.reader import Reader >>> path = r\"1001513-735093\" >>> prod = Reader().open(path) >>> prod.read_mtd() ( ,  )   Returns: (etree._Element, str): Metadata XML root and its namespace",
"func":1
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.get_default_band",
"url":25,
"doc":"Get default band: The first existing one between  VV and  HH for SAR data.   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band()    Returns: str: Default band",
"func":1
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.get_default_band_path",
"url":25,
"doc":"Get default band path (the first existing one between  VV and  HH for SAR data), ready to use (orthorectified)  WARNING This functions orthorectifies SAR bands if not existing !   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band_path() Executing processing graph   10%  20%  30%  40%  50%  60%  70%  80%  90% done. '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif'   Returns: str: Default band path",
"func":1
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.extent",
"url":25,
"doc":"Get UTM extent of the tile   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.utm_extent() Name  . geometry 0 Sentinel-1 Image Overlay  . POLYGON  817914.501 4684349.823, 555708.624 4 . [1 rows x 12 columns]   Returns: gpd.GeoDataFrame: Footprint in UTM",
"func":1
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.crs",
"url":25,
"doc":"Get UTM projection   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.utm_crs() CRS.from_epsg(32630)   Returns: crs.CRS: CRS object",
"func":1
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.get_band_paths",
"url":25,
"doc":"Return the paths of required bands.  WARNING This functions orthorectifies SAR bands if not existing !   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_band_paths([VV, HH]) {  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif'  HH doesn't exist }   Args: band_list (list): List of the wanted bands resolution (float): Band resolution Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.get_existing_band_paths",
"url":25,
"doc":"Return the existing orthorectified band paths (including despeckle bands).  WARNING This functions orthorectifies SAR bands if not existing !  WARNING This functions despeckles SAR bands if not existing !   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_band_paths() Executing processing graph   10%  20%  30%  40%  50%  60%  70%  80%  90% done. Executing processing graph   10%  20%  30%  40%  50%  60%  70%  80%  90% done. {  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif',  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VH.tif',  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV_DSPK.tif',  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VH_DSPK.tif' }   Returns: dict: Dictionary containing the path of every orthorectified bands",
"func":1
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.get_existing_bands",
"url":25,
"doc":"Return the existing orthorectified bands (including despeckle bands).  WARNING This functions orthorectifies SAR bands if not existing !  WARNING This functions despeckles SAR bands if not existing !   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_bands() [ ,  ,  ,  ]   Returns: list: List of existing bands in the products",
"func":1
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.sar_prod_type",
"url":25,
"doc":"SAR product type, either Single Look Complex or Ground Range"
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.sensor_mode",
"url":25,
"doc":"Sensor Mode of the current product"
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.pol_channels",
"url":25,
"doc":"Polarization Channels stored in the current product"
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.footprint",
"url":13,
"doc":"Get UTM footprint of the products (without nodata,  in french  emprise utile )   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.footprint() index geometry 0 0 POLYGON  199980.000 4500000.000, 199980.000 4 .   Returns: gpd.GeoDataFrame: Footprint as a GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.get_date",
"url":13,
"doc":"Get the product's acquisition date.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_date(as_date=True) datetime.datetime(2020, 8, 24, 0, 0) >>> prod.get_date(as_date=False) '20200824'   Args: as_date (bool): Return the date as a datetime.date. If false, returns a string. Returns: str: Its acquisition date",
"func":1
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.load",
"url":13,
"doc":"Open the bands and compute the wanted index. The bands will be purged of nodata and invalid pixels, the nodata will be set to 0 and the bands will be masked arrays in float. Bands that come out this function at the same time are collocated and therefore have the same shapes. This can be broken if you load data separately. Its is best to always load DEM data with some real bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> bands = prod.load([GREEN, NDVI], resolution=20) >>> bands  ' {  :  array( [0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0,  :  array( [0.0615 , 0.061625, 0.061 ,  ., 0.12085 , 0.120225, 0.113575], [0.061075, 0.06045 , 0.06025 ,  ., 0.114625, 0.119625, 0.117625], [0.06475 , 0.06145 , 0.060925,  ., 0.111475, 0.114925, 0.115175],  ., [0.1516 , 0.14195 , 0.1391 ,  ., 0.159975, 0.14145 , 0.127075], [0.140325, 0.125975, 0.131875,  ., 0.18245 , 0.1565 , 0.13015 ], [0.133475, 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675, 0.16405  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0 }  '   Args: bands (Union[list, BandNames, Callable]): Band list resolution (float): Resolution of the band, in meters size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided. Returns: dict: {band_name, band xarray}",
"func":1
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.has_band",
"url":13,
"doc":"Does this products has the specified band ? By band, we mean: - satellite band - index - DEM band - cloud band   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.has_band(GREEN) True >>> prod.has_band(TIR_2) False >>> prod.has_band(NDVI) True >>> prod.has_band(SHADOWS) False >>> prod.has_band(HILLSHADE) True   Args: band (Union[obn, sbn]): Optical or SAR band Returns: bool: True if the products has the specified band",
"func":1
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.output",
"url":13,
"doc":"Output directory of the product, to write orthorectified data for example."
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.stack",
"url":13,
"doc":"Stack bands and index of a products.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> stack = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  In meters >>> stack  '  array( [ 0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [ 0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [ 2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [ 1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [ 1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [ 1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ,  0.27066118, 0.23466069, 0.18792598,  ., -0.4611526 , -0.49751845, -0.4865216 ], [ 0.22425456, 0.28004232, 0.27851456,  ., -0.5032771 , -0.501796 , -0.502669 ], [-0.07466951, 0.06360884, 0.1207174 ,  ., -0.50617427, -0.50219285, -0.5034222 ], [-0.47076276, -0.4705828 , -0.4747971 ,  ., -0.32138503, -0.36619243, -0.37428448], [-0.4826967 , -0.5032287 , -0.48544118,  ., -0.278925 , -0.31404778, -0.36052078], [-0.488381 , -0.48253912, -0.4697526 ,  ., -0.38105175, -0.30813277, -0.27739233 ,  0.0615 , 0.061625 , 0.061 ,  ., 0.12085 , 0.120225 , 0.113575 ], [ 0.061075 , 0.06045 , 0.06025 ,  ., 0.114625 , 0.119625 , 0.117625 ], [ 0.06475 , 0.06145 , 0.060925 ,  ., 0.111475 , 0.114925 , 0.115175 ],  ., [ 0.1516 , 0.14195 , 0.1391 ,  ., 0.159975 , 0.14145 , 0.127075 ], [ 0.140325 , 0.125975 , 0.131875 ,  ., 0.18245 , 0.1565 , 0.13015 ], [ 0.133475 , 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675 , 0.16405  ], dtype=float32) Coordinates:  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0  z (z) MultiIndex - variable (z) object 'NDVI' 'MNDWI' 'GREEN' - band (z) int64 1 1 1 Attributes: long_name: ['NDVI', 'MNDWI', 'GREEN']  '   Args: bands (list): Bands and index combination resolution (float): Stack resolution. . If not specified, use the product resolution. stack_path (str): Stack path save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000) Returns: xr.DataArray: Stack as a DataArray",
"func":1
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.name",
"url":13,
"doc":"Product name (its filename without any extension)."
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.split_name",
"url":13,
"doc":"Split name, to retrieve every information from its filename (dates, tile, product type .)."
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.archive_path",
"url":13,
"doc":"Archive path, same as the product path if not specified. Useful when you want to know where both the extracted and archived version of your product are stored."
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.path",
"url":13,
"doc":"Usable path to the product, either extracted or archived path, according to the satellite."
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.is_archived",
"url":13,
"doc":"Is the archived product is processed (a products is considered as archived if its products path is a directory)."
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.needs_extraction",
"url":13,
"doc":"Does this products needs to be extracted to be processed ? ( True by default)."
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.date",
"url":13,
"doc":"Acquisition date."
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.datetime",
"url":13,
"doc":"Acquisition datetime."
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.tile_name",
"url":13,
"doc":"Tile if possible (for data that can be piled, for example S2 and Landsats)."
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.sensor_type",
"url":13,
"doc":"Sensor type, SAR or optical."
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.product_type",
"url":13,
"doc":"Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.band_names",
"url":13,
"doc":"Band mapping between band wrapping names such as  GREEN and band real number such as  03 for Sentinel-2."
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.is_reference",
"url":13,
"doc":"If the product is a reference, used for algorithms that need pre and post data, such as fire detection."
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.corresponding_ref",
"url":13,
"doc":"The corresponding reference products to the current one (if the product is not a reference but has a reference data corresponding to it). A list because of multiple ref in case of non-stackable products (S3, S1 .)"
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.nodata",
"url":13,
"doc":"Product nodata, set to 0 by default. Please do not touch this or all index will fail."
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.platform",
"url":13,
"doc":"Product platform, such as Sentinel-2"
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.resolution",
"url":13,
"doc":"Default resolution in meters of the current product. For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles."
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.condensed_name",
"url":13,
"doc":"Condensed name, the filename with only useful data to keep the name unique (ie.  20191215T110441_S2_30TXP_L2A_122756 ). Used to shorten names and paths."
},
{
"ref":"eoreader.products.sar.csk_product.CskProduct.sat_id",
"url":13,
"doc":"Satellite ID, i.e.  S2 for Sentinel-2"
},
{
"ref":"eoreader.products.sar.rs2_product",
"url":26,
"doc":"RADARSAT-2 products. More info [here](https: www.pcigeomatics.com/geomatica-help/references/gdb_r/RADARSAT-2.html RADARSAT2__rs2_sfs)."
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2ProductType",
"url":26,
"doc":"RADARSAT-2 projection identifier. Take a look [here](https: www.pcigeomatics.com/geomatica-help/references/gdb_r/RADARSAT-2.html)"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2ProductType.SLC",
"url":26,
"doc":"Single-look complex"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2ProductType.SGX",
"url":26,
"doc":"SAR georeferenced extra"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2ProductType.SGF",
"url":26,
"doc":"SAR georeferenced fine"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2ProductType.SCN",
"url":26,
"doc":"ScanSAR narrow beam"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2ProductType.SCW",
"url":26,
"doc":"ScanSAR wide beam"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2ProductType.SCF",
"url":26,
"doc":"ScanSAR fine"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2ProductType.SCS",
"url":26,
"doc":"ScanSAR sampled"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2ProductType.SSG",
"url":26,
"doc":"SAR systematic geocorrected"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2ProductType.SPG",
"url":26,
"doc":"SAR precision geocorrected"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode",
"url":26,
"doc":"RADARSAT-2 sensor mode. Take a look [here](https: www.pcigeomatics.com/geomatica-help/references/gdb_r/RADARSAT-2.html)  WARNING The name in the metadata may vary !"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.S",
"url":26,
"doc":"Standard Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.W",
"url":26,
"doc":"Spotlight Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.F",
"url":26,
"doc":"Wide Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.WF",
"url":26,
"doc":"Wide Fine Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.MF",
"url":26,
"doc":"Multi-Look Fine Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.WMF",
"url":26,
"doc":"Wide Multi-Look Fine Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.XF",
"url":26,
"doc":"Extra-Fine Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.U",
"url":26,
"doc":"Ultra-Fine Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.WU",
"url":26,
"doc":"Wide Ultra-Fine Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.EH",
"url":26,
"doc":"Extended High Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.EL",
"url":26,
"doc":"Extended Low Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.SQ",
"url":26,
"doc":"Standard Quad-Pol Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.WSQ",
"url":26,
"doc":"Wide Standard Quad-Pol Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.FQ",
"url":26,
"doc":"Fine Quad-Pol Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.WFQ",
"url":26,
"doc":"Spotlight Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.SCN",
"url":26,
"doc":"Spotlight Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.SCW",
"url":26,
"doc":"Spotlight Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.OSVN",
"url":26,
"doc":"Ocean Surveillance Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.DVWF",
"url":26,
"doc":"Ship Detection Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2SensorMode.SLA",
"url":26,
"doc":"Spotlight Mode"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Polarization",
"url":26,
"doc":"RADARSAT-2 polarization mode. Take a look [here](https: www.pcigeomatics.com/geomatica-help/references/gdb_r/RADARSAT-2.html RADARSAT2__rs2_sfs)"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Polarization.HH",
"url":26,
"doc":""
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Polarization.VV",
"url":26,
"doc":""
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Polarization.VH",
"url":26,
"doc":""
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Polarization.HV",
"url":26,
"doc":""
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product",
"url":26,
"doc":"Class for RADARSAT-2 Products You can use directly the .zip file"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.wgs84_extent",
"url":26,
"doc":"Get the WGS84 extent of the file before any reprojection. This is useful when the SAR pre-process has not been done yet.   >>> from eoreader.reader import Reader >>> path = r\"RS2_OK73950_PK661843_DK590667_U25W2_20160228_112418_HH_SGF.zip\" >>> prod = Reader().open(path) >>> prod.wgs84_extent() geometry 1 POLYGON  106.57999 -6.47363, 107.06926 -6.473 .   Returns: gpd.GeoDataFrame: WGS84 extent as a gpd.GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.get_datetime",
"url":26,
"doc":"Get the product's acquisition datetime, with format  YYYYMMDDTHHMMSS   %Y%m%dT%H%M%S   >>> from eoreader.reader import Reader >>> path = r\"RS2_OK73950_PK661843_DK590667_U25W2_20160228_112418_HH_SGF.zip\" >>> prod = Reader().open(path) >>> prod.get_datetime(as_datetime=True) datetime.datetime(2016, 2, 28, 11, 24, 18) >>> prod.get_datetime(as_datetime=False) '20160228T112418'   Args: as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string. Returns: Union[str, datetime.datetime]: Its acquisition datetime",
"func":1
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.read_mtd",
"url":26,
"doc":"Read metadata and outputs the metadata XML root and its namespace   >>> from eoreader.reader import Reader >>> path = r\"LC08_L1GT_023030_20200518_20200527_01_T2\" >>> prod = Reader().open(path) >>> prod.read_mtd() ( , '{http: www.rsi.ca/rs2/prod/xml/schemas}')   Returns: (etree._Element, str): Metadata XML root and its namespace",
"func":1
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.get_default_band",
"url":25,
"doc":"Get default band: The first existing one between  VV and  HH for SAR data.   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band()    Returns: str: Default band",
"func":1
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.get_default_band_path",
"url":25,
"doc":"Get default band path (the first existing one between  VV and  HH for SAR data), ready to use (orthorectified)  WARNING This functions orthorectifies SAR bands if not existing !   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band_path() Executing processing graph   10%  20%  30%  40%  50%  60%  70%  80%  90% done. '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif'   Returns: str: Default band path",
"func":1
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.extent",
"url":25,
"doc":"Get UTM extent of the tile   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.utm_extent() Name  . geometry 0 Sentinel-1 Image Overlay  . POLYGON  817914.501 4684349.823, 555708.624 4 . [1 rows x 12 columns]   Returns: gpd.GeoDataFrame: Footprint in UTM",
"func":1
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.crs",
"url":25,
"doc":"Get UTM projection   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.utm_crs() CRS.from_epsg(32630)   Returns: crs.CRS: CRS object",
"func":1
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.get_band_paths",
"url":25,
"doc":"Return the paths of required bands.  WARNING This functions orthorectifies SAR bands if not existing !   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_band_paths([VV, HH]) {  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif'  HH doesn't exist }   Args: band_list (list): List of the wanted bands resolution (float): Band resolution Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.get_existing_band_paths",
"url":25,
"doc":"Return the existing orthorectified band paths (including despeckle bands).  WARNING This functions orthorectifies SAR bands if not existing !  WARNING This functions despeckles SAR bands if not existing !   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_band_paths() Executing processing graph   10%  20%  30%  40%  50%  60%  70%  80%  90% done. Executing processing graph   10%  20%  30%  40%  50%  60%  70%  80%  90% done. {  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif',  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VH.tif',  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV_DSPK.tif',  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VH_DSPK.tif' }   Returns: dict: Dictionary containing the path of every orthorectified bands",
"func":1
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.get_existing_bands",
"url":25,
"doc":"Return the existing orthorectified bands (including despeckle bands).  WARNING This functions orthorectifies SAR bands if not existing !  WARNING This functions despeckles SAR bands if not existing !   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_bands() [ ,  ,  ,  ]   Returns: list: List of existing bands in the products",
"func":1
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.sar_prod_type",
"url":25,
"doc":"SAR product type, either Single Look Complex or Ground Range"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.sensor_mode",
"url":25,
"doc":"Sensor Mode of the current product"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.pol_channels",
"url":25,
"doc":"Polarization Channels stored in the current product"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.footprint",
"url":13,
"doc":"Get UTM footprint of the products (without nodata,  in french  emprise utile )   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.footprint() index geometry 0 0 POLYGON  199980.000 4500000.000, 199980.000 4 .   Returns: gpd.GeoDataFrame: Footprint as a GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.get_date",
"url":13,
"doc":"Get the product's acquisition date.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_date(as_date=True) datetime.datetime(2020, 8, 24, 0, 0) >>> prod.get_date(as_date=False) '20200824'   Args: as_date (bool): Return the date as a datetime.date. If false, returns a string. Returns: str: Its acquisition date",
"func":1
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.load",
"url":13,
"doc":"Open the bands and compute the wanted index. The bands will be purged of nodata and invalid pixels, the nodata will be set to 0 and the bands will be masked arrays in float. Bands that come out this function at the same time are collocated and therefore have the same shapes. This can be broken if you load data separately. Its is best to always load DEM data with some real bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> bands = prod.load([GREEN, NDVI], resolution=20) >>> bands  ' {  :  array( [0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0,  :  array( [0.0615 , 0.061625, 0.061 ,  ., 0.12085 , 0.120225, 0.113575], [0.061075, 0.06045 , 0.06025 ,  ., 0.114625, 0.119625, 0.117625], [0.06475 , 0.06145 , 0.060925,  ., 0.111475, 0.114925, 0.115175],  ., [0.1516 , 0.14195 , 0.1391 ,  ., 0.159975, 0.14145 , 0.127075], [0.140325, 0.125975, 0.131875,  ., 0.18245 , 0.1565 , 0.13015 ], [0.133475, 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675, 0.16405  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0 }  '   Args: bands (Union[list, BandNames, Callable]): Band list resolution (float): Resolution of the band, in meters size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided. Returns: dict: {band_name, band xarray}",
"func":1
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.has_band",
"url":13,
"doc":"Does this products has the specified band ? By band, we mean: - satellite band - index - DEM band - cloud band   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.has_band(GREEN) True >>> prod.has_band(TIR_2) False >>> prod.has_band(NDVI) True >>> prod.has_band(SHADOWS) False >>> prod.has_band(HILLSHADE) True   Args: band (Union[obn, sbn]): Optical or SAR band Returns: bool: True if the products has the specified band",
"func":1
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.output",
"url":13,
"doc":"Output directory of the product, to write orthorectified data for example."
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.stack",
"url":13,
"doc":"Stack bands and index of a products.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> stack = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  In meters >>> stack  '  array( [ 0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [ 0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [ 2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [ 1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [ 1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [ 1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ,  0.27066118, 0.23466069, 0.18792598,  ., -0.4611526 , -0.49751845, -0.4865216 ], [ 0.22425456, 0.28004232, 0.27851456,  ., -0.5032771 , -0.501796 , -0.502669 ], [-0.07466951, 0.06360884, 0.1207174 ,  ., -0.50617427, -0.50219285, -0.5034222 ], [-0.47076276, -0.4705828 , -0.4747971 ,  ., -0.32138503, -0.36619243, -0.37428448], [-0.4826967 , -0.5032287 , -0.48544118,  ., -0.278925 , -0.31404778, -0.36052078], [-0.488381 , -0.48253912, -0.4697526 ,  ., -0.38105175, -0.30813277, -0.27739233 ,  0.0615 , 0.061625 , 0.061 ,  ., 0.12085 , 0.120225 , 0.113575 ], [ 0.061075 , 0.06045 , 0.06025 ,  ., 0.114625 , 0.119625 , 0.117625 ], [ 0.06475 , 0.06145 , 0.060925 ,  ., 0.111475 , 0.114925 , 0.115175 ],  ., [ 0.1516 , 0.14195 , 0.1391 ,  ., 0.159975 , 0.14145 , 0.127075 ], [ 0.140325 , 0.125975 , 0.131875 ,  ., 0.18245 , 0.1565 , 0.13015 ], [ 0.133475 , 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675 , 0.16405  ], dtype=float32) Coordinates:  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0  z (z) MultiIndex - variable (z) object 'NDVI' 'MNDWI' 'GREEN' - band (z) int64 1 1 1 Attributes: long_name: ['NDVI', 'MNDWI', 'GREEN']  '   Args: bands (list): Bands and index combination resolution (float): Stack resolution. . If not specified, use the product resolution. stack_path (str): Stack path save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000) Returns: xr.DataArray: Stack as a DataArray",
"func":1
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.name",
"url":13,
"doc":"Product name (its filename without any extension)."
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.split_name",
"url":13,
"doc":"Split name, to retrieve every information from its filename (dates, tile, product type .)."
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.archive_path",
"url":13,
"doc":"Archive path, same as the product path if not specified. Useful when you want to know where both the extracted and archived version of your product are stored."
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.path",
"url":13,
"doc":"Usable path to the product, either extracted or archived path, according to the satellite."
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.is_archived",
"url":13,
"doc":"Is the archived product is processed (a products is considered as archived if its products path is a directory)."
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.needs_extraction",
"url":13,
"doc":"Does this products needs to be extracted to be processed ? ( True by default)."
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.date",
"url":13,
"doc":"Acquisition date."
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.datetime",
"url":13,
"doc":"Acquisition datetime."
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.tile_name",
"url":13,
"doc":"Tile if possible (for data that can be piled, for example S2 and Landsats)."
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.sensor_type",
"url":13,
"doc":"Sensor type, SAR or optical."
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.product_type",
"url":13,
"doc":"Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.band_names",
"url":13,
"doc":"Band mapping between band wrapping names such as  GREEN and band real number such as  03 for Sentinel-2."
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.is_reference",
"url":13,
"doc":"If the product is a reference, used for algorithms that need pre and post data, such as fire detection."
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.corresponding_ref",
"url":13,
"doc":"The corresponding reference products to the current one (if the product is not a reference but has a reference data corresponding to it). A list because of multiple ref in case of non-stackable products (S3, S1 .)"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.nodata",
"url":13,
"doc":"Product nodata, set to 0 by default. Please do not touch this or all index will fail."
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.platform",
"url":13,
"doc":"Product platform, such as Sentinel-2"
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.resolution",
"url":13,
"doc":"Default resolution in meters of the current product. For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles."
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.condensed_name",
"url":13,
"doc":"Condensed name, the filename with only useful data to keep the name unique (ie.  20191215T110441_S2_30TXP_L2A_122756 ). Used to shorten names and paths."
},
{
"ref":"eoreader.products.sar.rs2_product.Rs2Product.sat_id",
"url":13,
"doc":"Satellite ID, i.e.  S2 for Sentinel-2"
},
{
"ref":"eoreader.products.sar.s1_product",
"url":27,
"doc":"Sentinel-1 products"
},
{
"ref":"eoreader.products.sar.s1_product.S1ProductType",
"url":27,
"doc":"S1 products types. Take a look here: https: earth.esa.int/web/sentinel/missions/sentinel-1/data-products"
},
{
"ref":"eoreader.products.sar.s1_product.S1ProductType.RAW",
"url":27,
"doc":"Raw products (lvl 0):  not used by EOReader "
},
{
"ref":"eoreader.products.sar.s1_product.S1ProductType.SLC",
"url":27,
"doc":"Single Look Complex (SLC, lvl 1)"
},
{
"ref":"eoreader.products.sar.s1_product.S1ProductType.GRD",
"url":27,
"doc":"Ground Range Detected (GRD, lvl 1, phase lost)"
},
{
"ref":"eoreader.products.sar.s1_product.S1ProductType.OCN",
"url":27,
"doc":"Ocean products (lvl 2):  not used by EOReader "
},
{
"ref":"eoreader.products.sar.s1_product.S1SensorMode",
"url":27,
"doc":"S1 sensor mode. Take a look here: https: earth.esa.int/web/sentinel/user-guides/sentinel-1-sar/acquisition-modes The primary conflict-free modes are IW, with VV+VH polarisation over land, and WV, with VV polarisation, over open ocean. EW mode is primarily used for wide area coastal monitoring including ship traffic, oil spill and sea-ice monitoring. SM mode is only used for small islands and on request for extraordinary events such as emergency management."
},
{
"ref":"eoreader.products.sar.s1_product.S1SensorMode.SM",
"url":27,
"doc":"Stripmap (SM)"
},
{
"ref":"eoreader.products.sar.s1_product.S1SensorMode.IW",
"url":27,
"doc":"Interferometric Wide swath (IW)"
},
{
"ref":"eoreader.products.sar.s1_product.S1SensorMode.EW",
"url":27,
"doc":"Extra-Wide swath (EW)"
},
{
"ref":"eoreader.products.sar.s1_product.S1SensorMode.WV",
"url":27,
"doc":"Wave (WV) -> single polarisation only (HH or VV)"
},
{
"ref":"eoreader.products.sar.s1_product.S1Product",
"url":27,
"doc":"Class for Sentinel-1 Products You can use directly the .zip file"
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.wgs84_extent",
"url":27,
"doc":"Get the WGS84 extent of the file before any reprojection. This is useful when the SAR pre-process has not been done yet.   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.wgs84_extent() Name  . geometry 0 Sentinel-1 Image Overlay  . POLYGON  0.85336 42.24660, -2.32032 42.65493, . [1 rows x 12 columns]   Returns: gpd.GeoDataFrame: WGS84 extent as a gpd.GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.get_datetime",
"url":27,
"doc":"Get the product's acquisition datetime, with format  YYYYMMDDTHHMMSS   %Y%m%dT%H%M%S   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_datetime(as_datetime=True) datetime.datetime(2019, 12, 15, 6, 9, 6) >>> prod.get_datetime(as_datetime=False) '20191215T060906'   Args: as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string. Returns: Union[str, datetime.datetime]: Its acquisition datetime",
"func":1
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.read_mtd",
"url":27,
"doc":"Read metadata and outputs the metadata XML root and its namespace   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.read_mtd() ( ,  )   Returns: (etree._Element, str): Metadata XML root and its namespace",
"func":1
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.get_default_band",
"url":25,
"doc":"Get default band: The first existing one between  VV and  HH for SAR data.   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band()    Returns: str: Default band",
"func":1
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.get_default_band_path",
"url":25,
"doc":"Get default band path (the first existing one between  VV and  HH for SAR data), ready to use (orthorectified)  WARNING This functions orthorectifies SAR bands if not existing !   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band_path() Executing processing graph   10%  20%  30%  40%  50%  60%  70%  80%  90% done. '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif'   Returns: str: Default band path",
"func":1
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.extent",
"url":25,
"doc":"Get UTM extent of the tile   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.utm_extent() Name  . geometry 0 Sentinel-1 Image Overlay  . POLYGON  817914.501 4684349.823, 555708.624 4 . [1 rows x 12 columns]   Returns: gpd.GeoDataFrame: Footprint in UTM",
"func":1
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.crs",
"url":25,
"doc":"Get UTM projection   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.utm_crs() CRS.from_epsg(32630)   Returns: crs.CRS: CRS object",
"func":1
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.get_band_paths",
"url":25,
"doc":"Return the paths of required bands.  WARNING This functions orthorectifies SAR bands if not existing !   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_band_paths([VV, HH]) {  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif'  HH doesn't exist }   Args: band_list (list): List of the wanted bands resolution (float): Band resolution Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.get_existing_band_paths",
"url":25,
"doc":"Return the existing orthorectified band paths (including despeckle bands).  WARNING This functions orthorectifies SAR bands if not existing !  WARNING This functions despeckles SAR bands if not existing !   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_band_paths() Executing processing graph   10%  20%  30%  40%  50%  60%  70%  80%  90% done. Executing processing graph   10%  20%  30%  40%  50%  60%  70%  80%  90% done. {  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif',  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VH.tif',  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV_DSPK.tif',  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VH_DSPK.tif' }   Returns: dict: Dictionary containing the path of every orthorectified bands",
"func":1
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.get_existing_bands",
"url":25,
"doc":"Return the existing orthorectified bands (including despeckle bands).  WARNING This functions orthorectifies SAR bands if not existing !  WARNING This functions despeckles SAR bands if not existing !   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_bands() [ ,  ,  ,  ]   Returns: list: List of existing bands in the products",
"func":1
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.sar_prod_type",
"url":25,
"doc":"SAR product type, either Single Look Complex or Ground Range"
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.sensor_mode",
"url":25,
"doc":"Sensor Mode of the current product"
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.pol_channels",
"url":25,
"doc":"Polarization Channels stored in the current product"
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.footprint",
"url":13,
"doc":"Get UTM footprint of the products (without nodata,  in french  emprise utile )   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.footprint() index geometry 0 0 POLYGON  199980.000 4500000.000, 199980.000 4 .   Returns: gpd.GeoDataFrame: Footprint as a GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.get_date",
"url":13,
"doc":"Get the product's acquisition date.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_date(as_date=True) datetime.datetime(2020, 8, 24, 0, 0) >>> prod.get_date(as_date=False) '20200824'   Args: as_date (bool): Return the date as a datetime.date. If false, returns a string. Returns: str: Its acquisition date",
"func":1
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.load",
"url":13,
"doc":"Open the bands and compute the wanted index. The bands will be purged of nodata and invalid pixels, the nodata will be set to 0 and the bands will be masked arrays in float. Bands that come out this function at the same time are collocated and therefore have the same shapes. This can be broken if you load data separately. Its is best to always load DEM data with some real bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> bands = prod.load([GREEN, NDVI], resolution=20) >>> bands  ' {  :  array( [0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0,  :  array( [0.0615 , 0.061625, 0.061 ,  ., 0.12085 , 0.120225, 0.113575], [0.061075, 0.06045 , 0.06025 ,  ., 0.114625, 0.119625, 0.117625], [0.06475 , 0.06145 , 0.060925,  ., 0.111475, 0.114925, 0.115175],  ., [0.1516 , 0.14195 , 0.1391 ,  ., 0.159975, 0.14145 , 0.127075], [0.140325, 0.125975, 0.131875,  ., 0.18245 , 0.1565 , 0.13015 ], [0.133475, 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675, 0.16405  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0 }  '   Args: bands (Union[list, BandNames, Callable]): Band list resolution (float): Resolution of the band, in meters size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided. Returns: dict: {band_name, band xarray}",
"func":1
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.has_band",
"url":13,
"doc":"Does this products has the specified band ? By band, we mean: - satellite band - index - DEM band - cloud band   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.has_band(GREEN) True >>> prod.has_band(TIR_2) False >>> prod.has_band(NDVI) True >>> prod.has_band(SHADOWS) False >>> prod.has_band(HILLSHADE) True   Args: band (Union[obn, sbn]): Optical or SAR band Returns: bool: True if the products has the specified band",
"func":1
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.output",
"url":13,
"doc":"Output directory of the product, to write orthorectified data for example."
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.stack",
"url":13,
"doc":"Stack bands and index of a products.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> stack = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  In meters >>> stack  '  array( [ 0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [ 0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [ 2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [ 1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [ 1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [ 1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ,  0.27066118, 0.23466069, 0.18792598,  ., -0.4611526 , -0.49751845, -0.4865216 ], [ 0.22425456, 0.28004232, 0.27851456,  ., -0.5032771 , -0.501796 , -0.502669 ], [-0.07466951, 0.06360884, 0.1207174 ,  ., -0.50617427, -0.50219285, -0.5034222 ], [-0.47076276, -0.4705828 , -0.4747971 ,  ., -0.32138503, -0.36619243, -0.37428448], [-0.4826967 , -0.5032287 , -0.48544118,  ., -0.278925 , -0.31404778, -0.36052078], [-0.488381 , -0.48253912, -0.4697526 ,  ., -0.38105175, -0.30813277, -0.27739233 ,  0.0615 , 0.061625 , 0.061 ,  ., 0.12085 , 0.120225 , 0.113575 ], [ 0.061075 , 0.06045 , 0.06025 ,  ., 0.114625 , 0.119625 , 0.117625 ], [ 0.06475 , 0.06145 , 0.060925 ,  ., 0.111475 , 0.114925 , 0.115175 ],  ., [ 0.1516 , 0.14195 , 0.1391 ,  ., 0.159975 , 0.14145 , 0.127075 ], [ 0.140325 , 0.125975 , 0.131875 ,  ., 0.18245 , 0.1565 , 0.13015 ], [ 0.133475 , 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675 , 0.16405  ], dtype=float32) Coordinates:  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0  z (z) MultiIndex - variable (z) object 'NDVI' 'MNDWI' 'GREEN' - band (z) int64 1 1 1 Attributes: long_name: ['NDVI', 'MNDWI', 'GREEN']  '   Args: bands (list): Bands and index combination resolution (float): Stack resolution. . If not specified, use the product resolution. stack_path (str): Stack path save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000) Returns: xr.DataArray: Stack as a DataArray",
"func":1
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.name",
"url":13,
"doc":"Product name (its filename without any extension)."
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.split_name",
"url":13,
"doc":"Split name, to retrieve every information from its filename (dates, tile, product type .)."
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.archive_path",
"url":13,
"doc":"Archive path, same as the product path if not specified. Useful when you want to know where both the extracted and archived version of your product are stored."
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.path",
"url":13,
"doc":"Usable path to the product, either extracted or archived path, according to the satellite."
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.is_archived",
"url":13,
"doc":"Is the archived product is processed (a products is considered as archived if its products path is a directory)."
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.needs_extraction",
"url":13,
"doc":"Does this products needs to be extracted to be processed ? ( True by default)."
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.date",
"url":13,
"doc":"Acquisition date."
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.datetime",
"url":13,
"doc":"Acquisition datetime."
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.tile_name",
"url":13,
"doc":"Tile if possible (for data that can be piled, for example S2 and Landsats)."
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.sensor_type",
"url":13,
"doc":"Sensor type, SAR or optical."
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.product_type",
"url":13,
"doc":"Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.band_names",
"url":13,
"doc":"Band mapping between band wrapping names such as  GREEN and band real number such as  03 for Sentinel-2."
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.is_reference",
"url":13,
"doc":"If the product is a reference, used for algorithms that need pre and post data, such as fire detection."
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.corresponding_ref",
"url":13,
"doc":"The corresponding reference products to the current one (if the product is not a reference but has a reference data corresponding to it). A list because of multiple ref in case of non-stackable products (S3, S1 .)"
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.nodata",
"url":13,
"doc":"Product nodata, set to 0 by default. Please do not touch this or all index will fail."
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.platform",
"url":13,
"doc":"Product platform, such as Sentinel-2"
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.resolution",
"url":13,
"doc":"Default resolution in meters of the current product. For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles."
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.condensed_name",
"url":13,
"doc":"Condensed name, the filename with only useful data to keep the name unique (ie.  20191215T110441_S2_30TXP_L2A_122756 ). Used to shorten names and paths."
},
{
"ref":"eoreader.products.sar.s1_product.S1Product.sat_id",
"url":13,
"doc":"Satellite ID, i.e.  S2 for Sentinel-2"
},
{
"ref":"eoreader.products.sar.sar_product",
"url":25,
"doc":"Super class for SAR products"
},
{
"ref":"eoreader.products.sar.sar_product.SarProductType",
"url":25,
"doc":"Generic products types, used to chose a SNAP graph."
},
{
"ref":"eoreader.products.sar.sar_product.SarProductType.CPLX",
"url":25,
"doc":"Single Look Complex"
},
{
"ref":"eoreader.products.sar.sar_product.SarProductType.GDRG",
"url":25,
"doc":"Ground Range"
},
{
"ref":"eoreader.products.sar.sar_product.SarProductType.OTHER",
"url":25,
"doc":"Other products types, no used in EOReader"
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct",
"url":25,
"doc":"Super class for SAR Products"
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.get_default_band",
"url":25,
"doc":"Get default band: The first existing one between  VV and  HH for SAR data.   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band()    Returns: str: Default band",
"func":1
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.get_default_band_path",
"url":25,
"doc":"Get default band path (the first existing one between  VV and  HH for SAR data), ready to use (orthorectified)  WARNING This functions orthorectifies SAR bands if not existing !   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band_path() Executing processing graph   10%  20%  30%  40%  50%  60%  70%  80%  90% done. '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif'   Returns: str: Default band path",
"func":1
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.wgs84_extent",
"url":25,
"doc":"Get the WGS84 extent of the file before any reprojection. This is useful when the SAR pre-process has not been done yet.   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.wgs84_extent() Name  . geometry 0 Sentinel-1 Image Overlay  . POLYGON  0.85336 42.24660, -2.32032 42.65493, . [1 rows x 12 columns]   Returns: gpd.GeoDataFrame: WGS84 extent as a gpd.GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.extent",
"url":25,
"doc":"Get UTM extent of the tile   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.utm_extent() Name  . geometry 0 Sentinel-1 Image Overlay  . POLYGON  817914.501 4684349.823, 555708.624 4 . [1 rows x 12 columns]   Returns: gpd.GeoDataFrame: Footprint in UTM",
"func":1
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.crs",
"url":25,
"doc":"Get UTM projection   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.utm_crs() CRS.from_epsg(32630)   Returns: crs.CRS: CRS object",
"func":1
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.get_band_paths",
"url":25,
"doc":"Return the paths of required bands.  WARNING This functions orthorectifies SAR bands if not existing !   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_band_paths([VV, HH]) {  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif'  HH doesn't exist }   Args: band_list (list): List of the wanted bands resolution (float): Band resolution Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.get_existing_band_paths",
"url":25,
"doc":"Return the existing orthorectified band paths (including despeckle bands).  WARNING This functions orthorectifies SAR bands if not existing !  WARNING This functions despeckles SAR bands if not existing !   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_band_paths() Executing processing graph   10%  20%  30%  40%  50%  60%  70%  80%  90% done. Executing processing graph   10%  20%  30%  40%  50%  60%  70%  80%  90% done. {  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif',  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VH.tif',  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV_DSPK.tif',  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VH_DSPK.tif' }   Returns: dict: Dictionary containing the path of every orthorectified bands",
"func":1
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.get_existing_bands",
"url":25,
"doc":"Return the existing orthorectified bands (including despeckle bands).  WARNING This functions orthorectifies SAR bands if not existing !  WARNING This functions despeckles SAR bands if not existing !   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_bands() [ ,  ,  ,  ]   Returns: list: List of existing bands in the products",
"func":1
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.sar_prod_type",
"url":25,
"doc":"SAR product type, either Single Look Complex or Ground Range"
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.sensor_mode",
"url":25,
"doc":"Sensor Mode of the current product"
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.pol_channels",
"url":25,
"doc":"Polarization Channels stored in the current product"
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.footprint",
"url":13,
"doc":"Get UTM footprint of the products (without nodata,  in french  emprise utile )   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.footprint() index geometry 0 0 POLYGON  199980.000 4500000.000, 199980.000 4 .   Returns: gpd.GeoDataFrame: Footprint as a GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.get_datetime",
"url":13,
"doc":"Get the product's acquisition datetime, with format  YYYYMMDDTHHMMSS   %Y%m%dT%H%M%S   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_datetime(as_datetime=True) datetime.datetime(2020, 8, 24, 11, 6, 31) >>> prod.get_datetime(as_datetime=False) '20200824T110631'   Args: as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string. Returns: Union[str, datetime.datetime]: Its acquisition datetime",
"func":1
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.get_date",
"url":13,
"doc":"Get the product's acquisition date.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_date(as_date=True) datetime.datetime(2020, 8, 24, 0, 0) >>> prod.get_date(as_date=False) '20200824'   Args: as_date (bool): Return the date as a datetime.date. If false, returns a string. Returns: str: Its acquisition date",
"func":1
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.read_mtd",
"url":13,
"doc":"Read metadata and outputs the metadata XML root and its namespace most of the time, except from L8-collection 1 data which outputs a pandas DataFrame   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.read_mtd() ( ,  )   Returns: Any: Metadata XML root and its namespace or pd.DataFrame",
"func":1
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.load",
"url":13,
"doc":"Open the bands and compute the wanted index. The bands will be purged of nodata and invalid pixels, the nodata will be set to 0 and the bands will be masked arrays in float. Bands that come out this function at the same time are collocated and therefore have the same shapes. This can be broken if you load data separately. Its is best to always load DEM data with some real bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> bands = prod.load([GREEN, NDVI], resolution=20) >>> bands  ' {  :  array( [0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0,  :  array( [0.0615 , 0.061625, 0.061 ,  ., 0.12085 , 0.120225, 0.113575], [0.061075, 0.06045 , 0.06025 ,  ., 0.114625, 0.119625, 0.117625], [0.06475 , 0.06145 , 0.060925,  ., 0.111475, 0.114925, 0.115175],  ., [0.1516 , 0.14195 , 0.1391 ,  ., 0.159975, 0.14145 , 0.127075], [0.140325, 0.125975, 0.131875,  ., 0.18245 , 0.1565 , 0.13015 ], [0.133475, 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675, 0.16405  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0 }  '   Args: bands (Union[list, BandNames, Callable]): Band list resolution (float): Resolution of the band, in meters size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided. Returns: dict: {band_name, band xarray}",
"func":1
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.has_band",
"url":13,
"doc":"Does this products has the specified band ? By band, we mean: - satellite band - index - DEM band - cloud band   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.has_band(GREEN) True >>> prod.has_band(TIR_2) False >>> prod.has_band(NDVI) True >>> prod.has_band(SHADOWS) False >>> prod.has_band(HILLSHADE) True   Args: band (Union[obn, sbn]): Optical or SAR band Returns: bool: True if the products has the specified band",
"func":1
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.output",
"url":13,
"doc":"Output directory of the product, to write orthorectified data for example."
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.stack",
"url":13,
"doc":"Stack bands and index of a products.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> stack = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  In meters >>> stack  '  array( [ 0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [ 0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [ 2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [ 1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [ 1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [ 1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ,  0.27066118, 0.23466069, 0.18792598,  ., -0.4611526 , -0.49751845, -0.4865216 ], [ 0.22425456, 0.28004232, 0.27851456,  ., -0.5032771 , -0.501796 , -0.502669 ], [-0.07466951, 0.06360884, 0.1207174 ,  ., -0.50617427, -0.50219285, -0.5034222 ], [-0.47076276, -0.4705828 , -0.4747971 ,  ., -0.32138503, -0.36619243, -0.37428448], [-0.4826967 , -0.5032287 , -0.48544118,  ., -0.278925 , -0.31404778, -0.36052078], [-0.488381 , -0.48253912, -0.4697526 ,  ., -0.38105175, -0.30813277, -0.27739233 ,  0.0615 , 0.061625 , 0.061 ,  ., 0.12085 , 0.120225 , 0.113575 ], [ 0.061075 , 0.06045 , 0.06025 ,  ., 0.114625 , 0.119625 , 0.117625 ], [ 0.06475 , 0.06145 , 0.060925 ,  ., 0.111475 , 0.114925 , 0.115175 ],  ., [ 0.1516 , 0.14195 , 0.1391 ,  ., 0.159975 , 0.14145 , 0.127075 ], [ 0.140325 , 0.125975 , 0.131875 ,  ., 0.18245 , 0.1565 , 0.13015 ], [ 0.133475 , 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675 , 0.16405  ], dtype=float32) Coordinates:  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0  z (z) MultiIndex - variable (z) object 'NDVI' 'MNDWI' 'GREEN' - band (z) int64 1 1 1 Attributes: long_name: ['NDVI', 'MNDWI', 'GREEN']  '   Args: bands (list): Bands and index combination resolution (float): Stack resolution. . If not specified, use the product resolution. stack_path (str): Stack path save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000) Returns: xr.DataArray: Stack as a DataArray",
"func":1
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.name",
"url":13,
"doc":"Product name (its filename without any extension)."
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.split_name",
"url":13,
"doc":"Split name, to retrieve every information from its filename (dates, tile, product type .)."
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.archive_path",
"url":13,
"doc":"Archive path, same as the product path if not specified. Useful when you want to know where both the extracted and archived version of your product are stored."
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.path",
"url":13,
"doc":"Usable path to the product, either extracted or archived path, according to the satellite."
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.is_archived",
"url":13,
"doc":"Is the archived product is processed (a products is considered as archived if its products path is a directory)."
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.needs_extraction",
"url":13,
"doc":"Does this products needs to be extracted to be processed ? ( True by default)."
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.date",
"url":13,
"doc":"Acquisition date."
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.datetime",
"url":13,
"doc":"Acquisition datetime."
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.tile_name",
"url":13,
"doc":"Tile if possible (for data that can be piled, for example S2 and Landsats)."
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.sensor_type",
"url":13,
"doc":"Sensor type, SAR or optical."
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.product_type",
"url":13,
"doc":"Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.band_names",
"url":13,
"doc":"Band mapping between band wrapping names such as  GREEN and band real number such as  03 for Sentinel-2."
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.is_reference",
"url":13,
"doc":"If the product is a reference, used for algorithms that need pre and post data, such as fire detection."
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.corresponding_ref",
"url":13,
"doc":"The corresponding reference products to the current one (if the product is not a reference but has a reference data corresponding to it). A list because of multiple ref in case of non-stackable products (S3, S1 .)"
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.nodata",
"url":13,
"doc":"Product nodata, set to 0 by default. Please do not touch this or all index will fail."
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.platform",
"url":13,
"doc":"Product platform, such as Sentinel-2"
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.resolution",
"url":13,
"doc":"Default resolution in meters of the current product. For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles."
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.condensed_name",
"url":13,
"doc":"Condensed name, the filename with only useful data to keep the name unique (ie.  20191215T110441_S2_30TXP_L2A_122756 ). Used to shorten names and paths."
},
{
"ref":"eoreader.products.sar.sar_product.SarProduct.sat_id",
"url":13,
"doc":"Satellite ID, i.e.  S2 for Sentinel-2"
},
{
"ref":"eoreader.products.sar.tsx_product",
"url":28,
"doc":"TerraSAR-X products. More info [here](https: tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf)."
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProductType",
"url":28,
"doc":"TerraSAR-X projection identifier. Take a look [here](https: tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf)"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProductType.SSC",
"url":28,
"doc":"Single Look Slant Range, Complex representation"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProductType.MGD",
"url":28,
"doc":"Multi Look Ground Range, Detected representation"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProductType.GEC",
"url":28,
"doc":"Geocoded Ellipsoid Corrected, Detected representation"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProductType.EEC",
"url":28,
"doc":"Enhanced Ellipsoid Corrected, Detected representation"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxSensorMode",
"url":28,
"doc":"TerraSAR-X sensor mode. Take a look [here](https: tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf)"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxSensorMode.HS",
"url":28,
"doc":"High Resolution Spotlight"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxSensorMode.SL",
"url":28,
"doc":"Spotlight"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxSensorMode.ST",
"url":28,
"doc":"Staring Spotlight"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxSensorMode.SM",
"url":28,
"doc":"Stripmap"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxSensorMode.SC",
"url":28,
"doc":"ScanSAR"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxPolarization",
"url":28,
"doc":"TerraSAR-X polarization mode. Take a look [here](https: tandemx-science.dlr.de/pdfs/TX-GS-DD-3302_Basic-Products-Specification-Document_V1.9.pdf)"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxPolarization.SINGLE",
"url":28,
"doc":"\"Single Polarization"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxPolarization.DUAL",
"url":28,
"doc":"\"Dual Polarization"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxPolarization.QUAD",
"url":28,
"doc":"\"Quad Polarization"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxPolarization.TWIN",
"url":28,
"doc":"\"Twin Polarization"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct",
"url":28,
"doc":"Class for TerraSAR-X Products"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.wgs84_extent",
"url":28,
"doc":"Get the WGS84 extent of the file before any reprojection. This is useful when the SAR pre-process has not been done yet.   >>> from eoreader.reader import Reader >>> path = r\"TSX1_SAR__MGD_SE___SM_S_SRA_20160229T223018_20160229T223023\" >>> prod = Reader().open(path) >>> prod.wgs84_extent() geometry 0 POLYGON  106.65491 -6.39693, 106.96233 -6.396 .   Returns: gpd.GeoDataFrame: WGS84 extent as a gpd.GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.get_datetime",
"url":28,
"doc":"Get the product's acquisition datetime, with format  YYYYMMDDTHHMMSS   %Y%m%dT%H%M%S   >>> from eoreader.reader import Reader >>> path = r\"TSX1_SAR__MGD_SE___SM_S_SRA_20160229T223018_20160229T223023\" >>> prod = Reader().open(path) >>> prod.get_datetime(as_datetime=True) datetime.datetime(2016, 2, 29, 22, 30, 18) >>> prod.get_datetime(as_datetime=False) '20160229T223018'   Args: as_datetime (bool): Return the date as a datetime.datetime. If false, returns a string. Returns: Union[str, datetime.datetime]: Its acquisition datetime",
"func":1
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.read_mtd",
"url":28,
"doc":"Read metadata and outputs the metadata XML root and its namespace   >>> from eoreader.reader import Reader >>> path = r\"TSX1_SAR__MGD_SE___SM_S_SRA_20200605T042203_20200605T042211\" >>> prod = Reader().open(path) >>> prod.read_mtd() ( ,  )   Returns: (etree._Element, str): Metadata XML root and its namespace",
"func":1
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.get_default_band",
"url":25,
"doc":"Get default band: The first existing one between  VV and  HH for SAR data.   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band()    Returns: str: Default band",
"func":1
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.get_default_band_path",
"url":25,
"doc":"Get default band path (the first existing one between  VV and  HH for SAR data), ready to use (orthorectified)  WARNING This functions orthorectifies SAR bands if not existing !   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_default_band_path() Executing processing graph   10%  20%  30%  40%  50%  60%  70%  80%  90% done. '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif'   Returns: str: Default band path",
"func":1
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.extent",
"url":25,
"doc":"Get UTM extent of the tile   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.utm_extent() Name  . geometry 0 Sentinel-1 Image Overlay  . POLYGON  817914.501 4684349.823, 555708.624 4 . [1 rows x 12 columns]   Returns: gpd.GeoDataFrame: Footprint in UTM",
"func":1
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.crs",
"url":25,
"doc":"Get UTM projection   >>> from eoreader.reader import Reader >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.utm_crs() CRS.from_epsg(32630)   Returns: crs.CRS: CRS object",
"func":1
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.get_band_paths",
"url":25,
"doc":"Return the paths of required bands.  WARNING This functions orthorectifies SAR bands if not existing !   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_band_paths([VV, HH]) {  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif'  HH doesn't exist }   Args: band_list (list): List of the wanted bands resolution (float): Band resolution Returns: dict: Dictionary containing the path of each queried band",
"func":1
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.get_existing_band_paths",
"url":25,
"doc":"Return the existing orthorectified band paths (including despeckle bands).  WARNING This functions orthorectifies SAR bands if not existing !  WARNING This functions despeckles SAR bands if not existing !   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_band_paths() Executing processing graph   10%  20%  30%  40%  50%  60%  70%  80%  90% done. Executing processing graph   10%  20%  30%  40%  50%  60%  70%  80%  90% done. {  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV.tif',  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VH.tif',  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VV_DSPK.tif',  : '20191215T060906_S1_IW_GRD\\20191215T060906_S1_IW_GRD_VH_DSPK.tif' }   Returns: dict: Dictionary containing the path of every orthorectified bands",
"func":1
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.get_existing_bands",
"url":25,
"doc":"Return the existing orthorectified bands (including despeckle bands).  WARNING This functions orthorectifies SAR bands if not existing !  WARNING This functions despeckles SAR bands if not existing !   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip\" >>> prod = Reader().open(path) >>> prod.get_existing_bands() [ ,  ,  ,  ]   Returns: list: List of existing bands in the products",
"func":1
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.sar_prod_type",
"url":25,
"doc":"SAR product type, either Single Look Complex or Ground Range"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.sensor_mode",
"url":25,
"doc":"Sensor Mode of the current product"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.pol_channels",
"url":25,
"doc":"Polarization Channels stored in the current product"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.footprint",
"url":13,
"doc":"Get UTM footprint of the products (without nodata,  in french  emprise utile )   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.footprint() index geometry 0 0 POLYGON  199980.000 4500000.000, 199980.000 4 .   Returns: gpd.GeoDataFrame: Footprint as a GeoDataFrame",
"func":1
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.get_date",
"url":13,
"doc":"Get the product's acquisition date.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.get_date(as_date=True) datetime.datetime(2020, 8, 24, 0, 0) >>> prod.get_date(as_date=False) '20200824'   Args: as_date (bool): Return the date as a datetime.date. If false, returns a string. Returns: str: Its acquisition date",
"func":1
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.load",
"url":13,
"doc":"Open the bands and compute the wanted index. The bands will be purged of nodata and invalid pixels, the nodata will be set to 0 and the bands will be masked arrays in float. Bands that come out this function at the same time are collocated and therefore have the same shapes. This can be broken if you load data separately. Its is best to always load DEM data with some real bands.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> bands = prod.load([GREEN, NDVI], resolution=20) >>> bands  ' {  :  array( [0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0,  :  array( [0.0615 , 0.061625, 0.061 ,  ., 0.12085 , 0.120225, 0.113575], [0.061075, 0.06045 , 0.06025 ,  ., 0.114625, 0.119625, 0.117625], [0.06475 , 0.06145 , 0.060925,  ., 0.111475, 0.114925, 0.115175],  ., [0.1516 , 0.14195 , 0.1391 ,  ., 0.159975, 0.14145 , 0.127075], [0.140325, 0.125975, 0.131875,  ., 0.18245 , 0.1565 , 0.13015 ], [0.133475, 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675, 0.16405  ], dtype=float32) Coordinates:  band (band) int32 1  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0 }  '   Args: bands (Union[list, BandNames, Callable]): Band list resolution (float): Resolution of the band, in meters size (Union[tuple, list]): Size of the array (width, height). Not used if resolution is provided. Returns: dict: {band_name, band xarray}",
"func":1
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.has_band",
"url":13,
"doc":"Does this products has the specified band ? By band, we mean: - satellite band - index - DEM band - cloud band   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> prod.has_band(GREEN) True >>> prod.has_band(TIR_2) False >>> prod.has_band(NDVI) True >>> prod.has_band(SHADOWS) False >>> prod.has_band(HILLSHADE) True   Args: band (Union[obn, sbn]): Optical or SAR band Returns: bool: True if the products has the specified band",
"func":1
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.output",
"url":13,
"doc":"Output directory of the product, to write orthorectified data for example."
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.stack",
"url":13,
"doc":"Stack bands and index of a products.   >>> from eoreader.reader import Reader >>> from eoreader.bands.alias import  >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> prod = Reader().open(path) >>> stack = prod.stack([NDVI, MNDWI, GREEN], resolution=20)  In meters >>> stack  '  array( [ 0.949506 , 0.92181516, 0.9279379 ,  ., 1.8002278 , 1.5424857 , 1.6747767 ], [ 0.95369846, 0.91685396, 0.8957871 ,  ., 1.5847116 , 1.5248713 , 1.5011379 ], [ 2.9928885 , 1.3031474 , 1.0076253 ,  ., 1.5969834 , 1.5590671 , 1.5018653 ],  ., [ 1.4245619 , 1.6115025 , 1.6201663 ,  ., 1.2387121 , 1.4025431 , 1.800678 ], [ 1.5627214 , 1.822388 , 1.7245892 ,  ., 1.1694248 , 1.2573677 , 1.5767351 ], [ 1.653781 , 1.6424649 , 1.5923225 ,  ., 1.3072611 , 1.2181134 , 1.2478763  ,  0.27066118, 0.23466069, 0.18792598,  ., -0.4611526 , -0.49751845, -0.4865216 ], [ 0.22425456, 0.28004232, 0.27851456,  ., -0.5032771 , -0.501796 , -0.502669 ], [-0.07466951, 0.06360884, 0.1207174 ,  ., -0.50617427, -0.50219285, -0.5034222 ], [-0.47076276, -0.4705828 , -0.4747971 ,  ., -0.32138503, -0.36619243, -0.37428448], [-0.4826967 , -0.5032287 , -0.48544118,  ., -0.278925 , -0.31404778, -0.36052078], [-0.488381 , -0.48253912, -0.4697526 ,  ., -0.38105175, -0.30813277, -0.27739233 ,  0.0615 , 0.061625 , 0.061 ,  ., 0.12085 , 0.120225 , 0.113575 ], [ 0.061075 , 0.06045 , 0.06025 ,  ., 0.114625 , 0.119625 , 0.117625 ], [ 0.06475 , 0.06145 , 0.060925 ,  ., 0.111475 , 0.114925 , 0.115175 ],  ., [ 0.1516 , 0.14195 , 0.1391 ,  ., 0.159975 , 0.14145 , 0.127075 ], [ 0.140325 , 0.125975 , 0.131875 ,  ., 0.18245 , 0.1565 , 0.13015 ], [ 0.133475 , 0.1341 , 0.13345 ,  ., 0.15565 , 0.170675 , 0.16405  ], dtype=float32) Coordinates:  y (y) float64 4.5e+06 4.5e+06 4.5e+06  . 4.39e+06 4.39e+06  x (x) float64 2e+05 2e+05 2e+05  . 3.097e+05 3.098e+05 3.098e+05 spatial_ref int32 0  z (z) MultiIndex - variable (z) object 'NDVI' 'MNDWI' 'GREEN' - band (z) int64 1 1 1 Attributes: long_name: ['NDVI', 'MNDWI', 'GREEN']  '   Args: bands (list): Bands and index combination resolution (float): Stack resolution. . If not specified, use the product resolution. stack_path (str): Stack path save_as_int (bool): Save stack as integers (uint16 and therefore multiply the values by 10.000) Returns: xr.DataArray: Stack as a DataArray",
"func":1
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.name",
"url":13,
"doc":"Product name (its filename without any extension)."
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.split_name",
"url":13,
"doc":"Split name, to retrieve every information from its filename (dates, tile, product type .)."
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.archive_path",
"url":13,
"doc":"Archive path, same as the product path if not specified. Useful when you want to know where both the extracted and archived version of your product are stored."
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.path",
"url":13,
"doc":"Usable path to the product, either extracted or archived path, according to the satellite."
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.is_archived",
"url":13,
"doc":"Is the archived product is processed (a products is considered as archived if its products path is a directory)."
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.needs_extraction",
"url":13,
"doc":"Does this products needs to be extracted to be processed ? ( True by default)."
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.date",
"url":13,
"doc":"Acquisition date."
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.datetime",
"url":13,
"doc":"Acquisition datetime."
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.tile_name",
"url":13,
"doc":"Tile if possible (for data that can be piled, for example S2 and Landsats)."
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.sensor_type",
"url":13,
"doc":"Sensor type, SAR or optical."
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.product_type",
"url":13,
"doc":"Product type, satellite-related field, such as L1C or L2A for Sentinel-2 data."
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.band_names",
"url":13,
"doc":"Band mapping between band wrapping names such as  GREEN and band real number such as  03 for Sentinel-2."
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.is_reference",
"url":13,
"doc":"If the product is a reference, used for algorithms that need pre and post data, such as fire detection."
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.corresponding_ref",
"url":13,
"doc":"The corresponding reference products to the current one (if the product is not a reference but has a reference data corresponding to it). A list because of multiple ref in case of non-stackable products (S3, S1 .)"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.nodata",
"url":13,
"doc":"Product nodata, set to 0 by default. Please do not touch this or all index will fail."
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.platform",
"url":13,
"doc":"Product platform, such as Sentinel-2"
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.resolution",
"url":13,
"doc":"Default resolution in meters of the current product. For SAR product, we use Ground Range resolution as we will automatically orthorectify the tiles."
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.condensed_name",
"url":13,
"doc":"Condensed name, the filename with only useful data to keep the name unique (ie.  20191215T110441_S2_30TXP_L2A_122756 ). Used to shorten names and paths."
},
{
"ref":"eoreader.products.sar.tsx_product.TsxProduct.sat_id",
"url":13,
"doc":"Satellite ID, i.e.  S2 for Sentinel-2"
},
{
"ref":"eoreader.reader",
"url":29,
"doc":"Product Factory, class creating products according to their names"
},
{
"ref":"eoreader.reader.CheckMethod",
"url":29,
"doc":"Methods to recognize a product"
},
{
"ref":"eoreader.reader.CheckMethod.MTD",
"url":29,
"doc":"Check the metadata: faster method"
},
{
"ref":"eoreader.reader.CheckMethod.NAME",
"url":29,
"doc":"Check the filename: Safer method that allows modified product names as it recursively looks for the metadata name in the product files. For products that have generic metadata files (ie. RS2 that as mtd named  product.xml ), it also checks the band name."
},
{
"ref":"eoreader.reader.CheckMethod.BOTH",
"url":29,
"doc":"Check the metadata and the filename: Double check if you have a doubt."
},
{
"ref":"eoreader.reader.Platform",
"url":29,
"doc":"Platforms supported by EOReader"
},
{
"ref":"eoreader.reader.Platform.S1",
"url":29,
"doc":"Sentinel-1"
},
{
"ref":"eoreader.reader.Platform.S2",
"url":29,
"doc":"Sentinel-2"
},
{
"ref":"eoreader.reader.Platform.S2_THEIA",
"url":29,
"doc":"Sentinel-2 Theia"
},
{
"ref":"eoreader.reader.Platform.S3",
"url":29,
"doc":"Sentinel-3"
},
{
"ref":"eoreader.reader.Platform.L8",
"url":29,
"doc":"Landsat-8"
},
{
"ref":"eoreader.reader.Platform.L7",
"url":29,
"doc":"Landsat-7"
},
{
"ref":"eoreader.reader.Platform.L5",
"url":29,
"doc":"Landsat-5"
},
{
"ref":"eoreader.reader.Platform.L4",
"url":29,
"doc":"Landsat-4"
},
{
"ref":"eoreader.reader.Platform.L3",
"url":29,
"doc":"Landsat-3"
},
{
"ref":"eoreader.reader.Platform.L2",
"url":29,
"doc":"Landsat-2"
},
{
"ref":"eoreader.reader.Platform.L1",
"url":29,
"doc":"Landsat-1"
},
{
"ref":"eoreader.reader.Platform.PLA",
"url":29,
"doc":"PlanetScope"
},
{
"ref":"eoreader.reader.Platform.CSK",
"url":29,
"doc":"COSMO-SkyMed"
},
{
"ref":"eoreader.reader.Platform.TSX",
"url":29,
"doc":"TerraSAR-X"
},
{
"ref":"eoreader.reader.Platform.RS2",
"url":29,
"doc":"RADARSAT-2"
},
{
"ref":"eoreader.reader.MTD_REGEX",
"url":29,
"doc":"Platform XML regex, mapping every metadata XML to a regex allowing the reader to recognize them (as a fallback)."
},
{
"ref":"eoreader.reader.Reader",
"url":29,
"doc":"Factory class creating satellite products according to their names. It creates a singleton that you can call only on,e time per file."
},
{
"ref":"eoreader.reader.Reader.open",
"url":29,
"doc":"Open the product.   >>> from eoreader.reader import Reader >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> Reader().open(path)    Args: product_path (str): Product path archive_path (str): Archive path output_path (str): Output Path look_for_mtd (bool): Look for the metadata. If false, only check the Returns: Product: Correct products",
"func":1
},
{
"ref":"eoreader.reader.Reader.valid_name",
"url":29,
"doc":"Check if the product's name is valid for the given satellite   >>> from eoreader.reader import Reader, Platform >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> With IDs >>> Reader().valid_name(path, \"S1\") False >>> Reader().valid_name(path, \"S2\") True >>>  With names >>> Reader().valid_name(path, \"Sentinel-1\") False >>> Reader().valid_name(path, \"Sentinel-2\") True >>>  With Platform >>> Reader().valid_name(path, Platform.S1) False >>> Reader().valid_name(path, Platform.S2) True   Args: product_path (str): Product path platform (str): Platform's name or ID Returns: bool: True if valid name",
"func":1
},
{
"ref":"eoreader.reader.Reader.valid_mtd",
"url":29,
"doc":"Check if the product's mtd is in the product folder/archive   >>> from eoreader.reader import Reader, Platform >>> path = r\"S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip\" >>> With IDs >>> Reader().valid_mtd(path, \"S1\") False >>> Reader().valid_mtd(path, \"S2\") True >>>  With names >>> Reader().valid_mtd(path, \"Sentinel-1\") False >>> Reader().valid_mtd(path, \"Sentinel-2\") True >>>  With Platform >>> Reader().valid_mtd(path, Platform.S1) False >>> Reader().valid_mtd(path, Platform.S2) True   Args: product_path (str): Product path platform (str): Platform's name or ID Returns: bool: True if valid name",
"func":1
},
{
"ref":"eoreader.utils",
"url":30,
"doc":"Utils: mostly getting directories relative to the project"
},
{
"ref":"eoreader.utils.get_src_dir",
"url":30,
"doc":"Get src directory. Returns: str: Root directory",
"func":1
},
{
"ref":"eoreader.utils.get_root_dir",
"url":30,
"doc":"Get root directory. Returns: str: Root directory",
"func":1
},
{
"ref":"eoreader.utils.get_data_dir",
"url":30,
"doc":"Get data directory. Returns: str: Data directory",
"func":1
},
{
"ref":"eoreader.utils.get_db_dir",
"url":30,
"doc":"Get database directory in the DS2 Returns: str: Database directory",
"func":1
}
]