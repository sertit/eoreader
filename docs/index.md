```{include} ../README.md
```

# Site content

```{eval-rst}
.. toctree::
   :maxdepth: 1
   :caption: For Users

   main_features
   optical
   sar
   custom
   faq
```

```{eval-rst}
.. toctree::
   :maxdepth: 1
   :caption: Tutorials

   notebooks/base
   notebooks/SAR
   notebooks/VHR
   notebooks/sentinel-3
   notebooks/water_detection
   notebooks/dem
   notebooks/custom
   notebooks/optical_cleaning_methods
   notebooks/s3_compatible_storage
   notebooks/dask
```

```{eval-rst}
.. autosummary::
   :toctree: api
   :caption: EOReader API
   :template: custom-module-template.rst
   :recursive:
   
   eoreader.reader
   eoreader.products
   eoreader.bands
   eoreader.env_vars
   eoreader.keywords
   eoreader.exceptions
   eoreader.utils 
```

```{eval-rst}
.. toctree::
   :maxdepth: 1
   :caption: For Contributors

   contributing
   history
   GitHub Repository <https://github.com/sertit/eoreader>
```

