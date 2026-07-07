Structure:
MDM2_Complete_integration/
├── main.py
├── config.py
├── utils.py
├── facility_functions.py
├── All_header_data/
│   ├── AHFL_NEW_200.xlsx
│   ├── AMN_NEW_200.xlsx
│   ├── AR_NEW_200.xlsx
│   └── ... (all other facility input header files)
├── All_lab_data/
│   ├── AHFL_OUTPUT_FINAL_100426.xlsx
│   ├── AMN_OUTPUT_FINAL_170426.xlsx
│   ├── AR_OUTPUT_FINAL_170426.xlsx
│   └── ... (all other facility input lab files)
├── Consult_files/
│   ├── AHFL_Consult.xlsx
│   ├── CSCC_Consult.xlsx
│   ├── CSM_Consult_New_200.xlsx
│   └── ... (all other facility input consult files)
├── lab.xlsx
├── Lab_panel.xlsx
├── Output/
│   ├── LAB_AHFL_MDM2.xlsx
│   ├── LAB_AHFL_MDM2.csv
│   ├── LAB_AMN_MDM2.xlsx
│   └── ... (all other facility input consult files)
└── ... (other supporting files)


The MDM2 system consists of:

config.py – facility configurations.

utils.py – shared helper functions (date normalization, MDM2 logic, flattening, etc.).

Facility‑specific modules – ahfl_functions.py, bcs_functions.py, caicp_functions.py, etc.

main.py – the main pipeline.
