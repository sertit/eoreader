# Test File Template

## Overview
[Provide a brief overview of the test file. What does it test?]

## Test Structure

⚠️ **AI Risk:** Test cases **must** cover edge cases (e.g., missing bands, invalid windows). AI may generate overly simplistic tests.

### 1. Imports
```python
from __future__ import annotations

import pytest

from eoreader.reader import Reader
from eoreader.bands import RED, GREEN, BLUE, NDVI
```

### 2. Fixtures
```python
@pytest.fixture
def reader():
    return Reader()
```

### 3. Test Cases
#### Test Case 1: [Test Name]
- **Purpose:** [Describe what this test validates]
- **Input:** [Describe input data or conditions]
- **Expected Output:** [Describe expected result]
- **Code:**
```python
def test_[test_name](reader):
    # Load product
    product = reader.open("[path/to/product]")
    
    # Load bands
    bands = product.load([RED, GREEN, BLUE])
    
    # Assertions
    assert RED in bands
    assert bands[RED].shape == (expected_shape)
    assert bands[RED].attrs["crs"] == expected_crs
```

#### Test Case 2: [Test Name]
- **Purpose:** [Describe what this test validates]
- **Input:** [Describe input data or conditions]
- **Expected Output:** [Describe expected result]
- **Code:**
```python
def test_[test_name](reader):
    # Your test code here
    pass
```

---
**References:**
- Issue: [#XX](https://github.com/sertit/eoreader/issues/XX)
- PR: [#YY](https://github.com/sertit/eoreader/pull/YY)
