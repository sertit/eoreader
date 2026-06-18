"""Test for duplicate mask loading bug fix in S2Product._load_masks.

This test verifies that when loading a mask with multiple associated bands,
the mask file is only opened/processed ONCE per associated band, not N times
(where N is the number of associated bands).

Bug context:
In `_load_masks`, when iterating over `associated_bands[band]`, the code was
appending `band` to `bands_to_load` once per associated band when the mask file
wasn't on disk. For example, with `associated_bands = {DETFOO: [RED, GREEN, BLUE]}`,
`bands_to_load` would become `[DETFOO, DETFOO, DETFOO]`, causing each associated
band mask to be opened 3 times.

Fix:
The fix ensures `band` is only appended to `bands_to_load` once, by checking
`if band not in bands_to_load` before appending.
"""

from unittest.mock import MagicMock, patch

import pytest

from eoreader.bands import S2MaskBandNames
from eoreader.keywords import ASSOCIATED_BANDS
from eoreader.products.optical.s2_product import S2Product


class TestS2LoadMasksNoDuplicateLoading:
    """Test that S2Product._load_masks doesn't load the same mask multiple times."""

    @pytest.fixture
    def mock_s2_product(self):
        """Create a mock S2Product instance with necessary attributes mocked."""
        with patch.object(S2Product, "__init__", lambda self, *args, **kwargs: None):
            prod = S2Product.__new__(S2Product)

            # Set required attributes
            prod._processing_baseline = 4.0

            # Mock _sanitized_associated_bands to return our test data
            prod._sanitized_associated_bands = MagicMock()

            # Mock _get_band_key to return a predictable key
            def get_band_key(band, assoc_band, **kw):
                band_name = band.name if hasattr(band, "name") else str(band)
                assoc_name = (
                    assoc_band.name
                    if hasattr(assoc_band, "name") and assoc_band
                    else str(assoc_band)
                    if assoc_band
                    else "None"
                )
                return f"{band_name}_{assoc_name}"

            prod._get_band_key = MagicMock(side_effect=get_band_key)

            # Mock get_band_path to return a path that doesn't exist (forces loading)
            mock_path = MagicMock()
            mock_path.is_file.return_value = False
            prod.get_band_path = MagicMock(return_value=mock_path)

            # Mock _open_masks to track what it receives
            prod._open_masks = MagicMock(return_value={})

            yield prod

    def test_load_masks_no_duplicates_with_multiple_associated_bands(
        self, mock_s2_product
    ):
        """Verify _open_masks receives bands_to_load without duplicates.

        When a mask (e.g., DETFOO) has multiple associated bands (e.g., [RED, GREEN, BLUE]),
        the band should appear only once in bands_to_load passed to _open_masks.
        """
        prod = mock_s2_product

        # DETFOO mask with 3 associated bands
        associated_bands = {S2MaskBandNames.DETFOO: ["RED", "GREEN", "BLUE"]}

        # Mock returns the same associated_bands that we pass as input
        prod._sanitized_associated_bands.return_value = associated_bands

        # Call the actual _load_masks method
        prod._load_masks(
            bands=[S2MaskBandNames.DETFOO],
            pixel_size=10,
            size=None,
            **{ASSOCIATED_BANDS: associated_bands},
        )

        # Verify _open_masks was called
        assert prod._open_masks.called, "_open_masks should have been called"

        # Get the bands_to_load argument passed to _open_masks
        call_args = prod._open_masks.call_args
        bands_to_load = call_args[0][0]  # First positional argument

        # THE KEY ASSERTION: DETFOO should appear exactly once, not 3 times
        detfoo_count = bands_to_load.count(S2MaskBandNames.DETFOO)
        assert detfoo_count == 1, (
            f"S2MaskBandNames.DETFOO should appear exactly once in bands_to_load, "
            f"but appears {detfoo_count} times. bands_to_load = {bands_to_load}"
        )

    def test_load_masks_multiple_masks_with_associated_bands(self, mock_s2_product):
        """Test with multiple masks, each having multiple associated bands."""
        prod = mock_s2_product

        # DETFOO with 3 associated bands, SATURA with 2 associated bands
        associated_bands = {
            S2MaskBandNames.DETFOO: ["RED", "GREEN", "BLUE"],
            S2MaskBandNames.SATURA: ["RED", "GREEN"],
        }

        # Mock returns the same associated_bands that we pass as input
        prod._sanitized_associated_bands.return_value = associated_bands

        # Call the actual _load_masks method
        prod._load_masks(
            bands=[S2MaskBandNames.DETFOO, S2MaskBandNames.SATURA],
            pixel_size=10,
            size=None,
            **{ASSOCIATED_BANDS: associated_bands},
        )

        # Get the bands_to_load argument
        call_args = prod._open_masks.call_args
        bands_to_load = call_args[0][0]

        # Each mask should appear exactly once
        assert bands_to_load.count(S2MaskBandNames.DETFOO) == 1
        assert bands_to_load.count(S2MaskBandNames.SATURA) == 1
        assert len(bands_to_load) == 2
