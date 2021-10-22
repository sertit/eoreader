#!/usr/bin/env python
# coding: utf-8

# # Basic example
# Let's use EOReader for the first time !
# 
# <div class="alert alert-warning">
#   
# <strong>Warning:</strong> You will need <strong>matplotlib</strong> to complete this tutorial
#     
# </div>

# In[1]:


import os

# First of all, we need some satellite data. 
# Let's open a lightweight a Landsat-5 MSS collection 2 tile.
path = os.path.join("/home", "data", "DATA", "PRODS", "LANDSATS_COL2", "LM05_L1TP_200029_19841014_20200902_02_T2.tar")


# In[2]:


from eoreader.reader import Reader

# Create the reader
eoreader = Reader()

# This reader is a singleton can be called once and then open all your data.
# Use it like a logging.getLogger() instance


# In[3]:


# Open your product
prod = eoreader.open(path, remove_tmp=True) # No need to unzip here
print(prod)


# In[4]:


# Here you have opened your product and you have its object in hands
# You can play a little with it to see what it got inside
print(f"Landsat tile: {prod.tile_name}")
print(f"Acquisition datetime: {prod.datetime}")


# In[5]:


# Retrieve the UTM CRS of the tile
prod.crs


# In[6]:


# Open here some more interesting geographical data: extent
extent = prod.extent
extent.geometry.to_crs("EPSG:4326").iat[0]  # Display


# In[7]:


# Open here some more interesting geographical data: footprint
footprint = prod.footprint
footprint.geometry.to_crs("EPSG:4326").iat[0]  # Display


# See the difference between footprint and extent hereunder:
# 
# |Without nodata | With nodata|
# |--- | ---|
# | ![without_nodata](https://zupimages.net/up/21/14/69i6.gif) | ![with_nodata](https://zupimages.net/up/21/14/vg6w.gif) |

# In[8]:


from eoreader.bands.alias import *
from eoreader.env_vars import DEM_PATH

# Select the bands you want to load
bands = [GREEN, NDVI, TIR_1, CLOUDS, SHADOWS]

# Compute DEM band only if you have set a DEM in your environment path
if DEM_PATH in os.environ:
    bands.append(HILLSHADE)

# Be sure they exist for Landsat-5 MSS sensor:
ok_bands = [band for band in bands if prod.has_band(band)]
print(to_str(ok_bands)) # Landsat-5 MSS doesn't provide TIR and SHADOWS bands


# In[9]:


# Load those bands as a dict of xarray.DataArray
band_dict = prod.load(ok_bands)
band_dict[GREEN]


# In[10]:


# The nan corresponds to the nodata you see on the footprint
get_ipython().run_line_magic('matplotlib', 'inline')

# Plot a subsampled version
band_dict[GREEN][:, ::10, ::10].plot()


# In[11]:


# Plot a subsampled version
band_dict[NDVI][:, ::10, ::10].plot()


# In[12]:


# Plot a subsampled version
if HILLSHADE in band_dict:
    band_dict[HILLSHADE][:, ::10, ::10].plot()


# In[13]:


# You can also stack those bands
stack = prod.stack(ok_bands)
stack


# In[14]:


# Error in plotting with a list
if "long_name" in stack.attrs:
    stack.attrs.pop("long_name")

# Plot a subsampled version
import matplotlib.pyplot as plt
nrows = len(stack)
fig, axes = plt.subplots(nrows=nrows, figsize=(2*nrows, 6*nrows), subplot_kw={"box_aspect": 1})  # Square plots
for i in range(nrows):
    stack[i, ::10, ::10].plot(x="x", y="y", ax=axes[i])

