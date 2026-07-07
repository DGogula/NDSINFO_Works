import pandas as pd
from pymongo import MongoClient
import re
import ast

def process_chart_by_filename_without_calling_Mango(
    base_filename: str,
    excel_path: str,
) -> pd.DataFrame:
    df = pd.read_excel(excel_path)

    # ✅ Match all rows that start with base_filename (including suffix like _48, _49, etc.)
    matches = df[df["filename"].astype(str).str.startswith(base_filename)].copy()

    # display(matches)

    rows = []
    for _, d in matches.iterrows():
        fname = d["filename"]
        lower = d.get("sections", {})
        if isinstance(lower, str):
            try:
                lower = ast.literal_eval(lower)   # parse the dict string safely
            except Exception:
                lower = {}
        if isinstance(lower, dict):
            lower = lower.get("lower", {})
        else:
            lower = {}

        if lower and isinstance(lower, dict):
            max_len = max(len(v) for v in lower.values())
            for i in range(max_len):
                row = {"filename": fname}
                for key, values in lower.items():
                    row[key] = values[i] if i < len(values) else None
                rows.append(row)

    if not rows:
        return pd.DataFrame(columns=["filename","Administered Date","START DATE","END DATE","MEDICATION","ORDER DETAIL"])

    final_df = pd.DataFrame(rows)

    # display(final_df)
    # -------- 2) Filter COMB == 'IP' if COMB exists --------
    if "COMB" in final_df.columns:
        filtered_df = final_df[final_df["COMB"] == "IP"].copy()
    else:
        filtered_df = final_df.copy()

    # Ensure DATE/END DATE exist
    if "DATE" not in filtered_df.columns:
        filtered_df["DATE"] = ""
    if "END DATE" not in filtered_df.columns:
        filtered_df["END DATE"] = ""

    # -------- 3) Clean dates --------
    filtered_df.loc[:, "DATE"] = (
        filtered_df["DATE"].astype(str).str.replace(".", "", regex=False).str.strip()
    )
    filtered_df.loc[:, "END DATE"] = (
        filtered_df["END DATE"].astype(str).str.strip().replace({"_": "", "0": "", "nan": ""})
    )

    # Drop invalid DATE rows
    filtered_df = filtered_df[~filtered_df["DATE"].isin(["", "_", "nan", "NaT", "None"])].copy()

    # To datetime
    for col in ["DATE", "END DATE"]:
        filtered_df.loc[:, col] = pd.to_datetime(filtered_df[col], errors="coerce")

    # Rename DATE -> START DATE
    filtered_df = filtered_df.rename(columns={"DATE": "START DATE"})

    # -------- 4) Expand Administered Date across range --------
    expanded_rows = []
    for _, r in filtered_df.iterrows():
        start = r["START DATE"]
        end = r["END DATE"]
        if pd.isna(start):
            continue
        if pd.isna(end) or end < start:
            end = start

        for dt in pd.date_range(start, end, freq="D"):
            nr = r.copy()
            nr["Administered Date"] = dt
            expanded_rows.append(nr)

    expanded_df = pd.DataFrame(expanded_rows)

    # Guarantee columns even if empty
    if expanded_df.empty:
        for col in ["START DATE", "END DATE", "Administered Date"]:
            if col not in expanded_df.columns:
                expanded_df[col] = pd.NaT

    # Format dates to MM/DD/YYYY
    for col in ["START DATE", "END DATE", "Administered Date"]:
        expanded_df[col] = pd.to_datetime(expanded_df[col], errors="coerce").dt.strftime("%m/%d/%Y")

    # -------- 5) Reorder columns --------
    order = [
        "filename",
        "Administered Date",
        "START DATE",
        "END DATE",
        "MEDICATION",
        "ORDER DETAIL",
    ]
    expanded_df = expanded_df.reindex(columns=order + [c for c in expanded_df.columns if c not in order])

    # Sort by filename + date
    tmp = expanded_df.copy()
    tmp["__sort_date"] = pd.to_datetime(tmp["Administered Date"], errors="coerce")
    tmp = tmp.sort_values(["filename", "__sort_date"]).drop(columns="__sort_date")

    # -------- 6) Add PRN flag & drop unused --------
    def get_prn(order_detail):
        if pd.isna(order_detail):
            return ""
        return "PRN" if "PRN" in str(order_detail).upper() else ""

    tmp["PRN"] = tmp["ORDER DETAIL"].apply(get_prn)

    for col in ["PROVIDER", "COMB"]:
        if col in tmp.columns:
            tmp.drop(columns=[col], inplace=True)

    # if output_path:
    #     tmp.to_excel(output_path, index=False)

    return tmp

def process_chart_by_filename(
    base_filename: str,
    mongo_uri: str = "mongodb://172.19.19.87:27017/",
    db_name: str = "MEDICATIONPAGE_100",
    coll_name: str = "DATA",
    output_path: str = None
) -> pd.DataFrame:
    """
    Extract only docs whose filename starts with `base_filename` (e.g. 'AHFL_HMV001983973'),
    flatten/clean/filter, expand Administered Date between START and END DATE (inclusive),
    reorder columns, and optionally save to Excel.

    Returns the expanded, ordered DataFrame.
    """
    client = MongoClient(mongo_uri)
    coll = client[db_name][coll_name]

    # Fetch only matching docs: filenames like 'AHFL_HMV001983973_48', '..._49', etc.
    # Regex anchors at start; allow optional _suffix
    cursor = coll.find({"filename": {"$regex": f"^{re.escape(base_filename)}(_|$)"}})

    # -------- 1) Flatten documents (handle uneven list lengths) --------
    rows = []
    for d in cursor:
        fname = d.get("filename", "")
        lower = d.get("sections", {}).get("lower", {})
        if lower and isinstance(lower, dict) and len(lower) > 0:
            max_len = max(len(v) for v in lower.values())
            for i in range(max_len):
                row = {"filename": fname}
                for key, values in lower.items():
                    row[key] = values[i] if i < len(values) else None
                rows.append(row)
        else:
            rows.append({"filename": fname})

    if not rows:
        # Nothing matched — return empty DF with expected columns
        cols = ["filename","Administered Date","START DATE","END DATE","COMB","MEDICATION","ORDER DETAIL"]
        empty = pd.DataFrame(columns=cols)
        if output_path:
            empty.to_excel(output_path, index=False)
        return empty

    final_df = pd.DataFrame(rows)

    # -------- 2) Filter COMB == 'IP' --------
    if "COMB" not in final_df.columns:
        # No COMB -> nothing to keep
        filtered_df = final_df.iloc[0:0].copy()
    else:
        filtered_df = final_df[final_df["COMB"] == "IP"].copy()

    # If DATE/END DATE missing, create to avoid KeyErrors
    if "DATE" not in filtered_df.columns:
        filtered_df["DATE"] = ""
    if "END DATE" not in filtered_df.columns:
        filtered_df["END DATE"] = ""

    # -------- 3) Clean START/END dates --------
    # DATE -> remove '.'; trim
    filtered_df.loc[:, "DATE"] = (
        filtered_df["DATE"].astype(str).str.replace(".", "", regex=False).str.strip()
    )

    # END DATE -> remove '_' and '0' placeholders; trim
    filtered_df.loc[:, "END DATE"] = (
        filtered_df["END DATE"].astype(str).str.strip().replace({"_": "", "0": "", "nan": ""})
    )

    # Drop rows where DATE is blank/invalid placeholders
    filtered_df = filtered_df[~filtered_df["DATE"].isin(["", "_", "nan", "NaT", "None"])].copy()

    # Convert both to datetime; then force MM/DD/YYYY
    for col in ["DATE", "END DATE"]:
        filtered_df.loc[:, col] = pd.to_datetime(filtered_df[col], errors="coerce")

    # Rename DATE -> START DATE
    filtered_df = filtered_df.rename(columns={"DATE": "START DATE"})

    # -------- 4) Expand rows over Administered Date range --------
    expanded_rows = []
    for _, r in filtered_df.iterrows():
        start = r["START DATE"]
        end = r["END DATE"]

        if pd.isna(start):
            continue  # skip if no valid start

        if pd.isna(end) or end < start:
            end = start

        for dt in pd.date_range(start, end, freq="D"):
            new_r = r.copy()
            new_r["Administered Date"] = dt
            expanded_rows.append(new_r)

    expanded_df = pd.DataFrame(expanded_rows)

    if expanded_df.empty:
        # Ensure columns exist even if empty
        for col in ["START DATE", "END DATE", "Administered Date"]:
            if col not in expanded_df.columns:
                expanded_df[col] = pd.NaT

    # Format dates back to MM/DD/YYYY
    for col in ["START DATE", "END DATE", "Administered Date"]:
        expanded_df[col] = pd.to_datetime(expanded_df[col], errors="coerce").dt.strftime("%m/%d/%Y")

    # -------- 5) Reorder columns --------
    order = [
        "filename",
        "Administered Date",
        "START DATE",
        "END DATE",
        "COMB",
        "MEDICATION",
        "ORDER DETAIL",
    ]
    expanded_df = expanded_df.reindex(columns=order + [c for c in expanded_df.columns if c not in order])

    # Sort by filename + Administered Date
    tmp = expanded_df.copy()
    tmp["__sort_date"] = pd.to_datetime(tmp["Administered Date"], errors="coerce")
    tmp = tmp.sort_values(["filename", "__sort_date"]).drop(columns="__sort_date")

    my_df=tmp
    # route_keywords = {
    #     "IV": [
    #         "IVPB", " IV ", "INFUSION", "BOLUS", "FLUSH", "SOLUTION", "INJECTION", "VIAL", "ANESTHESIA","IN SODIUM"
    #     ],
    #     # "Subcutaneous": [
    #     #     "SUBCUTANEOUS", "SC", "SUBQ", "SYRINGE"
    #     # ],
    #     "Intramuscular": [
    #         "IM"
    #     ],
    #     "Oral": [
    #         "TABLET", "CAPSULE", " PO ", "ODT", "DISINTEGRATING",
    #         "EFFERVESCENT", "SOLUTION", "SUSPENSION", "LIQUID",
    #         "SYRUP", "LOZENGE", "PACKET", "POWDER","ORAL GEL"
    #     ],
    #     "Inhalation": [
    #         "INHALER", "PUFF", "AEROSOL", "NEBULIZER", "SPRAY"
    #     ],
    #     "Ophthalmic": [
    #         "OPHTHALMIC", "EYE DROP", "EYE", "SUSP"
    #     ],
    #     "Topical": [
    #         "OINTMENT", "CREAM", "TOPICAL", "JELLY", "LOTION", "APPLICATOR", "STICK", "PATCH"
    #     ],
    #     "Rectal": [
    #         "SUPPOSITORY", "RECTAL", "ENEMA"
    #     ],
    #     "Sublingual/Buccal": [
    #         "SUBLINGUAL", "BUCCAL", "LOZENGE", "MOUTH"
    #     ],
    #     "Other/Special": [
    #         "RADIO-ISOTOPE", "TECHNETIUM", "PATIENT OWN MED"
    #     ]
    # }

    # def get_route(medication: str) -> str:
    #     med_upper = medication.upper()
    #     for route, keywords in route_keywords.items():
    #         if any(kw in med_upper for kw in keywords):
    #             return route
    #     return "Unknown"

    def get_prn(order_detail: str) -> str:
        if pd.isna(order_detail):
            return ""
        return "PRN" if "PRN" in order_detail.upper() else ""

    # Example usage
    # my_df["Route"] = my_df["MEDICATION"].apply(get_route)
    my_df["PRN"] = my_df["ORDER DETAIL"].apply(get_prn)
    del my_df["PROVIDER"]
    del my_df["COMB"]
    # my_df[["Medication RISK", "Matched Medication"]] = my_df.apply(
    # lambda row: pd.Series(get_medication_risk(row["MEDICATION"], row["Route"])),
    # axis=1)

    

    return my_df

# import config_SCP as cfg
# cdr_df = pd.read_excel(cfg.DRUG_IV_DF)
# # cdr_df = pd.read_excel("Drugs_from_Critical_Care_CDR_which_makes_level_High.xlsx")
# rx_df = pd.read_excel("RX_DRUG_DOT_COM.xlsx")
# otc_df = pd.read_excel("OTC_DRUG_DOT_COM.xlsx")
# intensive_df = pd.read_excel("Intensive_drugs.xlsx")

# # Normalize all drug lists to uppercase for substring matching
# cdr_list = [str(x).upper() for x in cdr_df["DRUGS"].dropna().unique()]
# rx_list = [str(x).upper() for x in pd.concat([rx_df["Drug_Name"], rx_df["Generic_Name"], rx_df["Brand_Name"]]).dropna().unique()]
# otc_list = [str(x).upper() for x in pd.concat([otc_df["Drug_Name"], otc_df["Generic_Name"], otc_df["Brand_Name"]]).dropna().unique()]
# intensive_list = [str(x).upper() for x in intensive_df["DRUGS"].dropna().unique()]

# def get_medication_risk(medication: str, route: str) -> str:
#     """
#     Classify medication risk level using Route-based rules + drug reference lists.
#     """

#     med_upper = str(medication).upper()

#     if pd.isna(medication) or pd.isna(route):
#         return "Not Categorized", med_upper

#     med_upper = str(medication).upper()
#     route = str(route).strip()

#     # -------- Rule 1: IV / Subcutaneous / Intramuscular / Inhalation --------
#     if route in ["IV", "Subcutaneous", "Intramuscular", "Inhalation"]:
#         for drug in cdr_list:
#             if drug.strip() in med_upper:
#                 return "Critical Care CDR",drug.strip()
#         for drug in intensive_list:
#             if drug.strip() in med_upper:
#                 return "PARENTAL",drug.strip()
#         return "RX", med_upper   # fallback if not found

#     # -------- Rule 2: Rectal / Other/Special --------
#     if route in ["Rectal", "Other/Special"]:
#         return "RX",med_upper

#     # -------- Rule 3: Oral / Ophthalmic / Topical / Sublingual/Buccal --------
#     if route in ["Oral", "Ophthalmic", "Topical", "Sublingual/Buccal"]:
#         for drug in rx_list:
#             if drug.strip() in med_upper: 
#                 return "RX",drug.strip()
#         for drug in otc_list:
#             if drug.strip() in med_upper:
#                 return "OTC",drug.strip()
#         return "Not Categorized",med_upper

#     # -------- Rule 4: Catch all --------
#     return "Not Categorized",med_upper