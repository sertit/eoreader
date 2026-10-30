# Documentation Update Template

## Overview
[Provide a brief overview of the documentation update. What is being changed?]

## Changes Required

⚠️ **AI Risk:** Documentation **must** follow the [sensor-agnostic contract](../../ARCHITECTURE.md#key-patterns-for-contributors). AI may suggest sensor-specific details that violate this.

### 1. Module/Class Documentation
- **File:** [Path to file, e.g., `eoreader/products/product.py`]
- **Changes:**
  - [ ] Update docstring for `[Class/Function Name]`
  - [ ] Add examples or usage notes
  - [ ] Clarify parameters or return types

### 2. User Guide
- **File:** [Path to file, e.g., `docs/optical.md`]
- **Changes:**
  - [ ] Add new sensor/constellation section
  - [ ] Update examples or code snippets
  - [ ] Add troubleshooting or FAQ entries

### 3. API Reference
- **File:** [Path to file, e.g., `docs/api.md`]
- **Changes:**
  - [ ] Add new band names to API reference
  - [ ] Update method signatures or descriptions
  - [ ] Add cross-references to related modules

### 4. Notebooks
- **File:** [Path to notebook, e.g., `docs/notebooks/basics/loading_bands.ipynb`]
- **Changes:**
  - [ ] Update notebook to reflect new functionality
  - [ ] Add new examples or use cases
  - [ ] Ensure notebook runs without errors

---
**References:**
- Issue: [#XX](https://github.com/sertit/eoreader/issues/XX)
- PR: [#YY](https://github.com/sertit/eoreader/pull/YY)
