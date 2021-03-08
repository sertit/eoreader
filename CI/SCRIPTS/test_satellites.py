""" Script testing EOReader """

import logging
import os

import pytest

from eoreader.bands.alias import *
from eoreader.exceptions import InvalidBandError
from eoreader.reader import Reader
from eoreader.utils import EOREADER_NAME

LOGGER = logging.getLogger(EOREADER_NAME)

READER = Reader()
PRODS = r"D:\_EXTRACTEO\DATA\PRODS\\"
ZIP = r"D:\_EXTRACTEO\OUTPUT\ZIP\\"
RES = 400  # meters


def test_optical():
    """ Function testing the correct functioning of the optical satellites """
    opt_path = [
        f"{PRODS}THEIA\SENTINEL2A_20190625-105728-756_L2A_T31UEQ_C_V2-2",  # S2 Theia
        f"{PRODS}LANDSATS_ZIP\LC08_L1GT_023030_20200518_20200527_01_T2",  # L8
        f"{PRODS}LANDSATS_ZIP\LE07_L1GT_025030_20200609_20200609_01_RT",  # L7
        f"{PRODS}LANDSATS_ZIP\LT05_L1GS_029031_20111112_20160830_01_T2",  # L5 - TM
        f"{PRODS}LANDSATS_ZIP\LM05_L1GS_026032_19870310_20180328_01_T2",  # L5 - MSS
        f"{PRODS}LANDSATS_ZIP\LT04_L1GS_024031_19930710_20160927_01_T2",  # L4 - TM
        f"{PRODS}LANDSATS_ZIP\LM04_L1GS_030031_19831029_20180413_01_T2",  # L4 - MSS
        f"{PRODS}LANDSATS_ZIP\LM03_L1GS_033028_19820906_20180414_01_T2",  # L3
        f"{PRODS}LANDSATS_ZIP\LM02_L1GS_024030_19820202_20180413_01_T2",  # L2
        f"{PRODS}LANDSATS_ZIP\LM01_L1GS_034032_19771229_20180423_01_T2",  # L1
        f"{ZIP}S2A_MSIL1C_20200824T110631_N0209_R137_T30TTK_20200824T150432.SAFE.zip",  # S2
        f"{ZIP}S3B_SL_1_RBT____20191115T233722_20191115T234022_20191117T031722_0179_032_144_3420_LN2_O_NT_003.SEN3",
        # S3-SLSTR
        f"{ZIP}S3A_OL_1_EFR____20191215T105023_20191215T105323_20191216T153115_0179_052_322_2160_LN1_O_NT_002.SEN3"
        # S3-OLCI
    ]
    for path in opt_path:
        if os.path.exists(path):
            prod = READER.open(path)
            prod.stack([RED, GREEN, RED, NDVI], resolution=RES)


def test_sar():
    """ Function testing the correct functioning of the SAR satellites """
    sar_path = [
        f"{PRODS}COSMO\\1011117-766193",  # COSMO
        f"{PRODS}RS2\RS2_OK124206_PK1090291_DK1036668_MF6W_20201007_222810_HH_SGF",  # RS2
        f"{PRODS}TERRASAR\TDX1_SAR__MGD_SE___SM_S_SRA_20201016T231611_20201016T231616",  # TSX
        f"{ZIP}S1A_IW_GRDH_1SDV_20191215T060906_20191215T060931_030355_0378F7_3696.zip"  # S1
    ]
    for path in sar_path:
        if os.path.exists(path):
            prod = READER.open(path)
            with pytest.raises(InvalidBandError):
                prod.stack([VV, VV_DSPK], resolution=RES)
