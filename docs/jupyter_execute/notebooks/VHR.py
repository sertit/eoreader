#!/usr/bin/env python
# coding: utf-8

# # VHR example
# Let's use EOReader with Very High Resolution data.
# 
# <div class="alert alert-warning">
#   
# <strong>Warning:</strong> 
#    <li> We do not provide Pleiades data
#    <li> You will need <strong>matplotlib</strong> to complete this tutorial
# </div>

# In[1]:


import os
import glob

# First of all, we need some VHR data, let's use Pleiades data
path = glob.glob(os.path.join("/home", "data", "DATA", "PRODS", "PLEIADES", "5547047101", "IMG_PHR1A_PMS_001"))[0]


# In[2]:


# Create logger
import logging

logger = logging.getLogger("eoreader")
logger.setLevel(logging.INFO)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# create formatter
formatter = logging.Formatter('%(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)


# In[3]:


from eoreader.reader import Reader

# Create the reader
eoreader = Reader()


# In[4]:


# Open your product
prod = eoreader.open(path, remove_tmp=True)
print(f"Acquisition datetime: {prod.datetime}")
print(f"Condensed name: {prod.condensed_name}")

# Please be aware that EOReader will always work in UTM projection, so if you give WGS84 data,
# EOReader will reproject the stacks and this can be time consuming


# In[5]:


from eoreader.bands.alias import *
from eoreader.env_vars import DEM_PATH

# Here, if you want to orthorectify or pansharpen your data manually, you can set your stack here.
# If you do not provide this stack but you give a non-orthorectified product to EOReader 
# (ie. SEN or PRJ products for Pleiades), you must provide a DEM to orthorectify correctly the data
# prod.ortho_stack = ""
os.environ[DEM_PATH] = os.path.join("/home", "data", "DS2", "BASES_DE_DONNEES", "GLOBAL", "MERIT_Hydrologically_Adjusted_Elevations", "MERIT_DEM.vrt")


# In[6]:


# Open here some more interesting geographical data: extent
extent = prod.extent
extent.geometry.to_crs("EPSG:4326").iat[0]  # Display


# In[7]:


# Open here some more interesting geographical data: footprint
footprint = prod.footprint
footprint.geometry.to_crs("EPSG:4326").iat[0]  # Display


# In[8]:


# Select the bands you want to load
bands = [GREEN, NDVI, TIR_1, CLOUDS, HILLSHADE]

# Be sure they exist for Pleiades sensor:
ok_bands = [band for band in bands if prod.has_band(band)]
print(to_str(ok_bands)) # Pleiades doesn't provide TIR and SHADOWS bands


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
band_dict[CLOUDS][:, ::10, ::10].plot()


# In[13]:


# Plot a subsampled version
band_dict[HILLSHADE][:, ::10, ::10].plot()


# In[14]:


# You can also stack those bands
stack = prod.stack(ok_bands)
stack


# In[15]:


# Error in plotting with a list
if "long_name" in stack.attrs:
    stack.attrs.pop("long_name")

# Plot a subsampled version
import matplotlib.pyplot as plt
nrows = len(stack)
fig, axes = plt.subplots(nrows=nrows, figsize=(2*nrows, 6*nrows), subplot_kw={"box_aspect": 1})
for i in range(nrows):
    stack[i, ::10, ::10].plot(x="x", y="y", ax=axes[i])

