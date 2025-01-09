# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import re
from sklearn.linear_model import LinearRegression


def calculate_capacity(df):
    """
    For mdat files, calculate the capacity that accumulates for adjacent charge and discharge steps

    Parameters
    ----------
    df : DataFrame
        Contains echem data for a single Cell Assembly LC and test.

    Returns
    -------
    Updated dataframe with apacity values.

    """
    repeats = pd.Series(df["Repeat"]).unique()
    steps = pd.Series(df["Step"]).unique()
    started_discharge = False
    started_charge = False
    discharge_capacity = 0
    charge_capacity = 0
    for repeat in repeats:
        for step in steps:
            # Filter for the specific step and repeat
            temp_df = df[(df["Step"] == step) & (df["Repeat"] == repeat)]

            if not temp_df.empty:  # Ensure temp_df is not empty
                # Check if this is a discharge step
                if temp_df["Current (A)"].mean() < 0:
                    if not started_discharge:
                        # Initialize discharge capacity for the first discharge step
                        started_discharge = True
                        discharge_capacity = temp_df[
                            "Step Capacity (Ah)"
                        ].mean()

                    else:
                        # Accumulate capacity for subsequent discharge steps
                        discharge_capacity += temp_df[
                            "Step Capacity (Ah)"
                        ].mean()

                    # Update the DataFrame with the cumulative capacity
                    df.loc[
                        (df["Step"] == step) & (df["Repeat"] == repeat),
                        "Capacity (Ah)",
                    ] = discharge_capacity

                elif temp_df["Current (A)"].mean() > 0:
                    # Check if this is a charge step
                    if not started_charge:
                        # Initialize charge capacity for first charge
                        started_charge = True
                        charge_capacity = temp_df["Step Capacity (Ah)"].mean()

                    else:
                        # Accumulate capacity for subsequent charge steps
                        charge_capacity += temp_df["Step Capacity (Ah)"].mean()

                    # Update the DataFrame with the cumulative capacity
                    df.loc[
                        (df["Step"] == step) & (df["Repeat"] == repeat),
                        "Capacity (Ah)",
                    ] = charge_capacity
    return df


def calculate_step_capacity(df):
    df = df.sort_values(by="Time (s)")
    return get_time_delta((df["Time (s)"]) / 3600) * abs(
        df["Current (A)"].mean()
    )


def get_time_delta(s):
    """
    Calculates the time delta for a time series

    Parameters
    ----------
    s : TYPE
        DESCRIPTION.

    Returns
    -------
    float
        Time difference from first index and last index position of a time series.

    """
    return abs(float(s.iloc[0]) - float(s.iloc[-1]))


def find_test_type(s):
    if re.match(r".*ICI.*", s):
        return "ICI"
    elif re.match(r".*FORM.*", s):
        return "FORM"
    elif re.match(r".*CYC.*", s):
        return "CYC"
    elif re.match(r".*HPPC.*", s):
        return "HPPC"
    else:
        return "N/A"


def calculate_soc(df):
    """
    From capacity values, calculate SOC for each step/repeat
    Parameters
    ----------
    df : DataFrame
        Contains echem data for a single Cell Assembly LC and test.

    Returns
    -------
    Updated dataframe with apacity values.

    """
    repeats = pd.Series(df["Repeat"]).unique()
    steps = pd.Series(df["Step"]).unique()
    started_discharge = False
    started_charge = False
    max_capacity = df["Capacity (Ah)"].max()
    for repeat in repeats:
        for step in steps:
            # Filter for the specific step and repeat
            temp_df = df[(df["Step"] == step) & (df["Repeat"] == repeat)]

            if not temp_df.empty:  # Ensure temp_df is not empty
                # Check if this is a discharge step
                if temp_df["Current (A)"].mean() < 0:
                    # Calculate SOC increment
                    soc_increment = (
                        temp_df["Step Capacity (Ah)"].mean() / max_capacity
                    ) * 100
                    if not started_discharge:
                        # Initialize discharge capacity for the first discharge step
                        started_discharge = True
                        discharge_soc = 100
                    else:
                        # Accumulate SOC for subsequent discharge steps
                        discharge_soc -= soc_increment

                    # Update the DataFrame with the SOC
                    df.loc[
                        (df["Step"] == step) & (df["Repeat"] == repeat),
                        "SOC (%)",
                    ] = discharge_soc

                # Check if this is a charge step
                elif temp_df["Current (A)"].mean() > 0:
                    # Calculate SOC increment
                    soc_increment = (
                        temp_df["Step Capacity (Ah)"].mean() / max_capacity
                    ) * 100

                    # Check if this is a charge step
                    if not started_charge:
                        # Initialize charge capacity for first charge
                        started_charge = True
                        charge_soc = 0
                    else:
                        # Accumulate SOC for subsequent charge steps
                        charge_soc += soc_increment

                    # Update the DataFrame with the SOC
                    df.loc[
                        (df["Step"] == step) & (df["Repeat"] == repeat),
                        "SOC (%)",
                    ] = charge_soc

    return df


def calculate_overpotential(df):
    """
    Takes ICI df and calculates difference between last current applied voltage and end of rest voltage to measure overpotential

    Parameters
    ----------
    df : DataFrame
        ICI dataframe.

    Returns
    -------
    df : DataFrame
        ICI dataframe, now with overpotential column.

    """
    # Initialize the 'Overpotential (V)' column in the processed DataFrame
    df["Overpotential (V)"] = None

    # Group data by each repeat cycle
    for repeat, repeat_data in df.groupby("Repeat"):
        # Initialize voltage storage for Delithiation and Lithiation
        last_voltage_charge, last_voltage_rest_charge = None, None
        last_voltage_discharge, last_voltage_rest_discharge = None, None
        # Group by steps for each repeat
        for step, step_data in repeat_data.groupby("Step"):
            # Avoid looking at a CV step
            if not step_data["Exp Name"].iloc[0] == "Potentiostatic":
                # If current is negative, get the last voltage value on discharge
                if step_data["Current (A)"].mean() < 0:
                    last_voltage_discharge = step_data["Voltage (V)"].iloc[-1]
                # If current is positive, get the last voltage value on charge
                elif step_data["Current (A)"].mean() > 0:
                    last_voltage_charge = step_data["Voltage (V)"].iloc[-1]
                # If rest step, perform overpotential calculations
                elif step_data["Exp Name"].iloc[0] == "Open Circuit":
                    # Ensure the previous step exists
                    if step > 0:
                        prev_step_data = repeat_data[repeat_data["Step"] == step - 1]
                        if not prev_step_data.empty:
                            if prev_step_data["Current (A)"].mean() < 0:
                                last_voltage_rest_discharge = step_data["Voltage (V)"].iloc[-1]
                                if last_voltage_discharge is not None:
                                    overpotential_discharge = abs(last_voltage_discharge - last_voltage_rest_discharge)
                                    df.loc[prev_step_data.index, "Overpotential (V)"] = overpotential_discharge
                                # Reset variables for next use
                                last_voltage_discharge = None
                                last_voltage_rest_discharge = None
                            elif prev_step_data["Current (A)"].mean() > 0:
                                last_voltage_rest_charge = step_data["Voltage (V)"].iloc[-1]
                                if last_voltage_charge is not None:
                                    overpotential_charge = abs(last_voltage_charge - last_voltage_rest_charge)
                                    df.loc[prev_step_data.index, "Overpotential (V)"] = overpotential_charge
                                # Reset variables for next use
                                last_voltage_charge = None
                                last_voltage_rest_charge = None
    return df


def calculate_dE_dsqrtt(df):
    # Initialize 'k' column
    df["k"] = None

    # Dictionary to store regression results for each repeat and rest step
    regression_results = {}

    for repeat, repeat_data in df.groupby("Repeat"):
        regression_results[repeat] = {}
        for step, step_data in repeat_data.groupby("Step"):
            # Avoid looking at a CV step
            if not step_data["Exp Name"].iloc[0] == "Potentiostatic":
                # If rest step, perform regression for k
                if step_data["Exp Name"].iloc[0] == "Open Circuit":
                    # Ensure the previous step exists
                    if step > 0:
                        prev_step_data = repeat_data[
                            repeat_data["Step"] == step - 1
                        ]
                        if not prev_step_data.empty:
                            step_data["Time (s)"] = (
                                step_data["Time (s)"]
                                - step_data["Time (s)"].min()
                            )
                            # Calculate the square root of time
                            step_data["sqrt_time"] = np.sqrt(
                                step_data["Time (s)"]
                            )

                            # Filter data within the desired range (1 to 5 in sqrt_time) and Voltage <= 1.5 V
                            filtered_data = step_data[
                                (step_data["sqrt_time"] >= 1)
                                & (step_data["sqrt_time"] <= 5)
                                & (
                                    step_data["Voltage (V)"] <= 1.5
                                )  # Trim high-voltage points
                            ]

                            # Prepare the data for regression
                            X = filtered_data["sqrt_time"].values.reshape(
                                -1, 1
                            )
                            y = filtered_data["Voltage (V)"].values

                            # Perform linear regression if there are enough data points
                            if len(X) > 1:
                                reg = LinearRegression().fit(X, y)

                                df.loc[step_data.index, "k"] = np.abs(
                                    reg.coef_[0]
                                )

                        # # Store the regression model and relevant data, including pre-rest current
                        # regression_results[repeat][step] = {
                        #     "model": reg,
                        #     "intercept": reg.intercept_,
                        #     "slope": reg.coef_[0],
                        #     "R^2": reg.score(X, y),
                        #     "k": (
                        #         np.abs(reg.coef_[0])
                        #     )
                        # }

                    else:
                        print(
                            f"Not enough data points for regression in Repeat {repeat}, Step {step}."
                        )

    return df


def main():
    df = pd.read_excel(
        r"C:/Users/mhearl/OneDrive - 24M Technologies/Documents/04_Python Scripts/APDP/data/output/out.xlsx"
    )
    df = calculate_soc(df)
    df = calculate_overpotential(df)
    df = calculate_dE_dsqrtt(df)
    df.to_excel(
        r"C:/Users/mhearl/OneDrive - 24M Technologies/Documents/04_Python Scripts/APDP/data/output/ici_out.xlsx"
    )


if __name__ == "__main__":
    main()
