# -*- coding: utf-8 -*-
from zipfile import ZipFile
import re
from utils import calculate_capacity, find_test_type
from transformers import transform_mdat
import pandas as pd


def extract_csv(csv, df):
    ...


def extract_mdat(mdat):
    """
    Data extraction logic for Solartron mdat data files.

    Parameters
    ----------
    mdat : str
        File path to data file.

    Returns
    -------
    Print statement on extracted data from file.
    """
    # Opens mdat file using ZipFile context manager
    with ZipFile(mdat, mode="r") as mdat:
        # Empty pandas df to concat individual cor files
        df = pd.DataFrame()

        # Iterate through all archive files contained within mdat
        for file in mdat.namelist():
            # Gets file name, i.e. 'data file.cor', for each archive file, splits on Run##/file_name
            file_name = file.split("/")[1]
            test_type = find_test_type(file_name)
            # Archive file context manager, allows os reading of binary-like file objects
            with mdat.open(file) as _mdat:
                # Regular expression for selecting the tab delimeted t(s), V(V), I(A/cm2)) data from mdat format
                data_pattern = re.compile(
                    r"^-?\d+(\.\d+)?(E[+-]?\d+)?(\t-?\d+(\.\d+)?(E[+-]?\d+)?)*$"
                )

                # Initialize empty list for accumulating lines of header data and echem data
                header_data = []
                echem_data = []

                # If file is .cor it contains the test data needing extraction
                if file_name.endswith(".cor"):
                    lines = _mdat.readlines()

                    # Initialize line tracking variables
                    data_rows_started = False

                    # This loop fills the header_data and echem_data lists with the data from .cor
                    for line in lines:
                        line = line.decode("utf-8").strip()

                        if data_pattern.match(line):
                            data_rows_started = True
                        if data_rows_started:
                            parts = [
                                float(number) for number in line.split("\t")
                            ]
                            echem_data.append(parts)
                        else:
                            try:
                                line = line.split(":")
                                line = [line[0].strip(), line[1].strip()]
                                header_data.append(line)
                            except IndexError:
                                pass
                    temp_df, cell_lc = transform_mdat(header_data, echem_data)
                    df = pd.concat([df, temp_df])
    df["Test Type"] = test_type
    df = calculate_capacity(df)
    print(f"Extracted {file_name} data.")
    return df
