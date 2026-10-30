# EOReader Technical Guide

This file is the technical reference for the **EOReader** codebase: 
architecture, module layout, build & test setup, code style, CI/CD, and common pitfalls.  
It is the "read this" target for the task-based navigation in [AGENTS.md](https://github.com/sertit/eoreader/blob/main/AGENTS.md).

Human contribution guidelines live in [CONTRIBUTING.md](https://github.com/sertit/eoreader/blob/main/CONTRIBUTING.md).  
The project's AI-assisted contribution policy lives in [AI_POLICY.md](https://github.com/sertit/eoreader/blob/main/AI_POLICY.md).

---

## Project Overview

**EOReader** is a remote-sensing open-source Python library reading [optical](https://eoreader.readthedocs.io/latest/optical.html) 
and [SAR](https://eoreader.readthedocs.io/latest/sar.html) constellations.
It also loads and stacks satellite bands, spectral indices, cloud bands, DEM bands and masks in a **sensor-agnostic** way.

- **Language**: Python 3.11–3.14
- **Package name**: `eoreader`
- **License**: Apache 2.0
- **Repository**: https://github.com/sertit/eoreader
- **Default branch**: `main`
- **Author**: ICube-SERTIT (https://sertit.unistra.fr/)

> [!IMPORTANT]
> The goal of this library is to manage **one satellite product at a time**. 
> To handle mosaics, pairs or time series, use [`EOSets`](https://github.com/sertit/eosets).

Both optical and SAR constellations are supported. 
The list is maintained in the `Constellation` enum of `eoreader/reader.py` (source of truth) 
and in [README.md](https://github.com/sertit/eoreader/blob/main/README.md).

---

## Key Files to Read First (by task)

| Task                               | Read Order                                                                                      |
|------------------------------------|-------------------------------------------------------------------------------------------------|
| Understanding the band abstraction | `eoreader/bands/bands.py` → `eoreader/bands/band_names.py` → `eoreader/bands/spectral_bands.py` |
| Adding a new optical product       | `eoreader/products/optical/s2_product.py` → `optical_product.py` → `products/product.py`        |
| Adding a new SAR product           | `eoreader/products/sar/sar_product.py` → `s1_product.py` → `eoreader/data/*.xml`                |
| Understanding `load()`/`stack()`   | `eoreader/products/product.py` (`load`, `_load`, `_load_bands`, `stack`, `_collocate_bands`)    |
| Reader / constellation detection   | `eoreader/reader.py`                                                                            |
| STAC integration                   | `eoreader/stac/stac_item.py` → `stac_utils.py` → `products/stac_product.py`                     |
| Spectral indices                   | `eoreader/bands/indices.py` → `eoreader/bands/mappings.py`                                      |
| Testing                            | `ci/conftest.py` → `ci/scripts_utils.py` → `ci/on_push/test_satellites.py`                      |
| CI/CD                              | `.gitlab-ci.yml` → `.github/workflows/`                                                         |
| Configuration                      | `eoreader/env_vars.py` → `eoreader/keywords.py`                                                 |

---

## Architecture

### Core Concepts

1. **Sensor-agnostic band abstraction**: every band is referenced by an EOReader semantic name (e.g. `RED`, `VV`, `NDVI`, `CLOUDS`, `DEM`). 
   Each product maps these names to the raw sensor band (number or name) through a `BandMap`. 
   Downstream algorithms only ever see the semantic name and normalised units, never the sensor specifics.
2. **Product class hierarchy**:
   - `eoreader.products.product.Product` (base class): `load()`, `stack()`, `footprint`, `extent`, `centroid`, `crs`, `stac`, `plot()`, band path management, metadata reading (XML/HTML/archives), DEM warping, band collocation.
   - `OpticalProduct(Product)` (optical base) and `SarProduct(Product)` (SAR base).
   - One module per constellation, e.g. `s2_product.py`, `landsat_product.py`, `capella_product.py`.
   - `CustomProduct(Product)`: a custom stack previously written by EOReader.
   - `StacProduct(Product)`: reads products from STAC items.
3. **Reader factory**: `Reader.open(path)` recognizes the constellation from the product structure (metadata, filename, or both, via `CheckMethod.MTD/NAME/BOTH`) and returns the right `Product` subclass.
4. **Georeferenced lazy I/O**: bands are returned as `xarray.DataArray` (crs/transform from the product metadata, via `rioxarray`/`rasterio`). Vectors (footprint, extent, masks) are `geopandas.GeoDataFrame`s. 
   Stacks can be written to disk (default driver `COG`).
5. **Optional Dask**: if `EOREADER_USE_DASK=1` and `dask` is installed, products are read as dask-backed arrays.
6. **SAR processing via SNAP**: SAR bands are orthorectified and calibrated with ESA SNAP GPT graphs. The default graphs are the XML files in `eoreader/data/` (overridable with `EOREADER_PP_GRAPH` / `EOREADER_DSPK_GRAPH`). 
   The `gpt` executable must be on the `PATH`.
7. **Cloud storage**: products can live on S3. All path handling goes through `sertit.AnyPath`. Never use raw `os.path` on product paths.

### Key Modules

| Module                                         | Purpose                                                                                                                            |
|------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| `eoreader/reader.py`                           | `Reader` factory, `Constellation` enum, `CheckMethod`                                                                              |
| `eoreader/products/product.py`                 | Base `Product`: `load()`, `stack()`, band management, STAC, plotting                                                               |
| `eoreader/products/optical/optical_product.py` | `OpticalProduct`, `CleanMethod`, `RawUnits`                                                                                        |
| `eoreader/products/sar/sar_product.py`         | `SarProduct`, `SarProductType`, SNAP orchestration                                                                                 |
| `eoreader/products/custom_product.py`          | `CustomProduct`, `CustomFields` (custom stacks)                                                                                    |
| `eoreader/products/stac_product.py`            | `StacProduct` (STAC item input)                                                                                                    |
| `eoreader/bands/bands.py`                      | `Band`, `BandMap` (STAC-band-like objects, sensor mapping)                                                                         |
| `eoreader/bands/spectral_bands.py`             | `SpectralBand`, `SpectralBandMap`                                                                                                  |
| `eoreader/bands/sar_bands.py`                  | `SarBand`, `SarBandMap`                                                                                                            |
| `eoreader/bands/band_names.py`                 | Name enums: `SpectralBandNames`, `SarBandNames`, `CloudsBandNames`, `DemBandNames`, `MaskBandNames` (+ per-constellation variants) |
| `eoreader/bands/indices.py`                    | Spectral indices (native + `spyndex` integration)                                                                                  |
| `eoreader/bands/mappings.py`                   | EOReader ↔ spyndex ↔ STAC common name dictionaries                                                                                 |
| `eoreader/stac/stac_item.py`                   | Internal STAC item creation from a product                                                                                         |
| `eoreader/env_vars.py`                         | Environment variables that change behavior (documented there)                                                                      |
| `eoreader/keywords.py`                         | Extra `load()`/`stack()` kwargs constants (`CLEAN_OPTICAL`, `TO_REFLECTANCE`, `EXO_KW`, ...)                                       |
| `eoreader/exceptions.py`                       | `EoReaderError` hierarchy (`InvalidBandError`, `InvalidProductError`, ...)                                                         |
| `eoreader/utils.py`                            | Path helpers, `use_dask()`, warping/collocation utilities                                                                          |
| `eoreader/__init__.py`                         | `cache` (`methodtools.lru_cache`), `EOREADER_NAME`, `DATETIME_FMT`                                                                 |
| `eoreader/data/*.xml`                          | Default SNAP GPT graphs (S1/SAR/CPLX preprocessing, despeckling)                                                                   |

### Subpackages

| Subpackage                   | Purpose                                                                       | Notes                                                                                                            |
|------------------------------|-------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| `eoreader/products/optical/` | One module per constellation + bases (`optical_product.py`, `vhr_product.py`) | `maxar_product.py` is legacy (renamed to Vantor). The `Constellation` enum in `reader.py` is the source of truth |
| `eoreader/products/sar/`     | One module per constellation + base (`sar_product.py`)                        | SNAP-dependent                                                                                                   |
| `eoreader/bands/`            | Band objects, enums, indices, mappings                                        | Entry point for the public band API                                                                              |
| `eoreader/stac/`             | STAC item/extension creation                                                  | Optional `stac` extra                                                                                            |

---

## Configuration

EOReader has no config file. Behaviour is driven by **environment variables**. 
All of them are declared in `eoreader/env_vars.py` with full docstrings (names, defaults, behaviour). 
That module is the source of truth and is rendered in the API docs. Set them at runtime:

```python
import os

os.environ["EOREADER_USE_DASK"] = "1"
```

> [!NOTE]
> These variables are read at import/call time where relevant. Do not hardcode machine-specific paths. Always read from the environment.

---

## Build & Test Setup

### Dev Environment

The project uses conda (conda-forge) or plain pip:

```bash
# Conda
conda env create -f environment.yml
conda activate eoreader
pip install -e .

# or Pip
pip install -r requirements.txt
pip install -e .
```

Additional extras:

```bash
pip install -e ".[stac]"    # pystac, stac-asset, planetary_computer
pip install -r requirements-doc.txt   # documentation build
```

### Linting

We use `pre-commit` with `ruff` (check + format) plus JSON/YAML/XML and large-file checks. 
It's important to install it, since we run the exact same hooks in CI:

```bash
pre-commit install
pre-commit run --all-files
```

The ruff ruleset (`select`, `ignore`, `keep-runtime-typing`) is declared in `pyproject.toml` (`[tool.ruff.lint]`). That file is the source of truth.

### Running the Tests

Tests live in `ci/` (NOT in `eoreader/tests/`):

```bash
# Everything that runs on every push (requires CI data, see below)
python -m pytest ci/on_push

# End-to-end / heavy suites (weekly in CI)
python -m pytest ci/weekly

# A single file / test
python -m pytest ci/on_push/test_bands.py
python -m pytest ci/on_push/test_satellites.py::test_optical_s2
```

> [!IMPORTANT]
> The test suite is **not self-contained**: it reads real satellite products from SERTIT infrastructure 
> (S3 bucket `s3://sertit-ci/eoreader` or the local DB3 database). 
> Some products are licensed and cannot be redistributed, so most contributors cannot run the full suite locally. 
> Use `--ci_db_dir <path>` to point pytest at a local directory containing the CI database layout (`optical/`, `sar/`, `others/`, `broken_products/`).

Relevant pytest options (`ci/conftest.py`):
- `--ci_db_dir`: override the CI database directory
- `--tmp_directory`: where temporary outputs are written

Relevant environment variables in tests:
- `CI_EOREADER_USE_S3=0|1`: read CI data from S3 or from disk
- `EOREADER_USE_DASK=0|1`: exercise the dask code path
- `EOREADER_DEM_PATH`: path to a DEM (e.g. MERIT) for DEM-related tests
- `CI_EOREADER_BAND_FOLDER`: bypass SNAP/DEM recomputation in tests

SAR tests require ESA SNAP's `gpt` executable on the `PATH`.

---

## Testing Patterns

### Test File Organization

- `ci/on_push/`: the per-PR suite (one `test_*.py` file per topic)
- `ci/weekly/`: the heavier end-to-end, broken-products and masks suites
- `ci/scripts_utils.py`: shared helpers: `get_ci_db_dir()`, `get_ci_data_dir()`, `opt_path()`, `sar_path()`, `dask_env()` (runs a test with a dask client), `s3_env()` (GDAL/S3 tuning), `reduce_verbosity()`
- `ci/conftest.py`: `--ci_db_dir`, `--tmp_directory`, `eoreader_tests_path` fixture

### Assertion Style

- Compare loaded `xarray.DataArray`s against expected values/properties (crs, transform, shape, nodata, units, band names) rather than full arrays when possible.
- Use `pytest` markers and fixtures over manual skip logic.
- Reuse the `READER = Reader()` instance from `ci.scripts_utils` where appropriate.

---

## Code Style & Conventions

### Copyright header

Every Python file starts with the Apache 2.0 header (year updated at each release):

```python
# Copyright 202x, SERTIT-ICube - France, https://sertit.unistra.fr/
# This file is part of eoreader project
#     https://github.com/sertit/eoreader
#
# Licensed under the Apache License, Version 2.0 (the "License");
# ...
```

Always include it in new files. Do not touch the year in unrelated files.

### Docstrings

- Google-style docstrings with `Args:`, `Returns:`, `Raises:`, `Examples:`.
- Public API docstrings are rendered in the Sphinx docs (autosummary). Keep them accurate and self-contained.
- `Examples` must be runnable when used as doctests.

### Enums & typing

- Constellation/sensor/band enumerations are `ListEnum` (from `sertit.misc`) with per-member docstrings (see `eoreader/reader.py`).
- Add type hints to every new function and method (including tests).
- `from __future__ import annotations` is used in the core modules. Follow the local pattern.

### Naming

- One module per constellation: `<constellation>_product.py` in `eoreader/products/optical/` or `eoreader/products/sar/`.
- Private helpers are prefixed with `_`.
- Tests: `ci/<suite>/test_<topic>.py`.

### Import organisation

```python
from __future__ import annotations

import os  # stdlib
import numpy as np  # third-party
import xarray as xr
from sertit import AnyPath  # sertit (SERTIT utils)

from eoreader import EOREADER_NAME  # eoreader
from eoreader.bands import RED  # eoreader submodules
```

---

## Key Patterns for Contributors

### Adding a New Constellation

1. Create `eoreader/products/optical/<x>_product.py` (or `sar/`) with an `XProduct(OpticalProduct)` / `XProduct(SarProduct)` class.
2. Add the `Constellation` member in `eoreader/reader.py`.
3. Implement the mandatory overrides:
   - `_read_mtd` / metadata parsing (and `_get_name_constellation_specific`, `_get_split_name`, etc. as needed)
   - `_map_bands()`: a `BandMap` mapping EOReader band names to raw sensor bands (band number or name), with per-band `Band` objects (`name`, `id`, `gsd`, `common_name`, STAC keywords...)
   - `footprint` / `extent` / `centroid` / `crs` sources
   - `_get_band_folder` / `get_band_path` for band resolution (including archives: `_get_archived_rio_path` helpers)
4. Register the class in `eoreader/products/__init__.py` and `eoreader/products/optical/__init__.py` (or `sar/__init__.py`) with the `__all__` updates.
5. Add tests in `ci/on_push/` (and `ci/weekly/` for end-to-end) following the existing per-constellation patterns.
6. Add the constellation to `CHANGES.md` with an `ENH:` entry, to the docs (`docs/optical.md` or `docs/sar.md`) and to the `README.md` constellation list.

### Adding a New Band or Index

- New band name: add the enum member in `eoreader/bands/band_names.py`, export it in `eoreader/bands/__init__.py`, and update `mappings.py` (spyndex/STAC common name dictionaries) if applicable.
- New native index: add the function in `eoreader/bands/indices.py` and register it in `_idx_fct`-driven registries. Prefer delegating to `spyndex` when the index exists there.

### Adding a New Environment Variable or Keyword

- Environment variable: declare it in `eoreader/env_vars.py` with a full docstring (it is part of the public API docs), then use it in the code path.
- `load()`/`stack()` keyword: declare the constant in `eoreader/keywords.py`.

### Custom Stacks & STAC

- `CustomProduct` reads stacks previously written by `stack()`: keep the `CustomFields` naming conventions stable (they encode constellation, bands, resolution, window, datetime).
- `StacProduct` and the `.stac` property are the integration points for internal STAC catalogs. STAC keywords live in `eoreader/stac/`.

---

## CI/CD

### GitLab CI (`.gitlab-ci.yml`): where tests run

GitHub is the primary repo. Pushes are mirrored to SERTIT's GitLab, which runs CI.

Per-PR, the `ci/on_push` suite runs (with or without dask, with data on disk or read from S3). 
The heavier `ci/weekly` suite runs on schedule and tags, including on the newest supported Python. 
Stages: `lint` → `test` → `weekly_tests`, in SERTIT `geo` containers. The exact job matrix is maintained in `.gitlab-ci.yml` (source of truth).

### GitHub Actions (`.github/workflows/`)

| Workflow | Purpose |
|---|---|
| `mirror_to_gitlab.yml` | Mirrors every push to GitLab and triggers CI |
| `publish.yml` | On tag `v*`: build (uv) + publish to PyPI via trusted publishing |

---

## Release Procedure

Releases are made by maintainers. The procedure lives in [CONTRIBUTING.md § Release EOReader](https://github.com/sertit/eoreader/blob/main/CONTRIBUTING.md#release-eoreader). 
Conda-forge packaging follows automatically.

> [!CAUTION]
> **A coding agent must NEVER create a new release** (no tags, no version bumps, no publish workflow dispatches). 
> See the hard limits in [AGENTS.md](https://github.com/sertit/eoreader/blob/main/AGENTS.md).

---

## Common Pitfalls & Gotchas

1. **SAR requires SNAP**: any change touching `SarProduct` or GPT graphs cannot be fully validated without the `gpt` executable on the `PATH` and a DEM (e.g., MERIT). If you lack these, state it in the PR description. CI is then the validation path.
2. **Dask laziness**: never force materialisation (`.compute()`, `np.asarray`, `rasters.read`) in the middle of a `load()`/`stack()` pipeline. The whole point of the dask path is to stay lazy until the user computes.
3. **Caching**: `eoreader.cache` wraps `methodtools.lru_cache` per instance. If `methodtools` is missing, caches are shared between products (a warning is printed). Be careful with `@cache`-decorated methods and mutable state.
4. **Cloud paths**: always use `AnyPath`/`cloudpathlib`. S3 products are byte-ranged. Reading a whole file from S3 when a window suffices is a bug.
5. **Windows vs full product**: band names encode the window (`get_band_file_name`). Changing window handling affects cached band paths.
6. **Band naming**: `EOREADER_LEGACY_BAND_NAME_RESOLUTION` changes resolution tokens in band names. Test both when touching naming.
7. **Raw product mutation**: workarounds like `EOREADER_FIX_VANTOR` deliberately fix faulty raw metadata. Keep such fixes guarded by an environment switch.
8. **numpy 2**: `rasterio>=1.3.10` and `xarray>=2024.06.0` require numpy 2. Don't reintroduce numpy-1-only patterns.
9. **Test data licensing**: do NOT commit satellite products, stacks or derived outputs. `check-added-large-files` (1600 kB) is a backstop, not a license.
10. **Copyright year**: updated project-wide at release time (`DOC:` commit). Do not do it as a side effect of unrelated PRs.

---

## External Dependencies (Key)

Key dependencies and their roles in the stack. The source of truth for what is actually installed is `pyproject.toml` (runtime `dependencies`, `stac` extra) and `requirements.txt` (development):

| Dependency                                     | Purpose                                                                              |
|------------------------------------------------|--------------------------------------------------------------------------------------|
| `xarray` / `rioxarray`                         | Georeferenced arrays, raster writing                                                 |
| `rasterio`                                     | Raster I/O backend (GDAL)                                                            |
| `geopandas` / `shapely`                        | Vector data (footprints, extents, masks)                                             |
| `sertit[full]`                                 | SERTIT utilities: `AnyPath`, rasters, geometry, SNAP, CI/dask/s3 helpers, `ListEnum` |
| `spyndex`                                      | Spectral index computation                                                           |
| `lxml`                                         | Metadata XML parsing                                                                 |
| `odc-geo`                                      | Geometry handling (warping)                                                          |
| `pyresample`                                   | Re-gridding                                                                          |
| `cloudpathlib[s3]` / `s3fs`                    | Cloud (S3) storage                                                                   |
| `dask[distributed]`                            | Optional lazy computation                                                            |
| `zarr` / `h5netcdf` / `tifffile`               | Auxiliary raster formats                                                             |
| `methodtools`                                  | Per-instance `lru_cache`                                                             |
| `pystac` / `stac-asset` / `planetary_computer` | Optional `stac` extra                                                                |

---

## Documentation

- **Source**: `docs/` (Sphinx + MyST, `.md` files with `eval-rst` blocks, notebooks rendered by `myst_nb`)
- **Build**: `sphinx-build docs docs/_build/html -E` (needs `requirements-doc.txt`)
- **Notebooks**: `docs/notebooks/{basics,advanced,experimental}/. Outputs are served from a Jupyter cache (see `readthedocs.yml` and the *Update notebooks* section of `CONTRIBUTING.md`)
- **API docs**: generated by autosummary from module docstrings
- **Online**: https://eoreader.readthedocs.io/latest/
- `docs/contributing.md` and `docs/history.md` simply include `CONTRIBUTING.md` and `CHANGES.md`. Keep those files as the source of truth.

