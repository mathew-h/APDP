# -*- coding: utf-8 -*-
"""
Created on Wed Oct 23 13:40:08 2024

@author: mhearl
"""

import os
import shutil
import pandas as pd
from datetime import datetime
from tkinter import Tk
from tkinter.filedialog import askopenfilenames
from zipfile import ZipFile
from tkinter import messagebox
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from sklearn.linear_model import LinearRegression
import numpy as np
import seaborn as sns
from collections import defaultdict
import re

electrode_area = 77
lithiation_current_step = "Step04"
lithiation_rest_step = "Step05"
delithiation_current_step = "Step11"
delithiation_rest_step = "Step12"

# Molar volume of electrode

# Specific Surface area of the electrode


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def main():
    # clear()
    global processed_data
    start = datetime.now()

    zips = select_files()

    extracted_paths = unzip_mdats(zips)

    all_data = get_data(extracted_paths)

    processed_data = cumulate_capacity(all_data)

    processed_data = calculate_overpotential(processed_data)

    processed_data = calculate_soc(processed_data)

    print(processed_data.head())
    finish = datetime.now()
    # get variables for naming the file that will be saved - current time, test type (FORM or CYC), test request
    cur_time = finish.strftime("_%y%m%d_%H%M%S")
    testfolder = os.path.dirname(zips[0]).split("/")[-1]
    fname = testfolder + "_Combined_Solartron" + cur_time
    savedir = os.path.dirname(zips[0])
    csvfile = savedir + "/" + fname + ".csv"
    print("Saving as CSVs to ", fname)
    processed_data.to_csv(
        csvfile,
        header=True,
    )
    finish2 = datetime.now()
    elapsed2 = finish2 - start
    print("Done")
    print("Completed in " + str(elapsed2))

    # plot_voltage_vs_time_for_rest(processed_data)

    regression_results = regression_rest_steps(processed_data)

    plot_k_vs_ocp(processed_data, regression_results)

    ocp_slope_df = pseudo_OCP_slope(processed_data)

    plot_ocp_slope_vs_voltage(ocp_slope_df)

    # plot_overpotential_and_voltage_vs_soc(processed_data)

    # diffusion_df = calculate_D(ocp_slope_df, regression_results)

    return processed_data


def select_files():
    root = Tk()
    root.attributes("-topmost", 1)
    root.withdraw()

    files = list(askopenfilenames(parent=root, title="Choose files"))
    all_files = files.copy()

    msgbox = messagebox.askquestion(
        "Add files", "Add extra files", icon="warning"
    )

    while msgbox == "yes":
        additional_files = list(
            askopenfilenames(parent=root, title="Choose additional files")
        )
        all_files.extend(additional_files)
        msgbox = messagebox.askquestion(
            "Add files", "Add more files", icon="warning"
        )

    root.destroy()
    return all_files


def unzip_mdats(zs):
    tempdir = os.path.dirname(zs[0]) + "/temp/"
    extracted_paths = []
    for _zip in zs:
        with ZipFile(_zip, "r") as z:
            for file_info in z.infolist():
                if file_info.is_dir():
                    continue
                if ".mpro" in file_info.filename:
                    continue

                file_path = file_info.filename
                extracted_path = file_path.split("/", 1)[1]
                extracted_path = os.path.join(tempdir, extracted_path)
                extracted_paths += [extracted_path]
                os.makedirs(os.path.dirname(extracted_path), exist_ok=True)
                with open(extracted_path, "wb") as dst:
                    with z.open(file_info, "r") as src:
                        shutil.copyfileobj(src, dst)
        dst.close()

    return extracted_paths


def get_data(files):
    all_data = pd.DataFrame()

    for file in files:
        # print(f"Processing {file}")
        tempfile = open(file, "r")
        Lines = tempfile.readlines()

        # Initialize line tracking variables
        line_num, rep, time, loop, step = 0, 0, 0, 0, 0

        if ".cor" in file:
            for line in Lines:
                line_num += 1
                if (
                    "End Header:                   MultiStat_DCData_1.0"
                    in line
                ):
                    h = line_num
                if "Repeat:" in line:
                    rep = Lines[line_num - 1].split(sep=":")[1].strip()
                elif line_num == len(Lines) - 1 and rep == 0:
                    rep = "No Repeat"
                if "Run:" in line:
                    run = line_num - 1
                if "Channel:" in line:
                    ch = line_num - 1
                if "Step:" in line and step == 0:
                    step = line_num - 1
                if "Loop Count:" in line:
                    loop = Lines[line_num - 1].split(sep=":")[1].strip()
                elif line_num == len(Lines) - 1 and loop == 0:
                    loop = "No loop"
                if "File Base:" in line:
                    fb = line_num - 1
                if "File Path:" in line:
                    fp = line_num - 1
                if "Exp Type:" in line:
                    exptype = line_num - 1
                if "Open Circuit Potential (V):" in line:
                    ocv = line_num - 1
                if "End Information:            DC File Columns" in line:
                    cols = Lines[line_num - 2].split()
                if "Date:" in line:
                    date = line_num - 1
                if "Time:" in line and time == 0:
                    time = line_num - 1
                if "Exp Title:" in line:
                    exptitle = line_num - 1
                if "Exp Name:" in line:
                    expname = line_num - 1

            try:
                # Load data from file
                csv = pd.read_csv(file, sep="\t", header=h, names=cols)
            except Exception:
                continue

            # Drop unwanted columns
            drop_list = [x for x in cols if "Loop" in str(x)]
            main_minus_aux = [x for x in cols if "Main-" in str(x)]
            drop_list.extend(main_minus_aux)
            csv = csv.drop(columns=drop_list, axis=1)

            # Rename columns
            csv = csv.rename(
                columns=lambda c: "Time (Seconds)"
                if "T(S" in c
                else "Voltage (V)"
                if "E(V)" in c
                else "Current (A)"
                if "I(" in c
                else "Delithiation (C)"
                if "Delithiation(" in c
                else "Energy (Wh)"
                if "Energy(" in c
                else c
            )

            # Assign additional metadata columns
            csv["Repeat"] = rep
            csv["Run"] = Lines[run].split(sep=":")[1].strip()
            csv["Channel"] = Lines[ch].split(sep=":")[1].strip()
            csv["Step"] = Lines[step].split(sep=":")[1].strip()
            csv["Loop Count"] = loop
            csv["File Name"] = Lines[fb].split(sep=":")[1].strip()
            csv["File Path"] = Lines[fp].split(sep="h:")[1].strip()
            csv["Exp Type"] = Lines[exptype].split(sep=":")[1].strip()
            csv["OCV"] = Lines[ocv].split(sep=":")[1].strip()
            csv["Exp Title"] = Lines[exptitle].split(sep=":")[1].strip()
            csv["Exp Name"] = Lines[expname].split(sep=":")[1].strip()
            csv["Exp Start Time"] = (
                Lines[date].split(sep=":")[1].strip()
                + " "
                + Lines[time].split(sep=":", maxsplit=1)[1:][0].strip()
            )

            # Calculate Capacity and Energy if not present
            if "Delithiation (C)" in csv.columns:
                csv["Capacity (Ah)"] = csv["Delithiation (C)"] / 3600
                csv = csv.drop("Delithiation (C)", axis=1)
            else:
                csv["Capacity (Ah)"] = (
                    csv["Time (Seconds)"].diff() / 3600 * csv["Current (A)"]
                ).cumsum()
            if "Energy (Wh)" not in csv.columns:
                csv["Energy (Wh)"] = (
                    csv["Voltage (V)"] * csv["Capacity (Ah)"]
                ).cumsum()

            # Calculate dQ/dV
            csv["raw dQ/dV (Ah/V)"] = (
                csv["Current (A)"]
                * csv["Time (Seconds)"].diff(periods=40)
                / 3600
                / abs(csv["Voltage (V)"].diff(periods=40))
            )
            csv["dQ/dV (Ah/V)"] = csv.groupby("Step")[
                "raw dQ/dV (Ah/V)"
            ].transform(
                lambda x: x.rolling(
                    window=120, win_type="hamming", center=True
                ).mean()
            )
            csv["dQ/dV (Ah/V)"] = csv["dQ/dV (Ah/V)"].dropna()

            # Drop columns with all NA values to avoid FutureWarning
            csv = csv.dropna(axis=1, how="all")

            # Concatenate to all_data if csv has rows
            if not csv.empty:
                all_data = pd.concat([all_data, csv], ignore_index=True)

        tempfile.close()

    return all_data


def cumulate_capacity(d, electrode_area=1.0):
    """
    Calculate cumulative capacities for lithiation (discharge) and delithiation (charge).

    Parameters:
    d: DataFrame containing the data.
    electrode_area: Electrode area for current density calculation (default is 1.0 m^2).

    Returns:
    Updated DataFrame with cumulative capacities.
    """
    # Sort data for easier processing
    all_data = d.sort_values(by=["Channel", "Repeat", "Time (Seconds)"]).copy()

    # Initialize cumulative capacity trackers
    cumulative_discharge = 0
    cumulative_charge = 0

    if "Cumulative Capacity (Ah)" in all_data.columns:
        all_data["Cumulative Capacity (Ah)"] = all_data[
            "Cumulative Capacity (Ah)"
        ].astype(float)
    else:
        # Create a column for Cumulative Capacity if it doesn't already exist
        all_data["Cumulative Capacity (Ah)"] = 0.0

    # Function to get the last capacity values for Lithiation and Delithiation
    def get_last_capacity_values(df):
        # Filter for Lithiation steps (Current < 0) and Delithiation steps (Current > 0)
        discharge_data = df[df["Current (A)"] < 0]
        charge_data = df[df["Current (A)"] > 0]

        # Get the last capacity value for each repeat for Lithiation and Delithiation
        last_discharge_capacity = (
            discharge_data.groupby("Repeat")["Capacity (Ah)"].last().abs()
        )
        last_charge_capacity = (
            charge_data.groupby("Repeat")["Capacity (Ah)"].last().abs()
        )

        return last_discharge_capacity, last_charge_capacity

    # Iterate over each Repeat
    for repeat in all_data["Repeat"].unique():
        # Extract subset for this repeat
        repeat_data = all_data[all_data["Repeat"] == repeat]

        # Iterate over each row index in repeat_data to update Delithiation/Lithiation capacity
        for idx in repeat_data.index:
            is_applied_current = (
                "Galvanostatic" in all_data.at[idx, "Exp Name"]
            )
            current_value = all_data.at[idx, "Current (A)"]

            # Ensure that 'Capacity (Ah)' has a valid value before using it
            capacity_value = all_data.at[idx, "Capacity (Ah)"]
            if pd.isna(capacity_value):
                continue  # Skip this row if 'Capacity (Ah)' is NaN

            # Check if the row is for Lithiation or Delithiation based on current and experiment type
            if (
                is_applied_current and current_value < 0
            ):  # Lithiation cycle step
                all_data.at[
                    idx, "Cumulative Capacity (Ah)"
                ] = cumulative_discharge + abs(float(capacity_value))
                all_data.at[idx, "Current Density (A/m^2)"] = (
                    all_data.at[idx, "Current (A)"] / electrode_area
                )

            elif (
                is_applied_current and current_value > 0
            ):  # Delithiation cycle step
                all_data.at[
                    idx, "Cumulative Capacity (Ah)"
                ] = cumulative_charge + abs(float(capacity_value))
                all_data.at[idx, "Current Density (A/m^2)"] = (
                    all_data.at[idx, "Current (A)"] / electrode_area
                )

        # Carry over the final capacity value to the next repeat
        (
            last_discharge_capacity,
            last_charge_capacity,
        ) = get_last_capacity_values(repeat_data)

        if repeat in last_discharge_capacity:
            cumulative_discharge = last_discharge_capacity[repeat]

        if repeat in last_charge_capacity:
            cumulative_charge = last_charge_capacity[repeat]

    return all_data.sort_values(by=["Channel", "Repeat", "Time (Seconds)"])


def calculate_soc(d):
    # Sort data for easier processing
    all_data = d.sort_values(by=["Channel", "Repeat", "Time (Seconds)"]).copy()

    # Initialize SOC trackers
    soc_delithiation = 100
    soc_lithiation = 0

    # Ensure SOC (%) column exists by setting initial default values
    all_data[
        "SOC (%)"
    ] = 0.0  # Set initial SOC to float for compatibility with calculations

    # Iterate over each Repeat
    for repeat in all_data["Repeat"].unique():
        # Extract subset for this repeat
        repeat_data = all_data[all_data["Repeat"] == repeat]

        # Determine if this repeat is a charge (delithiation) or discharge (lithiation) cycle
        first_current_value = repeat_data["Current (A)"].iloc[0]

        # Update SOC only at the beginning of each repeat based on charge or discharge
        if first_current_value > 0:  # Delithiation cycle step
            current_soc = soc_delithiation
            soc_delithiation -= 1.67  # Decrement SOC for the next repeat
        elif first_current_value < 0:  # Lithiation cycle step
            current_soc = soc_lithiation
            soc_lithiation += 1.67  # Increment SOC for the next repeat
        else:
            current_soc = None  # No change if current is zero or indeterminate

        # Assign the current SOC to each row in the repeat
        all_data.loc[repeat_data.index, "SOC (%)"] = (
            current_soc if current_soc is not None else all_data["SOC (%)"]
        )

    return all_data.sort_values(by=["Channel", "Repeat", "Time (Seconds)"])


def calculate_overpotential(processed):
    # Initialize the 'Overpotential (V)' column in the processed DataFrame
    processed["Overpotential (V)"] = None

    # Group data by each repeat cycle
    for repeat, repeat_data in processed.groupby("Repeat"):
        # Initialize voltage storage for Delithiation and Lithiation
        last_voltage_charge, last_voltage_rest_charge = None, None
        last_voltage_discharge, last_voltage_rest_discharge = None, None

        # Process each row to detect applied current and rest steps
        for idx, row in repeat_data.iterrows():
            # Detect step type
            is_applied_current = "Galvanostatic" in row["Exp Name"]
            is_rest = "Open Circuit" in row["Exp Name"]

            # Capture Delithiation (charge) voltage
            if is_applied_current and row["Current (A)"] > 0:
                last_voltage_charge = row["Voltage (V)"]

            elif is_rest and last_voltage_charge is not None:
                # Capture all indices for the current "Open Circuit" step in the same repeat
                rest_indices = repeat_data[
                    (repeat_data.index >= idx)
                    & (repeat_data["Exp Name"] == "Open Circuit")
                ].index
                last_voltage_rest_charge = row["Voltage (V)"]
                overpotential_charge = abs(
                    last_voltage_charge - last_voltage_rest_charge
                )

                # Broadcast overpotential across all rows of the current rest step in the repeat
                processed.loc[
                    rest_indices, "Overpotential (V)"
                ] = overpotential_charge

                # Reset for the next Delithiation cycle
                last_voltage_charge, last_voltage_rest_charge = None, None

            # Capture Lithiation (discharge) voltage
            elif is_applied_current and row["Current (A)"] < 0:
                last_voltage_discharge = row["Voltage (V)"]

            elif is_rest and last_voltage_discharge is not None:
                # Capture all indices for the current "Open Circuit" step in the same repeat
                rest_indices = repeat_data[
                    (repeat_data.index >= idx)
                    & (repeat_data["Exp Name"] == "Open Circuit")
                ].index
                last_voltage_rest_discharge = row["Voltage (V)"]
                overpotential_discharge = abs(
                    last_voltage_discharge - last_voltage_rest_discharge
                )

                # Broadcast overpotential across all rows of the current rest step in the repeat
                processed.loc[
                    rest_indices, "Overpotential (V)"
                ] = overpotential_discharge

                # Reset for the next Lithiation cycle
                last_voltage_discharge, last_voltage_rest_discharge = (
                    None,
                    None,
                )

    return processed


def regression_rest_steps(d):
    # Sort data for easier processing
    all_data = d.sort_values(by=["Channel", "Repeat", "Time (Seconds)"]).copy()

    # Dictionary to store regression results for each repeat and rest step
    regression_results = {}

    # Dictionary to store the pre-rest current values for each repeat and current step
    pre_rest_current = {}

    # Mapping between rest steps and their corresponding current steps
    rest_to_current_step = {
        lithiation_rest_step: lithiation_current_step,
        delithiation_rest_step: delithiation_current_step,
    }

    # Loop through each repeat to capture the current value before each current step
    for repeat in all_data["Repeat"].unique():
        # Filter for the data within the current repeat
        repeat_data = all_data[all_data["Repeat"] == repeat]

        # Capture current value before Lithiation current step
        discharge_end_current = repeat_data[
            repeat_data["Step"] == lithiation_current_step
        ]
        if not discharge_end_current.empty:
            pre_rest_current[
                (repeat, lithiation_current_step)
            ] = discharge_end_current.iloc[-1]["Current (A)"]

        # Capture current value before Delithiation current step
        charge_end_current = repeat_data[
            repeat_data["Step"] == delithiation_current_step
        ]
        if not charge_end_current.empty:
            pre_rest_current[
                (repeat, delithiation_current_step)
            ] = charge_end_current.iloc[-1]["Current (A)"]

    # Perform regression on rest steps
    for repeat in all_data["Repeat"].unique():
        regression_results[
            repeat
        ] = {}  # Initialize a dictionary for this repeat

        for rest_step in [lithiation_rest_step, delithiation_rest_step]:
            # Filter for the specified rest step and repeat number
            rest_step_data = all_data[
                (all_data["Step"] == rest_step)
                & (all_data["Repeat"] == repeat)
            ].copy()

            # Set the start time of the rest to 0 for this step
            rest_step_data["Time (Seconds)"] = (
                rest_step_data["Time (Seconds)"]
                - rest_step_data["Time (Seconds)"].min()
            )

            # Calculate the square root of time
            rest_step_data["sqrt_time"] = np.sqrt(
                rest_step_data["Time (Seconds)"]
            )

            # Filter data within the desired range (1 to 5 in sqrt_time) and Voltage <= 1.5 V
            filtered_data = rest_step_data[
                (rest_step_data["sqrt_time"] >= 1)
                & (rest_step_data["sqrt_time"] <= 5)
                & (
                    rest_step_data["Voltage (V)"] <= 1.5
                )  # Trim high-voltage points
            ]

            # Prepare the data for regression
            X = filtered_data["sqrt_time"].values.reshape(-1, 1)
            y = filtered_data["Voltage (V)"].values

            # Perform linear regression if there are enough data points
            if len(X) > 1:
                reg = LinearRegression().fit(X, y)

                # Retrieve the corresponding current step
                current_step = rest_to_current_step[rest_step]

                # Retrieve pre-rest current value, with a default value of 0 if not found
                pre_rest_current_value = pre_rest_current.get(
                    (repeat, current_step), 0.0
                )

                # Store the regression model and relevant data, including pre-rest current
                regression_results[repeat][rest_step] = {
                    "model": reg,
                    "intercept": reg.intercept_,
                    "slope": reg.coef_[0],
                    "R^2": reg.score(X, y),
                    "pre_rest_current": np.abs(
                        pre_rest_current_value
                    ),  # Safely use np.abs()
                    "k": (
                        np.abs(reg.coef_[0])
                        / np.abs(pre_rest_current_value / electrode_area)
                    )
                    if pre_rest_current_value != 0
                    else None,
                    "filtered_data": filtered_data,  # Store filtered data for reference
                }
            else:
                print(
                    f"Not enough data points for regression in Repeat {repeat}, Step {rest_step}."
                )

    return regression_results


def pseudo_OCP_slope(d):
    # Sort data for easier processing
    all_data = d.sort_values(by=["Channel", "Repeat", "Time (Seconds)"]).copy()

    # Dictionary to store pseudo OCP
    pseudo_OCP = []

    # Collect pseudo OCP and cell voltage for lithiation and delithiation rest steps
    for repeat in all_data["Repeat"].unique():
        repeat_data = all_data[all_data["Repeat"] == repeat]

        # Lithiation rest step
        lithiation_data = repeat_data[
            repeat_data["Step"] == lithiation_rest_step
        ]
        if not lithiation_data.empty:
            pseudo_ocp_value = lithiation_data.iloc[0]["Voltage (V)"]
            time_value = lithiation_data.iloc[0]["Time (Seconds)"]
            cell_voltage = lithiation_data.iloc[0][
                "Voltage (V)"
            ]  # Assuming this is the cell voltage
            pseudo_OCP.append(
                {
                    "Repeat": repeat,
                    "Step": lithiation_rest_step,
                    "Time (Seconds)": time_value,
                    "Pseudo OCP (V)": pseudo_ocp_value,
                    "Cell Voltage (V)": cell_voltage,  # Adding cell voltage
                }
            )

        # Delithiation rest step
        delithiation_data = repeat_data[
            repeat_data["Step"] == delithiation_rest_step
        ]
        if not delithiation_data.empty:
            pseudo_ocp_value = delithiation_data.iloc[0]["Voltage (V)"]
            time_value = delithiation_data.iloc[0]["Time (Seconds)"]
            cell_voltage = delithiation_data.iloc[0][
                "Voltage (V)"
            ]  # Assuming this is the cell voltage
            pseudo_OCP.append(
                {
                    "Repeat": repeat,
                    "Step": delithiation_rest_step,
                    "Time (Seconds)": time_value,
                    "Pseudo OCP (V)": pseudo_ocp_value,
                    "Cell Voltage (V)": cell_voltage,  # Adding cell voltage
                }
            )

    # Convert pseudo_OCP to a DataFrame
    pseudo_OCP_df = pd.DataFrame(pseudo_OCP)

    # Calculate the slope of pseudo OCP vs. time for adjacent repeats of the same step type
    slopes = []
    for step in [lithiation_rest_step, delithiation_rest_step]:
        step_data = pseudo_OCP_df[pseudo_OCP_df["Step"] == step].sort_values(
            by=["Repeat"]
        )
        for i in range(1, len(step_data)):
            prev_row = step_data.iloc[i - 1]
            current_row = step_data.iloc[i]
            time_diff = (
                current_row["Time (Seconds)"] - prev_row["Time (Seconds)"]
            )
            ocp_diff = (
                current_row["Pseudo OCP (V)"] - prev_row["Pseudo OCP (V)"]
            )

            if time_diff > 0:  # Avoid division by zero
                slope = ocp_diff / time_diff
                slopes.append(
                    {
                        "Repeat": current_row["Repeat"],
                        "Step": step,
                        "OCP Slope": slope,
                    }
                )
    # print(slopes)
    # Append slopes to pseudo_OCP_df
    slopes_df = pd.DataFrame(slopes)
    pseudo_OCP_df = pseudo_OCP_df.merge(
        slopes_df, on=["Repeat", "Step"], how="left"
    )

    return pseudo_OCP_df


def calculate_D(df1, df2):
    ...


def plot_voltage_vs_capacity(d):
    # Ensure 'Cumulative Capacity (Ah)' is present and valid
    if "Cumulative Capacity (Ah)" not in d.columns:
        print("Cumulative Capacity (Ah) column is missing")
        return

    # Extract necessary columns
    voltage = d["Voltage (V)"]
    cumulative_capacity = d["Cumulative Capacity (Ah)"]

    # Create the plot
    plt.figure(figsize=(10, 6))
    plt.plot(
        cumulative_capacity,
        voltage,
        marker="o",
        color="b",
        linestyle="-",
        label="Voltage vs Cumulative Capacity",
    )

    # Adding labels and title
    plt.title("Voltage vs Cumulative Capacity (Ah)", fontsize=14)
    plt.xlabel("Cumulative Capacity (Ah)", fontsize=12)
    plt.ylabel("Voltage (V)", fontsize=12)

    # Display gridlines for better readability
    plt.grid(True)

    # Add a legend
    plt.legend()

    # Show the plot
    plt.show()


def plot_ocp_slope_vs_voltage(pseudo_OCP_df):
    """
    Plots the OCP slope vs. cell voltage for lithiation and delithiation processes on the same graph,
    with y-axis values displayed in scientific notation.

    Parameters:
    pseudo_OCP_df (pd.DataFrame): Dataframe containing pseudo OCP, cell voltage, and OCP slope information.
    lithiation_rest_step (int): The step number corresponding to the lithiation rest process.
    delithiation_rest_step (int): The step number corresponding to the delithiation rest process.
    """
    # Add a "Process" column to distinguish lithiation and delithiation data
    pseudo_OCP_df["Process"] = pseudo_OCP_df["Step"].apply(
        lambda step: "Lithiation"
        if step == lithiation_rest_step
        else "Delithiation"
    )

    # Set up the plotting style
    sns.set(style="whitegrid", palette="muted", font_scale=1.2)

    # Create the plot
    plt.figure(figsize=(10, 6))
    scatter = sns.scatterplot(
        data=pseudo_OCP_df,
        x="Cell Voltage (V)",
        y="OCP Slope",
        hue="Process",  # Different colors for lithiation and delithiation
        palette={"Lithiation": "blue", "Delithiation": "red"},
        style="Process",  # Optional: Use marker styles for differentiation
        markers={"Lithiation": "o", "Delithiation": "s"},
        s=50,  # Marker size
    )

    # Configure the y-axis to display scientific notation explicitly
    formatter = ticker.ScalarFormatter(useMathText=True)
    formatter.set_scientific(True)
    formatter.set_powerlimits((-1, 1))  # Force scientific notation
    scatter.yaxis.set_major_formatter(formatter)

    # Add plot titles and labels
    plt.title("OCP Slope vs. Cell Voltage for Lithiation and Delithiation")
    plt.xlabel("Cell Voltage (V)")
    plt.ylabel("OCP Slope (V/s)")
    plt.grid(True)
    plt.legend(title="Process", loc="best")
    plt.tight_layout()
    plt.show()


def plot_k_vs_ocp(all_data, regression_results):
    # Prepare lists to store k and OCP values for Lithiation and Delithiation repeats
    k_discharge = []
    ocp_discharge = []
    k_charge = []
    ocp_charge = []

    # Iterate through the nested dictionary for each repeat and step
    for repeat, steps in regression_results.items():
        # Filter data for the current repeat
        repeat_data = all_data[all_data["Repeat"] == repeat]

        # Extract the final voltage (OCP) for Lithiation (lithiation_rest_step) and Delithiation (Step10)
        ocp_discharge_value = (
            repeat_data[repeat_data["Step"] == lithiation_rest_step][
                "Voltage (V)"
            ].iloc[-1]
            if not repeat_data[
                repeat_data["Step"] == lithiation_rest_step
            ].empty
            else None
        )
        ocp_charge_value = (
            repeat_data[repeat_data["Step"] == delithiation_rest_step][
                "Voltage (V)"
            ].iloc[-1]
            if not repeat_data[
                repeat_data["Step"] == delithiation_rest_step
            ].empty
            else None
        )

        # Iterate over each step in the current repeat
        for step, values in steps.items():
            k_value = values.get("k", None)

            # Ensure that k value exists
            if k_value is None:
                continue  # Skip if no k value in this step

            # Determine if the step is Lithiation (lithiation_rest_step) or Delithiation (delithiation_rest_step) and store OCP accordingly
            if (
                step == lithiation_rest_step
                and ocp_discharge_value is not None
            ):  # Lithiation step
                k_discharge.append(k_value)
                ocp_discharge.append(ocp_discharge_value)
            elif (
                step == delithiation_rest_step and ocp_charge_value is not None
            ):  # Delithiation step
                k_charge.append(k_value)
                ocp_charge.append(ocp_charge_value)

    # Plot for Lithiation steps
    plt.figure(figsize=(10, 5))
    plt.scatter(ocp_discharge, k_discharge, color="blue", label="Lithiation")
    plt.xlabel("Cell Voltage (V)")
    plt.ylabel("k (Ohm s^-0.5 cm^2)")
    plt.title("k vs. V for Lithiation Steps")
    plt.legend()
    plt.grid(True)
    plt.show()

    # Plot for Delithiation steps
    plt.figure(figsize=(10, 5))
    plt.scatter(ocp_charge, k_charge, color="green", label="Delithiation")
    plt.xlabel("Cell Voltage (V)")
    plt.ylabel("k (Ohm s^-0.5 cm^2)")
    plt.title("k vs. V for Delithiation Steps")
    plt.legend()
    plt.grid(True)
    plt.show()


def plot_overpotential_and_voltage_vs_soc(processed):
    # Filter rows with calculated overpotential and SOC and isolate required steps
    plot_data = processed.dropna(subset=["Overpotential (V)", "SOC (%)"])

    # Separate data for lithiation (lithiation_rest_step) and delithiation (Step10) rest steps
    discharge_data = plot_data[
        plot_data["Step"] == lithiation_rest_step
    ]  # Lithiation (discharge) rest step
    charge_data = plot_data[
        plot_data["Step"] == delithiation_rest_step
    ]  # Delithiation (charge) rest step

    # Retrieve last voltage values from applied current steps for lithiation (lithiation_current_step) and delithiation (Step09)
    last_voltage_discharge = (
        processed[processed["Step"] == lithiation_current_step]
        .groupby("Repeat")["Voltage (V)"]
        .last()
    )
    last_voltage_charge = (
        processed[processed["Step"] == delithiation_current_step]
        .groupby("Repeat")["Voltage (V)"]
        .last()
    )

    # Map these last voltage values to rest steps for lithiation and delithiation
    discharge_data = discharge_data.join(
        last_voltage_discharge, on="Repeat", rsuffix="_LastDischarge"
    )
    charge_data = charge_data.join(
        last_voltage_charge, on="Repeat", rsuffix="_LastCharge"
    )

    # Calculate the overvoltage by adding overpotential to last applied current voltage
    discharge_data["Overvoltage (V)"] = (
        discharge_data["Overpotential (V)"]
        + discharge_data["Voltage (V)_LastDischarge"]
    )
    charge_data["Overvoltage (V)"] = (
        charge_data["Overpotential (V)"]
        + charge_data["Voltage (V)_LastCharge"]
    )

    # Plotting
    plt.figure(figsize=(10, 5))

    # Scatter plot for overpotential (original voltage + overpotential)
    plt.scatter(
        discharge_data["SOC (%)"],
        discharge_data["Overpotential (V)"],
        color="blue",
        label="Lithiation Overpotential",
    )
    plt.scatter(
        charge_data["SOC (%)"],
        charge_data["Overpotential (V)"],
        color="green",
        label="Delithiation Overpotential",
    )

    # Line plot for actual cell voltage on lithiation and delithiation
    plt.plot(
        discharge_data["SOC (%)"],
        discharge_data["Voltage (V)_LastDischarge"],
        color="blue",
        linestyle="--",
        label="Lithiation Voltage",
    )
    plt.plot(
        charge_data["SOC (%)"],
        charge_data["Voltage (V)_LastCharge"],
        color="green",
        linestyle="--",
        label="Delithiation Voltage",
    )

    # Line plot for overvoltage (cell voltage + overpotential)
    plt.plot(
        discharge_data["SOC (%)"],
        discharge_data["Overvoltage (V)"],
        color="cyan",
        linestyle="-",
        label="Lithiation Overvoltage",
    )
    plt.plot(
        charge_data["SOC (%)"],
        charge_data["Overvoltage (V)"],
        color="lime",
        linestyle="-",
        label="Delithiation Overvoltage",
    )

    # Set plot labels and title
    plt.xlabel("State of Charge (SOC) (%)")
    plt.ylabel("Voltage (V)")
    plt.title(
        "Overpotential, Cell Voltage, and Overvoltage vs. SOC for Lithiation and Delithiation"
    )
    plt.legend()
    plt.grid(True)

    # Show the plot
    plt.show()


def plot_voltage_vs_time_for_rest(processed, step="Step05", repeat="29"):
    """
    Scatter plot Voltage (V) vs Time (Seconds) and Voltage (V) vs sqrt(Time (Seconds))
    for a specific rest step and repeat.

    Parameters:
    - processed: DataFrame containing the processed data.
    - step: The rest step to filter (e.g., lithiation_rest_step for lithiation or delithiation_rest_step for delithiation).
    - repeat: The specific repeat cycle to filter.
    """
    # Filter the data for the specified rest step and repeat
    rest_data = processed[
        (processed["Step"] == step) & (processed["Repeat"] == repeat)
    ]

    if rest_data.empty:
        print(
            f"No data found for step '{step}' and repeat '{repeat}'. Please check the inputs."
        )
        return

    # Compute the square root of zeroed time
    rest_data = rest_data.copy()  # Avoid modifying the original DataFrame
    minimum_time = rest_data[
        "Time (Seconds)"
    ].min()  # Correct method to get the minimum value
    rest_data["Time (Seconds) Zeroed"] = (
        rest_data["Time (Seconds)"] - minimum_time
    )  # Subtract minimum time
    rest_data["sqrt_time"] = np.sqrt(
        rest_data["Time (Seconds) Zeroed"]
    )  # Compute square root

    # Plot Voltage vs Time
    plt.figure(figsize=(12, 5))

    plt.subplot(1, 2, 1)  # First plot
    plt.scatter(
        rest_data["Time (Seconds)"],
        rest_data["Voltage (V)"],
        label=f"Repeat {repeat} ({step})",
        color="blue",
        alpha=0.7,
    )
    plt.xlabel("Time (Seconds)")
    plt.ylabel("Voltage (V)")
    plt.title(f"Voltage vs Time for {step}, Repeat {repeat}")
    plt.grid(True)
    plt.legend()

    # Plot Voltage vs sqrt(Time)
    plt.subplot(1, 2, 2)  # Second plot
    plt.scatter(
        rest_data["sqrt_time"],
        rest_data["Voltage (V)"],
        label=f"Repeat {repeat} ({step})",
        color="green",
        alpha=0.7,
    )
    plt.xlabel("sqrt(Time (Seconds))")
    plt.ylabel("Voltage (V)")
    plt.title(f"Voltage vs sqrt(Time) for {step}, Repeat {repeat}")
    plt.grid(True)
    plt.legend()

    # Adjust layout and show the plots
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
