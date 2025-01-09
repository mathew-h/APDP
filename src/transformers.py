# -*- coding: utf-8 -*-
import pandas as pd
from utils import calculate_step_capacity


def transform_mdat(*data):
    """
    Takes list type data extracted from extract.py and transforms into appropriate df format

    Parameters
    ----------
    *data : list
        List of lists containing data[1] echem data and data[0] containing header data.

    Returns
    -------
    None.
    """
    temp_df = pd.DataFrame(
        data[1],
        columns=[
            "Time (s)",
            "Voltage (V)",
            "Current (A)",
        ],
    )
    header_data = data[0]
    for row in header_data:
        match row[0]:
            case "Run":
                temp_df["Run"] = int(row[1])
            case "Step":
                temp_df["Step"] = int(row[1].split("p")[1])
            case "Repeat":
                if not row[1].isnumeric():
                    temp_df["Repeat"] = 0
                else:
                    temp_df["Repeat"] = int(row[1])
            case "File Base":
                temp_df["File Base"] = row[1]
            case "Channel":
                cell_lc = row[1]
                temp_df["Cell Assembly LC"] = row[1]
            case "Exp Name":
                temp_df["Exp Name"] = row[1]

    temp_df["Step Capacity (Ah)"] = calculate_step_capacity(temp_df)
    return temp_df, cell_lc


def transform_csv(*data):
    ...
