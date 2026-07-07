import ast
import re   
import copy
from datetime import datetime
from mdm3_db import *
from route_detection_v1 import normalize_route
from detect_discontinue_med import detect_stop_related_sentences, extract_stopped_meds
#from drug_classification_anp import drug_classification_anp, risk_from_medications_v2
from mdm3_medication_utils_v2 import *
from surgery_keyword_search import extract_surgery_keywords ### upadted on 05-11-25
from route_pattern import SQ_variations
from antibiotics_med import sepsis_antibiotics_iv, uti_antibiotic_names, diverticulitis_antibiotics_iv, chf_med_names, copd_med, covid_med
from med_list import med_otc_lx, med_rx_lx

print(CRITICAL_ROUTES)

def normalize_date(date_str):
        """
        Normalize any common date format to mm/dd/yyyy
        """
        if not date_str or not isinstance(date_str, str):
            return ""

        date_str = date_str.strip()
        date_str = re.sub(r'\s+', ' ', date_str)  # normalize multiple spaces

        # Supported input formats
        date_formats = [
            "%d %B %Y",       # 29 October 2024
            "%d %b %Y",       # 29 Oct 2024
            "%B %d, %Y",      # October 29, 2024
            "%b %d, %Y",      # Oct 29, 2024
            "%b-%d-%Y",       # Oct-29-2024
            "%B-%d-%Y",       # October-29-2024
            "%b-%d-%y",       # Oct-29-24
            "%B-%d-%y",       # October-29-24
            "%d-%b-%Y",       # 29-Oct-2024
            "%d-%B-%Y",       # 29-October-2024
            "%d-%b-%y",       # 29-Oct-24
            "%d-%B-%y",       # 29-October-24
            "%m/%d/%Y",       # 10/29/2024
            "%m/%d/%y",       # 10/29/24
            "%d/%m/%Y",       # 29/10/2024
            "%d/%m/%y",       # 29/10/24
            "%d %b, %Y",      # 29 Oct, 2024
            "%d %B, %Y",      # 29 October, 2024
            "%d %b, %y",      # 29 Oct, 24
            "%d %B, %y",      # 29 October, 24
            "%m-%d-%y",       # 10-29-24

            # --- Newly Added ---
            "%B %d %Y",       # February 2 2025
            "%b %d %Y",       # Feb 2 2025
            "%m-%d-%Y",       # 2-9-2025, 3-01-2025, 3-02-2025
        ]

        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str.title(), fmt)
                return dt.strftime("%m/%d/%Y")
            except ValueError:
                continue

        # Handle uppercase formats like "01 NOV 2024"
        try:
            dt = datetime.strptime(date_str.upper(), "%m/%d/%Y")
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            pass
            
        try:
            dt = datetime.strptime(date_str.upper(), "%d %b %Y")
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            pass

        try:
            dt = datetime.strptime(date_str.upper(), "%d-%b-%Y")
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            pass
        try:
            match = re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", date_str)
            if match:
                date_str = match.group(0)
                dt = datetime.strptime(date_str.upper(),"%m/%d/%y")
                return dt.strftime("%m/%d/%Y")
        except ValueError:
            pass

    # If no format matches, return as-is
        return date_str

def extract_only_date(val):
    if pd.isna(val):
        return pd.NaT

    val = str(val).strip()

    # extract first MM/DD/YY pattern
    match = re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", val)
    if not match:
        return pd.NaT
    
    date_str = match.group(0)

    # convert to pandas datetime (date only)
    try:
        return pd.to_datetime(date_str, format="%m/%d/%y").date()
    except:
        return pd.NaT
    


def drug_classification_anp(input_row)  -> list:
    """ Classify drugs based on multiple databases and criteria.
    """
    input_row = input_row.copy()
    drug_list = input_row["Med_Chart_Medication_Text"]
    if drug_list == "Missing" or not isinstance(drug_list, list):
        return "Missing"
    
    new_drug_list = []
    global CRITICAL_ROUTES

    sodium_chloride_alternate = ["NACL","NS"]  # fixed
    
    for drug in drug_list:
        drug = copy.deepcopy(drug)
        drug["category"] = []
        drug["nomalized_route"] = ""
        drug_strength = str(drug.get("strength","")).strip().upper()
        medication_full_name = str(drug.get("medication","")).strip().upper()
        
        drug["cc"]=[]
        drug["parenteral"]=[]
        drug["toxic"]=[]
        drug["intg"]=[]
        drug["ccwor"]=[]

        med_name_list = drug.get("name", [])
        if not med_name_list:
            continue
        
        med_name_list = [clean_med_name(med_name.upper()) 
                         for med_name in med_name_list 
                         if len(remove_numbers(med_name)) > 3]

        med_name_list_wno = [remove_numbers(med_name) for med_name in med_name_list]

        categorized = False
        change_normalized = False
        
        med_route = str(drug.get("route", "")).upper().strip()
                
        # ---- FIXED ROUTE NORMALIZATION ----
        if med_route in CRITICAL_ROUTES:
            drug["nomalized_route"] = "IV"
        elif med_route in ["SUSPENSION", "IM", "INTRAMUSCULAR"]:
            drug["nomalized_route"] = "IM"
        elif med_route in SQ_variations:
            drug["nomalized_route"] = "SQ"
        else:
            change_normalized = True
        
        # ---- CC_CDR DATABASE ----
        for med_name, med_name_wo_no in zip(med_name_list, med_name_list_wno):

            cc_cond1 = (med_name in cc_cdr_db_med_route)
            cc_cond2 = (med_name_wo_no in cc_cdr_db_med_route)

            if cc_cond1:
                db_routes = [r.upper().strip() 
                             for r in cc_cdr_db_med_route[med_name].split("|")]
            elif cc_cond2:
                db_routes = [r.upper().strip() 
                             for r in cc_cdr_db_med_route[med_name_wo_no].split("|")]
            else:
                continue

            if change_normalized:
                drug["nomalized_route"] = normalize_route(
                    med_name, medication_full_name, med_route, anp_drug_list=[]
                )

            # ---- FIXED CC ROUTE MATCH ----
            cc_cond3 = (
                med_route in db_routes or
                drug["nomalized_route"] in db_routes or
                any(compare_routes(r, med_route) for r in db_routes)
            )

            if cc_cond3 and (medication_full_name in cc_cdr_db_med_route.keys()):
                drug["category"].append("CC_CDR|ROUTE")
                drug["cc"].append(med_name)
                categorized = True
                break

            elif cc_cond3:
                numbers = extract_numbers(medication_full_name)
                strength_vals = extract_numbers(drug_strength)
                in_alt_names = (med_name in sodium_chloride_alternate) or \
                               (med_name_wo_no in sodium_chloride_alternate)

                is_sodium_chloride = (
                    ("SODIUM CHLORIDE" in medication_full_name and 
                     "IN SODIUM CHLORIDE" not in medication_full_name) or 
                    in_alt_names
                )

                if is_sodium_chloride:
                    if (
                        "3%" in medication_full_name or
                        any(n >= 2000 for n in numbers) or
                        (strength_vals and strength_vals[0] >= 2000 and 
                         "ML" in drug_strength.replace(" ", ""))
                    ):
                        drug["category"].append("CC_CDR|ROUTE")
                        drug["cc"].append(med_name)
                        categorized = True
                else:
                    if "SODIUM" in med_name or "CHLORIDE" in med_name or in_alt_names:
                        continue
                    
                    drug["category"].append("CC_CDR|ROUTE")
                    drug["cc"].append(med_name)
                    categorized = True
                    break

            else:
                drug["category"].append("CC_CDR|NOROUTE")
                drug["ccwor"].append(med_name)

        # ---- OTHER DATABASES ----
        if not categorized:
            # FIXED → parenteral should NOT use toxicity DB
            result_toxic1 = compare_string_with_list_v1(med_name_list, toxicity_drug_db_list)
            result_toxic2 = compare_string_with_list_v1(med_name_list_wno, toxicity_drug_db_list)

            result_paren1 = compare_string_with_list_v1(med_name_list, parental_drug_db_list)
            result_paren2 = compare_string_with_list_v1(med_name_list_wno, parental_drug_db_list)

            if result_toxic1[0] or result_toxic2[0]:
                drug["category"].append("TOXIC_DRUG")
                drug["toxic"].append(result_toxic1[1] if result_toxic1[0] else result_toxic2[1])
                categorized = True

            if result_paren1[0] or result_paren2[0]:
                drug["category"].append("PARENTERAL_DRUG")
                drug["parenteral"].append(result_paren1[1] if result_paren1[0] else result_paren2[1])
                categorized = True

            # ---- INTEGRATED DRUG DB ----
            if not categorized:
                for med_name, med_name_wno in zip(med_name_list, med_name_list_wno):

                    if med_name in intg_drug_db_dict:
                        drug["category"].append(intg_drug_db_dict[med_name])
                        drug["intg"].append(med_name)
                        categorized = True
                        break

                    if med_name_wno in intg_drug_db_dict:
                        drug["category"].append(intg_drug_db_dict[med_name_wno])
                        drug["intg"].append(med_name_wno)
                        categorized = True
                        break

                    if med_name in intg_drug_db_dict_brand:
                        drug["category"].append(intg_drug_db_dict_brand[med_name])
                        drug["intg"].append(med_name)
                        categorized = True
                        break

                    if med_name_wno in intg_drug_db_dict_brand:
                        drug["category"].append(intg_drug_db_dict_brand[med_name_wno])
                        drug["intg"].append(med_name_wno)
                        categorized = True
                        break

                    if med_name in intg_drug_db_dict_generic:
                        drug["category"].append(intg_drug_db_dict_generic[med_name])
                        drug["intg"].append(med_name)
                        categorized = True
                        break

                    if med_name_wno in intg_drug_db_dict_generic:
                        drug["category"].append(intg_drug_db_dict_generic[med_name_wno])
                        drug["intg"].append(med_name_wno)
                        categorized = True
                        break

        if not categorized and med_name_list:
            drug["category"].append("NOT_KNOWN")

        new_drug_list.append(drug)

    return new_drug_list


# def drug_classification_anp(input_row)  -> list:
#     """ Classify drugs based on multiple databases and criteria.
#     """
#     input_row = input_row.copy()
#     drug_list = input_row["Med_Chart_Medication_Text"]
#     if drug_list == "Missing" or not isinstance(drug_list, list):
#         return "Missing"
    
#     new_drug_list = []
    
#     #global missing_medication_list

#     global CRITICAL_ROUTES

#     sodium_chloride_alternate = ["NACL","NS"] ##added on 23-10-2025


#     for drug in drug_list:
#         drug = copy.deepcopy(drug)
#         drug["category"] = []
#         drug["nomalized_route"] = ""
#         drug_strength = str(drug.get("strength","")).strip().upper()
#         medication_full_name = str(drug.get("medication","")).strip().upper() # SODIUM CHLORIDE 0.9 % FLUSH
#         #drug["medication"] = "NOT_AVAIL" ##### commented 08-11-2025
#         #drip_status = drug.get("drip","")
#         #print("medication fullname", medication_full_name)
#         drug["cc"]=[]
#         drug["parenteral"] = []
#         drug["toxic"] = []
#         drug["intg"]=[]
#         drug["ccwor"]=[]
        
#         # Extract and clean medication names
#         med_name_list = drug.get("name", [])
#         if not med_name_list:
#             continue
            
#         med_name_list     =  [clean_med_name(med_name.upper()) for med_name in med_name_list if len(remove_numbers(med_name))>3]
#         med_name_list_wno =  [remove_numbers(med_name) for med_name in med_name_list]

#         categorized = False
#         change_normalized = False
        
#         med_route = str(drug.get("route", "")).upper().strip()
                
#         if med_route in CRITICAL_ROUTES:#['IVPB', 'IVP', 'INTRAVENOUS', 'INFUSION', 'TRANSFUSION']
#             #med_route = "IV" 
#             drug["nomalized_route"]= "IV" 
#         elif med_route in ["SUSPENSION","SUSPENSION","Intramuscular","IM","INTRAMUSCULAR","INTRA"]:
#             #med_route = "IM" #SC/SQ 
#             drug["nomalized_route"]= "IM"  
#         elif med_route in SQ_variations: #['SUBCUTANEOUS', 'SC', 'SUBCUT','SUBCOT',"ID"]: #'SYRINGE','INJECTION']: ##update on 30-10-2025 
#             #med_route = "SQ"
#             drug["nomalized_route"] = "SQ"
#         # elif drip_status:
#         #     drug["nomalized_route"] = "DRIP"
#         else: 
#             change_normalized = True
        
#         # Check CC_CDR route database
        
#         for med_name, med_name_wo_no in zip(med_name_list, med_name_list_wno):
#             # if (med_name in continue_med) or (med_name_wo_no in continue_med):
#             #     continue
#             cc_cond1=(med_name in cc_cdr_db_med_route)# or any(((med_name in med_key) or (med_name.replace(" ","") in med_key)) for med_key in list(cc_cdr_db_med_route.keys())))
#             cc_cond2=(med_name_wo_no in cc_cdr_db_med_route)# or any(((med_name_wo_no in med_key) or (med_name_wo_no.replace(" ","") in med_key)) for med_key in list(cc_cdr_db_med_route.keys())))
#             if cc_cond1:
#                 #med_name = [med_key for med_key in list(cc_cdr_db_med_route.keys()) if ((med_name in med_key) or (med_name.replace(" ","") in med_key))][0]
#                 #med_name_wo_no = [med_key for med_key in list(cc_cdr_db_med_route.keys()) if ((med_name_wo_no in med_key) or (med_name_wo_no.replace(" ","") in med_key))][0]
#                 db_routes = [route.upper().strip() for route in cc_cdr_db_med_route[med_name].split("|")]
#             elif cc_cond2:
#                 #med_name = [med_key for med_key in list(cc_cdr_db_med_route.keys()) if ((med_name_wo_no in med_key) or (med_name_wo_no.replace(" ","") in med_key))][0]
#                 db_routes = [route.upper().strip() for route in cc_cdr_db_med_route[med_name_wo_no].split("|")]
            
#             if cc_cond1 or cc_cond2:
#                 if change_normalized:
#                     drug["nomalized_route"] = normalize_route(med_name, medication_full_name, med_route, anp_drug_list=[])

#                 cc_cond3=(compare_routes(" ".join(db_routes), med_route) or med_route in db_routes or compare_routes(" ".join(db_routes), drug["nomalized_route"]) or drug["nomalized_route"] in db_routes)
#                 if cc_cond3 and (medication_full_name in  cc_cdr_db_med_route.keys()):
#                     drug["category"].append("CC_CDR|ROUTE")
#                     drug["cc"].append(med_name)
#                     categorized = True
#                     break
#                 elif cc_cond3: ##later updated # 3% sodium chloride, or >= 2000 ML
#                     numbers = extract_numbers(medication_full_name)
#                     strength = extract_numbers(drug_strength)
#                     in_alt_names = (med_name in sodium_chloride_alternate) or (med_name_wo_no in sodium_chloride_alternate)

#                     # Simplify the main condition
#                     is_sodium_chloride = (
#                         ("SODIUM CHLORIDE" in medication_full_name and "IN SODIUM CHLORIDE" not in medication_full_name)
#                         or in_alt_names
#                     )

#                     if is_sodium_chloride:
#                         # Check for numeric pattern conditions
#                         if any(int(n) == 3 for n in numbers) or any(n >= 2000 for n in numbers) or (strength and strength[0] >= 2000 and "ML" in drug_strength.replace(" ","")):
#                             drug["category"].append("CC_CDR|ROUTE")
#                             drug["cc"].append(med_name)
#                             categorized = True
#                     else:
#                         # Skip if it’s related to sodium/chloride variants
#                         if "SODIUM" in med_name or "CHLORIDE" in med_name or in_alt_names:
#                             continue
#                         # Otherwise categorize
#                         drug["category"].append("CC_CDR|ROUTE")
#                         drug["cc"].append(med_name)
#                         categorized = True
#                         break
#                 else:
#                     drug["category"].append("CC_CDR|NOROUTE")
#                     drug["ccwor"].append(med_name)
#                   # Found in CC_CDR, no need to check other databases
        
#         # Check other databases if not already categorized
#         if not categorized:
#             result_toxic1= compare_string_with_list_v1(med_name_list, toxicity_drug_db_list)
#             result_toxic2= compare_string_with_list_v1(med_name_list_wno, toxicity_drug_db_list)
#             result_paren1= compare_string_with_list_v1(med_name_list, parental_drug_db_list)
#             result_paren2= compare_string_with_list_v1(med_name_list_wno, parental_drug_db_list)
#             if result_toxic1[0] or result_toxic2[0]:
#                 drug["category"].append("TOXIC_DRUG")
#                 if result_toxic1[0]:
#                     drug["toxic"].append(result_toxic1[1])
#                 else:
#                     drug["toxic"].append(result_toxic2[1])
#                 categorized = True

#             if result_paren1[0] or result_paren2[0]:
#                 drug["category"].append("PARENTERAL_DRUG")
#                 if result_paren1[0]:
#                     drug["parenteral"].append(result_paren1[1])
#                 else:
#                     drug["parenteral"].append(result_paren2[1])
#                 categorized = True
            
#             # Check integrated drug databases
#             if not categorized:
#                 for med_name, med_name_wno in zip(med_name_list, med_name_list_wno):
#                     intg_cond1 = (med_name in intg_drug_db_dict) #or any(med_name in med_key for med_key in list(intg_drug_db_dict.keys())))
#                     intg_cond2 = (med_name_wno in intg_drug_db_dict)# or any(med_name_wno in med_key for med_key in list(intg_drug_db_dict.keys())))
#                     intg_brand_cond1 = (med_name in intg_drug_db_dict_brand) #or any(med_name in med_key for med_key in list(intg_drug_db_dict_brand.keys())))
#                     intg_brand_cond2 = (med_name_wno in intg_drug_db_dict_brand)# or any(med_name_wno in med_key for med_key in list(intg_drug_db_dict_brand.keys())))
#                     intg_generic_cond1 = (med_name in intg_drug_db_dict_generic)# or any(med_name in med_key for med_key in list(intg_drug_db_dict_generic.keys())))
#                     intg_generic_cond2 = (med_name_wno in intg_drug_db_dict_generic)# or any(med_name_wno in med_key for med_key in list(intg_drug_db_dict_generic.keys())))
                    
#                     if intg_cond1:
#                         med_name = [med_key for med_key in list(intg_drug_db_dict.keys()) if med_name in med_key][0]
#                         drug["category"].append(intg_drug_db_dict[med_name])
#                         drug["intg"].append(med_name)
#                         categorized = True
#                         break
#                     elif intg_cond2:
#                         med_name = [med_key for med_key in list(intg_drug_db_dict.keys()) if med_name_wno in med_key][0]
#                         drug["category"].append(intg_drug_db_dict[med_name])
#                         drug["intg"].append(med_name)
#                         categorized = True
#                         break
#                     elif intg_brand_cond1:
#                         med_name = [med_key for med_key in list(intg_drug_db_dict_brand.keys()) if med_name in med_key][0]
#                         drug["category"].append(intg_drug_db_dict_brand[med_name])
#                         drug["intg"].append(med_name)
#                         categorized = True
#                         break
#                     elif intg_brand_cond2:
#                         med_name = [med_key for med_key in list(intg_drug_db_dict_brand.keys()) if med_name_wno in med_key][0]
#                         drug["category"].append(intg_drug_db_dict_brand[med_name])
#                         drug["intg"].append(med_name)
#                         categorized = True
#                         break
#                     elif intg_generic_cond1:
#                         med_name = [med_key for med_key in list(intg_drug_db_dict_generic.keys()) if med_name in med_key][0]
#                         drug["category"].append(intg_drug_db_dict_generic[med_name])
#                         drug["intg"].append(med_name)
#                         categorized = True
#                         break
#                     elif intg_generic_cond2:
#                         med_name = [med_key for med_key in list(intg_drug_db_dict_generic.keys()) if med_name_wno in med_key][0]
#                         drug["category"].append(intg_drug_db_dict_generic[med_name])
#                         drug["intg"].append(med_name)
#                         categorized = True
#                         break
        
#         # Default category if not found in any database
#         if not categorized and med_name_list:
#             #drug["category"].append("RX")
#             drug["category"].append("NOT_KNOWN")
#             #missing_medication_list.append((med_name_list[0],med_route))
#         new_drug_list.append(drug)
#     return new_drug_list

def risk_from_medications_v2(row, dvt_med_names=[]) -> tuple:
    """
    Determine MDM Risk contribution from medication list
    using drug_classification flags (NER + category list).
    """
    

    surgery_list = extract_matches(row["Emergency_major_surgery"])+extract_matches(row["Surgery"])+extract_matches(row["Surgery_discussion"])+extract_matches(row["Risk_phrases"])+extract_matches(row["Risk_factors"])
    if surgery_list:
        surgery_list = [s.strip().upper() for s in surgery_list]


    global CRITICAL_ROUTES
   
    levels = ["MINIMAL", "LOW", "MODERATE", "HIGH"]
    risk_level = "LOW"
    validate = []
    row = row.copy()

    # uti detection
    uti_detect = row["UTI_Detected"]
    uti_text   = row['UTI_Text'][1]
    uti_text_str = ",".join(uti_text)
    wbc_count  = row['WBC_values']
    wbc_count_str = ",".join([str(wc)for wc in wbc_count])

    ### 30102025
    chart_id = row["Chart"]
    anp_combined = str(row["ANP_Combined_cleaned"]) + str(row["Medication_Combined_cleaned"]) ############## 01102025

    chf_true = row.get("CHF_True", False)

    copd_dict = row.get("ANP_COPD", {})
    
    ################## this part will be updated in v2
    if "output_medication_with_classification_anp" in row: 
        meds  = row.get("output_medication_with_classification", [])
        meds1 = row.get("output_medication_with_classification_anp", [])
        #print("combined")
    
        if meds == "Missing" or not isinstance(meds, list):
            #validate.append(("MEDICATION DATA", "Missing"))
            meds = meds1
            #return risk_level, validate
            if len(meds) == 0:
                validate.append(("MEDICATION ORDER EXTRACTION", "MISSING"))
                return risk_level, validate
        else:
            meds = meds+meds1
    else:
        meds = row.get("output_medication_with_classification", [])
        #print("not combined")
        if meds == "Missing" or not isinstance(meds, list):
            validate.append(("MEDICATION ORDER EXTRACTION", "MISSING"))
            return risk_level, validate
    ################################################################

    if len(meds) == 0:
        return risk_level, validate
        
    for med in meds:
        true_med=[]
        med = copy.deepcopy(med)
        names = med.get("name", [])
        names = [name.upper() for name in names if name]
        #names_str = "Med > "+"|".join(names[0:3]) if names else "UNKNOWN" #"|".join(names[0:1]) if names else "UNKNOWN"
        ANP_True = med.get("ANP",False)
        anp_med_start = "ANP_MED > "
        ################### this will also be updated in v2
        names_str_anp = anp_med_start +"|".join(names[0:3]) if names else "UNKNOWN"
        ############################## 
        route = str(med.get("route", "")).upper()
        form = str(med.get("form", "")).upper()
        normalized_route = str(med.get("nomalized_route","")).upper()
        categories = [str(c).upper() for c in med.get("category", [])]
        names_str = "MED_ORDER > "+ med.get("medication","")
        dos = row["formatted_DOS"]


        ########## this will be updated in v2 
        if ANP_True:    #"NOT_AVAIL" in names_str: 
            names_str = names_str_anp
            #print(names_str)
            if not route:
                route = "Route Missing"
        ################################

        if len(names) == 0:
            continue  # Skip if no valid name

        ### stopped med detection from ANP
        detect_stop_med = detect_stop_related_sentences(anp_text=anp_combined, words=names)
        continue_outer= False
        for sent in detect_stop_med: #### 03-11-2025
            stoped_med = extract_stopped_meds(sent) 
            if not("CONTINUE" in sent or "DO NOT HOLD" in sent): ###### 01-11-2025
                if len(stoped_med) > 0:
                    if (any(name in stoped_med for name in names) or any(name in stp_med for stp_med in stoped_med for name in names)):
                        validate.append((names_str, f"Medication Discontinue - {sent} >> Not Counted"))
                        #print(f"{chart_id}, {names_str} >>>>>>> {detect_stop_med[0]}")
                        continue_outer =  True
                        break
                    else:
                        continue
                else:
                    validate.append((names_str, f"Medication Discontinue - {sent} >> Not Counted"))
                    #print(f"{chart_id}, {names_str} >>>>>>> {detect_stop_med[0]}")
                    continue_outer =  True
                    break
            elif len(stoped_med) > 0 and (any(name in stoped_med for name in names) or any(name in stp_med for stp_med in stoped_med for name in names)):
                validate.append((names_str, f"Medication Discontinue - {sent} >> Not Counted"))
                #print(f"{chart_id}, {names_str}>>>>>>> {detect_stop_med[0]}")
                continue_outer =  True
                break
        if continue_outer:
            continue

        # Special handling for DVT prophylaxis medications
        if chart_id in dvt_chart_med and any(dvt.upper() in names for dvt in dvt_chart_med[chart_id]): ######Added on 30-10-2025
            validate.append((names_str, "DVT Prophylaxis Initial >> Not Counted"))
            continue
        elif any(dvt in names for dvt in dvt_med_names):
            validate.append((names_str, "DVT Prophylaxis >> Not Counted"))
            continue  # Skip DVT meds for risk calculation
        elif chart_id in dvt_chart_med_sq:
            skip_outer = False
            for key_dos, value in dvt_chart_med_sq[chart_id].items():
                if dos >= key_dos and any(dvt.upper() in names for dvt in value):
                    validate.append((names_str, "DVT Prophylaxis Subsequent >> Not Counted"))
                    skip_outer = True
                    break  # break inner loop
            if skip_outer:
                continue  # skip outer loop
        
        # Normalize critical routes to "IV"
        if not normalized_route and route in CRITICAL_ROUTES:
            normalized_route = "IV"
        ##### Added rule on 12-11-2025
        if chf_true and any(m_syn in chf_med_names for m_syn in names) and ("IV" in [form, route, normalized_route] or "INJECTION" in [form, route, normalized_route] or "SYRINGE" in [form, route, normalized_route]):
            validate.append((names_str, f"CHF - {route} >> High"))
            risk_level = max(risk_level, "HIGH", key=levels.index)
            print(f"CHF HIGH RISK >> {chart_id} >> {names_str} >> {route}")
            continue

        # result = {
        #     'has_copd': False,
        #     'severity': None,
        #     'matches': [],
        #     'excluded': False
        # }
        if copd_dict.get("has_copd", False):
            copd_matches = copd_dict.get("matches", [])
            print(f"Chart ID: {chart_id}, COPD Matches: {copd_matches}")
            copd_severity = copd_dict.get("severity", None)
            if (copd_severity == "severe" or copd_severity == "moderate") and any(m_syn in names for m_syn in copd_med) and ("IV" in [form, route, normalized_route] or "INJECTION" in [form, route, normalized_route]):
                validate.append((names_str, f"COPD - {route} >> High"))
                risk_level = max(risk_level, "HIGH", key=levels.index)
                continue
        ##### Added rule on 10-11-2025
        if surgery_list and ("SEPSIS" in surgery_list or any("SEPSIS" in s for s in surgery_list)):
            if any(m_syn in sepsis_antibiotics_iv for m_syn in names) and ("IV" in [form, route, normalized_route] or "INJECTION" in [form, route, normalized_route] or "SYRINGE" in [form, route, normalized_route]) :
                validate.append((names_str, f"SEPSIS - {route} >> High"))
                risk_level = max(risk_level, "HIGH", key=levels.index)
                continue

        ##### Added rule on 12-11-2025
        if surgery_list and ("DIVERTICULITIS" in surgery_list or any("DIVERTICULITIS" in s for s in surgery_list)):
            if any(m_syn in diverticulitis_antibiotics_iv for m_syn in names) and ("IV" in [form, route, normalized_route] or "INJECTION" in [form, route, normalized_route] or "SYRINGE" in [form, route, normalized_route]) :
                validate.append((names_str, f"DIVERTICULITIS - {route} >> High"))
                risk_level = max(risk_level, "HIGH", key=levels.index)
                continue

        # --- High risk ---
        if "TOXIC_DRUG" in categories and ("INJECTION" in [form, route, normalized_route] or "IV" in [form, route, normalized_route]):   # drugs needing intensive monitoring ###updated 22-10-25
            validate.append((names_str, f"Toxic Drug - {route} >> High"))
            risk_level = max(risk_level, "HIGH", key=levels.index)
            continue  # Continue to check other meds, don't return immediately

        if "PARENTERAL_DRUG" in categories and ("INJECTION" in [form, route, normalized_route] or "IV" in [form, route, normalized_route]):
            validate.append((names_str, f"Parenteral with IV - {route} >> High"))
            risk_level = max(risk_level, "HIGH", key=levels.index)
            continue

        if uti_detect and wbc_count and any(float(w_cnt) > 12.0 for w_cnt in wbc_count) and any(m_syn in uti_antibiotic_names for m_syn in names):
            validate.append((names_str, f"{uti_text_str}-WBC: {wbc_count_str} >> High"))
            #print(names_str, f"{uti_text_str}-{wbc_count_str} >> High")
            risk_level = max(risk_level, "HIGH", key=levels.index)
            continue

        # if any(contrast in names for contrast in ["CONTRAST", "IOPAMIDOL", "GADOLINIUM", "IOHEXOL"]): # Commented on 28-10-25
        #     validate.append((names_str, "Imaging/Contrast >> High"))
        #     risk_level = max(risk_level, "HIGH", key=levels.index)
        #     continue

        if any(contrast in names for contrast in ["LEVETIRACETAM","KEPPRA"]) and "IV" in [form, route, normalized_route] and ("SEIZURES" in surgery_list or 'SEIZURES / EPILEPSY' in surgery_list or "EPILEPSY" in surgery_list):
            validate.append((names_str, F"KEPPRA WITH IV - {route} >> High"))
            risk_level = max(risk_level, "HIGH", key=levels.index)
            continue

        # CC_CDR medications - Critical Care Drugs
        if "CC_CDR|ROUTE" in categories:
            validate.append((names_str, f"Critical Care Drug with Route-{route} >> High"))
            risk_level = max(risk_level, "HIGH", key=levels.index)
            continue

        # elif "CC_CDR|NOROUTE" in categories and ("IV" in [route, normalized_route] or "SQ" in [route, normalized_route]): ###updated/commented on 22-10-25
        #     validate.append((names_str, f"Critical Care Drug with route-{route} >> High"))
        #     risk_level = max(risk_level, "HIGH", key=levels.index)
        #     continue

        elif "CC_CDR|NOROUTE" in categories:
            validate.append((names_str, f"Critical Care Drug without Route-{route} >> Moderate"))
            risk_level = max(risk_level, "MODERATE", key=levels.index)
            continue
        # --- Moderate risk ---

        if "TOXIC_DRUG" in categories :   ###updated 22-10-25
            validate.append((names_str, f"Toxic Drug-{route} >> Moderate"))
            risk_level = max(risk_level, "MODERATE", key=levels.index)
            continue 

        if "INJECTION" in [form, route, normalized_route] or "IV" in [form, route, normalized_route]:
            validate.append((names_str, f"Injection/IV-{route} >> Moderate"))
            risk_level = max(risk_level, "MODERATE", key=levels.index)
            continue
        if "PARENTERAL_DRUG" in categories:
            validate.append((names_str, f"Parenteral drug without route - {route} >> Moderate"))
            risk_level = max(risk_level, "MODERATE", key=levels.index)
            continue
        # 'DISCONTINUED',
        # 'NOT FOUND',
        # 'OVER THE COUNTER',
        # 'PRESCRIPTION ONLY',
        # 'RX AND/OR OTC',
        # 'UNKNOWN'
        
        # --- Moderate risk ---
        if any(rx_cat in categories for rx_cat in ["PRESCRIPTION ONLY","PRESCRIPTION","RX", "RX AND/OR OTC","DISCONTINUED","NOT FOUND","UNKNOWN"]):
            validate.append((names_str, f"Prescription-{route} >> Moderate"))
            risk_level = max(risk_level, "MODERATE", key=levels.index)
            continue
        elif "NOT_KNOWN" in categories and any(name in med_rx_lx for name in names): #### added on 19-11-25
            validate.append((names_str, f"Prescription-{route} >> MODERATE"))
            risk_level = max(risk_level, "MODERATE", key=levels.index)
            continue
        # --- Low risk ---
        elif "OVER THE COUNTER" in categories:
            validate.append((names_str, "OTC >> Low"))
            risk_level = max(risk_level, "LOW", key=levels.index)
            continue
        elif "NOT_KNOWN" in categories and any(name in med_otc_lx for name in names): ###### added on 19-11-25
            validate.append((names_str, "OTC >> Low"))
            risk_level = max(risk_level, "LOW", key=levels.index)
            continue
        elif "NOT_KNOWN" in categories:
            validate.append((names_str, "UNKNOWN >> MODERATE"))
            risk_level = max(risk_level, "MODERATE", key=levels.index)
            continue

    return risk_level, validate

def risk_from_medications_v3(row, dvt_med_names=[]) -> tuple:
    """
    Determine MDM Risk contribution from medication list
    using drug_classification flags (NER + category list).
    """
    

    surgery_list = extract_matches(row["Emergency_major_surgery"])+extract_matches(row["Surgery"])+extract_matches(row["Surgery_discussion"])+extract_matches(row["Risk_phrases"])+extract_matches(row["Risk_factors"])
    if surgery_list:
        surgery_list = [s.strip().upper() for s in surgery_list]


    global CRITICAL_ROUTES
   
    levels = ["MINIMAL", "LOW", "MODERATE", "HIGH"]
    risk_level = "LOW"
    validate = []
    row = row.copy()

    # uti detection
    uti_detect = row["UTI_Detected"]
    uti_text   = row['UTI_Text'][1]
    uti_text_str = ",".join(uti_text)
    wbc_count  = row['WBC_values']
    wbc_count_str = ",".join([str(wc)for wc in wbc_count])

    ### 30102025
    chart_id = str(row["Chart"]).upper().strip()
    anp_combined = str(row["ANP_Combined_cleaned"]) + str(row["Medication_Combined_cleaned"]) ############## 01102025

    chf_true = row.get("CHF_True", False)
    covid_true = row.get("COVID_True", False)

    copd_dict = row.get("ANP_COPD", {})
    
    ################## this part will be updated in v2
    if "output_medication_with_classification_anp" in row: 
        meds  = row.get("output_medication_with_classification", [])
        meds1 = row.get("output_medication_with_classification_anp", [])
        #print("combined")
    
        if meds == "Missing" or not isinstance(meds, list):
            #validate.append(("MEDICATION DATA", "Missing"))
            meds = meds1
            #return risk_level, validate
            if len(meds) == 0:
                validate.append(("MEDICATION ORDER EXTRACTION", "MISSING"))
                return risk_level, validate
        else:
            meds = meds+meds1
    else:
        meds = row.get("output_medication_with_classification", [])
        #print("not combined")
        if meds == "Missing" or not isinstance(meds, list):
            validate.append(("MEDICATION ORDER EXTRACTION", "MISSING"))
            return risk_level, validate
    ################################################################

    if len(meds) == 0:
        return risk_level, validate
        
    for med in meds:
        true_med=[]
        med = copy.deepcopy(med)
        names = med.get("name", [])
        names = [name.upper() for name in names if name and len(name)>3]
        #names_str = "Med > "+"|".join(names[0:3]) if names else "UNKNOWN" #"|".join(names[0:1]) if names else "UNKNOWN"
        ANP_True = med.get("ANP",False)
        anp_med_start = "ANP_MED > "
        ################### this will also be updated in v2
        names_str_anp = anp_med_start +"|".join(names[0:3]) if names else "UNKNOWN"
        ############################## 
        route = str(med.get("route", "")).upper()
        form = str(med.get("form", "")).upper()
        normalized_route = str(med.get("nomalized_route","")).upper()
        categories = [str(c).upper() for c in med.get("category", [])]
        names_str = "MED_ORDER > "+ str(med.get("medication",""))
        dos = row["formatted_DOS"]


        ########## this will be updated in v2 
        if ANP_True:    #"NOT_AVAIL" in names_str: 
            names_str = names_str_anp
            #print(names_str)
            if not route:
                route = "Route Missing"
        ################################

        if len(names) == 0:
            continue  # Skip if no valid name

        ### stopped med detection from ANP
        detect_stop_med = detect_stop_related_sentences(anp_text=anp_combined, words=names)
        continue_outer= False
        for sent in detect_stop_med: #### 03-11-2025
            stoped_med = extract_stopped_meds(sent)
            if ANP_True:
                names_str_local = "|".join([
                                                name for name in names 
                                                if (name in stoped_med) or 
                                                any(name in stp_med for stp_med in stoped_med)
                                            ]) 
                names_str = anp_med_start+names_str_local  if names_str_local else names_str
                
            if not("CONTINUE" in sent or "DO NOT HOLD" in sent): ###### 01-11-2025
                
                if len(stoped_med) > 0:
                    if (any(name in stoped_med for name in names) or any(name in stp_med for stp_med in stoped_med for name in names)):
                        validate.append((names_str, f"Medication Discontinue - {sent} >> Not Counted"))
                        #print(f"{chart_id}, {names_str} >>>>>>> {detect_stop_med[0]}")
                        continue_outer =  True
                        break
                    else:
                        continue
                else:
                    validate.append((names_str, f"Medication Discontinue - {sent} >> Not Counted"))
                    #print(f"{chart_id}, {names_str} >>>>>>> {detect_stop_med[0]}")
                    continue_outer =  True
                    break
            elif len(stoped_med) > 0 and (any(name in stoped_med for name in names) or any(name in stp_med for stp_med in stoped_med for name in names)):
                validate.append((names_str, f"Medication Discontinue - {sent} >> Not Counted"))
                #print(f"{chart_id}, {names_str}>>>>>>> {detect_stop_med[0]}")
                continue_outer =  True
                break
        if continue_outer:
            continue

        # Special handling for DVT prophylaxis medications
        if chart_id in dvt_chart_med and any(dvt.upper() in names for dvt in dvt_chart_med[chart_id]): ######Added on 30-10-2025
            if ANP_True:
                names_str_local = "|".join([name for name in names if name in dvt_chart_med[chart_id]])
                names_str = anp_med_start+names_str_local  if names_str_local else names_str
            validate.append((names_str, "DVT Prophylaxis Initial >> Not Counted"))
            continue
        elif any(dvt in names for dvt in dvt_med_names):
            if ANP_True:
                names_str_local = "|".join([name for name in names if name in dvt_med_names])
                names_str = anp_med_start+names_str_local  if names_str_local else names_str
            validate.append((names_str, "DVT Prophylaxis >> Not Counted"))
            continue  # Skip DVT meds for risk calculation
        elif chart_id in dvt_chart_med_sq:
            skip_outer = False
            for key_dos, value in dvt_chart_med_sq[chart_id].items():
                if dos >= key_dos and any(dvt.upper() in names for dvt in value):
                    if ANP_True:
                        names_str_local = "|".join([name for name in names if name in value])
                        names_str = anp_med_start+names_str_local  if names_str_local else names_str
                    validate.append((names_str, "DVT Prophylaxis Subsequent >> Not Counted"))
                    skip_outer = True
                    break  # break inner loop
            if skip_outer:
                continue  # skip outer loop
        
        # Normalize critical routes to "IV"
        if not normalized_route and route in CRITICAL_ROUTES:
            normalized_route = "IV"
        ##### Added rule on 12-11-2025
        if chf_true and any(m_syn in chf_med_names for m_syn in names) and ("IV" in [form, route, normalized_route] or "INJECTION" in [form, route, normalized_route] or "SYRINGE" in [form, route, normalized_route]):
            if ANP_True:
                names_str_local =  "|".join([m_syn for m_syn in names if m_syn in chf_med_names])
                names_str = anp_med_start+ names_str_local  if names_str_local else names_str
            validate.append((names_str, f"WITH CHF - {route} >> High"))
            risk_level = max(risk_level, "HIGH", key=levels.index)
            print(f"CHF HIGH RISK >> {chart_id} >> {names_str} >> {route}")
            continue
        # result = {
        #     'has_copd': False,
        #     'severity': None,
        #     'matches': [],
        #     'excluded': False
        # }
        if covid_true and any(m_syn in covid_med for m_syn in names) and ("IV" in [form, route, normalized_route] or "INJECTION" in [form, route, normalized_route] or "SYRINGE" in [form, route, normalized_route]):
            if ANP_True:
                names_str_local =  "|".join([m_syn for m_syn in names if m_syn in covid_med])
                names_str = anp_med_start + names_str_local  if names_str_local else names_str
            validate.append((names_str, f"WITH COVID - {route} >> High"))
            risk_level = max(risk_level, "HIGH", key=levels.index)
            print(f"COVID HIGH RISK >> {chart_id} >> {names_str} >> {route}")
            continue

        if copd_dict.get("has_copd", False):
            copd_matches = copd_dict.get("matches", [])
            print(f"Chart ID: {chart_id}, COPD Matches: {copd_matches}")
            copd_severity = copd_dict.get("severity", None)
            if (copd_severity == "severe" or copd_severity == "moderate") and any(m_syn in names for m_syn in copd_med) and ("IV" in [form, route, normalized_route] or "INJECTION" in [form, route, normalized_route]):
                if ANP_True:
                    names_str_local = "|".join([m_syn for m_syn in copd_med if m_syn in names])
                    names_str = anp_med_start+names_str_local  if names_str_local else names_str

                validate.append((names_str, f" WITH COPD - {route} >> High"))
                risk_level = max(risk_level, "HIGH", key=levels.index)
                continue
        ##### Added rule on 10-11-2025
        if surgery_list and ("SEPSIS" in surgery_list or any("SEPSIS" in s for s in surgery_list)):
            if any(m_syn in sepsis_antibiotics_iv for m_syn in names) and ("IV" in [form, route, normalized_route] or "INJECTION" in [form, route, normalized_route] or "SYRINGE" in [form, route, normalized_route]) :
                if ANP_True:
                    names_str_local = "|".join([m_syn for m_syn in names if m_syn in sepsis_antibiotics_iv])
                    names_str = anp_med_start+names_str_local  if names_str_local else names_str
                validate.append((names_str, f"WITH SEPSIS - {route} >> High"))
                risk_level = max(risk_level, "HIGH", key=levels.index)
                continue

        ##### Added rule on 12-11-2025
        if surgery_list and ("DIVERTICULITIS" in surgery_list or any("DIVERTICULITIS" in s for s in surgery_list)):
            if any(m_syn in diverticulitis_antibiotics_iv for m_syn in names) and ("IV" in [form, route, normalized_route] or "INJECTION" in [form, route, normalized_route] or "SYRINGE" in [form, route, normalized_route]) :
                if ANP_True:
                    names_str_local = "|".join([m_syn for m_syn in names if m_syn in diverticulitis_antibiotics_iv])
                    names_str = anp_med_start+names_str_local  if names_str_local else names_str
                validate.append((names_str, f"WITH DIVERTICULITIS - {route} >> High"))
                risk_level = max(risk_level, "HIGH", key=levels.index)
                continue

        # --- High risk ---
        if "TOXIC_DRUG" in categories and ("INJECTION" in [form, route, normalized_route] or "IV" in [form, route, normalized_route]):   # drugs needing intensive monitoring ###updated 22-10-25
            if ANP_True:
                names_str_local = "|".join(med.get("toxic",[])) 
                names_str = anp_med_start+names_str_local  if names_str_local else names_str
            validate.append((names_str, f"Toxic Drug With IV - {route} >> High"))
            risk_level = max(risk_level, "HIGH", key=levels.index)
            continue  # Continue to check other meds, don't return immediately

        if "PARENTERAL_DRUG" in categories and ("INJECTION" in [form, route, normalized_route] or "IV" in [form, route, normalized_route]):
            if ANP_True:
                names_str_local = "|".join(med.get("parenteral",[]))
                names_str = anp_med_start+names_str_local  if names_str_local else names_str
            validate.append((names_str, f"Parenteral with IV - {route} >> High"))
            risk_level = max(risk_level, "HIGH", key=levels.index)
            continue

        if uti_detect and wbc_count and any(float(w_cnt) > 12.0 for w_cnt in wbc_count) and any(m_syn in uti_antibiotic_names for m_syn in names):
            if ANP_True:
                names_str_local = "|".join([m_syn for m_syn in names if m_syn in uti_antibiotic_names])
                names_str = anp_med_start+names_str_local  if names_str_local else names_str
            validate.append((names_str, f"{uti_text_str}-WBC: {wbc_count_str} >> High"))
            #print(names_str, f"{uti_text_str}-{wbc_count_str} >> High")
            risk_level = max(risk_level, "HIGH", key=levels.index)
            continue

        # if any(contrast in names for contrast in ["CONTRAST", "IOPAMIDOL", "GADOLINIUM", "IOHEXOL"]): # Commented on 28-10-25
        #     validate.append((names_str, "Imaging/Contrast >> High"))
        #     risk_level = max(risk_level, "HIGH", key=levels.index)
        #     continue

        if any(contrast in names for contrast in ["LEVETIRACETAM","KEPPRA"]) and "IV" in [form, route, normalized_route] and ("SEIZURES" in surgery_list or 'SEIZURES / EPILEPSY' in surgery_list or "EPILEPSY" in surgery_list):
            if ANP_True:
                names_str_local =  "|".join([contrast for contrast in ["LEVETIRACETAM","KEPPRA"] if contrast in names])
                names_str = anp_med_start+names_str_local  if names_str_local else names_str
            validate.append((names_str, F"KEPPRA WITH IV - {route} >> High"))
            risk_level = max(risk_level, "HIGH", key=levels.index)
            continue

        # CC_CDR medications - Critical Care Drugs
        if "CC_CDR|ROUTE" in categories:
            if ANP_True:
                names_str_local = "|".join(med.get("cc",[]))
                names_str = anp_med_start+names_str_local  if names_str_local else names_str
            validate.append((names_str, f"Critical Care Drug with Route-{route} >> High"))
            risk_level = max(risk_level, "HIGH", key=levels.index)
            continue

        # elif "CC_CDR|NOROUTE" in categories and ("IV" in [route, normalized_route] or "SQ" in [route, normalized_route]): ###updated/commented on 22-10-25
        #     validate.append((names_str, f"Critical Care Drug with route-{route} >> High"))
        #     risk_level = max(risk_level, "HIGH", key=levels.index)
        #     continue

        if "CC_CDR|NOROUTE" in categories:
            if ANP_True:
                names_str_local = "|".join(med.get("ccwor",[]))
                names_str = anp_med_start+names_str_local  if names_str_local else names_str
            validate.append((names_str, f"Critical Care Drug without Route-{route} >> Moderate"))
            risk_level = max(risk_level, "MODERATE", key=levels.index)
            continue
        # --- Moderate risk ---

        if "TOXIC_DRUG" in categories :   ###updated 22-10-25
            if ANP_True:
                names_str_local = "|".join(med.get("toxic",[]))
                names_str = anp_med_start+names_str_local  if names_str_local else names_str
            validate.append((names_str, f"Toxic Drug - {route} >> Moderate"))
            risk_level = max(risk_level, "MODERATE", key=levels.index)
            continue

        if "PARENTERAL_DRUG" in categories: #### PARENTERAL DRUG WITHOUT IV
            if ANP_True:
                names_str_local = "|".join(med.get("parenteral",[]))
                names_str = anp_med_start+names_str_local  if names_str_local else names_str
            validate.append((names_str, f"Parenteral drug - {route} >> Moderate"))
            risk_level = max(risk_level, "MODERATE", key=levels.index)
            continue

        if "INJECTION" in [form, route, normalized_route] or "IV" in [form, route, normalized_route]:
            validate.append((names_str, f"Injection/IV-{route} >> Moderate"))
            risk_level = max(risk_level, "MODERATE", key=levels.index)
            continue
        
        # 'DISCONTINUED',
        # 'NOT FOUND',
        # 'OVER THE COUNTER',
        # 'PRESCRIPTION ONLY',
        # 'RX AND/OR OTC',
        # 'UNKNOWN'

        if any(rx_cat in categories for rx_cat in ["PRESCRIPTION ONLY","","RX", "RX AND/OR OTC","DISCONTINUED","NOT FOUND","UNKNOWN"]):
            if ANP_True:
                names_str_local = "|".join(med.get("intg",[]))
                names_str = anp_med_start+names_str_local  if names_str_local else names_str
            validate.append((names_str, f"Prescription-{route} >> Moderate"))
            risk_level = max(risk_level, "MODERATE", key=levels.index)
            continue
        elif "PRESCRIPTION" in categories:
            validate.append((names_str, f"Prescription-{route} >> Moderate"))
            risk_level = max(risk_level, "MODERATE", key=levels.index)
            continue
        elif "NOT_KNOWN" in categories and any(name in med_rx_lx for name in names): #### added on 19-11-25
            validate.append((names_str, f"Prescription-{route} >> MODERATE"))
            risk_level = max(risk_level, "MODERATE", key=levels.index)
            continue
        # --- Low risk ---
        elif "OVER THE COUNTER" in categories:
            validate.append((names_str, "OTC >> Low"))
            risk_level = max(risk_level, "LOW", key=levels.index)
        elif "NOT_KNOWN" in categories and any(name in med_otc_lx for name in names): ###### added on 19-11-25
            validate.append((names_str, "OTC >> Low"))
            risk_level = max(risk_level, "LOW", key=levels.index)
        
        else: #"NOT_KNOWN" in categories
            validate.append((names_str, "UNKNOWN >> MODERATE"))
            risk_level = max(risk_level, "MODERATE", key=levels.index)
    return risk_level, validate

def calculate_mdm_risk_v2(row) -> tuple:
    """
    Calculate MDM Risk (Element 3) from structured flags + classified meds
    """
    levels = ["MINIMAL", "LOW", "MODERATE", "HIGH"]

    row = row.copy()
    DVT_FLAG = extract_flag(row["DVT_PPX"])
    if DVT_FLAG:
        dvt_med_names =  extract_matches(row["DVT_PPX"])
    # --- Structured findings ---
    if (extract_flag(row["Emergency_major_surgery"]) or extract_flag(row["Emergency_Keywords"]) or
        (extract_flag(row["Surgery"]) and extract_flag(row["Surgery_discussion"]) and (extract_flag(row["Risk_phrases"]) or extract_flag(row["Risk_factors"]))) or
        extract_flag(row["DNR_hospitalization"])  or #or extract_matches(row["DNR_hospitalization"])
        #extract_flag(row["EMS_WR"]) or extract_matches(row["EMS_WR"]) or
        (extract_flag(row["EMS_WR"]) and (extract_flag(row["Risk_factors"]) or extract_flag(row["Risk_phrases"])))): #Elective major surgery without risk
        structured_risk = "HIGH"
    elif extract_flag(row["Risk_factors"]) and ("CKD" in extract_matches(row["Risk_factors"]) or "AKI" in extract_matches(row["Risk_factors"]) or "TRANSFUSION" in extract_matches(row["Risk_factors"])) and "ON DIALYSIS" in extract_matches(row["Risk_factors"]):
        structured_risk = "HIGH" ###### added on 31-10-2025
    elif (extract_flag(row["Sdoh_phrases"]) or extract_flag(row["EMS_WR"]) or 
        extract_flag(row["Therapy_keyword"]) or extract_flag(row["Surgery"]) or # or  extract_flag(row["Risk_factors"]))) extract_flag(row["DVT_PPX"]) or extract_matches(row["DVT_PPX"])
        extract_flag(row["Surgery"])): # or  extract_flag(row["Risk_factors"]))) extract_flag(row["DVT_PPX"]) or extract_matches(row["DVT_PPX"])
        structured_risk = "MODERATE"
    elif (extract_flag(row["Minimal_keyword"]) or extract_flag(row["Risk_factors"]) or extract_flag(row["Risk_phrases"])):
        structured_risk = "LOW"
    else:
        structured_risk = "LOW"

    # --- Risk from meds (classified before passing here) ---
    #print(row.get("output_medication", []))
    if not DVT_FLAG:
        med_risk, validate = risk_from_medications_v3(row, dvt_med_names=[]) ###### updated from v2 to v3
    else:
        med_risk, validate = risk_from_medications_v3(row, dvt_med_names=dvt_med_names) ###### updated from v2 to v3
    
    # --- Return the higher risk ---
    return (max(structured_risk, med_risk, key=levels.index), validate)