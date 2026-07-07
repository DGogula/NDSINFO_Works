import re
import os
import pandas as pd
from run_pipeline_v1 import chart_count_date, chart_path, medication_path, Target, target_path
from header_variation import data_columns_anp_others, data_columns_medication, chart_med_variations


def clean_text(text):
    """ Cleans the input text by removing unwanted characters and normalizing spaces, while keeping newlines intact. """
    text = text.replace("nan", " ")
    text = re.sub(r"[^a-zA-Z0-9.,/%\-\n ]", " ", text)  # keep \n intact
    text = re.sub(r"[ \t]+", " ", text).strip()  # collapse spaces/tabs only
    return text

def remove_after_prn(text: str) -> str:
    text = text.upper()
    # Look for PRN MEDICATIONS only if it starts at the beginning of a line
    return re.split(r'\nPRN MEDICATIONS\b', text, flags=re.IGNORECASE)[0].rstrip()

def extract_filenames(excel_path, selection_columns=['Filename']):
    """
    Reads an Excel file, extracts filenames from specified columns, 
    and cleans them by removing prefixes/suffixes.

    Args:
        excel_path (str): Path to the Excel file.
        selection_columns (list): List of column names to extract.

    Returns:
        list: A list of cleaned filenames.
    """
    # Read Excel file
    selection = pd.read_excel(excel_path, engine='openpyxl')
    
    # Combine data from specified columns
    combined = pd.concat([selection[c] for c in selection_columns], ignore_index=True)
    
    # Convert to list
    selection_list = combined.to_list()
    
    # Extract and clean filenames
    selection_list = [
        file.split("_")[-1].split(".")[0].strip()
        for file in selection_list if isinstance(file, str)
    ]
    
    return selection_list


# Example usage:
# result = extract_filenames('./target_files/Target_MCE_100.xlsx')
# print(result[:10])


def load_and_prepare_chart_and_medication(chart_path, medication_path):
    """
    Loads chart and medication Excel files, and prepares both DataFrames
    by extracting and cleaning 'Filename' and 'Chart' columns.

    Args:
        chart_path (str): Path to the chart Excel file.
        folder_path (str): Path to the folder containing the medication Excel file.

    Returns:
        tuple: (chart_full, medication) as pandas DataFrames.
    """
    # --- Load Chart Data ---
    chart_full = pd.read_excel(chart_path, engine='openpyxl')

    # Process chart filenames
    chart_full["Filename_mod"] = chart_full["Filename"].str.rsplit(".", n=1).str[0]
    chart_full["Chart"]        = chart_full["Filename_mod"].str.split("_").str[1].str.strip()

    # --- Load Medication Data ---
    #medication_path = os.path.join(folder_path, "MongoMedication_headers.xlsx")
    medication = pd.read_excel(medication_path, engine='openpyxl')

    # Process medication filenames
    medication["Filename"] = medication["filename"].str.split("_").str[1]
    medication["Chart"]    = medication["Filename"].str.split(".").str[0].str.strip()

    return chart_full, medication



def process_and_export_chart_medication(
    chart_full, 
    medication, 
    selection_list, 
    chart_count_date, 
    clean_text_func,
    output_dir="./inter_op"
):
    """
    Filters chart and medication data based on selected chart IDs,
    combines relevant text columns, cleans them, and exports results to Excel.

    Args:
        chart_full (pd.DataFrame): The chart DataFrame (preprocessed).
        medication (pd.DataFrame): The medication DataFrame (preprocessed).
        selection_list (list): List of chart identifiers to filter.
        chart_count_date (str): Date string for output filenames.
        clean_text_func (function): Function to clean text content.
        output_dir (str, optional): Directory to save Excel outputs. Defaults to './inter_op'.

    Returns:
        tuple: (filtered_chart, filtered_medication) as pandas DataFrames.
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    ### AHFL, CSCC, CSM
    
    # data_columns_anp_others = ['Assessment','Assessment & Plan','Assessment/Plan','Assessment','Assessment & Plan','Assessment and Plan','A/P','Assessment',
    #                          'Assessment & Plan','DVT prophylaxis','Social Determinants of Health', 'Social History','Discharge Diagnoses', 'Discharge Exam',
    #                          'Assessment and Plan','Plan','SDOH','Social Determinants of health',"Nutrition","Disposition"]# changes on 27-10-2025 # For AHFL, DVT PPX coming in Nutrition
    # data_columns_medication = ["Current Facility-Administered Medications","MEDICATIONS",'current facility-Administered Medications','current medication infusions', 
    #                        'current scheduled meds','display current scheduled meds','medication','Drug Management', 'Drug. Management', 'Drug.Management',
    #                        'Medication', 'Medications','Inpatient List of Medications','Scheduled Meds'] #changes on 27-10-25
    # # Added on 29-10-2025
    # chart_med_variations = ['Assessment','Assessment & Plan','Assessment/Plan','Assessment','Assessment & Plan', 'Assessment and Plan',"Current Facility-Administered Medications","MEDICATIONS",'current facility-Administered Medications','current medication infusions', 
    #                        'current scheduled meds','display current scheduled meds','medication','Medication', 'Medications','Inpatient List of Medications','Scheduled Meds']
    
    # data_columns_anp_others = ['Assessment','Assessment & Plan','Assessment/Plan','Assessment','Assessment & Plan','Assessment and Plan','A/P','Assessment',
    #                          'Assessment & Plan','DVT prophylaxis','Social Determinants of Health', 'Social History','Discharge Diagnoses', 'Discharge Exam',
    #                          'Assessment and Plan','Plan','SDOH','Social Determinants of health',"Nutrition","Disposition",
    #                          'Assessment', 'Assessments','Discharge Diagnosis','Health Concerns','Plan',
    #                          'A/P', 'ASSESSMENT','Assessments','Plan','DISCHARGE DIAGNOSES',
    #                          'Assessment/Plan', 'Assessments/Problem List','Plan','Discharge Diagnosis','Justification for hospitalization',
    #                          'Assessment','Assessment & plan','DVT Prophylaxis','plan',
    #                          ]# changes on 27-10-2025 # For AHFL, DVT PPX coming in Nutrition
    # data_columns_medication = ["Current Facility-Administered Medications","MEDICATIONS",'current facility-Administered Medications','current medication infusions', 
    #                         'current scheduled meds','display current scheduled meds','medication','Drug Management', 'Drug. Management', 'Drug.Management',
    #                         'Medication', 'Medications','Inpatient List of Medications','Scheduled Meds','Discharge Medications',
    #                         'Active Medications','Medications','DISCHARGE MEDICATIONS','MEDICINES ON DISCHARGE',
    #                         'Active Medications','Discharge Medications','Discharge medications',
    #                         ] #changes on 27-10-25
    # # Added on 29-10-2025
    # chart_med_variations = ['Assessment','Assessment & Plan','Assessment/Plan','Assessment','Assessment & Plan', 'Assessment and Plan',"Current Facility-Administered Medications","MEDICATIONS",'current facility-Administered Medications','current medication infusions', 
    #                         'current scheduled meds','display current scheduled meds','medication','Medication', 'Medications','Inpatient List of Medications','Scheduled Meds',
    #                         'Assessment','Assessment & Plan','Assessment/Plan',
    #                         'A/P', 'ASSESSMENT','Assessments','Plan',
    #                         'Assessment/Plan', 'Assessments/Problem List','Plan',
    #                         'Discharge Medications','Active Medications','Medications','DISCHARGE MEDICATIONS','MEDICINES ON DISCHARGE',
    #                         'Active Medications','Discharge Medications',
    #                         'Assessment','Assessment & plan','plan',
    #                         ]
    
    med_columns = list(set([col for col in chart_med_variations if col in chart_full.columns]))
    
    data_for_medication1 = list(set([col for col in data_columns_anp_others if col in chart_full.columns]))
    data_for_medication2 = list(set([col for col in data_columns_medication if col in chart_full.columns]))
    #chart_full = chart_full[0:10]
    
    print("ANP and Others:\n", data_for_medication1)
    print("Medication Columns:\n", data_for_medication2)
    print("Medication col for extraction:\n", med_columns)
    if len(selection_list) == 0:
        selection_list = chart_full["Chart"].unique().tolist()

    ### AHFL
    ### CSM
    # data_for_medication1 =['Assessment','Assessment & Plan', 'Assessment and Plan','DVT prophylaxis','Social Determinants of Health', 'Social History','Discharge Diagnoses', 'Discharge Exam']
    # data_for_medication2 =['current facility-Administered Medications','current medication infusions', 'current scheduled meds','display current scheduled meds','medication']
    ### CSCC
    # data_for_medication1 = ['A/P', 'Assessment',
    #        'Assessment & Plan', 'Assessment and Plan','Plan',
    # 'SDOH','Social Determinants of health']
    # data_for_medication2 = ['Drug Management', 'Drug. Management', 'Drug.Management','Medication', 'Medications','Inpatient List of Medications','Scheduled Meds']
    
    

    # --- Filter chart data ---
    filtered_chart = chart_full[chart_full['Chart'].isin(selection_list)].copy()

    #filtered_chart = filtered_chart[0:200] ###################### 

    #### Added on 12-11-2025 to remove PRN MEDICATIONS partS
    if "MEDICATIONS" in chart_full.columns: 
        filtered_chart["MEDICATIONS"] = filtered_chart["MEDICATIONS"].astype(str).apply(remove_after_prn)

    # Combine text fields for analysis
    filtered_chart['ANP_Combined'] = filtered_chart[data_for_medication1].apply(
        lambda x: '\t'.join(x.dropna()), axis=1
    )
    filtered_chart['Medication_Combined'] = filtered_chart[data_for_medication2].apply(
        lambda x: '\t'.join(x.dropna()), axis=1
    )
    # Added on 29-10-2025
    filtered_chart['Chart_Medication_Text'] = filtered_chart[med_columns].apply(
        lambda x: '\n'.join(x.dropna()), axis=1
    )

    # Clean text
    filtered_chart["ANP_Combined_cleaned"]        = filtered_chart["ANP_Combined"].astype(str).apply(clean_text_func)
    filtered_chart["Medication_Combined_cleaned"] = filtered_chart["Medication_Combined"].astype(str).apply(clean_text_func)

    # --- Filter medication data ---
    filtered_medication = medication[medication["Chart"].isin(selection_list)].copy()

    # --- Export to Excel ---
    chart_output_path = os.path.join(output_dir, f'Charts_Mongo_extracted_{chart_count_date}.xlsx')
    medication_output_path = os.path.join(output_dir, f'Medication_Mongo_extracted_{chart_count_date}.xlsx')

    filtered_chart.to_excel(chart_output_path, index=False, engine='openpyxl')
    filtered_medication.to_excel(medication_output_path, index=False, engine='openpyxl')
    print(f"Filtered medication: {filtered_medication.shape[0]}")

    return filtered_chart, filtered_medication



if __name__ == "__main__":
    chart_count_date = chart_count_date
    Target = Target
    if Target:
        target_list = extract_filenames(target_path)
        print("target: ", target_list[0:5])
    else:
        target_list = []
    print(f"Started Processing >>> {chart_count_date}, Target: {Target}")
    chart_path      = chart_path #r"charts\AHFL\BS\AHFL_BS_Missing_all data.xlsx"
    medication_path = medication_path #r"medication\AHFL\MongoMedication_BS_06-11-2025.xlsx" #.\medication\AHFL"

    # chart_path = r".\charts\AHFL\AHFL_100_All_Header_Data.xlsx"
    # medication_path = r"medication\AHFL\MongoMedication_100.xlsx" #.\medication\AHFL"

    # Example usage:
    chart_full, medication = load_and_prepare_chart_and_medication(chart_path, medication_path)

    filtered_chart, filtered_medication = process_and_export_chart_medication(
        chart_full=chart_full,
        medication=medication,
        selection_list=target_list,
        chart_count_date=chart_count_date,
        clean_text_func=clean_text,
    )
    print("DOS Available:", filtered_chart.shape[0])
    print("Charts Available:", filtered_chart['Chart'].nunique())