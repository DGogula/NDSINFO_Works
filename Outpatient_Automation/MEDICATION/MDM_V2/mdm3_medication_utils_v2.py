import ast
import re   
import copy

from mdm3_db import *
from route_detection_v1 import normalize_route
from detect_discontinue_med import detect_stop_related_sentences,extract_stopped_meds
from route_pattern import SQ_variations
from header_variation import dvt_columns
#from surgery_keyword_search import extract_surgery_keywords
print(SQ_variations)

CRITICAL_ROUTES = [
            'IVPB', 'IV', 
            'IV PUSH',"IVPUSH",
            'IVPB', 'IVP', 'INTRAVENOUS', 'INFUSION', 'TRANSFUSION',
            'INTRAVENOUS', 'IV', 
            'INTRAVENOUS PUSH','IV PUSH','BOLUS',"IVT", "IVI","IVB",
            "IVD","IPB","IVBID","IVPBB","I.V.","INFUSE",
        ]  
#"DRIP" removed on 22-10-2025

# CRITICAL_ROUTES = [
#             'IVPB', 'IVP', 'INTRAVENOUS', 'INFUSION', 'TRANSFUSION',
#             'INTRAVENOUS', 'IV', 
#             #'INTRATHECAL', 
#             #'EPIDURAL', 
#             #'INTRACARDIAC', 'INTRAARTERIAL', 'INTRAOCULAR',
#             'INTRAVENOUS PUSH','IV PUSH', 'BOLUS',"IVT", "IVI","IVB"
#             "IVD","DRIP",
#             #"SYRINGE","INJECTION"
#         ]


missing_medication_list = []
#Header_name = ["ANP_Combined_cleaned","Medication_Combined_cleaned","ANP_Combined","Medication_Combined"]
#Header_name = ["ANP_Combined","Medication_Combined"]

cases=0

def safe_eval(x):
    """Convert string to Python list, handle NaN/float/malformed cases."""
    if isinstance(x, float) or x is None:  # catches NaN or None
        return []
    if isinstance(x, str):
        if x.strip() in ["", "[]", "nan", "NaN"]:
            return []
        try:
            return ast.literal_eval(x)
        except Exception:
            return []
    return []

def clean_med_name(name: str) -> str:
        """ Clean medication name by removing parenthetical content and trimming whitespace. """
        return re.sub(r"\s*\(.*?\)", "", name).strip()

def remove_numbers(name):
    if not isinstance(name, str):
        return name
    cleaned = re.sub(r"\d+", "", name)  # remove all digits
    return str(cleaned.strip())

def compare_string_with_list(input_str_lst: list, str_list: list) -> bool:
    # Clean input string
    clean_input_lst = [re.sub(r'[^A-Za-z\s]', '', input_str).lower().strip() for input_str in input_str_lst]
    clean_s_lst = [re.sub(r'[^A-Za-z\s]', '', s).lower().strip() for s in str_list]
    if set(clean_input_lst).intersection(clean_s_lst):
        return True
    return False

def compare_string_with_list_v1(input_str_lst: list, str_list: list) -> bool:
    # Clean input string
    clean_input_lst = [re.sub(r'[^A-Za-z\s]', '', input_str).lower().strip() for input_str in input_str_lst]
    clean_s_lst = [re.sub(r'[^A-Za-z\s]', '', s).lower().strip() for s in str_list]
    common_med = set(clean_input_lst).intersection(clean_s_lst)
    if common_med:
        return True, "-".join(list(common_med))
    return False,[]

def normalize(value: str):
    """
    Normalize string into a set of route options (IV, IM, SQ, DRIP, etc.)
    Supports separators: |, /, spaces, commas.
    """
    if not isinstance(value, str):
        return set()
    
    # Split by |, /, space, or comma
    parts = re.split(r'[|/,\s]+', value.strip().upper())
    return {p for p in parts if p}  # remove empty strings

def compare_routes(val1: str, val2: str) -> bool:
    """
    Compare two route strings and return True if they share at least one option.
    """
    set1 = normalize(val1)
    set2 = normalize(val2)
    return not set1.isdisjoint(set2)

def extract_numbers(text):
    numbers = re.findall(r'\d[\d,]*(?:\.\d+)?', text)
    # Optional: remove commas and convert to float or int
    cleaned_numbers = [float(num.replace(',', '')) for num in numbers]
    return cleaned_numbers

def drug_classification(input_row)  -> list:
    """ Classify drugs based on multiple databases and criteria.
    """
    input_row = input_row.copy()
    drug_list = input_row["output_medication"]
    anp_drug_list = input_row["Med_Chart_Medication_Text"]
    if drug_list == "Missing" or not isinstance(drug_list, list):
        return "Missing"
    
    new_drug_list = []
    
    global missing_medication_list

    global CRITICAL_ROUTES

    sodium_chloride_alternate = ["NACL","NS"] ##added on 23-10-2025


    for drug in drug_list:
        drug = copy.deepcopy(drug)
        drug["category"] = []
        drug["nomalized_route"] = ""
        drug_strength = str(drug.get("strength","")).strip().upper()
        medication_full_name = str(drug.get("medication","")).strip().upper() # SODIUM CHLORIDE 0.9 % FLUSH
        drip_status = drug.get("drip","")
        #print("medication fullname", medication_full_name)
        
        # Extract and clean medication names
        med_name_list = drug.get("name", [])
        if not med_name_list:
            continue
            
        med_name_list     =  [clean_med_name(med_name.upper()) for med_name in med_name_list if med_name]
        med_name_list_wno =  [remove_numbers(med_name) for med_name in med_name_list]

        categorized = False
        change_normalized= False
        
        med_route = str(drug.get("route", "")).upper().strip()
                
        if med_route in CRITICAL_ROUTES:#['IVPB', 'IVP', 'INTRAVENOUS', 'INFUSION', 'TRANSFUSION']
            #med_route = "IV" 
            drug["nomalized_route"]="IV" 
        elif med_route in ["SUSPENSION","Intramuscular","IM","INTRAMUSCULAR","INTRA"]:
            #med_route = "IM" #SC/SQ 
            drug["nomalized_route"]="IM"  
        elif med_route in SQ_variations: #['SUBCUTANEOUS', 'SC', 'SUBCUT','SUBCOT',"ID"]: #'SYRINGE','INJECTION']:
            #med_route = "SQ"
            drug["nomalized_route"] = "SQ"
        elif not(drip_status == "" or drip_status is None or str(drip_status).upper() == "NAN"  or str(drip_status).upper() == "NONE"):
            drug["nomalized_route"] = "DRIP"
        else: 
            change_normalized = True
        
        # Check CC_CDR route database
        
        for med_name, med_name_wo_no in zip(med_name_list, med_name_list_wno):
            # if (med_name in continue_med) or (med_name_wo_no in continue_med):
            #     continue
            cc_cond1=(med_name in cc_cdr_db_med_route or any(((med_name in med_key) or (med_name.replace(" ","") in med_key)) for med_key in list(cc_cdr_db_med_route.keys())))
            cc_cond2=(med_name_wo_no in cc_cdr_db_med_route or any(((med_name_wo_no in med_key) or (med_name_wo_no.replace(" ","") in med_key)) for med_key in list(cc_cdr_db_med_route.keys())))
            if cc_cond1:
                med_name = [med_key for med_key in list(cc_cdr_db_med_route.keys()) if ((med_name in med_key) or (med_name.replace(" ","") in med_key))][0]
                #med_name_wo_no = [med_key for med_key in list(cc_cdr_db_med_route.keys()) if ((med_name_wo_no in med_key) or (med_name_wo_no.replace(" ","") in med_key))][0]
                db_routes = [route.upper().strip() for route in cc_cdr_db_med_route[med_name].split("|")]
            elif cc_cond2:
                med_name = [med_key for med_key in list(cc_cdr_db_med_route.keys()) if ((med_name_wo_no in med_key) or (med_name_wo_no.replace(" ","") in med_key))][0]
                db_routes = [route.upper().strip() for route in cc_cdr_db_med_route[med_name].split("|")]
            
            if cc_cond1 or cc_cond2:
                if change_normalized:
                    drug["nomalized_route"] = normalize_route(med_name, medication_full_name, med_route, anp_drug_list)
                    drug["route_found_from_anp"] = "True"

                cc_cond3=(compare_routes(" ".join(db_routes), med_route) or med_route in db_routes or compare_routes(" ".join(db_routes), drug["nomalized_route"]) or drug["nomalized_route"] in db_routes)
                if cc_cond3 and (medication_full_name in  cc_cdr_db_med_route.keys()):
                    drug["category"].append("CC_CDR|ROUTE")
                    categorized = True
                    break
                elif cc_cond3: ##later update # 3% sodium chloride, or >= 2000 ML
                    numbers = extract_numbers(medication_full_name)
                    strength_vals = extract_numbers(drug_strength)
                    in_alt_names = (med_name in sodium_chloride_alternate) or (med_name_wo_no in sodium_chloride_alternate)

                    # Simplify the main condition
                    is_sodium_chloride = (
                        ("SODIUM CHLORIDE" in medication_full_name and "IN SODIUM CHLORIDE" not in medication_full_name)
                        or in_alt_names
                    )

                    if is_sodium_chloride:
                        # Check for numeric pattern conditions
                        if (
                                "3%" in medication_full_name or
                                any(n >= 2000 for n in numbers) or
                                (strength_vals and strength_vals[0] >= 2000 and 
                                "ML" in drug_strength.replace(" ", ""))
                            ):
                        #if any(int(n) == 3 for n in numbers) or any(n >= 2000 for n in numbers) or (strength and strength[0] >= 2000 and "ML" in drug_strength):
                            drug["category"].append("CC_CDR|ROUTE")
                            categorized = True
                    else:
                        # Skip if it’s related to sodium/chloride variants
                        if "SODIUM" in med_name or "CHLORIDE" in med_name or in_alt_names:
                            continue
                        # Otherwise categorize
                        drug["category"].append("CC_CDR|ROUTE")
                        categorized = True
                        break
                else:
                    drug["category"].append("CC_CDR|NOROUTE")
                  # Found in CC_CDR, no need to check other databases
        
        # Check other databases if not already categorized
        if not categorized:
            if compare_string_with_list(med_name_list, toxicity_drug_db_list) or compare_string_with_list(med_name_list_wno, toxicity_drug_db_list):
                drug["category"].append("TOXIC_DRUG")
                categorized = True

            if compare_string_with_list(med_name_list, parental_drug_db_list) or compare_string_with_list(med_name_list_wno, parental_drug_db_list):
                drug["category"].append("PARENTERAL_DRUG")
                categorized = True
            
            # Check integrated drug databases
            if not categorized:
                for med_name, med_name_wno in zip(med_name_list, med_name_list_wno):
                    intg_cond1 = (med_name in intg_drug_db_dict or any(med_name in med_key for med_key in list(intg_drug_db_dict.keys())))
                    intg_cond2 = (med_name_wno in intg_drug_db_dict or any(med_name_wno in med_key for med_key in list(intg_drug_db_dict.keys())))
                    intg_brand_cond1 = (med_name in intg_drug_db_dict_brand or any(med_name in med_key for med_key in list(intg_drug_db_dict_brand.keys())))
                    intg_brand_cond2 = (med_name_wno in intg_drug_db_dict_brand or any(med_name_wno in med_key for med_key in list(intg_drug_db_dict_brand.keys())))
                    intg_generic_cond1 = (med_name in intg_drug_db_dict_generic or any(med_name in med_key for med_key in list(intg_drug_db_dict_generic.keys())))
                    intg_generic_cond2 = (med_name_wno in intg_drug_db_dict_generic or any(med_name_wno in med_key for med_key in list(intg_drug_db_dict_generic.keys())))
                    
                    if intg_cond1:
                        med_name = [med_key for med_key in list(intg_drug_db_dict.keys()) if med_name in med_key][0]
                        drug["category"].append(intg_drug_db_dict[med_name])
                        categorized = True
                        break
                    elif intg_cond2:
                        med_name = [med_key for med_key in list(intg_drug_db_dict.keys()) if med_name_wno in med_key][0]
                        drug["category"].append(intg_drug_db_dict[med_name])
                        categorized = True
                        break
                    elif intg_brand_cond1:
                        med_name = [med_key for med_key in list(intg_drug_db_dict_brand.keys()) if med_name in med_key][0]
                        drug["category"].append(intg_drug_db_dict_brand[med_name])
                        categorized = True
                        break
                    elif intg_brand_cond2:
                        med_name = [med_key for med_key in list(intg_drug_db_dict_brand.keys()) if med_name_wno in med_key][0]
                        drug["category"].append(intg_drug_db_dict_brand[med_name])
                        categorized = True
                        break
                    elif intg_generic_cond1:
                        med_name = [med_key for med_key in list(intg_drug_db_dict_generic.keys()) if med_name in med_key][0]
                        drug["category"].append(intg_drug_db_dict_generic[med_name])
                        categorized = True
                        break
                    elif intg_generic_cond2:
                        med_name = [med_key for med_key in list(intg_drug_db_dict_generic.keys()) if med_name_wno in med_key][0]
                        drug["category"].append(intg_drug_db_dict_generic[med_name])
                        categorized = True
                        break
        
        # Default category if not found in any database
        if not categorized and med_name_list:
            drug["category"].append("RX")
            missing_medication_list.append((med_name_list[0],med_route))
        new_drug_list.append(drug)
    return new_drug_list

dvt_chart_med = {}
dvt_chart_med_sq = {}

# Updated on 22-10-2025 - 29-10-2025 - 30-10-2025
def DVT_Medications(row, Header_names)    -> list:
    """Extract DVT prophylaxis medications from the specified text column."""
    global dvt_chart_med
    row = row.copy()
    chart_id = row["Chart"]
    visit_type = row["Visit"].upper()
    dos = row["formatted_DOS"]
    chart = row[Header_names].to_list()
    dvt_avl = [col for col in dvt_columns if col in row]
    dvt_text = " ".join(str(row[col]) for col in dvt_avl if pd.notna(row[col])).upper() if dvt_avl else ""

    if isinstance(chart, list):
         chart = " ".join(str(x) for x in chart if pd.notna(x)).upper()
    else:
        chart = str(chart).upper() if pd.notna(chart) else ""
    lovenox_variations = ["Lo","Lov","Love","Loven","Loveno","Lovenox","loveno","lovenoy"] ###updated
    lovenox_variations = [variation.upper() for variation in lovenox_variations]
    Heparin_variations = ["He","Hep","Hepa","Hepar","Hepari","Heparin"]
    Heparin_variations = [variation.upper() for variation in Heparin_variations]
    base_drugs = ["loveno","lovenoy","Lovenox", "Heparin","Eliquis","Xarelto","DNR","Warfarin","Jantoven", "Coumadin","apixaban","ENOXAPARIN","rivaroxaban"]
    list_of_dvt = base_drugs+Heparin_variations+lovenox_variations # spelling mistake found for heparin, lovenox as hepari, hepar, and other variations -- date 29-10-25
    # Create a regex pattern to match both "DVT ppx:" and "DVT prophylaxis:"
    #pattern_template = r"(DVT\s*(ppx|prophylaxis)\s*:*\s*{})"
#     pattern_template = (
#     r"(?i)\b(?:"  # (?i) for case-insensitive, start of non-capturing group
#     r"(?:DVT|VTE|VENOUS\s+THROMBOEMBOLISM|DEEP VEIN THROMBOSIS|deep venous thrombisis|deep venous thrombosis)?\s*(?:PPX|PX|PROPHYLAXIS|PREVENTION|PROPHYLASIX)*\s*[:\-]?\s*.*{0}\b"  # e.g. DVT prophylaxis: Enoxaparin
#     r"|{0}\b.*?(?:FOR|WITH|ON|GIVEN AS)\s*(?:DVT|VTE|VENOUS\s+THROMBOEMBOLISM|DEEP VEIN THROMBOSIS|deep venous thrombisis|deep venous thrombosis)\s*(?:PPX|PROPHYLAXIS|PREVENTION)"  # e.g. Enoxaparin for DVT prophylaxis
#     # Direct medication GTT mention (e.g., Heparin gtt)
#     r"|{0}\b\s*(?:GTT)\b.*?" ### Added on 11-11-2025
#     r"(?:FOR\s+[A-Z\s]+)?" ### Added on 11-11-2025 
#     r")"
# ) ##################### Commented on 19-11-25
    
    pattern_template = (
    r"(?i)(?s)\b(?:"  # (?i) for case-insensitive, start of non-capturing group
    # Option 1: Must have DVT terms OR prophylaxis terms (at least one)
    r"(?:(?:DVT|VTE|VENOUS\s+THROMBOEMBOLISM|deep venous thrombisis|deep venous thrombosis)\s*(?:PPX|PX|PROPHYLAXIS|PREVENTION|PROPHYLASIX|proph|prophy|treatments)?|(?:PPX|PX|PROPHYLAXIS|PREVENTION|PROPHYLASIX|proph|prophy|treatments)\s*(?:DVT|VTE|VENOUS\s+THROMBOEMBOLISM|deep venous thrombisis|deep venous thrombosis)?)\s*[:\-]?\s*.*{0}\b"
    
    r"|"  # OR
    
    # Option 2: Medication with FOR/WITH/ON/GIVEN AS must have DVT terms OR prophylaxis terms  
    r"{0}\b.*?(?:FOR|WITH|ON|GIVEN AS)\s*(?:(?:DVT|VTE|VENOUS\s+THROMBOEMBOLISM|deep venous thrombisis|deep venous thrombosis)\s*(?:PPX|PROPHYLAXIS|PREVENTION|PROPHYLASIX)?|(?:PPX|PROPHYLAXIS|PREVENTION|PROPHYLASIX)\s*(?:DVT|VTE|VENOUS\s+THROMBOEMBOLISM|deep venous thrombisis|deep venous thrombosis)?)"
    
    r"|"  # OR
    
    # Option 3: Direct medication GTT mention (e.g., Heparin gtt)
    r"{0}\b\s*(?:GTT)\b.*?"
    r"(?:FOR\s+[A-Z\s]+)?"
    r")"
)
    # Loop through each drug and check if it's present after either prefix
    found_matches = []
    list_of_dvt = set([drug.upper() for drug in list_of_dvt])
    for drug in list_of_dvt:
        drug = drug.upper()
        pattern = pattern_template.format(re.escape(drug))
        if re.search(pattern, chart, re.IGNORECASE):
            if drug in Heparin_variations:
                found_matches.append("HEPARIN")
                #found_matches.append("LOVENOX") ### added on 12-11-2025
            elif drug in lovenox_variations:
                found_matches.append("LOVENOX")
                found_matches.append("ENOXAPARIN") ### added 20-11-25
                #found_matches.append("HEPARIN") ### added on 12-11-2025
            else:
                found_matches.append(drug)
    for drug in base_drugs:
        drug = drug.upper()
        if drug in dvt_text:
            if drug in lovenox_variations:
                found_matches.append("LOVENOX")
                found_matches.append("ENOXAPARIN") ### added 20-11-25
            elif drug in Heparin_variations:
                found_matches.append("HEPARIN")
            else:
                found_matches.append(drug)
    if visit_type =="INITIAL":
        dvt_chart_med[chart_id] = list(set(found_matches))
    elif len(found_matches)>0:
        dvt_chart_med_sq[chart_id] = {dos:list(set(found_matches))}
    return [{True if len(found_matches) else False:list(set(found_matches))}]

# def generate_variations(phrase)  -> str:
#     """
#     Generate regex pattern variations for a given phrase or list of phrases
#     to catch punctuation, spaces, and hyphen differences.
#     """
#     # If input is a list, process each phrase recursively
#     if isinstance(phrase, list):
#         return [generate_variations(p) for p in phrase]
    
#     # If not string, convert to string safely
#     if not isinstance(phrase, str):
#         phrase = str(phrase)
    
#     # Escape regex metacharacters except spaces and hyphens
#     phrase = re.escape(phrase.strip().upper())
    
#     # Allow flexible spacing, hyphens, slashes, and punctuation
#     pattern = (
#         phrase
#         .replace(r'\ ', r'[\s\-]*')   # allow spaces or hyphens
#         .replace(r'\-', r'[\s\-]*')   # allow spaces or hyphens
#         .replace(r'\\/', r'[\s\/\-]*')  # allow slashes
#         .replace(r'\.', r'[\.\s\-]*')   # allow dots and spaces
#     )
#     return pattern


# chart_df["Surgery"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, Surgery_list_1))
# chart_df["Surgery_discussion"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, Surgery_discussion_list_2))
# chart_df["Risk_factors"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, Risk_factors_list_3))
# chart_df["Risk_phrases"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, Risk_phrases_4))
# chart_df["Sdoh_phrases"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, Sdoh_phrases))
# chart_df["EMS_WR"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, Elective_major_surgery_WR)) # Without Risk
# chart_df["DNR_hospitalization"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, DNR_Hospitalization))
# chart_df["Therapy_keyword"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, Therapy_list_low))
# chart_df["Minimal_keyword"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, Mdm_minimal))
# chart_df["Emergency_major_surgery"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, EMERGENCY_MAJOR_SURGERY))
# chart_df["Emergency_Keywords"] = chart_df.apply(extract_surgery_keywords, axis=1, args=(self.Header_names, Emergency_keywords))
# chart_df["DVT_PPX"] = chart_df.apply(DVT_Medications, axis=1, args=(self.Header_names,))
     

### Updated on 22-10-2025
# def extract_surgery_keywords(row, Header_names, keyword_list) -> list:
#     """
#     Extracts surgery-related keywords from multiple header columns in a DataFrame row.
    
#     Args:
#         row (pd.Series): A single row of DataFrame.
#         Header_names (list): List of column names to search in.
#         keyword_list (list): List of keywords to detect.
    
#     Returns:
#         list: [{True: [matched_keywords]}] or [{False: []}]
#     """
#     check_col = ["Surgery","Surgery_discussion","Risk_factors","Risk_phrases"]
#     keyword_match_found = []
#     for col in check_col:
#         if col in row:
#             key = list(row[col][0].keys())[0]
#             keyword_match_found.extend(row[col][0].get(key,[]))

#     # Normalize keywords to uppercase
#     keyword_list = [keyword.upper().strip() for keyword in keyword_list]

#     # Combine text from multiple columns
#     text = row[Header_names].to_list()
#     if isinstance(text, list):
#          text = "\n".join(str(x) for x in text if pd.notna(x)).upper()
#     else:
#         text = str(text).upper() if pd.notna(text) else ""

#     # Early exit if no text
#     if not text:
#         return [{False: []}]
    

#     found_matches = []

#     # Build pattern for direct matches
#     base_pattern = r"\b(" + "|".join(map(re.escape, keyword_list)) + r")\b"

#     # Find matches in the combined text
#     matches = re.findall(base_pattern, text, flags=re.IGNORECASE)

#     for m in matches:
#         if all(m not in k for k in keyword_match_found):
#             found_matches.append(m)

#     #(Optional) Check variations if you have generate_variations()
#     for phrase in keyword_list:
#         pattern = generate_variations(phrase)
#         if re.search(pattern, text, re.IGNORECASE) and all(phrase not in k for k in keyword_match_found):
#             found_matches.append(phrase)

#     # Return result in structured format
#     if found_matches:
#         return [{True: list(set(found_matches))}]
#     else:
#         return [{False: []}]


# def extract_surgery_keywords(row, Header_name, keyword_list)    -> list :
#     row = row.copy()
#     keyword_list = [keyword.upper() for keyword in keyword_list]
#     pattern = "|".join(map(re.escape, keyword_list))
#     pattern2 = generate_variations(keyword_list)
#     text = row[Header_name].to_list()
#     if isinstance(text, list):
#          text = " ".join(str(x) for x in text if pd.notna(x)).upper()
#     else:
#         text = str(text).upper() if pd.notna(text) else ""
#     found = bool(re.search(pattern, text, flags=re.IGNORECASE))
#     if found:
#         matched = [s for s in keyword_list if re.search(re.escape(s), text, flags=re.IGNORECASE)]
#         return [{found:matched}]
#     else:
#         found_matches=[]
#         for phrase in keyword_list:
#             pattern = generate_variations(phrase)
#             if re.search(pattern, text, re.IGNORECASE):
#                 found_matches.append(phrase.strip())
#         if len(found_matches) > 0:
#             return [{True:found_matches}]
#         else:
#             return [{False:found_matches}]


def risk_from_medications(row, dvt_med_names=[]) -> tuple:
    """
    Determine MDM Risk contribution from medication list
    using drug_classification flags (NER + category list).

    """
    uti_antibiotic_names = [
    # Piperacillin + Tazobactam
    "PIPERACILLIN",
    "TAZOBACTAM",
    "PIPERACILLIN AND TAZOBACTAM",
    "PIPERACILLIN-TAZOBACTAM",
    "ZOSYN",
    "TAZOCIN",

    # Ceftriaxone
    "CEFTRIAXONE",
    "ROCEPHIN",
    "MONOCEF",
    "TRIAXON",
    "CEFAXONE"
    ]
    #uti_antibiotic_names

    global CRITICAL_ROUTES
   
    levels = ["MINIMAL", "LOW", "MODERATE", "HIGH"]
    risk_level = "LOW"
    validate = []
    row = row.copy()

    #### uti detection
    uti_detect = row["UTI_Detected"]
    uti_text   = row['UTI_Text'][1]
    uti_text_str = ",".join(uti_text)
    wbc_count  = row['WBC_values']
    wbc_count_str = ",".join([str(wc)for wc in wbc_count])
    chart_id = row["Chart"] ########### 30102025
    anp_combined = str(row["ANP_Combined_cleaned"]) + str(row["Medication_Combined_cleaned"]) ############## 01102025

    meds = row.get("output_medication_with_classification", [])
    if meds == "Missing" or not isinstance(meds, list):
        validate.append(("MEDICATION DATA", "Missing"))
        return risk_level, validate
    if len(meds) == 0:
        return risk_level, validate
        
    for med in meds:
        med = copy.deepcopy(med)
        names = med.get("name", [])
        names = [name.upper() for name in names if name]
        #names_str = "Med > "+"|".join(names[0:3]) if names else "UNKNOWN" #"|".join(names[0:1]) if names else "UNKNOWN"
        route = str(med.get("route", "")).upper()
        form = str(med.get("form", "")).upper()
        normalized_route = str(med.get("nomalized_route","")).upper()
        categories = [str(c).upper() for c in med.get("category", [])]
        names_str = "Med > "+ med.get("medication","")
        dos = row["formatted_DOS"]
        # if uti_detect:
        #     print (uti_detect, uti_text, wbc_count_str, names_str)

        if len(names) == 0:
            continue  # Skip if no valid name

        ### stopped med detection in 
        detect_stop_med = detect_stop_related_sentences(anp_text=anp_combined, words=names)
        continue_outer= False
        for sent in detect_stop_med: #### 03-11-2025
            stoped_med = extract_stopped_meds(sent)
            if not("CONTINUE" in sent or "DO NOT HOLD" in sent): ###### 01-11-2025
                validate.append((names_str, f"Medication Discontinue: {sent} >> Not Counted"))
                print(f"{chart_id}, {names_str} >>>>>>> {detect_stop_med[0]}")
                continue_outer =  True
                break
            elif len(stoped_med) > 0 and any(name in stoped_med for name in names):
                validate.append((names_str, f"Medication Discontinue: {sent} >> Not Counted"))
                print(f"{chart_id}, {names_str}: {detect_stop_med[0]}")
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
            validate.append((names_str, f"{uti_text_str}-{wbc_count_str} >> High"))
            #print(names_str, f"{uti_text_str}-{wbc_count_str} >> High")
            risk_level = max(risk_level, "HIGH", key=levels.index)
            continue

        # if any(contrast in names for contrast in ["CONTRAST", "IOPAMIDOL", "GADOLINIUM", "IOHEXOL"]): # Commented on 28-10-25
        #     validate.append((names_str, "Imaging/Contrast >> High"))
        #     risk_level = max(risk_level, "HIGH", key=levels.index)
        #     continue
        if any(contrast in names for contrast in ["LEVETIRACETAM","KEPPRA"]) and "IV" in [form, route, normalized_route] : # Commented on 28-10-25
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

        if "PARENTERAL_DRUG" in categories:
            validate.append((names_str, f"Parenteral without IV -{route} >> Moderate"))
            risk_level = max(risk_level, "MODERATE", key=levels.index)
            continue

        if "INJECTION" in [form, route, normalized_route] or "IV" in [form, route, normalized_route]:
            validate.append((names_str, f"Injection/IV-{route} >> Moderate"))
            risk_level = max(risk_level, "MODERATE", key=levels.index)
            continue

        # --- Moderate risk ---
        if any(rx_cat in categories for rx_cat in ["PRESCRIPTION ONLY","PRESCRIPTION","RX", "RX AND/OR OTC"]):
            validate.append((names_str, f"Prescription-{route} >> Moderate"))
            risk_level = max(risk_level, "MODERATE", key=levels.index)
            continue

        # --- Low risk ---
        elif "OVER THE COUNTER" in categories:
            validate.append((names_str, "OTC >> Low"))
            risk_level = max(risk_level, "LOW", key=levels.index)

    return risk_level, validate


def extract_flag(cell)  -> bool:
    """Extracts boolean flag from [{True:[...]}, {False:[...]}] style cells."""
    if isinstance(cell, list) and len(cell) > 0 and isinstance(cell[0], dict):
        return list(cell[0].keys())[0]
    return False

def extract_matches(cell) -> list:
    """Extracts matched phrases from [{True:[...]}] style cells."""
    if isinstance(cell, list) and len(cell) > 0 and isinstance(cell[0], dict):
        return list(cell[0].values())[0]
    return []

def calculate_mdm_risk(row) -> tuple:
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
        med_risk, validate = risk_from_medications(row, dvt_med_names=[])
    else:
        med_risk, validate = risk_from_medications(row, dvt_med_names=dvt_med_names)
    
    # --- Return the higher risk ---
    return (max(structured_risk, med_risk, key=levels.index), validate)

def expand_row(row):
    """ Expand rows based on DATE and END DATE, handling errors for large date ranges.
    """
    global cases
    if pd.isna(row["DATE"]) or pd.isna(row["END DATE"]):
        return pd.DataFrame([row])  # return original row
    start_date = row["DATE"]
    end_date = row["END DATE"]
    diff_days = (end_date - start_date).days
    if int(diff_days) > 500:
        filename_tmp = row["Filename"]
        cases=cases+1
        print(f"Error Cases: {cases}")
        print(f"Filename: {filename_tmp}, Medication Range: {diff_days}")
        return pd.DataFrame([row])
    return pd.DataFrame({
        "DATE": pd.date_range(row["DATE"], row["END DATE"], freq="D"),
        "ST_DATE": row["ST_DATE"], 
        "COMB": row["COMB"],
        "MEDICATION": row["MEDICATION"],
        "ORDER DETAIL": row["ORDER DETAIL"],
        "PROVIDER": row["PROVIDER"],
        "END DATE": row["END DATE"],
        "filename": row["filename"],
        "Filename": row["Filename"],
        "Chart" : row["Chart"],
        "MED_ORDER": row["MED_ORDER"],
        "Med_MED_ORDER": row["Med_MED_ORDER"],
        "PRN": row["PRN"]
    })


def expand_row_v2(row):
    """ Expand rows based on DATE and END DATE, handling errors for large date ranges.
    """
    global cases
    if pd.isna(row["DATE"]) or pd.isna(row["END DATE"]):
        return pd.DataFrame([row])  # return original row
    start_date = row["DATE"]
    end_date = row["END DATE"]
    diff_days = (end_date - start_date).days
    if int(diff_days) > 500:
        filename_tmp = row["Filename"]
        cases=cases+1
        print(f"Error Cases: {cases}")
        print(f"Filename: {filename_tmp}, Medication Range: {diff_days}")
        return pd.DataFrame([row])
    return pd.DataFrame({
        "DATE": pd.date_range(row["DATE"], row["END DATE"], freq="D"),
        "ST_DATE": row["ST_DATE"], 
        "STATUS": row["STATUS"],
        "MEDICATION": row["MEDICATION"],
        "strenth": row["strength"],
        "route": row["route"],
        "END DATE": row["END DATE"],
        "filename": row["filename"],
        "Filename": row["Filename"],
        "Chart" : row["Chart"],
        "MED_ORDER": row["MED_ORDER"],
        "Med_MED_ORDER": row["Med_MED_ORDER"],
        "PRN": row["PRN"]
    })

def expand_row_v1(row):
    if pd.isna(row["DATE"]) or pd.isna(row["END DATE"]):
        return pd.DataFrame([row])  # return original row
    
    # Check if END DATE is before DATE and swap if needed
    start_date = row["DATE"]
    end_date = row["END DATE"]
    
    if end_date < start_date:
        # Swap the dates
        start_date, end_date = end_date, start_date
    
    return pd.DataFrame({
        "DATE": pd.date_range(start_date, end_date, freq="D"),
        "COMB": row["COMB"],
        "MEDICATION": row["MEDICATION"],
        "ORDER DETAIL": row["ORDER DETAIL"],
        "PROVIDER": row["PROVIDER"],
        "END DATE": end_date,  # Use the corrected end date
        "filename": row["filename"],
        "Filename": row["Filename"],
        "Chart": row["Chart"],
        "MED_ORDER": row["MED_ORDER"],
        "Med_MED_ORDER": row["Med_MED_ORDER"],
        "PRN": row["PRN"]
    })

def expand_row_v4(row):
    """ Expand rows based on DATE and END DATE, handling errors for large date ranges.
    """
    global cases
    if pd.isna(row["DATE"]) or pd.isna(row["END DATE"]):
        return pd.DataFrame([row])  # return original row
    start_date = row["DATE"]
    end_date = row["END DATE"]
    diff_days = (end_date - start_date).days
    if int(diff_days) > 500:
        filename_tmp = row["Filename"]
        cases=cases+1
        print(f"Error Cases: {cases}")
        print(f"Filename: {filename_tmp}, Medication Range: {diff_days}")
        return pd.DataFrame([row])
    return pd.DataFrame({
        "DATE": pd.date_range(row["DATE"], row["END DATE"], freq="D"),
        "ST_DATE": row["ST_DATE"], 
        "DOSE": row["DOSE"],
        "MEDICATION": row["MEDICATION"],
        #"FREQUENCY": row["FREQUENCY"],
        "ROUTE": row["ROUTE"],
        "END DATE": row["END DATE"],
        "filename": row["filename"],
        "Filename": row["Filename"],
        "Chart" : row["Chart"],
        "MED_ORDER": row["MED_ORDER"],
        "Med_MED_ORDER": row["Med_MED_ORDER"],
        "PRN": row["PRN"]
    })