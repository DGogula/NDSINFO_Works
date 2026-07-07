import os
import re
import time
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from detect_copd import COPDDetector
from mdm3_format import *
from mdm3_keyword_V3 import *
from mdm3_medication_utils_v3 import *
from uti_process import UtiProcessor
from generate_keyword_variation import generate_variations_major_surgery, verb_prefixes, verb_suffixes

from run_pipeline_v1 import chart_count_date
from chf_process import check_chf_current
from covid_detection import check_covid_current

EMERGENCY_MAJOR_SURGERY = generate_variations_major_surgery (EMERGENCY_MAJOR_SURGERY, verb_prefixes, verb_suffixes) ######## 05-11-2025

facility_list_a = ["AHFL", "CSCC", "CSM", "BCS", "BFS","MSMC","CCCC","LMC","CSRNB","OLGMC","WCMICP","CAICP","H","NL","AR","AMN","ARN","AW"]  ### AHFL, CSCC, CSM, BCS, BFS
facility_list_b = ["WA", "NLO", "MCE","WH"]  ### WA, NLO, MCE

class DateParser:
    """Handles date parsing operations."""
    
    @staticmethod
    def parse_mixed_date(x):
        """Try parsing date from multiple formats."""
        for fmt in ("%m/%d/%Y", "%b-%d-%Y", "%B-%d-%Y","%Y-%m-%d"):
            try:
                return pd.to_datetime(x, format=fmt)
            except Exception:
                continue
        return pd.NaT


class DataLoader:
    """Handles loading and validation of input data."""
    
    def __init__(self, chart_count_date: str):
        self.chart_count_date = chart_count_date
    
    def load_chart_data(self) -> pd.DataFrame:
        """Load and return chart data."""
        chart_path = f"./inter_op/Charts_Mongo_extracted_{self.chart_count_date}.csv"####
        return pd.read_csv(chart_path)
    
    def load_medication_data(self) -> pd.DataFrame:
        """Load and return medication data."""
        med_path = f"./inter_op/Medication_Mongo_extracted_{self.chart_count_date}.csv"####
        return pd.read_csv(med_path)
    
    def validate_input_files(self) -> bool:
        """Validate that input files exist."""
        chart_path = f"./inter_op/Charts_Mongo_extracted_{self.chart_count_date}.csv"####
        med_path = f"./inter_op/Medication_Mongo_extracted_{self.chart_count_date}.csv"####
        return os.path.exists(chart_path) and os.path.exists(med_path)


class ChartDataPreprocessor:
    """Handles preprocessing of chart data."""
    
    def __init__(self, date_parser: DateParser):
        self.date_parser = date_parser
    
    def preprocess(self, chart_df: pd.DataFrame) -> pd.DataFrame:
        """Preprocess chart dataframe."""
        chart_df = chart_df.copy()
        chart_df["formatted_DOS"] = chart_df["DOS"].apply(self.date_parser.parse_mixed_date)
        # chart_df["Med_ANP_Combined_cleaned"] = chart_df["Med_ANP_Combined_cleaned"].apply(safe_eval)
        # chart_df["Med_Medication_Combined_cleaned"] = chart_df["Med_Medication_Combined_cleaned"].apply(safe_eval)
        chart_df["Med_Chart_Medication_Text"] = chart_df["Med_Chart_Medication_Text"].apply(safe_eval)
        return chart_df


class MedicationDataPreprocessor:
    """Handles preprocessing of medication data."""
    
    # def preprocess1(self, med_df: pd.DataFrame) -> pd.DataFrame: ### WA, NLO, MCE
    #     """Preprocess medication dataframe."""
    #     med_df = med_df.copy()
    #     med_df["administered_date"] = med_df["administered_date"].fillna(med_df["scheduled_date"])
    #     med_df["administered_date"] = med_df["administered_date"].astype(str).str.split(";")
    #     med_df = med_df.explode("administered_date")
    #     med_df["administered_date"] = med_df["administered_date"].astype(str).str.strip()
    #     med_df["administered_date"] = med_df["administered_date"].apply(
    #         lambda x: re.sub(r"\s*-\s*", "-", x.strip())
    #     )
    #     med_df["administered_date"] = pd.to_datetime(
    #         med_df["administered_date"], format="%m-%d-%Y", errors="coerce"
    #     )
    #     med_df["Med_MED_ORDER"] = med_df["Med_MED_ORDER"].apply(safe_eval)
    #     return med_df
    def preprocess1(self, med_df: pd.DataFrame) -> pd.DataFrame: ### WA, NLO, MCE
        """Preprocess medication dataframe."""
        med_df = med_df.copy()
        med_df["administered_date"] = med_df["administered_date"].fillna(med_df["scheduled_date"])
        med_df["administered_date"] = med_df["administered_date"].astype(str).str.split(";")
        med_df = med_df.explode("administered_date")
        med_df["administered_date"] = med_df["administered_date"].astype(str).str.strip()
        med_df["administered_date"] = med_df["administered_date"].apply(
            lambda x: re.sub(r"-\s*-", "-", x.strip())
        )
        med_df["administered_date"] = med_df["administered_date"].apply(
            lambda x: re.sub(r"\s*-+\s*", "-", x.strip())
        )
        med_df["administered_date"] = med_df["administered_date"].str.replace(r"(\d{1,2}-\d{2})\s+(\d{4})", r"\1-\2", regex=True)
        med_df["format_administered_date"] = (
            med_df["administered_date"]
            .fillna("")  # handle None
            .str.extract(r"^(\d{1,2}-\d{2}-\d{4})")[0]
        )
        # Convert to datetime (optional)
        med_df["format_administered_date"] = pd.to_datetime(med_df["format_administered_date"], format="%m-%d-%Y", errors="coerce")
        med_df["Med_MED_ORDER"] = med_df["Med_MED_ORDER"].apply(safe_eval)
        return med_df
    
    def preprocess2(self, med_df:pd.DataFrame) -> pd.DataFrame: ### AHFL, CSM, CSCC
        med_df = med_df.copy()
        med_df["ST_DATE"] = med_df["DATE"]
        med_df["DATE"] = med_df["DATE"].apply(normalize_date)
        med_df["END DATE"] = med_df["END DATE"].apply(normalize_date)
        med_df["DATE"] = pd.to_datetime(med_df["DATE"],errors="coerce",format="%m/%d/%Y", dayfirst=False)
        med_df["END DATE"] = pd.to_datetime(med_df["END DATE"],errors="coerce",format="%m/%d/%Y", dayfirst=False)
        # med_df["DATE"] = med_df["DATE"].apply(extract_only_date)
        # med_df["END DATE"] = med_df["END DATE"].apply(extract_only_date)

        # med_df["DATE"] = (
        #     med_df["DATE"]
        #     .str.strip()                      # remove spaces
        #     .replace({"---": None, "Date": None, "": None})   # replace invalid values
        #     .pipe(pd.to_datetime, errors="coerce",format="%m/%d/%Y")             # convert to datetime
        # )
        # med_df["END DATE"] = (
        #     med_df["END DATE"]
        #     .str.strip()                      # remove spaces
        #     .replace({"---": None, "Date": None, "": None})   # replace invalid values
        #     .pipe(pd.to_datetime, errors="coerce",format="%m/%d/%Y")             # convert to datetime
        # )
        med_df["END DATE"] = med_df["END DATE"].fillna(med_df["DATE"])
        med_df["DATE"] = med_df["DATE"].fillna(med_df["END DATE"])
        med_df = pd.concat([expand_row_v4(r) for _, r in med_df.iterrows()], ignore_index=True) ############## expand function
        med_df["Med_MED_ORDER"] = med_df["Med_MED_ORDER"].apply(safe_eval)
        return med_df


class MedicationExtractor:
    """Handles medication extraction and classification."""
    
    def __init__(self, med_df: pd.DataFrame):
        self.med_df = med_df
        if "COMB" in med_df.columns:
            self.med_df["COMB"] = self.med_df["COMB"].str.upper().strip()
        self.med_df["Chart"] = self.med_df["Chart"].str.upper().str.strip()
        print(self.med_df.head())
    
    def extract_medications1(self, input_row: pd.Series) -> List[Dict[str, Any]]: ### WA, NLO, MCE 
        """Extract medications for a specific chart and date."""
        file_name = str(input_row["Chart"]).upper().strip()#input_row["Chart"].str.upper().strip()
        DOS = input_row["formatted_DOS"]
        # chart_med_ANP = input_row["Med_ANP_Combined_cleaned"]
        # chart_med_MED = input_row["Med_Medication_Combined_cleaned"]
        chart_med = input_row["Med_Chart_Medication_Text"]
        
        filter_med_data = self.med_df[
            (self.med_df["format_administered_date"] == DOS) &
            (self.med_df["Chart"] == file_name)
        ]
        
        if filter_med_data.empty:
            return "Missing"
        
        dos_med = []
        for _, row in filter_med_data.iterrows():
            if row["Med_MED_ORDER"]:
                med_col = row["Med_MED_ORDER"][0]
                med_col["route"] = row["route"]
                med_col["medication"] = row["drug_name"]
                med_col["drip"] = row["drip"]
                med_col["strength"] = row["strength"]
                dos_med.append(med_col)
        
        print(f"Medication extraction 1 executing")
        
        return [med for med in dos_med if med.get("name")]
    
    def extract_medications2(self, input_row: pd.Series) -> List[Dict[str, Any]]: ### AHFL, CSM, CSCC, BCS
        """
        Extract medications from the medication order considering the chart.
        """
        input_row = input_row.copy()
        dos_med = []
        file_name = str(input_row["Chart"]).upper().strip()
        #file_name = file_name.strip()
        DOS = input_row["formatted_DOS"]
        ANP_Combined = input_row["ANP_Combined"]
        Medication_Combined = input_row["Medication_Combined"]
        ANP_MED_Combined_str = str(ANP_Combined) + " " + str(Medication_Combined)
        # print(file_name)
        # print(DOS)
        # print(self.med_df["COMB"].head())
        #print(file_name, DOS)
        # Get chart medication names
        # chart_med_ANP = input_row["Med_ANP_Combined_cleaned"]
        # chart_med_MED = input_row["Med_Medication_Combined_cleaned"]
        #print("type", type(chart_med_ANP), type(chart_med_MED))
        chart_med = input_row["Med_Chart_Medication_Text"]
        #print(chart_med)
        #print(chart_med)
        chart_med_name = [med.upper() for med_dict in chart_med 
                        for med in med_dict.get("name", []) if med]
        # Filter medication data
        if "COMB" in self.med_df.columns:
            filter_med_data = self.med_df[
                (self.med_df["DATE"] == DOS) 
                & (self.med_df["Chart"] == file_name)
                & ~(self.med_df["COMB"] == "AMB")
            ]
        else:
            filter_med_data = self.med_df[
                (self.med_df["DATE"] == DOS) 
                & (self.med_df["Chart"] == file_name)
            ]
        # print(f"Filtered Med Data Rows: {len(filter_med_data)}")
        # print(self.med_df.head())
        
        if filter_med_data.empty:
            return "Missing"
        
        # Process PRN medications
        #prn_mask= ((filter_med_data["PRN"].str.upper() == "TRUE")|(filter_med_data["PRN"].str.upper() == "Y")|(filter_med_data["PRN"].str.upper() == "1")|(filter_med_data["PRN"].str.upper() == "YES")|filter_med_data["PRN"].str.contains(r"\bPRN\b", case=False, na=False))
        filter_med_data["PRN"] = filter_med_data["PRN"].astype(str)
        prn_mask = (filter_med_data["PRN"].str.upper().isin(["TRUE", "Y", "1", "YES"])) | filter_med_data["PRN"].str.contains(r"\bPRN\b", case=False, na=False)

       
        
        med_prn = filter_med_data[prn_mask]
        if not med_prn.empty:
            for _, prn_row in med_prn.iterrows():  # Changed variable name
                if prn_row["Med_MED_ORDER"]:
                    med_col = prn_row["Med_MED_ORDER"][0]
                    med_names = med_col.get("name", [])
                    
                    # Check if medication is mentioned in text
                    in_text = any(clean_med_name(name).upper() in ANP_MED_Combined_str 
                                for name in med_names if name)
                    in_struct_chart = any(clean_med_name(str(name)).upper() in chart_med_name 
                                for name in med_names if name)
                    
                    if in_text or in_struct_chart:
                        med_col["medication"] = prn_row["MEDICATION"]
                        med_col["drip"] = ""
                        dos_med.append(med_col)
        
        # Process non-PRN medications
        #med_non_prn = filter_med_data[((filter_med_data["PRN"].str.upper() == "FALSE") or (filter_med_data["PRN"].str.upper() == "NO"))]
        med_non_prn = filter_med_data[~prn_mask]
        if not med_non_prn.empty:
            for _, non_prn_row in med_non_prn.iterrows():  # Changed variable name
                if non_prn_row["Med_MED_ORDER"]:
                    med_col = non_prn_row["Med_MED_ORDER"][0]
                    med_col["medication"] = non_prn_row["MEDICATION"]
                    med_col["drip"] = ""
                    dos_med.append(med_col)
        
        # Filter out empty medication entries
        final_dos_med = [med for med in dos_med if med.get("name")]
        print("Final", len(final_dos_med))
        #print([m.get("medication") for m in final_dos_med])
        return final_dos_med
    #"NLO-BS_100_061125"
    def process_chart_medications(self, chart_df: pd.DataFrame) -> pd.DataFrame:
        """Process medications for all charts."""
        chart_df = chart_df.copy()
        if chart_facility in facility_list_a:
            print("==============Facility A ===================")
        #if "AHFL" in chart_count_date or "CSCC" in chart_count_date or "CSM" in chart_count_date or "BCS" in chart_count_date or "BFS" in chart_count_date:# or "BS" in chart_count_date:
            chart_df["output_medication"] = chart_df.apply(self.extract_medications2, axis=1) ###### change 
        elif chart_facility in facility_list_b:
            print("============Facility b===================")
            chart_df["output_medication"] = chart_df.apply(self.extract_medications1, axis=1)
        else:
            print("===============Facility not recognized for medication extraction.====================")
            chart_df["output_medication"] = chart_df.apply(lambda _: [], axis=1)

        chart_df["output_medication_with_classification"]     = chart_df.apply(drug_classification, axis=1)
        chart_df["MED_ORDER_COUNT"] = chart_df["output_medication_with_classification"].apply(lambda x: len(x) if isinstance(x, list) else 0) 
        chart_df["output_medication_with_classification_anp"] = chart_df.apply(drug_classification_anp, axis=1)
        chart_df["ANP_MED_COUNT"] = chart_df["output_medication_with_classification_anp"].apply(lambda x: len(x) if isinstance(x, list) else 0) 
        return chart_df


class KeywordExtractor:
    """Handles keyword extraction and classification."""
    
    def __init__(self):
        self.Header_names =  ["ANP_Combined","ANP_Combined_cleaned", "Medication_Combined","Medication_Combined_cleaned"]
    
    def extract_keywords(self, chart_df: pd.DataFrame) -> pd.DataFrame:
        """Extract and classify keywords from chart data."""
        chart_df = chart_df.copy()
        
        chart_df["Surgery_discussion"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, Surgery_discussion_list_2))
        chart_df["Risk_factors"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, Risk_factors_list_3))
        chart_df["Risk_phrases"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, Risk_phrases_4))
        chart_df["Sdoh_phrases"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, Sdoh_phrases))

        chart_df["Surgery"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, Surgery_list_1)) ##updated on 04-11-25

        chart_df["EMS_WR"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, Elective_major_surgery_WR)) # Without Risk
        chart_df["DNR_hospitalization"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, DNR_Hospitalization))
        chart_df["Therapy_keyword"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, Therapy_list_low))
        chart_df["Minimal_keyword"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, Mdm_minimal))
        chart_df["Emergency_major_surgery"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, EMERGENCY_MAJOR_SURGERY))
        chart_df["Emergency_Keywords"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, Emergency_keywords))
        chart_df["DVT_PPX"] = chart_df.apply(DVT_Medications, axis=1, args=(self.Header_names,))
        return chart_df


class MDM3RiskCalculator:
    """Handles MDM3 risk level calculation and reasoning."""
    
    def calculate_risk_levels(self, chart_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate MDM3 risk levels and prepare reasoning."""
        chart_df = chart_df.copy()
        chart_df["Validate_Level"] = chart_df.apply(calculate_mdm_risk_v2, axis=1)
        chart_df["Validate_Medication"] = chart_df["Validate_Level"].apply(lambda x: x[1])
        chart_df["MDM3_Level"] = chart_df["Validate_Level"].apply(lambda x: x[0])
        return chart_df
    
    def combine_reasoning_columns(self, chart_df: pd.DataFrame) -> pd.DataFrame:
        """Combine reasoning columns for MDM3 level justification."""
        chart_df = chart_df.copy()
       
        combined_col = ['Surgery', 'Surgery_discussion','Risk_factors','Risk_phrases',
       'Emergency_major_surgery', 'Sdoh_phrases', 'EMS_WR',
       'DNR_hospitalization', 'Therapy_keyword', 'Minimal_keyword','DVT_PPX','Emergency_Keywords','Validate_Medication']
        chart_df["Reason_For_MDM3"] = chart_df[combined_col].to_dict(orient="records")
        chart_df["Reason_For_MDM3"] = chart_df["Reason_For_MDM3"].apply(clean_dict)
        chart_df["Reason_For_MDM3"] = chart_df["Reason_For_MDM3"].apply(
            merge_validate_medication_v2, keep_duplicates=True
        )
        return chart_df


class OutputProcessor:
    """Handles final output processing and file saving."""
    
    def __init__(self, chart_count_date: str):
        self.chart_count_date = chart_count_date
    
    def prepare_final_dataframe(self, chart_df: pd.DataFrame) -> pd.DataFrame:
        """Prepare final dataframe with required columns and formatting."""
        os.makedirs("./output", exist_ok=True)
        base_path = f"./output/{self.chart_count_date}_Full_Medication_Test"
        chart_df["output_medication_str"] = chart_df["output_medication"].apply(lambda x: str(x))
        combine_col = ["ANP_Combined_cleaned","Medication_Combined_cleaned", "output_medication_str"]

        chart_df["REFERENCE TEXT MDM3"] = chart_df[combine_col].apply(lambda x: '~'.join(x.dropna()), axis=1)
        #chart_df["output_medication_str"] = chart_df["output_medication"].apply(lambda x: "~")
        # Rename columns
        # chart_df = chart_df.rename(columns={
        #     "Reason_For_MDM3": "REASONS FOR MDM3", 
        #     "Visit_time": "Visit Time"
        # })
        # chart_df.to_excel(f"{base_path}.xlsx", index=False, engine="openpyxl")
        # # Select final columns
        # ###"Filename", "DOS", "Visit", "Visit Time", "MDM3_Level", "REASONS FOR MDM3", "REFERENCE TEXT MDM3"
        # final_cols = ["Filename","Chart", "DOS", "Visit Time", "Visit", "MDM3_Level", "REASONS FOR MDM3","REFERENCE TEXT MDM3"]
        # final_df = chart_df[final_cols].copy()
        
        # # Clean empty visits
        # mask = (final_df["Visit"] == "acp") | (final_df["Visit"] == "procedure")
        # final_df.loc[mask, ["REASONS FOR MDM3", "MDM3_Level"]] = ""


        #Extracted_Data_for_MDM3
        chart_df = chart_df.rename(columns={
            "Reason_For_MDM3":"REASONS FOR MDM3",
            "Visit_time":"Visit Time",
            "Page_No":"Page No",
        })
        chart_df.to_excel(f"{base_path}.xlsx", index=False, engine="openpyxl")
        # Select final columns
        ###"Filename", "DOS", "Visit", "Visit Time", "MDM3_Level", "REASONS FOR MDM3", "REFERENCE TEXT MDM3"
        if "Page No" in chart_df.columns:
            final_cols = ["Filename","Chart", "DOS","Visit", "Visit Time","MDM3_Level", "REASONS FOR MDM3","REFERENCE TEXT MDM3","Page No"]#,
        else:
            final_cols = ["Filename","Chart", "DOS","Visit", "Visit Time","MDM3_Level", "REASONS FOR MDM3","REFERENCE TEXT MDM3"]
        #final_cols = ["Filename","Chart", "DOS", "Visit Time", "Visit", "MDM3_Level", "REASONS FOR MDM3"]
        final_df = chart_df[final_cols].copy()
        
        # Clean empty visits
        mask = (final_df["Visit"] == "acp") | (final_df["Visit"] == "procedure")
        final_df.loc[mask, ["REASONS FOR MDM3", "MDM3_Level"]] = ""

        # Clean formatting for Excel output
        final_df["REASONS FOR MDM3"] = final_df["REASONS FOR MDM3"].apply(clean_and_format_dict_v3) ###### updated on 15-11-2025
        #final_df = final_df.rename(columns={"REASONS FOR MDM3":"Extracted_Data_for_MDM3","Visit Time": "Visit_time"}) ## Temporary
        final_df = final_df.astype(str).apply(lambda col: col.str.replace(";", "", regex=False))
        final_df = final_df.astype(str).apply(lambda col: col.str.replace("\n", "~", regex=False))
        
        return final_df
    
    def save_outputs(self, final_df: pd.DataFrame) -> None:
        """Save outputs to Excel and CSV files."""
        os.makedirs("./output", exist_ok=True)
        text_identifier = chart_count_date.split("_")
        facility = text_identifier[0]
        count    = text_identifier[1]
        base_path = f"./output/{facility}_{count}_Chart-MED"
        
        final_df.to_excel(f"{base_path}.xlsx", index=False, engine="openpyxl")
        final_df.to_csv(f"{base_path}.csv", index=False, sep=";")
    
    def write_missing_medications(self) -> None:
        """Write missing medications to file."""
        unique_list = list(set(missing_medication_list))
        os.makedirs("./missing", exist_ok=True)
        file_name = f"./missing/medications_name_missing_{self.chart_count_date}.txt"
        
        with open(file_name, "w",encoding="utf-8") as f:
            for med in unique_list:
                f.write(":".join(list(med)) + "\n")
        
        print(f"Missing Medication list saved in folder: {file_name}")


class MDM3Processor:
    """
    Main class to process chart and medication data, extract medications,
    classify risk levels, and generate MDM3-level outputs.
    """
    
    def __init__(self, chart_count_date: str):
        self.chart_count_date = chart_count_date
        self.date_parser = DateParser()
        self.data_loader = DataLoader(chart_count_date)
        
    def process(self) -> pd.DataFrame:
        """Execute the complete MDM3 processing pipeline."""
        # Validate input files
        if not self.data_loader.validate_input_files():
            raise FileNotFoundError("Required input files are missing")
        
        # Load data
        chart_df = self.data_loader.load_chart_data()#[:20]
        med_df = self.data_loader.load_medication_data()
        
        # Preprocess data
        chart_preprocessor = ChartDataPreprocessor(self.date_parser)
        med_preprocessor = MedicationDataPreprocessor()
        
        chart_df = chart_preprocessor.preprocess(chart_df)
        if chart_facility in facility_list_a:
        #if "AHFL" in chart_count_date or "CSCC" in chart_count_date or "CSM" in chart_count_date or "BCS" in chart_count_date or "BFS" in chart_count_date: #"BS" in chart_count_date:
            med_df = med_preprocessor.preprocess2(med_df) ####### change AHFL, CSM, CSCC
        elif chart_facility in facility_list_b:
            med_df = med_preprocessor.preprocess1(med_df)  ####### change WA, NLO, MCE
        else:
            print("Facility not recognized for medication preprocessing.")
        # Extract medications
        med_extractor = MedicationExtractor(med_df)
        chart_df = med_extractor.process_chart_medications(chart_df)
        
        # Extract keywords
        keyword_extractor = KeywordExtractor()
        chart_df = keyword_extractor.extract_keywords(chart_df)

        # Extract uti keywords and lab wbc count
        processor = UtiProcessor()
        df_uti_detected = processor.process_uti(chart_df)
        # Option 1: Combine only available lab columns and extract WBC
        #print("Option 1: Combining ONLY available lab columns for WBC extraction")
        chart_df = processor.process_dataframe_lab_columns_wbc(df_uti_detected)

        # Check for current CHF terms
        # Added on 12-11-2025
        chart_df["CHF_True"] = chart_df["ANP"].apply(check_chf_current)

        #### check copd keywords
        #### added on 13-11-2025
        detector = COPDDetector()
        chart_df["ANP_COPD"] = chart_df["ANP"].apply(detector.detect)

        # Check for current covid terms
        # Added on 27-11-2025
        chart_df["COVID_True"] = chart_df["ANP"].apply(check_covid_current)
        
        # Calculate risk levels
        risk_calculator = MDM3RiskCalculator()
        chart_df = risk_calculator.calculate_risk_levels(chart_df)
        chart_df = risk_calculator.combine_reasoning_columns(chart_df)
        
        # Prepare and save outputs
        output_processor = OutputProcessor(self.chart_count_date)
        final_df = output_processor.prepare_final_dataframe(chart_df)
        output_processor.save_outputs(final_df)
        output_processor.write_missing_medications()
        
        return final_df


def process_mdm3_extraction(chart_count_date: str) -> pd.DataFrame:
    """
    Main function to process chart and medication data, extract medications,
    classify risk levels, and generate MDM3-level outputs.

    Args:
        chart_count_date (str): Unique identifier used in input/output filenames.

    Returns:
        pd.DataFrame: Final processed dataframe with MDM3 levels.
    """
    processor = MDM3Processor(chart_count_date)
    return processor.process()


# Example usage
if __name__ == "__main__":
    start_time = time.time()
    chart_count_date = chart_count_date #"AHFL-BS-2_1_061125"#"CSCC-BS_200_051125"# "CSM-BS-1_200_051125"#"CSCC-BS_200_051125"#"CSM-BS-2_200_051125" #"CSM-BS-1_200_051125" #"CSCC-BS_200_051125"  #"AHFL_100_291025"
    #chart_count_date = "BCS-BS_200_131125"# "WA-BS_200_071125"
    chart_facility = chart_count_date.split("-")[0]
    print(f"Started >>> {chart_count_date}, facility: {chart_facility}")
    final_df = process_mdm3_extraction(chart_count_date)
    print(final_df["MDM3_Level"].value_counts())
    print("Filename: ", final_df["Filename"].iloc[5])
    print(final_df["REASONS FOR MDM3"].iloc[5].replace("~", "\n"))
    print("Processing complete. Saved results in ./output/")
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Function executed in {execution_time:.4f} seconds")
    print(f"Completed: {chart_count_date}")