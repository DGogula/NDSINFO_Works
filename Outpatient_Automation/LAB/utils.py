# utils.py
import pandas as pd
import re
import ast
from datetime import datetime
from difflib import SequenceMatcher

# ------------------------------------------------------------
# Date helpers
# ------------------------------------------------------------
def normalize_date(date_str):
    """Normalize date to consistent MM/DD/YYYY format."""
    if not date_str or not isinstance(date_str, str):
        return None
    date_str = date_str.strip()
    formats = ["%m/%d/%Y", "%m/%d/%y", "%b-%d-%Y", "%B-%d-%Y"]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            continue
    # Handle month abbreviation typos (simplified)
    month_match = re.match(r'([A-Za-z]{3})[-/](\d{1,2})[-/](\d{4})', date_str)
    if month_match:
        month_str, day, year = month_match.groups()
        month_corrections = {'jan':'Jan','feb':'Feb','mar':'Mar','apr':'Apr','may':'May','jun':'Jun',
                             'jul':'Jul','aug':'Aug','sep':'Sep','oct':'Oct','nov':'Nov','dec':'Dec'}
        month = month_corrections.get(month_str.lower(), month_str)
        try:
            dt = datetime.strptime(f"{month}-{day}-{year}", "%b-%d-%Y")
            return dt.strftime("%m/%d/%Y")
        except:
            pass
    return None

def get_lab_content_by_dos(lab_content, target_dos):
    """Extract lab content only for sections matching target DOS."""
    target_dos_normalized = normalize_date(target_dos)
    if not target_dos_normalized:
        return lab_content
    date_pattern = r'(\d{1,2}/\d{1,2}/\d{2,4}|[A-Za-z]{3}-\d{1,2}-\d{4})'
    if not re.search(date_pattern, lab_content):
        return lab_content
    date_matches = list(re.finditer(date_pattern, lab_content))
    sections = []
    for i, match in enumerate(date_matches):
        lab_date = normalize_date(match.group(1))
        if lab_date == target_dos_normalized:
            start_pos = match.start()
            end_pos = date_matches[i+1].start() if i+1 < len(date_matches) else len(lab_content)
            sections.append(lab_content[start_pos:end_pos].strip())
    return "\n".join(sections) if sections else ""

def get_lab_content_by_dos_h(lab_content, target_dos):
    """STRICT VERSION - Only extract actual lab data for the target DOS"""
    target_dos_normalized = normalize_date(target_dos)
    
    #print(f"DEBUG: Target DOS: {target_dos}")
    #print(f"DEBUG: Normalized DOS: {target_dos_normalized}")
    
    if not target_dos_normalized:
        #print("DEBUG: Cannot normalize target DOS")
        return ""
    
    # Extract lines and look for date patterns
    lines = lab_content.split('\n')
    result_lines = []
    
    # Patterns to EXCLUDE (administrative noise)
    exclude_patterns = [
        r'^Electronically\s+signed\s+by:',
        r'^---\s*Page\s+\d+',
        r'^HILLSDALE HOSPITAL',
        r'^168\s+S\s+HOWELL\s+STREET',
        r'^MIRN:',
        r'^Account\s+#:',
        r'^Note\s+Type:',
        r'^Lab Results:',
        r'^Results:',
        r'^Reference',
        r'^Test Results',
        r'^Units',
        r'^Ordered',
        r'^Collected',
        r'^Status',
        r'^Range',
        r'^DR\.\s+[A-Z]',
        r'^CALLED TO:',
        r'^CRIT CALLED:',
        r'^CRIT COMMENT:',
        r'^VERIFIED',
        r'^READBACK',
        r'^SENT FOR',
        r'^registered$',
        r'^final$',
        r'MATTICCU',
        r'DR PACXKOWSKI',
        r'DR PACZKOWSKI',
        r'PNEUMONIAE',
        r'^Allen Test',
        r'^Specimen source:',
        r'^SOURCE',
        r'^\d{1,2}:\d{2}\s+\d{1,2}:\d{2}$'  # Time pairs like "07:05 08:00",
        
    ]
    
    # Common lab components to include
    lab_components = ['SED RATE', 'GLUCOSE', 'BUN', 'CREATININE', 'SODIUM', 'POTASSIUM', 
                     'CHLORIDE', 'CO2', 'CALCIUM', 'ALBUMIN', 'AST', 'ALT', 'ALKALINE', 
                     'BILIRUBIN', 'WBC', 'RBC', 'HGB', 'HEMOGLOBIN', 'HCT', 'HEMATOCRIT', 
                     'PLT', 'PLATELETS', 'BNP', 'CRP', 'LACTIC', 'MAGNESIUM', 'PHOSPHORUS', 
                     'PROCALCITONIN', 'TROPONIN', 'TSH', 'PH', 'PCO2', 'PO2', 'SO2', 
                     'HCO3', 'SBE', 'FIO2', 'RATE', 'MODE', 'VT', 'PEEP', 'RSBI', 'PSV',
                     'IPAP', 'EPAP', 'INR', 'PTT', 'LIPASE', 'OSMOLALITY', 'EGFR', 'AGE',
                     'FASTING', 'MCV', 'MCH', 'MCHC', 'RDW', 'MPV', 'SEG', 'BAND', 
                     'METAMYELOCYTE', 'MYELOCYTE', 'PROMYELOCYTE', 'LYMPH', 'MONO', 'EOS',
                     'BASO', 'BLASTS', 'NEUT', 'DIFF COUNT']
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Skip administrative lines
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in exclude_patterns):
            continue
        
        # Check if this line contains the target date AND lab data
        if target_dos_normalized in line:
            # Check if this line also contains lab data (not just a date line)
            has_lab_data = False
            
            # Pattern 1: Lab data with date on same line "COMPONENT VALUE [FLAG] [UNITS] DATE"
            if re.match(r'^[A-Z][A-Za-z0-9\s\/\-\(\)]+\s+[\d\.]+', line):
                if any(component in line.upper() for component in lab_components):
                    has_lab_data = True
            
            # Pattern 2: Reference range followed by lab data "L=8.3 CALCIUM 8.3 mg/dL DATE"
            elif re.match(r'^[LH]-?=[\d\.]+\s+[A-Z][A-Za-z]', line):
                if any(component in line.upper() for component in lab_components):
                    has_lab_data = True
            
            if has_lab_data:
                # Extract just the lab data part (remove collection times and "final")
                lab_part = re.sub(r'\d{1,2}:\d{2}\s+\d{1,2}:\d{2}', '', line)  # Remove times
                lab_part = re.sub(r'\s+final$', '', lab_part)  # Remove "final"
                lab_part = re.sub(r'\s+cancelled$', '', lab_part)  # Remove "cancelled"
                lab_part = lab_part.strip()
                
                #print(f"DEBUG: Found lab+date line {i}: {lab_part[:100]}...")
                result_lines.append(lab_part)
    
    # Also handle the previous format (date line followed by lab line)
    in_target_date_section = False
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Skip administrative lines
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in exclude_patterns):
            continue
        
        # Check if this is a date-only line (contains target date but no lab data)
        if target_dos_normalized in line and not any(component in line.upper() for component in lab_components):
            # This is a date line for our target DOS
            in_target_date_section = True
            continue
        
        # If we're in a target date section, look for lab data on next line
        if in_target_date_section:
            # Check if this line contains actual lab data
            is_lab_data = False
            
            if re.match(r'^[A-Z][A-Za-z0-9\s\/\-\(\)]+\s+[\d\.]+', line):
                if any(component in line.upper() for component in lab_components):
                    is_lab_data = True
            
            if is_lab_data:
                # Clean the lab line
                lab_part = re.sub(r'\s+final$', '', line)
                lab_part = re.sub(r'\s+cancelled$', '', lab_part)
                lab_part = lab_part.strip()
                
                #print(f"DEBUG: Found lab after date line {i}: {lab_part[:100]}...")
                result_lines.append(lab_part)
            
            # Reset the section flag after processing one lab entry
            in_target_date_section = False
    
    # Remove duplicates while preserving order
    unique_result_lines = []
    seen = set()
    for line in result_lines:
        # Extract just the lab name for deduplication (first word or two)
        lab_name_match = re.match(r'^([A-Z][A-Za-z0-9\s\/\-\(\)]+?)\s+[\d\.]', line)
        if lab_name_match:
            lab_name = lab_name_match.group(1).strip().upper()
            if lab_name not in seen:
                seen.add(lab_name)
                unique_result_lines.append(line)
        else:
            # If we can't extract lab name, just add the line
            if line not in seen:
                seen.add(line)
                unique_result_lines.append(line)
    
    result = "\n".join(unique_result_lines) if unique_result_lines else ""
    #print(f"DEBUG: After filtering - extracted {len(unique_result_lines)} unique lab entries")
    
    # if result:
    #     (f"DEBUG: Sample of extracted lab data:\n{result[:500]}...")
    
    return result

def clean_admin_noise(text, facility_specific_patterns=None):
    """
    Remove common administrative headers, signatures, page numbers,
    EMR noise, and report metadata from clinical text.

    Parameters:
        text (str): Raw text to clean.
        facility_specific_patterns (list, optional): Additional regex patterns
            (as strings) to remove for a particular facility.

    Returns:
        str: Cleaned text.
    """
    if pd.isna(text) or text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # 1. Signature blocks (common to many facilities)
    signature_patterns = [
        r'Electronically\s*signed\s*by.*',
        r'<Electronically signed by.*?>',
        r'Electronically Signed\.? By.*',
        r'Electronically.?signed.?by.*',
        r'^Electronically\s+signed\s+by:\s*.*',
        r'^Electronically\s+cosigned\s+by:\s*.*',
        r'^Page\s*\d+\s*of\s*\d+.*',
        r'^---\s*Page\s+\d+\s*\(Columnar Page\)\s*---.*',
        r'^Electronically\s+signed\s+by:.*',
        r'^Electronically\s+cosigned\s+by:.*',
        r'^Printed:\s*\d{1,2}\/\d{1,2}\/\d{4}.*Page\s*\d+\s*of\s*\d+.*$',
        r'^[A-Za-z]+,\s*[A-Za-z]+.*$',
        r'^[A-Z][A-Za-z\s]*Hospital.*$',
        r'^[A-Z][A-Za-z\s]*Medical\s+Center.*$',
        r'^[A-Z][A-Za-z\s]*Health\s+System.*$',
        r'^\d{1,5}\s+[A-Za-z0-9\s\.,]+(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Boulevard|Blvd|Drive|Dr).*$',
        r'^Patient\s+Location:.*$',
        r'^Report\s*:.*$',
        r'^Report Number:.*$',
        r'^Account #:.*$',
        r'^Loc:.*$',
        r'^Status:.*$',
               
    ]
    for pattern in signature_patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if m:
            text = text[:m.start()]
            break

    # 2. Common administrative lines
    remove_lines = [
        r'^CC:\s*.*',
        r'^Patient:\s*.*',
        r'^Medical Record\s*#?:\s*.*',
        r'^Account\s*#?:\s*.*',
        r'^Report\s*#?:\s*.*',
        r'^Signed\s*.*',
        r'^Document:\s*.*',
        r'^Report Date:\s*.*',
        r'^Page\s+\d+\s+of\s+\d+.*',
        r'^---\s*Page\s+\d+\s*\(.*?\)\s*---.*',
        r'^CHRISTUS.*',
        r'^Christus.*',
        r'^Printed:.*',
        r'^Request\s*id:.*',
        r'^FIN\s*:.*',
        r'^Name\s*:.*',
        r'^Dischg\s+Dt\s*:.*',
        r'^Patient\s+Location\s*:.*',
        r'^Status:.*',
        r'^Mnemonic:.*',
        r'^Copy to:.*',
        r'^Health Information Management.*',
        r'^Hospitalist History & Physical.*',
        r'^HILLSDALE HOSPITAL\s*$',
        r'^168\s+S\s+HOWELL\s+STREET.*',
    ]
    for pat in remove_lines:
        text = re.sub(pat, '', text, flags=re.IGNORECASE | re.MULTILINE)

    # 3. EMR‑specific noise (generic)
    emr_noise_patterns = [
        r'^Enterprise.*',
        r'^Order History.*',
        r'^Admission Status.*',
        r'^Attending Physician.*',
        r'^Location:.*',
        r'^Blood Bank.*',
        r'^Other Reports.*',
        r'^CareTrends.*',
        r'^CareActivity.*',
        r'^Summary.*',
        r'^Encounters.*',
        r'^Referrals.*',
        r'^Problem List.*',
        r'^Discharge.*',
        r'^Document.*',
        r'^ReconcileMeds.*',
        r'^\s*Order\s+Service.*$'
    ]
    for pat in emr_noise_patterns:
        text = re.sub(pat, '', text, flags=re.IGNORECASE | re.MULTILINE)

    # 4. Page numbers and report dates
    text = re.sub(r'Page\s*\d+\s*of\s*\d+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Report Date:\s*\d{8,14}', '', text)

    # 5. Facility‑specific additional patterns (optional)
    if facility_specific_patterns:
        for pat in facility_specific_patterns:
            text = re.sub(pat, '', text, flags=re.IGNORECASE | re.MULTILINE)

    # 6. Remove excessive blank lines and trim
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    text = text.strip()

    return text

# ------------------------------------------------------------
# MDM2 core logic (same for all facilities)
# ------------------------------------------------------------
def Process_MDM2(discussion, interpretation, prior_review, lab_orders, lab_review, historian):
    unique_data_points = set()
    if prior_review and isinstance(prior_review, list):
        for item in prior_review:
            if "No Evidence Found" not in str(item):
                source = list(item.values())[0]
                unique_data_points.add(f"Note: {source}")
    if lab_review and isinstance(lab_review, list):
        for item in lab_review:
            if "No Evidence Found" not in str(item):
                test_name = list(item.values())[0]
                unique_data_points.add(f"Review: {test_name}")
    if lab_orders and isinstance(lab_orders, list):
        for item in lab_orders:
            if "No Evidence Found" not in str(item):
                test_name = list(item.values())[0]
                unique_data_points.add(f"Order: {test_name}")
    if historian and isinstance(historian, list):
        for item in historian:
            if "No Evidence Found" not in str(item):
                unique_data_points.add("Independent Historian")
                break
    cat1_count = len(unique_data_points)
    cat2 = 0
    if interpretation and isinstance(interpretation, list):
        for item in interpretation:
            if "No Evidence Found" not in str(item):
                cat2 = 1
                break
    cat3 = 0
    if discussion and isinstance(discussion, list):
        for item in discussion:
            if "No Evidence Found" not in str(item):
                cat3 = 1
                break
    categories_met = 0
    if cat1_count >= 3:
        categories_met += 1
    if cat2 >= 1:
        categories_met += 1
    if cat3 >= 1:
        categories_met += 1
    if categories_met >= 2:
        mdm2_level = 4
        M2 = "High"
    elif cat1_count >= 3 or cat2 == 1 or cat3 == 1:
        mdm2_level = 3
        M2 = "Moderate"
    elif cat1_count >= 2:
        mdm2_level = 2
        M2 = "Low"
    else:
        mdm2_level = 1
        M2 = "Low"
    return mdm2_level, M2, [lab_orders, lab_review, historian, interpretation, discussion, prior_review]

# ------------------------------------------------------------
# Flattening helpers
# ------------------------------------------------------------
def flatten_list_of_dicts(data, key_name):
    values = []
    if isinstance(data, list):
        for d in data:
            if isinstance(d, dict) and key_name in d:
                val = d[key_name]
                if isinstance(val, list):
                    val = [v for v in val if "No Evidence Found" not in str(v)]
                    values.extend(val)
                elif val and "No Evidence Found" not in str(val):
                    values.append(val)
    return values

def simplify_list_of_dicts(data, key_name):
    values = []
    if isinstance(data, list):
        for d in data:
            if isinstance(d, dict) and key_name in d:
                val = d[key_name]
                if val and "No Evidence Found" not in str(val):
                    values.append(val)
    return values

# ------------------------------------------------------------
# Downgrade logic: AHFL (raw discussion list comparison)
# ------------------------------------------------------------
def apply_downgrade_logic_ahfl(df):
    """AHFL-specific downgrade: HIGH → MODERATE based on raw discussion list and independent interpretation."""
    df = df.copy()

    def extract_discussion_list(text):
        if pd.isna(text):
            return []
        text = str(text)
        match = re.search(r"Discussion Management/Test>\s*(\[.*?\])", text, flags=re.DOTALL)
        if not match:
            return []
        try:
            return ast.literal_eval(match.group(1))
        except:
            return []

    def extract_independent_interpretation(text):
        if pd.isna(text):
            return []
        text = str(text)
        match = re.search(r"Independent Interpretation>\s*(\[.*?\])", text, flags=re.DOTALL)
        if not match:
            return []
        try:
            return ast.literal_eval(match.group(1))
        except:
            return []

    def normalize_interpretation(t):
        t = t.lower()
        t = re.sub(r'[^a-z0-9\s]', ' ', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    def fuzzy_interpretation(a, b, threshold=0.70):
        if not a or not b:
            return False
        a = normalize_interpretation(a)
        b = normalize_interpretation(b)
        if not a or not b:
            return False
        return SequenceMatcher(None, a, b).ratio() >= threshold

    # Prepare sorting columns
    df["DOS_RAW"] = df["DOS"].astype(str).str.strip()
    df["DOS_SORT"] = pd.to_datetime(df["DOS_RAW"], errors="coerce")
    if "Visit Time" in df.columns:
        df["Visit_Time_Sort"] = pd.to_datetime(df["Visit Time"], format="%I:%M %p", errors="coerce")
    else:
        df["Visit_Time_Sort"] = pd.NaT
    # Handle Page No vs Page_No column naming
    if "Page_No" not in df.columns:
        if "Page No" in df.columns:
            df.rename(columns={"Page No": "Page_No"}, inplace=True)
        else:
            df["Page_No"] = None


    new_data = []
    for filename in df["Filename"].unique():
        sdf = df[df["Filename"] == filename].copy()
        sdf = sdf.sort_values(["DOS_SORT", "Visit_Time_Sort", "Page_No"], na_position="last")

        previous_discussion_set = set()
        seen_interpretations = set()
        first_row = True

        for idx, row in sdf.iterrows():
            is_initial = first_row

            reasons = str(row.get("REASONS FOR MDM2", ""))
            discussion_list = extract_discussion_list(reasons)
            independent_interp = extract_independent_interpretation(reasons)

            current_discussion_set = set(str(item).strip() for item in discussion_list)
            current_discussion_set = {x for x in current_discussion_set if x and x != "No Evidence Found"}

            current_interpretation_text = " | ".join(sorted(i.upper() for i in independent_interp)) if independent_interp else ""
            is_placeholder = len(independent_interp) == 1 and normalize_interpretation(independent_interp[0]) == "no evidence found"

            is_repeated = False
            if current_interpretation_text:
                for seen in seen_interpretations:
                    if fuzzy_interpretation(current_interpretation_text, seen, threshold=0.70):
                        is_repeated = True
                        break

            if not is_placeholder and not is_repeated and current_interpretation_text:
                seen_interpretations.add(current_interpretation_text)

            no_independent_interp = is_placeholder or is_repeated
            is_new_consult = bool(current_discussion_set - previous_discussion_set)

            if (not is_initial and not is_new_consult and no_independent_interp and row.get("MDM2_Level") == "HIGH"):
                row["MDM2_Level"] = "MODERATE"

            #print(f"[DEBUG] {row['Filename']} {row['DOS']} is_initial={is_initial}, is_new_consult={is_new_consult}, no_independent_interp={no_independent_interp}, level={row.get('MDM2_Level')}")

            previous_discussion_set = current_discussion_set.copy()
            first_row = False
            new_data.append(row)

    new_df = pd.DataFrame(new_data)
    if "DOS_RAW" in new_df.columns:
        new_df["DOS"] = new_df["DOS_RAW"]
    new_df.drop(columns=["DOS_RAW", "DOS_SORT", "Visit_Time_Sort"], inplace=True, errors="ignore")
    return new_df

# ------------------------------------------------------------
# Downgrade logic: BCS / CAICP / AR / ARN / AW / CCCC / CSRNB / H / JN (specialty fingerprints)
# ------------------------------------------------------------
def apply_downgrade_logic_specialties(df, specialties):
    """Specialty-based downgrade for facilities that use consult fingerprinting."""
    df = df.copy()

    def normalize_specialty(text):
        text = str(text).upper()
        text = re.sub(r'[^A-Z0-9\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def extract_consult_fingerprints(discussion_list):
        fps = set()
        for item in discussion_list:
            txt = normalize_specialty(item)
            for sp in specialties:
                if sp in txt:
                    fps.add(f"SPECIALTY:{sp}")
        return fps

    def extract_discussion_list(text):
        if pd.isna(text):
            return []
        text = str(text)
        match = re.search(r"Discussion Management/Test>\s*(\[.*?\])", text, flags=re.DOTALL)
        if not match:
            return []
        try:
            return ast.literal_eval(match.group(1))
        except:
            return []

    def extract_independent_interpretation(text):
        if pd.isna(text):
            return []
        text = str(text)
        match = re.search(r"Independent Interpretation>\s*(\[.*?\])", text, flags=re.DOTALL)
        if not match:
            return []
        try:
            return ast.literal_eval(match.group(1))
        except:
            return []

    def normalize_interpretation(t):
        t = t.lower()
        t = re.sub(r'[^a-z0-9\s]', ' ', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    def fuzzy_interpretation(a, b, threshold=0.70):
        if not a or not b:
            return False
        a = normalize_interpretation(a)
        b = normalize_interpretation(b)
        if not a or not b:
            return False
        return SequenceMatcher(None, a, b).ratio() >= threshold

    # Prepare sorting columns
    df["DOS_RAW"] = df["DOS"].astype(str).str.strip()
    df["DOS_SORT"] = pd.to_datetime(df["DOS_RAW"], errors="coerce")
    if "Visit Time" in df.columns:
        df["Visit_Time_Sort"] = pd.to_datetime(df["Visit Time"], format="%I:%M %p", errors="coerce")
    else:
        df["Visit_Time_Sort"] = pd.NaT
    # Handle Page No vs Page_No column naming
    if "Page_No" not in df.columns:
        if "Page No" in df.columns:
            df.rename(columns={"Page No": "Page_No"}, inplace=True)
        else:
            df["Page_No"] = None


    new_data = []
    for filename in df["Filename"].unique():
        sdf = df[df["Filename"] == filename].copy()
        sdf = sdf.sort_values(["DOS_SORT", "Visit_Time_Sort", "Page_No"], na_position="last")

        previous_fps = set()
        seen_interpretations = set()
        first_row = True

        for idx, row in sdf.iterrows():
            is_initial = first_row

            reasons = str(row.get("REASONS FOR MDM2", ""))
            discussion_list = extract_discussion_list(reasons)
            independent_interp = extract_independent_interpretation(reasons)

            current_interpretation_text = " | ".join(sorted(i.upper() for i in independent_interp)) if independent_interp else ""
            is_placeholder = len(independent_interp) == 1 and normalize_interpretation(independent_interp[0]) == "no evidence found"

            is_repeated = False
            if current_interpretation_text:
                for seen in seen_interpretations:
                    if fuzzy_interpretation(current_interpretation_text, seen, threshold=0.70):
                        is_repeated = True
                        break

            if not is_placeholder and not is_repeated and current_interpretation_text:
                seen_interpretations.add(current_interpretation_text)

            no_independent_interp = is_placeholder or is_repeated

            current_fps = extract_consult_fingerprints(discussion_list)
            is_new_consult = any(fp not in previous_fps for fp in current_fps)

            if (not is_initial and not is_new_consult and no_independent_interp and row.get("MDM2_Level") == "HIGH"):
                row["MDM2_Level"] = "MODERATE"

            previous_fps = current_fps.copy()
            first_row = False
            new_data.append(row)

    new_df = pd.DataFrame(new_data)
    if "DOS_RAW" in new_df.columns:
        new_df["DOS"] = new_df["DOS_RAW"]
    new_df.drop(columns=["DOS_RAW", "DOS_SORT", "Visit_Time_Sort"], inplace=True, errors="ignore")
    return new_df

# ------------------------------------------------------------
# Generic section change tracking (Lab Order, Lab Review, etc.)
# ------------------------------------------------------------
def track_section_changes(df, section_name):
    """
    For a given section (e.g., "Lab Order"), adds a column "Lab concluding remarks"
    with change status per patient.
    """
    df = df.copy()
    if "Lab concluding remarks" not in df.columns:
        df["Lab concluding remarks"] = ""
    df["DOS_RAW"] = df["DOS"].astype(str).str.strip()
    df["DOS_SORT"] = pd.to_datetime(df["DOS_RAW"], errors="coerce")
    new_data = []
    for filename in df["Filename"].unique():
        sdf = df[df["Filename"] == filename].copy()
        valid = sdf.dropna(subset=["DOS_SORT"]).sort_values("DOS_SORT")
        invalid = sdf[sdf["DOS_SORT"].isna()]
        sorted_df = pd.concat([valid, invalid])
        prev_set = set()
        previous_day_final_output = None
        for idx, row in sorted_df.iterrows():
            if pd.isna(row["DOS_SORT"]):
                remark = "Invalid or Missing DOS"
                existing = str(df.at[idx, "Lab concluding remarks"]).strip()
                df.at[idx, "Lab concluding remarks"] = existing + " ~ " + remark if existing else remark
                new_data.append(df.loc[idx])
                continue
            text = str(row.get("REASONS FOR MDM2", ""))
            pattern = rf"{section_name}>\s*(\[.*?\])"
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    current = ast.literal_eval(match.group(1))
                except:
                    current = []
                unique = []
                for kw in current:
                    clean = str(kw).strip()
                    if clean and clean not in prev_set:
                        unique.append(clean)
                        prev_set.add(clean)
                current_final = unique if unique else ["No Evidence Found"]
                if previous_day_final_output is None:
                    comparison = f"{section_name}: Initial Note"
                elif current_final == previous_day_final_output:
                    comparison = f"{section_name}: No change"
                else:
                    prev = {x for x in (previous_day_final_output or []) if x != "No Evidence Found"}
                    curr = {x for x in current_final if x != "No Evidence Found"}
                    added = list(curr - prev)
                    removed = list(prev - curr)
                    parts = []
                    if added:
                        parts.append(f"Added: {added}")
                    if removed:
                        parts.append(f"Removed: {removed}")
                    change = ", ".join(parts)
                    comparison = f"{section_name}: Content Updated: {change}" if change else f"{section_name}: Content Updated"
                existing_remark = str(df.at[idx, "Lab concluding remarks"]).strip()
                df.at[idx, "Lab concluding remarks"] = existing_remark + " ~ " + comparison if existing_remark else comparison
                previous_day_final_output = current_final
            else:
                df.at[idx, "Lab concluding remarks"] = "No Data Found"
            new_data.append(df.loc[idx])
    new_df = pd.DataFrame(new_data)
    new_df["DOS"] = new_df["DOS_RAW"]
    new_df.drop(columns=["DOS_RAW", "DOS_SORT"], inplace=True, errors="ignore")
    return new_df

# ------------------------------------------------------------
# Discussion Management change tracking (specialty-based)
# ------------------------------------------------------------
def track_discussion_changes(df, specialty_map):
    """Track changes in Discussion Management using specialty map."""
    def normalize_text_specialty(t):
        t = str(t).upper()
        t = re.sub(r'[^A-Z0-9\s]', ' ', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    def extract_specialties(keyword_list):
        specs = set()
        for item in keyword_list:
            if not isinstance(item, str):
                continue
            clean = normalize_text_specialty(item)
            for key, canonical in sorted(specialty_map.items(), key=lambda x: len(x[0]), reverse=True):
                if key in clean:
                    specs.add(canonical)
        return specs

    df = df.copy()
    if "Lab concluding remarks" not in df.columns:
        df["Lab concluding remarks"] = ""
    df["DOS_RAW"] = df["DOS"].astype(str).str.strip()
    df["DOS_SORT"] = pd.to_datetime(df["DOS_RAW"], errors="coerce")
    new_data = []
    for filename in df["Filename"].unique():
        sdf = df[df["Filename"] == filename].copy()
        valid = sdf.dropna(subset=["DOS_SORT"]).sort_values("DOS_SORT")
        invalid = sdf[sdf["DOS_SORT"].isna()]
        sorted_df = pd.concat([valid, invalid])
        prev_specs = set()
        first = True
        for idx, row in sorted_df.iterrows():
            if pd.isna(row["DOS_SORT"]):
                remark = "Invalid or Missing DOS"
                existing = str(df.at[idx, "Lab concluding remarks"]).strip()
                df.at[idx, "Lab concluding remarks"] = existing + " ~ " + remark if existing else remark
                new_data.append(df.loc[idx])
                continue
            text = str(row.get("REASONS FOR MDM2", ""))
            match = re.search(r"Discussion Management/Test>\s*(\[.*?\])", text, re.DOTALL)
            if not match:
                remark = "Discussion Management/Test: No Data Found"
                existing = str(df.at[idx, "Lab concluding remarks"]).strip()
                df.at[idx, "Lab concluding remarks"] = existing + " ~ " + remark if existing else remark
                new_data.append(df.loc[idx])
                continue
            try:
                current_keywords = ast.literal_eval(match.group(1))
            except:
                current_keywords = []
            current_specs = extract_specialties(current_keywords)
            if first:
                status = "Discussion Management/Test: Initial Note"
                first = False
            else:
                added = current_specs - prev_specs
                removed = prev_specs - current_specs
                if not added and not removed:
                    status = "Discussion Management/Test: No change"
                else:
                    parts = []
                    if added:
                        parts.append(f"Added: {sorted(added)}")
                    if removed:
                        parts.append(f"Removed: {sorted(removed)}")
                    status = "Discussion Management/Test: Content Updated: " + ", ".join(parts)
            existing = str(df.at[idx, "Lab concluding remarks"]).strip()
            df.at[idx, "Lab concluding remarks"] = existing + " ~ " + status if existing else status
            prev_specs = current_specs.copy()
            new_data.append(df.loc[idx])
    new_df = pd.DataFrame(new_data)
    new_df["DOS"] = new_df["DOS_RAW"]
    new_df.drop(columns=["DOS_RAW", "DOS_SORT"], inplace=True, errors="ignore")
    return new_df

# ------------------------------------------------------------
# Split Added/Removed into separate columns
# ------------------------------------------------------------
def split_added_removed(df, column_name="Lab concluding remarks"):
    """Extract Added and Removed sections into Lab_Added and Lab_Removed columns."""
    def extract_by_section(text):
        if pd.isna(text):
            return "", ""
        text = str(text)
        added_result = []
        removed_result = []
        sections = re.split(r"\s*~\s*", text)
        for section in sections:
            section_name_match = re.match(r"([^:]+):", section)
            if not section_name_match:
                continue
            section_name = section_name_match.group(1).strip()
            added_match = re.search(r"Added:\s*(\[[^\]]*\])", section)
            if added_match:
                try:
                    added_items = ast.literal_eval(added_match.group(1))
                    if added_items:
                        added_result.append(f"{section_name}: [{', '.join(added_items)}]")
                except:
                    pass
            removed_match = re.search(r"Removed:\s*(\[[^\]]*\])", section)
            if removed_match:
                try:
                    removed_items = ast.literal_eval(removed_match.group(1))
                    if removed_items:
                        removed_result.append(f"{section_name}: [{', '.join(removed_items)}]")
                except:
                    pass
        return " ~ ".join(added_result), " ~ ".join(removed_result)
    df[["Lab_Added", "Lab_Removed"]] = df[column_name].apply(lambda x: pd.Series(extract_by_section(x)))
    return df

# ------------------------------------------------------------
# Merge with external lab values file
# ------------------------------------------------------------
def merge_lab_values(df, lab_values_file, match_cols=None):
    """Merge Extracted_Labs and Qwen Microbiology from another Excel file."""
    if match_cols is None:
        match_cols = ["Filename", "DOS", "Visit", "Visit Time", "Page_No"]
    df2 = pd.read_excel(lab_values_file)
    # Ensure column name consistency
    rename_map = {}
    for col in df2.columns:
        if "Page No" in col:
            rename_map[col] = "Page_No"
        if "Visit_time" in col:
            rename_map[col] = "Visit Time"
    df2 = df2.rename(columns=rename_map)
    # Ensure all match columns exist
    missing = [c for c in match_cols if c not in df2.columns]
    if missing:
        print(f"Warning: Missing columns in lab values file: {missing}")
        match_cols = [c for c in match_cols if c in df2.columns]
        if not match_cols:
            print("No matching columns found. Returning original df.")
            return df
    df2_subset = df2[match_cols + ["Extracted_Labs", "Qwen Microbiology"]]
    merged = pd.merge(df, df2_subset, on=match_cols, how="left")
    return merged