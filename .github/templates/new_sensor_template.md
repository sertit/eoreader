# New Sensor Support Template

## Overview
[Provide a brief overview of the sensor/constellation you are adding support for. Include links to official documentation if available.]

## Constellation Details
- **Name:** [Sensor/Constellation Name]
- **Type:** [Optical/SAR]
- **Official Documentation:** [Link to documentation]
- **Data Access:** [How to access data for this sensor]


## Implementation Plan

⚠️ **AI Risk:** Band names and mappings **must** be verified against existing constellations (e.g., `s2_product.py`). Do not trust AI-generated mappings blindly. The most common omission: the `Constellation` enum member and the `__init__.py` registration below — without them, `Reader.open()` cannot find the product.

### 1. Constellation Module
- [ ] Create new module: `eoreader/products/[optical|sar]/<sensor>_product.py`
- [ ] Add the `Constellation` enum member in `eoreader/reader.py`
- [ ] Implement `XProduct(Product)` class (inheriting from `OpticalProduct` or `SarProduct`)
- [ ] Add constellation-specific metadata parsing (e.g., `_read_mtd`)
- [ ] Implement band mapping (`_map_bands`)
- [ ] Add footprint/extent/centroid/crs sources

### 2. Band Mapping
- [ ] Define band names in `eoreader/bands/band_names.py` (e.g., `SpectralBandNames`, `SarBandNames`)
- [ ] Export new band names in `eoreader/bands/__init__.py`
- [ ] Map raw sensor bands to EOReader semantic names in `_map_bands`

### 3. Registration
- [ ] Register the class in `eoreader/products/__init__.py` and `eoreader/products/[optical|sar]/__init__.py` (update `__all__`)

### 4. Testing
- [ ] Add tests in `ci/on_push/test_satellites.py` (or create new test file)
- [ ] Test band loading, stacking, and metadata parsing
- [ ] Test SAR preprocessing (if applicable)

### 5. Documentation
- [ ] Update `docs/optical.md` or `docs/sar.md` with sensor details
- [ ] Add examples in `docs/notebooks/` (if applicable)
- [ ] Update `README.md` constellation list

---
**References:**
- Issue: [#XX](https://github.com/sertit/eoreader/issues/XX)
- PR: [#YY](https://github.com/sertit/eoreader/pull/YY)
