# -*- coding: utf-8 -*-
import warnings
import pandas as pd
from transformers import transform_mdat
from transformers import transform_csv
from calculator import calculator

warnings.simplefilter(action="ignore", category=FutureWarning)


class DataProcessor:
    def __init__(self):
        self.df = pd.DataFrame()

    def __str__(self):
        info = f"Data frame with {len(self.df)} rows and {len(self.df.columns)} columns.\n"
        info += "Columns: " + ", ".join(self.df.columns) + "\n"
        info += "First few rows:\n"
        info += self.df.head().to_string(index=False)
        return info

    def transform_data(self, file_type, *data):
        if file_type == "mdat":
            transform_mdat(*data)
        elif file_type == "csv":
            transform_csv(*data)
        ...

    def fill_df(self, transformed_df_slice):
        # Exclude empty columns from df slice
        transformed_df_slice = transformed_df_slice.dropna(axis=1, how="all")
        # Check if self.data_frame is empty
        if self.df.empty:
            self.df = transformed_df_slice
        else:
            self.df = pd.concat(
                [self.df, transformed_df_slice],
                ignore_index=True,
                sort=True,
            )

    def calculations(self):
        for test in pd.Series(self.df["Test Type"]).unique():
            calculator(test, self.df[self.df["Test Type"] == test])
        ...

    def export_df(self):
        self.df.to_excel(
            "C:/Users/mhearl/OneDrive - 24M Technologies/Documents/04_Python Scripts/APDP/data/output/out.xlsx"
        )
