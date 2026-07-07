import re
from pymongo import MongoClient

# MongoDB connection
client = MongoClient("mongodb://172.19.19.87:27017/")
db = client["AHFL_Full"]
collection = db["charts_2"]

def discharge_cpt_from_mongo(filename: str, dos: str):


    # print("filename>",filename)
    # print("Input dos>",dos)
    """
    Get discharge CPT (99238 / 99239) for given filename + DOS.
    Normalizes both input DOS and DB DOS before comparison.
    """
    filename = filename.replace(".tiff", "").replace(".tif", "")

    # normalize user DOS
    dos_norm = normalize_dos(dos)

    # Find chart by filename
    doc = collection.find_one({"file_name": {"$regex": filename, "$options": "i"}})
    if not doc:
        return "N/A", f"No document found for filename {filename}"

    visits = doc.get("visits", {})
    for visit_key, visit_data in visits.items():
        if not visit_key.startswith("Date_of_Service_"):
            continue

        # extract DOS from visit key and normalize it
        visit_dos_raw = extract_dos_from_visit_key(visit_key)
        visit_dos = normalize_dos(visit_dos_raw)

        # print("visit_dos_raw>",visit_dos_raw)
        # print("visit_dos_raw>>",visit_dos_raw)
        # print("visit_dos",visit_dos)
        # print("dos_norm",dos_norm)


        # 🔹 Compare normalized forms only
        if visit_dos != dos_norm:
            continue

        if not isinstance(visit_data, list):
            return "N/A", "Visit data not in expected list format"

        section_map = {
            entry.get("section", "").strip(): entry.get("content", "")
            for entry in visit_data
        }

        # Hospice / expired check
        disposition_data = section_map.get("Disposition", "")
        if re.search(r"\b(HOSPICE|EXPIRED)\b", disposition_data, re.IGNORECASE):
            return "N/A", "Discharge not applicable (Hospice/Expired)."

        chart_text = "\n".join(section_map.values())
        return discharge_software(chart_text)

    # if nothing matched, show normalized DOS in error
    return "N/A", f"No matching DOS {dos_norm} found in file {filename}"

# Updated discharge_software to only take chart_text (since Extracted_Data not needed anymore)
def discharge_software(chart_text: str):
    """
    Determines discharge CPT code (99238 or 99239) based on time documentation.
    """
    minute_values = []

    # Rule 1: Explicit keyword matches
    if re.search(r"(DISCHARGE MANAGEMENT\s*[>:]?\s*30|GREATER THAN\s*30|MORE THAN\s*30)", chart_text, re.IGNORECASE):
        return "99239", "Discharge time is greater than 30 minutes."

    elif re.search(r"(DISCHARGE MANAGEMENT\s*[<:]?\s*30|LESS THAN\s*30)", chart_text, re.IGNORECASE):
        return "99238", "Discharge time is less than 30 minutes."

    # Rule 2: Extract + filter time mentions
    time_list = Extract_Discharge_Time(chart_text)
    filtered_time_list = filter_discharge_time_with_spent_condition(time_list, chart_text)

    for t in filtered_time_list:
        match = re.search(r"\d+", t)
        if match:
            minute_values.append(int(match.group()))
        else:
            num = words_to_number(t)
            if num:
                minute_values.append(num)

    # Rule 3: Threshold evaluation
    if not minute_values:
        return "99238", "No discharge management time found; defaulting to 99238 (<30 mins)."
    else:
        max_minutes = max(minute_values)
        cpt = "99239" if max_minutes > 30 else "99238"
        return cpt, f"Discharge Management time: {max_minutes} minutes"
def Extract_Discharge_Time(chart):
    """
    Extracts discharge-related time statements with natural sentence support,
    including multiline variations
    """

    pattern = r"""
        (?:
            (?:DISCHARGE\s+MANAGEMENT\s*[>:]?\s*)?
            (?:GREATER\s+THAN|MORE\s+THAN|LESS\s+THAN)?\s*
            \d+\s*
            (?:MINUTES?|MINS?|MIN)?\s*
            (?:HAVE\s+BEEN\s+)?SPENT
        )
        |
        (?:DISCHARGE\s+MANAGEMENT\s+\d+\s*(?:MINUTES?|MINS?|MIN))
        |
        (?:DISCHARGE\s+MANAGEMENT\s+TIME\s*[:\-]?\s*\d+\s*(?:MINUTES?|MINS?|MIN)?)
        |
        (?:DISCHARGE\s+PLANNING\s+(?:APPROXIMATELY\s+)?\d+\s*(?:MINUTES?|MINS?|MIN))
        |
        (?:SPENT\s+\d+\s*(?:MINUTES?|MINS?|MIN))
        |
        (?:DISCHARGE\s+PROCESS\s+\d+\s*(?:MINUTES?|MINS?|MIN))
        |
        (?:DISCHARGE\s+TIME\s+\d+\s*(?:MINUTES?|MINS?|MIN))
        |
        (?:I\s+SPENT\s+\d+\s*(?:MINUTES?|MINS?|MIN)[\w\s,;:.]*?(?:DISCHARGE|EVALUATING|PLANNING))
        |
        (?:\d+\s*(?:MINUTES?|MINS?|MIN)\s+SPENT[\w\s,;:.]*?(?:DISCHARGE|EVALUATING|PLANNING))
        |
        (?:\d+\s*(?:MINUTES?|MINS?|MIN)\s+OF\s+TIME\s+SPENT\s+ON\s+DISCHARGE)
        |
        (?:TIME\s+INVOLVED\s+IN\s+DISCHARGE\s+PROCESS\s*[:\-]?\s*
            (?:
                (?:GREATER\s+THAN|LESS\s+THAN)?\s*
                \d+\s*(?:MINUTES?|MINS?|MIN)?
                |
                (?:GREATER\s+THAN|LESS\s+THAN)?
            )
        )
        |
        (?:DISCHARGE\s+PROCESS\s*[:\-]?\s*\d+\s*(?:MINUTES?|MINS?|MIN)?)
        |
        (?:DISCHARGE\s+TIME\s*[:\-]?\s*\d+\s*(?:MINUTES?|MINS?|MIN)?)
        |
        (?:DISCHARGE\s*\(MIN\)\s*[:\-]?\s*\d+)
        |
        (?:TOTAL\s+TIME\s+SPENT\s+COORDINATING\s*\n?\s*DISCHARGE\s*\(MIN\)\s*[:\-]?\s*\d+)
        |
        (?:TIME\s+SPENT\s+ON\s+DISCHARGE(?:\s+OF\s+THE\s+PATIENT)?\s*[:\-]?\s*\d+\s*(?:MINUTES?|MINS?|MIN)?)
        |
        (?:TIME\s+SPENT\s+DURING\s+THE\s+DISCHARGE(?:\s+OF\s+THE\s+PATIENT)?\s*[:\-]?\s*\d+\s*(?:MINUTES?|MINS?|MIN)?)
        |
        (?:TIME\s+SPENT\s+ON\s+DISCHARGE(?:\s+OF\s+THE\s+PATIENT)?\s+\d+\s*(?:MINUTES?|MINS?|MIN)?)
        |
        (?:TIME\s+INVOLVED\s+IN\s+DISCHARGE\s+PROCESS\s*[:\-]?\s*\n?\s*
            (?:GREATER\s+THAN|LESS\s+THAN)?\s*\d+\s*(?:MINUTES?|MINS?|MIN)?
        )
        |
        (?:TOTAL\s+TIME\s+SPENT\s+FOR\s+DISCHARGE\s+PROCESS\s*[:]?\s*\d+\s*(?:MINUTES?|MINS?|MIN)?)        
        |
        (?:TOTAL\s+TIME\s+SPENT\s+DISCHARGING\s+THIS\s+PATIENT\s+WAS\s+MORE\s+THAN\s*[:]?\s*\d+\s*(?:MINUTES?|MINS?|MIN)?)        
        |
        (?:TOTAL\s+TIME\s+SPENT\s+IN\s+DISCHARGE\s+PLANNING\s*[:]?\s*\d+\s*(?:MINUTES?|MINS?|MIN)?)
        |
        (?:TOTAL\s+TIME\s+SPENT\s+DISCHARGING\s+THIS\s+PATIENT\s+WAS\s*[:]?\s*\d+\s*(?:MINUTES?|MINS?|MIN)?)
        |
        (?:DISCHARGE\s+TOOK\s+GREATER\s+THAN\s*[:]?\s*\d+\s*(?:MINUTES?|MINS?|MIN)?)
        |
        (?:DISCHARGE\s+TOOK\s+(?:GREATER|MORE|LESS)\s+THAN\s+\d+\s*(?:MINUTES?|MINS?|MIN)?)
        |
        (?:DISCHARGE\s+MANAGEMENT\s+(?:\d+|[A-Z-]+(?:\s+[A-Z-]+)*)\s*(?:MINUTES?|MINS?|MIN))
        |
        (?:I\s+SPENT\s+(?:MORE\s+THAN\s+)?\d+\s*(?:MINUTES?|MINS?|MIN)\s+ON\s+DISCHARGE\b)
        |
        (?:DISCHARGE\s+TIME\s*[:\-]?\s*\d+\s*(?:MINUTES?|MINS?|MIN))
        |
        (?:\d+\s*(?:MINUTES?|MINS?|MIN)\s+WERE\s+SPENT\s+ON\s+DISCHARGE)
        |
        (?:TIME\s+INVOLVED\s+IN\s+DISCHARGE\s+PROCESS\s*[:\-]?\s*\d+\s*(?:MINUTES?|MINS?|MIN))
        |
        (?:DISCHARGE\s+INSTRUCTIONS\s+\d+\s*(?:MINUTES?|MINS?|MIN))
        |
        (?:DISCHARGE\s+MANAGEMENT\s*[:\-]?\s*\d+\s*(?:MINUTES?|MINS?|MIN))

    """

    matches = re.findall(pattern, chart.upper(), re.VERBOSE)
    return matches


def filter_discharge_time_with_spent_condition(time_list, chart):
    """
    Filters extracted time phrases based on keywords found within each time string.
    """
    filtered_time_list = []
    context_keywords = [
        "SPENT", "WAS SPENT", "HAVE BEEN SPENT", "TIME SPENT", "TIME INVOLVED",
        "TIME SPENT ON DISCHARGE", "DISCHARGE MANAGEMENT", "DISCHARGE SUMMARY",
        "DISCHARGE SERVICES", "DISCHARGE PROCESS", "DISCHARGE TIME", 
        "DISCHARGE PLANNING", "EVALUATING", "PLANNING", "DOCUMENTING", "COORDINATING",
        "were spent","were spent on discharge"
    ]
    for time in time_list:
        if any(keyword.lower() in time.lower() for keyword in context_keywords):
            filtered_time_list.append(time)
    return filtered_time_list



def words_to_number(text):
    number_words = {
    "ZERO": 0, "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5, "SIX": 6,
    "SEVEN": 7, "EIGHT": 8, "NINE": 9, "TEN": 10, "ELEVEN": 11, "TWELVE": 12,
    "THIRTEEN": 13, "FOURTEEN": 14, "FIFTEEN": 15, "SIXTEEN": 16, "SEVENTEEN": 17,
    "EIGHTEEN": 18, "NINETEEN": 19, "TWENTY": 20, "THIRTY": 30, "FORTY": 40,
    "FIFTY": 50, "SIXTY": 60, "SEVENTY": 70, "EIGHTY": 80, "NINETY": 90}
    text = text.replace("-", " ")
    parts = text.split()
    total = 0
    for part in parts:
        if part in number_words:
            total += number_words[part]
    return total if total > 0 else None

from datetime import datetime

def normalize_dos(dos_str: str) -> str:
    """
    Normalize DOS into M/D/YYYY (no leading zeros).
    Works on both Linux and Windows.
    """
    dos_str = dos_str.strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(dos_str, fmt)
            # Manually strip leading zeros (cross-platform safe)
            month = str(int(dt.month))
            day = str(int(dt.day))
            year = str(dt.year)
            return f"{month}/{day}/{year}"  # always like 10/9/2024
        except ValueError:
            continue
    return dos_str  # fallback
    
def extract_dos_from_visit_key(visit_key: str) -> str:
    """
    Extract and normalize DOS from visit_key like:
    'Date_of_Service_10/9/2024 5:39 PM_H&P'
    Returns: '10/9/2024'
    """
    visit_info = visit_key.replace("Date_of_Service_", "")
    parts = visit_info.split()
    try:
        # first part should be mm/dd/yyyy
        dt = datetime.strptime(parts[0], "%m/%d/%Y")
        return dt.strftime("%-m/%-d/%Y")   # normalize
    except Exception:
        return parts[0]  # fallback