from eoreader.bands.band_names import (
    BLUE,
    CA,
    EOREADER_STAC_MAP,
    GREEN,
    HH,
    HV,
    NARROW_NIR,
    NIR,
    RED,
    SWIR_1,
    SWIR_2,
    TIR_1,
    TIR_2,
    VH,
    VRE_1,
    VRE_2,
    VRE_3,
    VV,
    WV,
    YELLOW,
)

EOREADER_TO_SPYNDEX_DICT = {
    CA: "A",
    BLUE: "B",
    GREEN: "G",
    RED: "R",
    VRE_1: "RE1",
    VRE_2: "RE2",
    VRE_3: "RE3",
    NIR: "N",
    NARROW_NIR: "N2",
    SWIR_1: "S1",
    SWIR_2: "S2",
    TIR_1: "T1",
    TIR_2: "T2",
    WV: "WV",
    YELLOW: "Y",
    VV: "VV",
    VH: "VH",
    HH: "HH",
    HV: "HV",
}

SPYNDEX_TO_EOREADER_DICT = dict(
    zip(EOREADER_TO_SPYNDEX_DICT.values(), EOREADER_TO_SPYNDEX_DICT.keys())
)

EOREADER_STAC_MAP = EOREADER_STAC_MAP
