# config.py

import os

# Base folder for input files
INPUT_HEADER = "All_header_data"
NEXT_INPUT_HEADER = "NEXT_200_All_Header_Files"
INPUT_LAB_VALUES = "All_lab_data"
INPUT_CONSULT = "Consult_files"
OUTPUT_FOLDER = "Output"
NEXT_OUTPUT_FOLDER = "Next Output"

# ------------------------------------------------------------------
# COMMON SPECIALTIES AND MAPPING (shared across facilities)
# ------------------------------------------------------------------
COMMON_SPECIALTIES = {
    "CARDIOLOGY", "CRITICAL CARE", "ENDOCRINOLOGY", "GASTROENTEROLOGY", "HEMATOLOGY",
    "INFECTIOUS DISEASE", "NEPHROLOGY", "NEUROLOGY", "NEUROSURGERY", "OCCUPATIONAL THERAPY",
    "ONCOLOGY", "ORTHOPEDICS", "PALLIATIVE CARE", "PSYCHIATRY", "PT/OT", "PULMONOLOGY",
    "RESPIRATORY THERAPY", "REHABILITATION", "RHEUMATOLOGY", "SOCIAL WORK", "SPEECH THERAPY",
    "SURGERY", "UROLOGY", "PODIATRY", "DIETARY", "GYNAECOLOGY", "OTOLARYNGOLOGY",
    "WOUND CARE", "OTHER CONSULTANTS AND SERVICES", "OT", "ORTHOPEDIC SURGERY", "GI", "GENERAL SURGERY", "CARDIOLOGIST",     "CARDIOTHORACIC SURGERY", "DIETITIAN", "EMERGENCY MEDICINE", "FAMILY MEDICINE",
    "PATHOLOGY", "PHARMACY", "RADIOLOGY",  "GYN", "INTENSIVE CARE", "ORTHOPEDIC", "ORTHOPEDIC: SURGERY", "PODIATRIC",
    "PULMONARY", "VASCULAR SURGERY", "CARDIAC SURGERY", "THORACIC SURGERY" 
}

COMMON_SPECIALTY_MAP = {spec: spec for spec in COMMON_SPECIALTIES}


# ------------------------------------------------------------------
# FACILITY CONFIGURATIONS
# ------------------------------------------------------------------
FACILITY_CONFIG = {
    # ------------------------------------------------------------------
    # AHFL (uses consult file)
    # ------------------------------------------------------------------
    "AHFL": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "AHFL_All_Header.xlsx"),
        "combine_groups": {
            "assessment_str": ["Assessment", "Assessment & Plan", "Assessment/Plan"],
            "hpi_str": ["History of Present", "History of Present Illness", "History of Present llIness"],
            "lab_str": ["Disposition", "Imaging", "LABS/Studies", "Significant Findings/Tests/Studies", "Social needs"],
            "Result_Date_str": ["Result Date"],
            "phy_str": ["PHYSICAL EXAMINATION", "Physical Exam"],
            "hospital_course_str": ["Hospital Course"],
            "subjective_str": ["Subjective"],
            "objective_str": ["Objective"],
            "code_status_str": ["Code Status"],
            "prn_medications_str": ["PRN MEDICATIONS"],
        },
        "columns_to_keep": ["Sr No", "Filename", "Chart", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "ahfl",
        "specialties": None,
        "specialty_map": None,
        "use_consult_file": True,
        "skip_cleaning": True,   # set to True to skip, False to run cleaning
        "consult_file": os.path.join(INPUT_CONSULT, "Cosult_Order_AHFL_NEW_ALL.xlsx"),
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "AHFL_LAB_OUTPUT_FINAL_180426.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_AHFL_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_AHFL_MDM2.csv"),
    },

    # ------------------------------------------------------------------
    # AMN (uses common specialties)
    # ------------------------------------------------------------------
    "AMN": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "AMN_NEW_200.xlsx"),
        "combine_groups" : {
            "assessment_str": ["Assessment",	"Assessment and Plan",	"Assessment/ Plan",	"Assessment/Plan", "Critical care time"],
            "hospitalcourse_str": ["Hospital course"],
            "hpi_str": ["HPI",	"History of present illness"],
            "lab_str": ["Blood chemistry Studies", "Diagnostic test", "Imaging", "Lab results", "Labs", "Microbiology", "Radiology", "Results recent labs", "Discharge Labs" ],
            "objective_str": ["Objective",	"Vital signs"],
            "consultation_str": ["discharge to"],
            "Code_status_str": ["Code status"]
        }, 
        
        "columns_to_keep": ["Sr No", "Filename", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "amn",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": False,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "AMN_OUTPUT_FINAL_170426.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_AMN_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_AMN_MDM2.csv"),
    },

    # ------------------------------------------------------------------
    # AR (uses common specialties)
    # ------------------------------------------------------------------
    "AR": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "AR_NEW_200.xlsx"), 
        "combine_groups": {
            "assessment_str": ["Assessment", "Assessment / Plan", "Assessment and Plan", "Assessment/ Plan", "Assessment/Plan"],
            "hospitalcourse_str": ["Hospital course"],
            "hpi_str": ["HPI", "History of present illness"],
            "lab_str": ["Blood chemistry Studies", "Discharge Labs", "Imaging", "Lab results", "Labs", "Microbiology", "Radiology", "Results recent labs"],
            "objective_str": ["Objective", "Vital signs"],
            "consultation_str": ["discharge to"],
            "Critical_care_time_str": ["Critical care time"],
        },
        "columns_to_keep": ["Sr No", "Filename", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "ar",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": False,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "AR_OUTPUT_FINAL_170426.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_AR_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_AR_MDM2.csv"),
    },

    # ------------------------------------------------------------------
    # ARN (uses common specialties)
    # ------------------------------------------------------------------
    "ARN": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "ARN_NEW_200.xlsx"),
        "combine_groups": {
            "assessment_str": ["Assessment", "Assessment / Plan", "Assessment and Plan", "Assessment/ Plan", "Assessment/Plan", "Order"],
            "hospitalcourse_str": ["Hospital course"],
            "hpi_str": ["HPI", "History of present illness"],
            "lab_str": ["Blood chemistry Studies", "Discharge Labs", "Imaging", "Lab results", "Labs", "Microbiology", "Radiology", "Results recent labs"],
            "objective_str": ["Objective", "Vital signs"],
            "consultation_str": ["Chief Complaint/Reason for consultation"],
        },
        "columns_to_keep": ["Sr No", "Filename", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "arn",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": False,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "ARN_OUTPUT_FINAL_170426.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_ARN_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_ARN_MDM2.csv"),
    },

    # ------------------------------------------------------------------
    # AW (uses common specialties)
    # ------------------------------------------------------------------
    "AW": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "AW_NEW_200.xlsx"),
        "combine_groups": {
            "assessment_str": ["Assessment", "Assessment / Plan", "Assessment and Plan", "Assessment/ Plan", "Assessment/Plan"],
            "hospitalcourse_str": ["Hospital course"],
            "hpi_str": ["HPI", "History of present illness"],
            "lab_str": ["Blood chemistry Studies", "Discharge Labs", "Imaging", "Lab results", "Labs", "Microbiology", "Pertinent labs", "Radiology", "Results recent labs"],
            "objective_str": ["Objective", "Vital signs"],
            "Code_status_str": ["Code status", "VTE prophylaxis", "Hospital problems"],
            "Critical_care_time_str": ["Critical care time"],
            "Discharge_Disposition_str": ["Discharge Disposition"],
            "Chief_Complaint_str": ["Chief Complaint", "follow up", "Social determinants of health"],
        },
        "columns_to_keep": ["Sr No", "Filename", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "aw",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": False,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "AW_OUTPUT_FINAL_170426.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_AW_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_AW_MDM2.csv"),
    },


    # ------------------------------------------------------------------
    # BCS (uses common specialties)
    # ------------------------------------------------------------------
    "BCS": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "BCS_ALL_header.xlsx"),
        "combine_groups": {
            "assessment_str": ["Assessment", "Assessment/Plan", "Assessment & plan", "plan"],
            "hpi_str": ["History of present iiiness", "History of present iliness", "History of present illness",
                        "History of present liiness", "History of present lliness", "History of present lllness"],
            "lab_str": ["EKG", "Hospital Course", "Imaging review", "Lab Review", "diagnostic", "labs", "orders", "Electronically signed by"],
            "objective_str": ["Objective", "Physical exam", "Vitals"],
            "DVT_Prophylaxis_str": ["DVT Prophylaxis"],
        },
        "columns_to_keep": ["Sr No", "Filename", "Chart", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "bcs",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": True,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "BCS_OUTPUT_FINAL_150426.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_BCS_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_BCS_MDM2.csv"),
    },

    # ------------------------------------------------------------------
    # CAICP (uses common specialties)
    # ------------------------------------------------------------------
    "CAICP": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "CAICP_NEW_200.xlsx"),
        "combine_groups": {
            "assessment_str": ["Assessment", "Assessment & plan", "Assessment and Plan", "Plan", "ASSESSMENT AND PLAN",
                              "ASSESSMENTANDPLAN", "Assessment_DOS", "ASSESSMENTAND PLAN", "DVT Prophylaxis",
                              "ASSESSMENT ANDPLAN", "Active Problem List"],
            "hospitalcourse_str": ["Hospital course", "Code status"],
            "hpi_str": ["BRIEF HISTORY", "HPI", "History of present illness"],
            "lab_str": ["Imaging", "Lab results", "Labs", "Critical care time", "Laboratory test", "Radiology"],
            "objective_str": ["Most recent Vital signs", "Objective", "Vital signs"],
        },
        "columns_to_keep": ["Sr No", "Filename", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "caicp",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": True,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "CAICP_OUTPUT_FINAL_160426.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_CAICP_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_CAICP_MDM2.csv"),
    },

    
    # ------------------------------------------------------------------
    # CCCC (uses common specialties)
    # ------------------------------------------------------------------
    "CCCC": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "CCCC_NEW_200.xlsx"),
        "combine_groups": {
            "assessment_str": ["Assessment & Plan", "Plan", "Problem list", "Code status", "Assessment_DOS", "Assessment and Plan"],
            "hospitalcourse_str": ["Hospital course"],
            "hpi_str": ["HPI", "History of present illness"],
            "lab_str": ["Imaging", "Physical exam", "Vital", "Microbiology", "Radiology", "Code status", "Infusions", "interval Update"],
            "objective_str": ["Objective", "Vital"],
        },
        "columns_to_keep": ["Sr No", "Filename", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "cccc",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": False,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "CCCC_OUTPUT_FINAL_160426.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_CCCC_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_CCCC_MDM2.csv"),
    },

    # ------------------------------------------------------------------
    # CSCC (uses consult file)
    # ------------------------------------------------------------------
    "CSCC": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "CSCC_All_Header.xlsx"),
        "combine_groups": {
            "assessment_str": ["A/P", "Assessment", "Assessment & Plan", "Assessment and Plan", "Assessment/Plan", "Code Status", "plan", "Plan", "Disposition"],
            "hpi_str": ["History of Present", "History of Present Illness", "History of Present llIness", "HPI", "Physical Exam", "HISTORIES", "HISTORY OF PRESENT ILLNESS"],
            "lab_str": ["LABS/Studies", "Significant Findings/Tests/Studies", "LABS AND IMAGING", "LABS AND MAGING", "Radiology", "Studies", "labs", "Lab", "Labs", "Radiological test", "ECG", "Recent Microbiology cultures", "LAB DATA REVIEWED", "Recent Result", "Resent Result", "Additional orders and Documentation", "significant diagnostic studies and procedures", "labs day of discharge", "Attested", "Imaging", "EKG", "Result Date"],
            "phy_str": ["PHYSICAL EXAMINATION", "Physical Exam", "Review of Systems", "Physical Examination"],
            "hospital_course_str": ["Hospital Course"],
            "subjective_str": ["Subjective"],
            "objective_str": ["Objective", "OBJECTIVE", "Vital Signs", "Discharge Vital Signs", "Vital signs", "Recent vital signs", "Resent vital signs"],
            "drug_management_str": ["Drug Management", "Drug. Management", "Drug.Management"],
        },
        "columns_to_keep": ["Sr No", "Filename", "Chart", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "cscc",
        "specialties": None,
        "specialty_map": None,
        "use_consult_file": True,
        "skip_cleaning": True,   # set to True to skip, False to run cleaning
        "consult_file": os.path.join(INPUT_CONSULT, "Consult_Order_CSCC_NEW_ALL.xlsx"),
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "CSCC_LAB_OUTPUT_FINAL_180426.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_CSCC_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_CSCC_MDM2.csv"),
    },

    # ------------------------------------------------------------------
    # CSM (uses consult file)
    # ------------------------------------------------------------------
    "CSM": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "CSM_NEW_200.xlsx"), 
        "combine_groups": {
            "assessment_str": ["Assessment", "Assessment & Plan", "Assessment and Plan", "Assessment/Plan", "plan"],
            "hpi_str": ["History of Present", "History of Present Illness", "History of Present llIness", "HPI", "HOPI"],
            "lab_str": ["LABS/Studies", "Significant Findings/Tests/Studies", "LABS AND IMAGING", "LABS AND MAGING", "Radiology", "Studies", "labs", "Lab", "Labs", "Radiological test", "Radiology", "ECG", "Recent Microbiology cultures", "LAB DATA REVIEWED", "Recent Result", "Resent Result", "Additional orders and Documentation", "significant diagnostic studies and procedures", "Significant Diagnostic Studies & Procedures", "labs day of discharge", "PHYSICAL EXAMINATION", "Physical Exam", "Result Date", "Imaging", "Exam"],
            "hospital_course_str": ["Hospital Course"],
            "subjective_str": ["Subjective"],
            "objective_str": ["Objective", "OBJECTIVE", "Vital Signs", "Discharge Vital Signs", "Vital signs", "Recent vital signs", "Resent vital signs"],
            "current_medication_infusions_str": ["current medication infusions"],
            "signed_str": ["signed", "Discharge Diagnosis"],
        },
        "columns_to_keep": ["Sr No", "Filename", "Chart", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "csm",
        "specialties": None,
        "specialty_map": None,
        "use_consult_file": True,
        "skip_cleaning": True,   # set to True to skip, False to run cleaning
        "consult_file": os.path.join(INPUT_CONSULT, "CSM_Consult_New_200.xlsx"),
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "CSM_OUTPUT_FINAL_100426.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_CSM_MDM.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_CSM_MDM.csv"),
    },

    # ------------------------------------------------------------------
    # CSRNB (uses common specialties)
    # ------------------------------------------------------------------
    "CSRNB": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "CSRNB_NEW_200.xlsx"),
        "combine_groups": {
            "assessment_str": ["Assessment", "Assessment & plan", "Global Assessment", "Plan", "Attestation"],
            "hospitalcourse_str": ["Hospital course"],
            "hpi_str": ["HPI", "History of present illness"],
            "lab_str": ["Imaging", "Labs", "Pertinent labs", "Microbiology", "Radiology", "Review"],
            "objective_str": ["Objective", "Vital signs"],
        },
        "columns_to_keep": ["Sr No", "Filename", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "csrnb",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": False,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "CSRNB_OUTPUT_FINAL_170426.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_CSRNB_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_CSRNB_MDM2.csv"),
    },

    # ------------------------------------------------------------------
    # H (uses common specialties)
    # ------------------------------------------------------------------
    "H": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "H_All_Header.xlsx"),  #H_NEW_200
        "combine_groups": {
            "assessment_str": ["ASESSMENTPLAN", "ASSESSEMENT/PLAN", "ASSESSEMENTIPLAN", ",ASSESSEMENTPLAN", "ASSESSMENT PLAN", 
                               "ASSESSMENTPLAN", "Assessment", "Assessment & plan", "Assessment / Plan", "Assessment /Plan", 
                               "Assessment and Plan", "Assessment/Plan", "Assessment and plan"],
                               				

            "hospitalcourse_str": ["Hospital course"],
            "hpi_str": ["Discharge Diagnosis", "HPI", "History of present illness"],
            "lab_str": ["Diagnostic test", "Imaging", "Lab results", "Laboratory test", "Labs", "Radiology", "Lab results: This visit"],
            "objective_str": ["Objective", "Vital signs"],
            "consultation_str": ["discharge to"],
            "Procedure_str": ["Procedure"],
        },
        "columns_to_keep": ["Sr No", "Filename", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "h",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": True,
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "H_LAB_OUTPUT_FINAL_080526.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_H_MDM21.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_H_MDM21.csv"),
    },

    # ------------------------------------------------------------------
    # JN (uses common specialties)
    # ------------------------------------------------------------------
    "JN": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "JN_NEW_200.xlsx"),
        "combine_groups": {
            "assessment_str": ["Assessment and plan", "Assessment/ plan", "Assessment/Plan", "A/P", "Assessment", "Assessment and Plan"],
            "hospitalcourse_str": ["Hospital course"],
            "hpi_str": ["HPI", "History of present illness"],
            "lab_str": ["Diagnostic Results", "Lab Results", "Labs", "Labs and Imaging", "Microbiology", "Fishbone Labs", "Diagnostic test", "Imaging", "Radiology", "Lab results"],
            "objective_str": ["Physical exam"],
            "Screening_for_social_Drivers_str": ["Screening for social Drivers"],
        },
        "columns_to_keep": ["Sr No", "Filename", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "jn",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": False,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "JN_OUTPUT_FINAL_170426.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_JN_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_JN_MDM2.csv"),
    },

    # ------------------------------------------------------------------
    # LMC (uses common specialties)
    # ------------------------------------------------------------------
    "LMC": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "LMC_NEW_200.xlsx"),
        "combine_groups": {
            "assessment_str": ["Assessment", "Assessment & Plan", "Assessment and Plan", "Free Text DxA&P Notes", "free text dxA&P", "CC", "Plan"],
            "hpi_str": ["HPI", "History of present illness"],
            "hospitalcourse_str": ["Hospital course", "Hospital course to date"],
            "lab_str": ["Imaging", "Lab", "Laboratory tests", "Radiology data", "results"],
            "objective_str": ["Objective", "Vital signs", "Vital"],
            "consultation_str": ["consultants"],
        },
        "columns_to_keep": ["Sr No", "Filename", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "lmc",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": True,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "LMC_OUTPUT_FINAL_310326.xlsx"),  
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_LMC_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_LMC_MDM2.csv"),
    },

    # ------------------------------------------------------------------
    # MCE (uses common specialties)
    # ------------------------------------------------------------------
    "MCE": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "MCE_All_Header.xlsx"), 
        "combine_groups": {
            "assessment_str": ["Assessment", "Assessments", "Plan", "Hospital Course", "Assessments/Problem List"],
            "hpi_str": ["HPI", "HPI/ Subjective"],
            "lab_str": ["Imaging results", "Lab results", "Imaging", "Imaging Results", "Lab Results"],
            "objective_str": ["Objective", "Vital Signs"],
            "consultation_str": ["Consultations"],
        },
        "columns_to_keep": ["Sr No", "Filename", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "mce",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": False,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "MCE_LAB_OUTPUT_FINAL_080526.xlsx"),  
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_MCE_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_MCE_MDM2.csv"),
    },

    # ------------------------------------------------------------------
    # MSMC (uses common specialties)
    # ------------------------------------------------------------------
    "MSMC": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "MSMC_NEW_200.xlsx"),
        "combine_groups": {
            "assessment_str": ["Assessment", "Assessment and plan", "Assessment/Plan", "Assessment / Plan", "PLAN", "PENDING LABS AND STUDIES"],
            "hpi_str": ["HPI"],
            "lab_str": ["ECHO OR ECG RESULTS", "IMAGING RESULTS REVIEW", "IMPRESSION", "LAB AND DIAGNOSTIC STUDIES",
                        "LAB RESULTS REVIEW", "LABS", "Latest lab results", "MICROBIOLOGY", "OTHER RESULTS",
                        "RECENT IMAGING RESULTS", "RECENT LAB RESULTS", "RECENT LABS", "Electronically signed by"],
            "objective_str": ["PHYSICAL EXAMINATION", "Physical Exam", "OBJECTIVE", "Vital Signs"],
            "consultation_str": ["CONSULT"],
        },
        "columns_to_keep": ["Sr No", "Filename", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "msmc",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": True,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "MSMC_OUTPUT_FINAL_140426.xlsx"),  
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_MSMC_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_MSMC_MDM2.csv"),
    },

    # ------------------------------------------------------------------
    # NL (uses common specialties)
    # ------------------------------------------------------------------
    "NL": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "NL_All_Header.xlsx"),
        "combine_groups": {
            "assessment_str": ["Assessment", "Assessment & plan", "Assessment and Plan", "Assessment/Plan", "Critical care time", "PLAN", "Discharge Assessment"],
            "hospitalcourse_str": ["Hospital course"],
            "hpi_str": ["HPI", "History of present illness"],
            "lab_str": ["Imaging", "Lab results", "Labs", "Radiology"],
            "objective_str": ["Objective", "Vital signs"],
            "consultation_str": ["discharge to"],
            "Critical_care_time_str": ["Critical care time"],
            "Code_status_str": ["Code status"],
        },
        "columns_to_keep": ["Sr No", "Filename", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "nl",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": True,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "NL_LAB_OUTPUT_FINAL_110526.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_NL_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_NL_MDM2.csv"),
    },

    # ------------------------------------------------------------------
    # NLO (uses common specialties)
    # ------------------------------------------------------------------
    "NLO": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "NLO_All_Header.xlsx"),
        "combine_groups": {
            "assessment_str": ["ASSESSMENT", "Assessments", "Plan", "Electronically signed by", "ADDENDUM"],
            "hpi_str": ["HPI / Subjective","HISTORY OF PRESENT ILLNESS", "HISTORY OF PRESENTING COMPLAINT", "HPI", "/ HPI", "HISTORY OF PRESENT COMPLAINT"],
            "lab_str": ["HOSPITAL COURSE", "INVESTIGATIONS DONE", "Imaging", "Imaging Results", "LABORATORY DATA", "Lab Results"],
            "subjective_str": ["SUBJECTIVE"],
            "objective_str": ["Objective", "Vital Signs"],
            "consultation_str": ["Consultations", "Electronically signed by"],
        },
        "columns_to_keep": ["Sr No", "Filename", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "nlo",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": True,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "NLO_LAB_OUTPUT_FINAL_080526.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_NLO_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_NLO_MDM2.csv"),
    },

    # ------------------------------------------------------------------
    # OLGMC (uses common specialties)
    # ------------------------------------------------------------------
    "OLGMC": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "OLGMC_All_Header.xlsx"),
        "combine_groups": {
            "assessment_str": ["ASSESSMENTIPLAN", "Assessment", "Assessment & plan", "Assessment and Plan", "Plan","Assessment/Plan"],
            "hospitalcourse_str": ["Hospital course"],
            "hpi_str": ["HPI", "History of present illness", "interval hx"],
            "lab_str": ["Radiology", "Recent labs", "Significant diagnostic studies", "diagnostic tests", "microbiology results"],
            "objective_str": ["Vital signs"],
            "MD_Addendum_str": ["MD Addendum", "VTE Prophylaxis"],
        },
        "columns_to_keep": ["Sr No", "Filename", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "olgmc",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": False,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "OLGMC_LAB_OUTPUT_FINAL_110526.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_OLGMC_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_OLGMC_MDM2.csv"),
    },

    # ------------------------------------------------------------------
    # R (uses common specialties)
    # ------------------------------------------------------------------
    "R": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "R_All_Header.xlsx"),
        "combine_groups": {
            "assessment_str": ["Assessment", "Assessment and Plan", "Hospital course", "Hospital course to date", "Plan", "Free Text A&P",
                              "Free Text DxA&P Notes", "free text dxA&P"],
            "hpi_str": ["HPI", "History of present illness"],
            "lab_str": ["Exam", "Imaging", "Impression", "Lab", "Laboratory tests", "Radiology data", "results"],
            "objective_str": ["Objective", "Vital signs"],
            "consultation_str": ["consultants"],
        },
        "columns_to_keep": ["Sr No", "Filename", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "r",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": True,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "R_LAB_OUTPUT_FINAL_110526.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_R_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_R_MDM2.csv"),
    },

    # ------------------------------------------------------------------
    # SFSPDC (uses common specialties)
    # ------------------------------------------------------------------
    "SFSPDC": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "SFSPDC_All_Header.xlsx"),
        "combine_groups": {
            "assessment_str": ["Clinical Impression", "Visit Diagnoses", "Discharge Diagnosis"],
            "hpi_str": ["HPI", "History of present illness"],
            "lab_str": ["Imaging", "Lab results", "Labs"],
            "objective_str": ["Additional documentation", "Physical exam", "Vital Signs"],
            "hospital_course_str": ["brief review of hospital course"],
            "Scheduled_Meds_str": ["Scheduled Meds"],
        },
        "columns_to_keep": ["Sr No", "Filename", "Chart", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "sfspdc",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": True,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "SFSPDC_OUTPUT_FINAL_160426.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_SFSPDC_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_SFSPDC_MDM2.csv"),
    },

    # ------------------------------------------------------------------
    # WA (uses common specialties)
    # ------------------------------------------------------------------
    "WA": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "WA_NEW_200.xlsx"), 
        "combine_groups": {
            "assessment_str": ["Assesment and Plan", "Assessment and Plan", "Assessment/Plan", "Plan"],
            "hpi_str": ["HPI", "History of present IlIness", "History of present Illness"],
            "lab_str": ["Imaging report", "Imaging results", "Lab results", "Microbiology"],
            "phy_str": ["Physical exam"],
            "objective_str": ["Vital Signs"],
            "consultation_str": ["Consultations"],
        },
        "columns_to_keep": ["Sr No", "Filename", "Chart", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "wa",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": True,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "WA_OUTPUT_FINAL_100426.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_WA_MDM.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_WA_MDM.csv"),
    },

    # ------------------------------------------------------------------
    # WCMICP (uses common specialties)
    # ------------------------------------------------------------------
    "WCMICP": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "WCMICP_NEW_200.xlsx"),
        "combine_groups": {
            "assessment_str": ["Assessment", "Assessment & plan", "Plan"],
            "hospitalcourse_str": ["Hospital course"],
            "hpi_str": ["HPI", "History of present illness"],
            "lab_str": ["Imaging", "Lab results", "Labs", "Radiology", "Lab test reviewed"],
            "objective_str": ["Most recent Vital signs", "Objective"],
            "Final_Diagnosis_str": ["Final Diagnosis"],
        },
        "columns_to_keep": ["Sr No", "Filename", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "wcmicp",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": False,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "WCMICP_OUTPUT_FINAL_160426.xlsx"),
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_WCMICP_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_WCMICP_MDM2.csv"),
    },

    # ------------------------------------------------------------------
    # WH (uses common specialties)
    # ------------------------------------------------------------------
    "WH": {
        "input_file": os.path.join(NEXT_INPUT_HEADER, "WH_All_header.xlsx"),
        "combine_groups": {
            "assessment_str": ["Assessment","Assessment and Plan", "Assessments/Problem List", "Plan", "Consultations"],
            "hpi_str": ["HPI", "History of present Illness"],
            "lab_str": ["Imaging results", "Lab results"],
            "objective_str": ["Physical Examination", "Physical exam", "Vital Signs"],
        },
        "columns_to_keep": ["Sr No", "Filename", "Chart", "DOS", "Visit", "Visit_time", "Page_No"],
        "function_suffix": "wh",
        "specialties": COMMON_SPECIALTIES,
        "specialty_map": COMMON_SPECIALTY_MAP,
        "use_consult_file": False,
        "skip_cleaning": True,   # set to True to skip, False to run cleaning
        "lab_values_file": os.path.join(INPUT_LAB_VALUES, "WH_LAB_OUTPUT_FINAL_110526.xlsx"), 
        "final_excel": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_WH_MDM2.xlsx"),
        "final_csv": os.path.join(NEXT_OUTPUT_FOLDER, "LAB_WH_MDM2.csv"),
    },

}