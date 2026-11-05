# Copyright 2026, SERTIT-ICube - France, https://sertit.unistra.fr/
# This file is part of eoreader project
#     https://github.com/sertit/eoreader
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Various mappings used in EOReader (wrt STAC and ASI)"""

from eoreader.bands.band_names import (
    BLUE,
    CA,
    DEEP_BLUE,
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
    DEEP_BLUE: "A",
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
    zip(EOREADER_TO_SPYNDEX_DICT.values(), EOREADER_TO_SPYNDEX_DICT.keys(), strict=True)
)

# Workaround: https://github.com/awesome-spectral-indices/awesome-spectral-indices/issues/74
SPYNDEX_TO_EOREADER_DICT.update({"T": TIR_1})

EOREADER_STAC_MAP = EOREADER_STAC_MAP
