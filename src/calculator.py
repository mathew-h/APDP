# -*- coding: utf-8 -*-
"""
Created on Thu Jan  2 16:04:08 2025

@author: mhearl
"""
import pandas as pd
from utils import calculate_soc, calculate_overpotential, calculate_dE_dsqrtt


def calculator(test, df):
    match test:
        case "ICI":
            ici_calcs(df[df["Test Type"] == "ICI"])
        case "CYC":
            cyc_calcs(df[df["Test Type"] == "CYC"])
        case "FORM":
            form_calcs(df[df["Test Type"] == "FORM"])
        case "HPPC":
            hppc_calcs(df[df["Test Type"] == "HPPC"])


def ici_calcs(df):
    for cell in df["Cell Assembly LC"].unique():
        df = calculate_soc(df[df["Cell Assembly LC"] == cell])
        df = calculate_overpotential(df[df["Cell Assembly LC"] == cell])
        df = calculate_dE_dsqrtt(df[df["Cell Assembly LC"] == cell])
    # df.to_excel(
    #     r"C:/Users/mhearl/OneDrive - 24M Technologies/Documents/04_Python Scripts/APDP/data/output/ici_out.xlsx"
    # )


def cyc_calcs(df):
    ...


def form_calcs(df):
    ...


def hppc_calcs(df):
    ...


def main():
    df = pd.read_excel(
        r"C:/Users/mhearl/OneDrive - 24M Technologies/Documents/04_Python Scripts/APDP/data/output/out.xlsx"
    )
    ici_calcs(df)


if __name__ == "__main__":
    main()
