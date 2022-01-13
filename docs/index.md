```{include} ../README.md
```

# Site content

```{eval-rst}
.. toctree::
   :maxdepth: 3
   :caption: For Users

   main_features
   optical
   sar
   custom
   faq
```

```{eval-rst}
.. toctree::
   :maxdepth: 2
   :caption: Tutorials

   notebooks/base
   notebooks/SAR
   notebooks/VHR
   notebooks/sentinel-3
   notebooks/water_detection
   notebooks/custom
   notebooks/optical_cleaning_methods
   notebooks/s3_compatible_storage
   notebooks/dask
```

```{eval-rst}
.. autosummary::
    :toctree: api
    :caption: API
    :template: custom-module-template.rst
    :recursive:

    eoreader
```

```{eval-rst}
.. toctree::
   :maxdepth: 1
   :caption: For Contributors

   contributing
   history
   GitHub Repository <https://github.com/sertit/eoreader>
```

