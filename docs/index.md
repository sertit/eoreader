```{include} ../README.md
```

# Site content

```{eval-rst}
.. toctree::
   :maxdepth: 2
   :caption: For Users

   main_features
   optical
   sar
```

```{eval-rst}
.. toctree::
   :maxdepth: 2
   :caption: Examples

   notebooks/base
   notebooks/SAR
   notebooks/VHR
   notebooks/water_detection
   notebooks/s3_compatible_storage
```

```{eval-rst}
.. autosummary::
    :toctree: api
    :caption: API
    :template: custom-module-template.rst
    :recursive:

    eoreader
```

