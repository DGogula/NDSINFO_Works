# main.py
import pandas as pd
import os
from config import FACILITY_CONFIG
from utils import (
    clean_admin_noise,
    track_section_changes, track_discussion_changes,
    split_added_removed, merge_lab_values,
    apply_downgrade_logic_ahfl, apply_downgrade_logic_specialties
)
import facility_functions as ff

def main():
    print("Available facilities:", list(FACILITY_CONFIG.keys()))
    facility = input("Enter facility name: ").strip().upper()
    if facility not in FACILITY_CONFIG:
        print("Invalid facility")
        return

    config = FACILITY_CONFIG[facility]
    suffix = config["function_suffix"]

    # Dynamically get the process_row function
    process_row_func = getattr(ff, f"process_row_{suffix}", None)
    if process_row_func is None:
        print(f"Error: process_row_{suffix} not found in facility_functions.py")
        return

    # Load data
    df = pd.read_excel(config["input_file"])  #headerfile loaded here
    print(f"Loaded {len(df)} rows.")

    # --------------------------------------------------------------
    # OPTIONAL: Clean columns only if skip_cleaning is False
    # --------------------------------------------------------------
    if not config.get("skip_cleaning", False):   # default False (clean)
        # Collect all column names that appear in combine_groups
        cols_to_clean = set()
        for col_list in config["combine_groups"].values():
            for col in col_list:
                if col in df.columns:
                    cols_to_clean.add(col)

        print(f"Cleaning {len(cols_to_clean)} columns using common admin noise filter...")
        for col in cols_to_clean:
            df[col] = df[col].astype(str).map(clean_admin_noise)
    else:
        print("Skipping column cleaning (skip_cleaning = True)")

    # --------------------------------------------------------------
    # Combine columns according to combine_groups
    # --------------------------------------------------------------
    for new_col, cols in config["combine_groups"].items():
        df[new_col] = ""
        for col in cols:
            if col in df.columns:
                df[new_col] = df[new_col] + " " + df[col].astype(str)
        df[new_col] = df[new_col].str.strip()

    cols_to_keep = config["columns_to_keep"] + list(config["combine_groups"].keys())
    df_final = df[cols_to_keep]   

    # Apply MDM2 row-wise
    print("Computing MDM2 levels...")
    df_out = df_final.apply(lambda row: process_row_func(row, config), axis=1)

    # Blank MDM2 for acp/procedure visits
    if "Visit" in df_out.columns:
        mask = (df_out["Visit"].astype(str).str.lower() == "acp") | (df_out["Visit"].astype(str).str.lower() == "procedure")
        df_out.loc[mask, ["REASONS FOR MDM2", "MDM2_Level"]] = ""

    # Post-processing
    print("Applying downgrade logic...")
    if config["use_consult_file"]:
        df_out = apply_downgrade_logic_ahfl(df_out)
    else:
        df_out = apply_downgrade_logic_specialties(df_out, config["specialties"])

    print("Tracking Lab Order changes...")
    df_out = track_section_changes(df_out, "Lab Order")
    print("Tracking Lab Review changes...")
    df_out = track_section_changes(df_out, "Lab Review")
    print("Tracking Independent Interpretation changes...")
    df_out = track_section_changes(df_out, "Independent Interpretation")
    print("Tracking Independent Historian changes...")
    df_out = track_section_changes(df_out, "Independent Historian")
    print("Tracking Review Prior Notes changes...")
    df_out = track_section_changes(df_out, "Review Prior Notes")

    if config["specialty_map"]:
        print("Tracking Discussion Management changes...")
        df_out = track_discussion_changes(df_out, config["specialty_map"])

    print("Splitting Added/Removed...")
    df_out = split_added_removed(df_out)

    print("Merging external lab values...")
    df_out = merge_lab_values(df_out, config["lab_values_file"])

    # Save outputs (ensure output folder exists)
    output_folder = os.path.dirname(config["final_excel"])
    if output_folder and not os.path.exists(output_folder):
        os.makedirs(output_folder)

    df_out.to_excel(config["final_excel"], index=False)
    df_out.to_csv(config["final_csv"], index=False, sep=";")
    print(f"Processing completed. Outputs: {config['final_excel']}, {config['final_csv']}")

if __name__ == "__main__":
    main()