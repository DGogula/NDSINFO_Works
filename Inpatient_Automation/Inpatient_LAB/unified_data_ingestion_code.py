import re
import os
from pathlib import Path
from collections import defaultdict
import pandas as pd
from datetime import datetime

# ----------------------------------------------------------------------
# SECTION 1: Functions from 1_code.py (file parsing and section extraction)
# ----------------------------------------------------------------------

ALLOWED_HEADERS = {
    "history of present illness": "HISTORY OF PRESENT ILLNESS",   # text in chart: text in excel sheet
    "hpi": "HISTORY OF PRESENT ILLNESS",
    "problem list/past medical history": "PROBLEM LIST/PAST MEDICAL HISTORY",
    "surgical history": "SURGICAL HISTORY",
    "procedure/surgical history": "SURGICAL HISTORY",
    "social history": "SOCIAL HISTORY",
    "family history": "FAMILY HISTORY",
    "allergies/allergy": "ALLERGIES/ALLERGY",
    "allergies": "ALLERGIES/ALLERGY",
    "home medications": "HOME MEDICATIONS",
    "procedure": "PROCEDURE",
    "procedures": "PROCEDURE",
    "procedure/surgery start": "PROCEDURE/SURGERY START",
    "complications": "COMPLICATIONS",
    "implants/explants": "IMPLANTS/EXPLANTS",
    "chief complaint": "CHIEF COMPLAINT",
    "cc": "CHIEF COMPLAINT",
    "reason for visit": "REASON FOR VISIT",
    "reason for consultation": "REASON FOR CONSULTATION",
    "review of systems": "REVIEW OF SYSTEMS",
    "vital signs": "VITAL SIGNS",
    "problem list": "PROBLEM LIST",
    "past medical history": "PROBLEM LIST/PAST MEDICAL HISTORY",
    "medications": "MEDICATIONS",
    "immunizations": "IMMUNIZATIONS",
    "lab results": "LAB RESULTS",
    "lab resuits": "LAB RESULTS",
    "lab. results": "LAB RESULTS",
    "diagnostic results": "DIAGNOSTIC RESULTS",
    "radiology/diagnostic results": "DIAGNOSTIC RESULTS",
    "pre-operative diagnosis": "PRE-OPERATIVE DIAGNOSIS",
    "post-operative diagnosis": "POST-OPERATIVE DIAGNOSIS",
    "description of procedure(s)": "DESCRIPTION OF PROCEDURE(S)",
    "description of procedure": "DESCRIPTION OF PROCEDURE(S)",
    "procedure description": "DESCRIPTION OF PROCEDURE(S)",
    "hospital course": "HOSPITAL COURSE",
    "patient condition": "PATIENT CONDITION",
    "procedures provided": "PROCEDURES PROVIDED",
    "treatment provided": "PROCEDURES PROVIDED",
    "indications for procedure": "INDICATIONS FOR PROCEDURE",
    "discharge diagnoses and plan": "DISCHARGE DIAGNOSES AND PLAN",
    "consulting services": "CONSULTING SERVICES",
    "significant findings": "SIGNIFICANT FINDINGS",
    "assessment/plan": "ASSESSMENT AND PLAN",
    "assessment/ plan": "ASSESSMENT AND PLAN",
    "as sessment/plan": "ASSESSMENT AND PLAN",
    "assessment & plan": "ASSESSMENT AND PLAN",
    "assessment and plan": "ASSESSMENT AND PLAN",
    "assessment": "ASSESSMENT AND PLAN",
    "plan": "ASSESSMENT AND PLAN",
    "orders": "ORDERS",
    "post operative diagnosis": "POST OPERATIVE DIAGNOSIS",
    "multiple procedure": "MULTIPLE PROCEDURE",
    "preoperative diagnosis": "PREOPERATIVE DIAGNOSIS",
    "procedure(s) performed": "PROCEDURE(S) PERFORMED",
    "procedures performed": "PROCEDURE(S) PERFORMED",
    "subjective": "SUBJECTIVE",
    "objective": "OBJECTIVE",
    "discharge diagnosis/plan": "DISCHARGE DIAGNOSIS/PLAN",
    "physical exam": "PHYSICAL EXAM",
    "attestation": "ATTESTATION",
    "finding(s)": "FINDING(S)",
    "patient discharge condition": "PATIENT DISCHARGE CONDITION",
    "discharge medications": "DISCHARGE MEDICATIONS",
    "discharge diagnosis": "DISCHARGE DIAGNOSIS",
    "discharge diagnoses": "DISCHARGE DIAGNOSIS",
    "admission information": "ADMISSION INFORMATION",
    "discharge disposition": "DISCHARGE DISPOSITION",
    "instructions/dme": "INSTRUCTIONS/DME",
    "laboratory": "LAB RESULTS",
    "physical examination": "PHYSICAL EXAM",
    "medical decision making": "MEDICAL DECISION MAKING",
    "findings": "FINDING(S)",
    "impression": "IMPRESSION",
    "extra data": "EXTRA DATA",   #all remaining data that doesn't fit into any of the above categories will be placed here
}

VISIT_MAPPING = {
    "HP": "HP",
    "CON": "Consult",
    "DS": "Discharge",
    "ED": "ED",
    "CATH LAB": "OPN",
    "CATH": "OPN",
    "GI": "OPN",
    "IPO": "OPN",
    "OP": "OPN",
    "OPT": "OPN",
    "PGN": "PGN",
    "CS": "Result",
}

def normalize_date_stage1(date_str: str) -> str:
    """Original normalize_date from 1_code.py – only handles MM/DD/YY and MM/DD/YYYY."""
    if not date_str:
        return None
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            continue
    return date_str

def parse_month_name_date(date_str: str) -> str:
    month_map = {
        'january': '01', 'february': '02', 'march': '03', 'april': '04',
        'may': '05', 'june': '06', 'july': '07', 'august': '08',
        'september': '09', 'october': '10', 'november': '11', 'december': '12',
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'jun': '06',
        'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
    }
    date_str = date_str.strip().lower()
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            continue
    parts = re.split(r'[ ,]+', date_str)
    if len(parts) >= 3:
        month_name = parts[0].lower()
        day = parts[1].zfill(2)
        year = parts[2]
        if month_name in month_map:
            return f"{month_map[month_name]}/{day}/{year}"
    return None

def parse_filename(filepath: Path):
    stem = filepath.stem
    match = re.match(r'^([0-9]+)[-_]+(.+)$', stem)
    if not match:
        raise ValueError(f"Unexpected filename format: {filepath.name}")
    chart_no = match.group(1)
    rest = match.group(2)
    rest = re.sub(r'^[-_]+', '', rest)
    seq_match = re.search(r'[-_]?(\d+)$', rest)
    if seq_match:
        seq = int(seq_match.group(1))
        visit_name = re.sub(r'[-_]?\d+$', '', rest)
    else:
        seq = None
        visit_name = rest
    if not visit_name:
        visit_name = rest
    return chart_no, visit_name, seq

def extract_date_time(text: str, visit: str):
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if 'DATE/TIME NOTE CREATED' in line:
            match_same = re.search(r'DATE/TIME NOTE CREATED:\s*(\d{1,2}/\d{1,2}/\d{2,4})\s+(\d{2}:\d{2}:\d{2})', line)
            if match_same:
                return normalize_date_stage1(match_same.group(1)), match_same.group(2)
            match_date_only = re.search(r'DATE/TIME NOTE CREATED:\s*(\d{1,2}/\d{1,2}/\d{2,4})', line)
            if match_date_only:
                dos = normalize_date_stage1(match_date_only.group(1))
                if i + 1 < len(lines):
                    time_match = re.search(r'(\d{2}:\d{2}:\d{2})', lines[i+1])
                    if time_match:
                        return dos, time_match.group(1)
                return dos, None
            if i + 1 < len(lines):
                next_line = lines[i+1].strip()
                date_match = re.match(r'(\d{1,2}/\d{1,2}/\d{2,4})', next_line)
                if date_match:
                    dos = normalize_date_stage1(date_match.group(1))
                    time_match = re.search(r'(\d{2}:\d{2}:\d{2})', next_line)
                    if not time_match and i + 2 < len(lines):
                        time_match = re.search(r'(\d{2}:\d{2}:\d{2})', lines[i+2])
                    return dos, time_match.group(1) if time_match else None
    if visit.startswith('DS'):
        for i, line in enumerate(lines):
            if re.search(r'Date of Discharge:', line, re.IGNORECASE):
                same_line_num = re.search(r'Date of Discharge:\s*(\d{1,2}/\d{1,2}/\d{2,4})', line, re.IGNORECASE)
                if same_line_num:
                    return normalize_date_stage1(same_line_num.group(1)), None
                same_line_month = re.search(r'Date of Discharge:\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', line, re.IGNORECASE)
                if same_line_month:
                    parsed = parse_month_name_date(same_line_month.group(1))
                    if parsed:
                        return parsed, None
                for j in range(i+1, min(i+3, len(lines))):
                    next_line = lines[j].strip()
                    date_match_num = re.match(r'(\d{1,2}/\d{1,2}/\d{2,4})', next_line)
                    if date_match_num:
                        return normalize_date_stage1(date_match_num.group(1)), None
                    date_match_month = re.match(r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})', next_line)
                    if date_match_month:
                        parsed = parse_month_name_date(date_match_month.group(1))
                        if parsed:
                            return parsed, None
                context = '\n'.join(lines[i:min(i+5, len(lines))])
                any_num = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', context)
                if any_num:
                    return normalize_date_stage1(any_num.group(1)), None
                any_month = re.search(r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})', context)
                if any_month:
                    parsed = parse_month_name_date(any_month.group(1))
                    if parsed:
                        return parsed, None
    date_label_pattern = re.compile(r'Date of (Admission|Discharge|Procedure|Service|Surgery|Visit):\s*(.+)', re.IGNORECASE)
    for line in lines:
        match = date_label_pattern.search(line)
        if match:
            date_part = match.group(2).strip()
            num_match = re.match(r'(\d{1,2}/\d{1,2}/\d{2,4})', date_part)
            if num_match:
                return normalize_date_stage1(num_match.group(1)), None
            month_match = re.match(r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})', date_part)
            if month_match:
                parsed = parse_month_name_date(month_match.group(1))
                if parsed:
                    return parsed, None
    return None, None

def extract_sections(text: str):
    """Stateless section extractor – each call creates fresh containers."""
    lines = text.splitlines()
    allowed_map = {k.lower(): v for k, v in ALLOWED_HEADERS.items()}
    sorted_keys = sorted(allowed_map.keys(), key=len, reverse=True)

    sections = {}
    current_header = None
    current_content = []
    extra_data_lines = []

    SKIP_PATTERNS = [
        'DATE/TIME NOTE CREATED',
        'DATE/TIME PATIENT SEEN',
        'ATTENDING PHYSICIAN:',
    ]

    def _flush():
        if current_header is None:
            return
        block = '\n'.join(current_content).strip()
        if not block:
            return
        if current_header in sections and sections[current_header]:
            sections[current_header] = sections[current_header] + '\n' + block
        else:
            sections[current_header] = block

    for line in lines:
        if any(pat in line for pat in SKIP_PATTERNS):
            continue

        stripped = line.strip()
        if not stripped:
            if current_header is not None:
                current_content.append(line)
            else:
                extra_data_lines.append(line)
            continue

        lower_line = stripped.lower()
        header_std = None
        trailing = ""

        # PRIORITY 1: Medications (X) Active pattern
        med_active_match = re.search(r'medications\s*[\(\{]\s*\d+\s*[\)\}]\s+active', lower_line, re.IGNORECASE)
        if med_active_match:
            header_std = "MEDICATIONS"
            trailing = line[med_active_match.end():].lstrip()
        elif lower_line in allowed_map:
            header_std = allowed_map[lower_line]
        elif lower_line.endswith(':') and lower_line[:-1] in allowed_map:
            header_std = allowed_map[lower_line[:-1]]
        else:
            for key in sorted_keys:
                if lower_line.startswith(key + ':'):
                    header_std = allowed_map[key]
                    trailing = line[len(key)+1:].lstrip()
                    break
                if lower_line.startswith(key + ' :'):
                    header_std = allowed_map[key]
                    trailing = line[len(key)+2:].lstrip()
                    break

        if header_std is not None:
            if header_std == current_header:
                if trailing:
                    current_content.append(trailing)
            else:
                _flush()
                current_header = header_std
                current_content = []
                if trailing:
                    current_content.append(trailing)
        else:
            if current_header is not None:
                current_content.append(line)
            else:
                extra_data_lines.append(line)

    _flush()

    if extra_data_lines:
        sections["EXTRA DATA"] = '\n'.join(extra_data_lines).strip()

    return sections

def map_visit_base(raw_visit: str) -> str:
    raw_upper = raw_visit.upper().strip()
    for key, mapped in VISIT_MAPPING.items():
        if raw_upper == key or raw_upper.startswith(key):
            return mapped
    return raw_visit

def process_folder(input_folder: str, output_excel: str):
    input_path = Path(input_folder)
    groups = defaultdict(list)

    for filepath in input_path.glob("*.txt"):
        try:
            chart_no, visit, seq = parse_filename(filepath)
            groups[(chart_no, visit)].append((seq, filepath))
        except ValueError as e:
            print(f"Skipping {filepath.name}: {e}")

    rows = []
    for (chart_no, visit_raw), file_list in groups.items():
        file_list.sort(key=lambda x: (x[0] is None, x[0] if x[0] is not None else 0))
        file_paths = [fpath for _, fpath in file_list]
        merged_text = []
        for fpath in file_paths:
            merged_text.append(fpath.read_text(encoding='utf-8-sig'))
        full_text = '\n'.join(merged_text)
        dos, visit_time = extract_date_time(full_text, visit_raw)
        if dos is None and visit_raw != 'CS':
            print(f"Warning: No date found for {chart_no}_{visit_raw}")

        rows.append({
            'Chart_No': chart_no,
            'raw_visit': visit_raw,
            'DOS': dos,
            'Visit_Time': visit_time,
            'file_paths': file_paths,
        })

    rows_by_chart = defaultdict(list)
    for row in rows:
        rows_by_chart[row['Chart_No']].append(row)

    final_rows = []
    for chart_no, chart_rows in rows_by_chart.items():
        for row in chart_rows:
            base = map_visit_base(row['raw_visit'])
            row['display_base'] = base
            row['sort_priority'] = 1 if row['raw_visit'] == 'CS' else 0
            if row['raw_visit'] == 'CS':
                row['sort_date'] = '12/31/2099'
                row['sort_time'] = '00:00:00'
            else:
                row['sort_date'] = row['DOS'] if row['DOS'] else '01/01/1900'
                row['sort_time'] = row['Visit_Time'] if row['Visit_Time'] else '00:00:00'

        chart_rows.sort(key=lambda x: (x['sort_priority'], x['raw_visit'], x['sort_date'], x['sort_time']))

        base_count = defaultdict(int)
        for row in chart_rows:
            base_count[row['display_base']] += 1

        temp_counter = defaultdict(int)
        for row in chart_rows:
            base = row['display_base']
            temp_counter[base] += 1
            if base_count[base] > 1:
                visit_display = f"{base}{temp_counter[base]}"
            else:
                visit_display = base

            merged_text = []
            for fpath in row['file_paths']:
                merged_text.append(fpath.read_text(encoding='utf-8-sig'))
            full_text = '\n'.join(merged_text)

            final_row = {
                'Chart_No': row['Chart_No'],
                'Visit': visit_display,
                'DOS': row['DOS'],
                'Visit_Time': row['Visit_Time']
            }
            
            if row['raw_visit'] == 'CS':
                final_row['RESULT'] = full_text.strip()
            else:
                sections = extract_sections(full_text)
                if sections:
                    for header, content in sections.items():
                        final_row[header] = content
                else:
                    final_row['CONTENT'] = full_text.strip()

            final_rows.append(final_row)

    all_possible_cols = set()
    for r in final_rows:
        all_possible_cols.update(r.keys())
    allowed_cols_set = set(ALLOWED_HEADERS.values()) | {'Chart_No', 'Visit', 'DOS', 'Visit_Time', 'CONTENT', 'RESULT', 'EXTRA DATA', 
                                                        "PROBLEM LIST/PAST MEDICAL HISTORY", "SURGICAL HISTORY", "FAMILY HISTORY", "SOCIAL HISTORY", 
                                                        "HISTORY OF PRESENT ILLNESS", "IMMUNIZATIONS"}
    # Start with mandatory columns that must always appear
    mandatory_columns = ['Chart_No', 'Visit', 'DOS', 'Visit_Time'] + [
        "PROBLEM LIST/PAST MEDICAL HISTORY", "SURGICAL HISTORY", "FAMILY HISTORY", 
        "SOCIAL HISTORY", "HISTORY OF PRESENT ILLNESS", "IMMUNIZATIONS"]
    # Add any other allowed columns that actually have data
    extra_cols = sorted([c for c in all_possible_cols if c in allowed_cols_set and c not in mandatory_columns])
    final_cols = mandatory_columns + extra_cols

    df = pd.DataFrame(final_rows, columns=final_cols)
    df.to_excel(output_excel, index=False, engine='openpyxl')
    print(f"Successfully wrote {len(final_rows)} rows to {output_excel}")

    # Return the first Chart_No (if any rows exist)
    first_chart = df.iloc[0]['Chart_No'] if len(df) > 0 else None
    return first_chart


# ----------------------------------------------------------------------
# SECTION 2: Functions from 2_emptydosfill.py (fill missing DOS)
# ----------------------------------------------------------------------

def normalize_date_stage2(date_str: str) -> str:
    """More comprehensive date normalizer from 2_emptydosfill.py."""
    if not date_str:
        return None
    for fmt in ("%m/%d/%y", "%m/%d/%Y", "%m-%d-%y", "%m-%d-%Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            continue
    month_map = {
        'january': '01', 'february': '02', 'march': '03', 'april': '04',
        'may': '05', 'june': '06', 'july': '07', 'august': '08',
        'september': '09', 'october': '10', 'november': '11', 'december': '12',
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'jun': '06',
        'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
    }
    lowered = date_str.lower().strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y"):
        try:
            dt = datetime.strptime(lowered, fmt)
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            continue
    match = re.match(r'([a-z]+)\s+(\d{1,2}),?\s+(\d{4})', lowered)
    if match:
        month = month_map.get(match.group(1))
        if month:
            return f"{month}/{match.group(2).zfill(2)}/{match.group(3)}"
    return None

def extract_max_date_from_vitals(vitals_text: str) -> str:
    if not vitals_text or not isinstance(vitals_text, str):
        return None
    dates = []
    pattern1 = r'\((\d{1,2}/\d{1,2})\s+\d{2}:\d{2}\)'
    pattern2 = r'\((\d{1,2}/\d{1,2}/\d{2,4})\)'
    
    for match in re.findall(pattern1, vitals_text):
        month, day = match.split('/')
        date_str = f"{month}/{day}/2024"
        norm = normalize_date_stage2(date_str)
        if norm:
            dates.append(norm)
    for match in re.findall(pattern2, vitals_text):
        parts = match.split('/')
        if len(parts) == 3:
            month, day, year = parts
            if len(year) == 2:
                year = '20' + year
            date_str = f"{month}/{day}/{year}"
            norm = normalize_date_stage2(date_str)
            if norm:
                dates.append(norm)
    
    if not dates:
        return None
    date_objs = []
    for d in dates:
        try:
            date_objs.append(datetime.strptime(d, "%m/%d/%Y"))
        except:
            continue
    if not date_objs:
        return None
    max_date = max(date_objs)
    return max_date.strftime("%m/%d/%Y")

def extract_date_from_text(text: str) -> str:
    if not text:
        return None
    patterns = [
        r'Electronically Signed On\s+(\d{1,2}/\d{1,2}/\d{2,4})',
        r'Electronically Signed On\s+(\d{1,2}-\d{1,2}-\d{2,4})',
        r'Signed On:\s*(\d{1,2}/\d{1,2}/\d{2,4})',
        r'Date of Service:\s*(\d{1,2}/\d{1,2}/\d{2,4})',
        r'Date of Procedure:\s*(\d{1,2}/\d{1,2}/\d{2,4})',
        r'Date:\s*(\d{1,2}/\d{1,2}/\d{2,4})',
        r'Electronically Signed On\s+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'Signed On:\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'Date of Service:\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'Date of Procedure:\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'Date:\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
        r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b',
        r'\b(\d{1,2}-\d{1,2}-\d{2,4})\b',
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            return normalize_date_stage2(match.group(1))
    return None

def fill_missing_dos(input_excel: str, output_excel: str = None):
    if output_excel is None:
        output_excel = input_excel.replace('.xlsx', '_filled.xlsx')
    
    df = pd.read_excel(input_excel, dtype=str)
    base_cols = {'Chart_No', 'Visit', 'DOS', 'Visit_Time'}
    content_cols = [c for c in df.columns if c not in base_cols]
    
    updated = 0
    for idx, row in df.iterrows():
        if str(row['Visit']).strip().lower() == 'result':
            continue
        if pd.notna(row['DOS']) and row['DOS'].strip():
            continue
        
        row_text = ' '.join(str(row[col]) for col in content_cols if pd.notna(row[col]))
        if not row_text.strip():
            continue
        
        date_str = extract_date_from_text(row_text)
        if not date_str and 'VITAL SIGNS' in df.columns:
            vitals_text = str(row['VITAL SIGNS']) if pd.notna(row['VITAL SIGNS']) else ''
            date_str = extract_max_date_from_vitals(vitals_text)
        
        if date_str:
            df.at[idx, 'DOS'] = date_str
            updated += 1
            print(f"Updated row {idx} (Chart {row['Chart_No']}, Visit {row['Visit']}) with DOS = {date_str}")
    
    df.to_excel(output_excel, index=False, engine='openpyxl')
    print(f"\nUpdated {updated} rows. Saved to {output_excel}")


# ----------------------------------------------------------------------
# SECTION 3: Functions from 3_homemed.py (split HOME MEDICATIONS from Medications)
# ----------------------------------------------------------------------

def split_medications_column(df: pd.DataFrame) -> pd.DataFrame:
    if 'HOME MEDICATIONS' not in df.columns:
        df['HOME MEDICATIONS'] = ''

    home_pattern = re.compile(r'(Home\s+Meds?|Home\s+Medications?)', re.IGNORECASE)
    inpatient_pattern = re.compile(
        r'Medications\s*[\(\{]\s*\d+\s*[\)\}]\s*Active',
        re.IGNORECASE | re.DOTALL
    )

    for idx, row in df.iterrows():
        meds = row['MEDICATIONS']
        if pd.isna(meds) or not isinstance(meds, str):
            continue

        home_match = home_pattern.search(meds)
        if not home_match:
            continue

        inpatient_match = inpatient_pattern.search(meds, home_match.end())
        if inpatient_match:
            home_part = meds[home_match.start():inpatient_match.start()].strip()
            remaining_part = meds[inpatient_match.start():].strip()
            df.at[idx, 'MEDICATIONS'] = remaining_part
        else:
            home_part = meds[home_match.start():].strip()
            remaining_part = meds[:home_match.start()].strip()
            df.at[idx, 'MEDICATIONS'] = remaining_part

        existing_home = row['HOME MEDICATIONS']
        if pd.notna(existing_home) and existing_home.strip():
            df.at[idx, 'HOME MEDICATIONS'] = existing_home.strip() + "\n\n" + home_part
        else:
            df.at[idx, 'HOME MEDICATIONS'] = home_part

    return df

def split_home_medications_main(input_excel: str, output_excel: str = None):
    if output_excel is None:
        output_excel = input_excel.replace('.xlsx', '_med_split.xlsx')
    
    df = pd.read_excel(input_excel, dtype=str)
    df = split_medications_column(df)
    df.to_excel(output_excel, index=False, engine='openpyxl')
    print(f"Saved to {output_excel}")



# ----------------------------------------------------------------------
# Orchestration: run all three stages sequentially
# ----------------------------------------------------------------------
def run_full_pipeline(input_directory: str, final_output_excel: str):
    """
    Executes the three processing stages:
    1. Parse .txt files -> Excel (stage1)
    2. Fill missing DOS (stage2)
    3. Split HOME MEDICATIONS from MEDICATIONS (stage3 = final_output_excel)
    """
    # Derive intermediate file names
    stage1_output = final_output_excel.replace('.xlsx', '_stage1_temp.xlsx')
    stage2_output = final_output_excel.replace('.xlsx', '_stage2_temp.xlsx')

    print("=== STAGE 1: Parsing text files ===")
    process_folder(input_directory, stage1_output)

    print("\n=== STAGE 2: Filling missing DOS ===")
    fill_missing_dos(stage1_output, stage2_output)

    print("\n=== STAGE 3: Splitting HOME MEDICATIONS ===")
    split_home_medications_main(stage2_output, final_output_excel)

    # Clean up intermediate files (optional)
    # Path(stage1_output).unlink(missing_ok=True)
    # Path(stage2_output).unlink(missing_ok=True)
    print(f"\nPipeline completed. Final output: {final_output_excel}")


if __name__ == "__main__":
    input_directory = "D:\DevGo\Inpatient\Data Ingestion\OCR"
    
    # Stage 1: get the first chart number directly
    stage1_temp = "temp_stage1.xlsx"
    first_chart_no = process_folder(input_directory, stage1_temp)
    
    if first_chart_no is None:
        print("No data found.")
        exit(1)
    
    # Build final output filename
    final_output = f"IP_Chart{first_chart_no}_data_extraction_30june_2026.xlsx"
    
    # Stage 2 and 3 as before
    stage2_temp = f"temp_stage2_{first_chart_no}.xlsx"
    
    fill_missing_dos(stage1_temp, stage2_temp)
    split_home_medications_main(stage2_temp, final_output)
    
    # Cleanup
    Path(stage1_temp).unlink(missing_ok=True)
    Path(stage2_temp).unlink(missing_ok=True)
    
    print(f"\nPipeline completed. Final output: {final_output}")