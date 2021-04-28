""" Environment variables that can change the processes """

PP_GRAPH = "EOREADER_PP_GRAPH"
"""Environment variables for overriding default pre-processing graph path"""

DSPK_GRAPH = "EOREADER_DSPK_GRAPH"
"""Environment variables for overriding default despeckling graph path"""

SAR_DEF_RES = "EOREADER_SAR_DEFAULT_RES"
"""Environment variables for SAR default resolution, used for SNAP orthorectification to override default resolution."""

S3_DEF_RES = "EOREADER_S3_DEFAULT_RES"
"""Environment variables for S3 default resolution, used for SNAP orthorectification to override default resolution."""

DEM_PATH = "EOREADER_DEM_PATH"
"""Environment variables for overriding default DEM path"""

CI_EOREADER_BAND_FOLDER = "CI_EOREADER_BAND_FOLDER"
"""
Environment variables used in CI to override the existing band path
in order to bypass SNAP process and DEM reprojection.
"""
