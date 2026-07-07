import sys
sys.path.append("/home/ubuntu/.local/lib/python3.12/site-packages")
sys.path.append("/usr/lib/python3/dist-packages")
sys.path.append('/lambda/nfs/NDS1/03_MedicalCoding/Endpoint_SourceCodes')
# from detection_fns_surgery_GPU import main_execute_single, main_execute_single_icd, main_execute_single_cpt, main_execute_single_hcpcs
from detection_fns_surgery_CPU import main_execute_single, main_execute_single_icd, main_execute_single_cpt, main_execute_single_hcpcs
import pandas as pd; import numpy as np; import re
from sentence_transformers import SentenceTransformer
import faiss
from openai import OpenAI
print("mybackend loaded")

import time
import pandas as pd
from anthropic import Anthropic, APIError

def call_claude_api(CPT_Data, retries=3, delay=2):
    CPT_Data = CPT_Data.lower()
    client = Anthropic(api_key="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")  # Replace with your real key
    prompt = (
        f"You are a medical coding assistant. "
        f"Based on the given statement, only provide the appropriate Medical procedure CPT codes."
        f"Strictly do not provide any explanation or code description.\n\n"
        f"Provide one code per statement."
        f"chart: {CPT_Data}")
    for attempt in range(retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",  # Confirm this is the right model name
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            reply = response.content[0].text.strip()
            first_code = reply.split('\n')[0].strip()
            return first_code
            # return reply.split("\n")
        except APIError as e:
            print(f"APIError on attempt {attempt+1}: {e}")
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))  # Exponential backoff
            else:
                raise RuntimeError("Claude API failed after multiple retries due to overload.")

def call_claude_api_chart(CPT_Data, retries=3, delay=2):
    CPT_Data = CPT_Data.lower()
    client = Anthropic(api_key="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")  # Replace with your real key
    prompt = (
        f"You are a medical coding assistant. "
        f"Based on the given medical chart, only provide the appropriate Medical procedure CPT codes."
        f"Strictly do not provide any explanation or code description.\n\n"
        f"chart: {CPT_Data}")
    for attempt in range(retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",  # Confirm this is the right model name
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            reply = response.content[0].text.strip()
            first_code = reply.split('\n')[0].strip()
            return first_code
            # return reply.split("\n")
        except APIError as e:
            print(f"APIError on attempt {attempt+1}: {e}")
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))  # Exponential backoff
            else:
                raise RuntimeError("Claude API failed after multiple retries due to overload.")


def DL_testing_CPT(query_statement,model_loader):
    myproc = query_statement
    myproc = myproc.lower()
    myprocedure = [myproc]
    CPT_Codes2,CPT_Confs2 = main_execute_single_cpt(myprocedure,model_loader.model_CPT, model_loader.tokenizer_common, model_loader.LABELS_CPT)
    return CPT_Codes2,CPT_Confs2, query_statement

def DL_testing_ICD(query_statement,model_loader):
    mydiag = query_statement
    mydiag = mydiag.lower()
    mydiagnosis = [mydiag]
    ICD_Codes,ICD_Confs = main_execute_single_icd(mydiagnosis,model_loader.model_ICD, model_loader.tokenizer_common, model_loader.LABELS_ICD)
    return ICD_Codes,ICD_Confs, query_statement

import re
def spinalvertebra_preprocessing(stat):
    stat = stat.lower()
    stat = stat.replace("("," ").replace(")"," ")
    # print("stat here:",stat)
    if "l5‑s1" in stat:
        # print("l5‑s1 detected")
        stat = stat.replace("l5‑s1","lumbosacral region")
    elif "c7-t1" in stat:
        stat = stat.replace("c7-t1","cervicothoracic region")
    elif "t12-l1" in stat:
        stat = stat.replace("t12-l1","thoracolumbar region")
    # print("Here B:", stat)
    return stat
    
def finetuned_adapter_loader_helper1():
    #####
    cptdb_path = r"/lambda/nfs/NDS1/03_MedicalCoding/Endpoint_SourceCodes/CPTDB.xlsx"
    SHEETS_TO_USE = ["Full_tree","Radio","Wound_care","Addon_Primary","cpt_descriptions","Sheet1","dec25"]
    def find_col(df, target_key):
        norm_target = target_key
        for c in df.columns:
            norm_col = c.strip()
            if norm_col == norm_target:
                return c
        raise KeyError(f"Could not find column for key '{target_key}' in columns: {list(df.columns)}")
    all_parts = []
    for sheet in SHEETS_TO_USE:
        df = pd.read_excel(cptdb_path, sheet_name=sheet); cpt_col = find_col(df, "CPT"); desc_col = find_col(df, "Full Description")
        mask = (
            df[cpt_col].notna() &
            df[desc_col].notna() &
            (df[cpt_col].astype(str).str.strip() != "") &
            (df[desc_col].astype(str).str.strip() != ""))
        sub = df.loc[mask, [cpt_col, desc_col]].copy()
        sub.columns = ["CPT", "Full Description"]
        all_parts.append(sub)
    #####
    found_path = r"/lambda/nfs/NDS1/03_MedicalCoding/Endpoint_SourceCodes/found_list.xlsx"
    SHEETS_TO_USE_FOUND = ["CORRECT_STATEMENTS"]
    for sheet in SHEETS_TO_USE_FOUND:
        df = pd.read_excel(found_path, sheet_name=sheet); cpt_col = find_col(df, "CPT"); desc_col = find_col(df, "Full Description")
        mask = (
            df[cpt_col].notna() &
            df[desc_col].notna() &
            (df[cpt_col].astype(str).str.strip() != "") &
            (df[desc_col].astype(str).str.strip() != ""))
        sub = df.loc[mask, [cpt_col, desc_col]].copy()
        sub.columns = ["CPT", "Full Description"]
        all_parts.append(sub)    
    print("ALL DB loaded... Please proceed") 
    #####
    if not all_parts: raise RuntimeError("No valid data collected from any sheet.")
    new_df = pd.concat(all_parts, ignore_index=True); new_df = new_df.drop_duplicates(subset=["CPT", "Full Description"]).reset_index(drop=True)
    new_df["CPT"] = new_df["CPT"].astype(str).str.upper().str.strip()
    new_df["Full Description"] = new_df["Full Description"].astype(str).str.upper().str.strip()
    # Remove unwanted characters () , ;
    new_df["Full Description"] = (
        new_df["Full Description"]
        .str.replace(r"[(),;:]", "", regex=True)
        .str.replace(r"\s+", " ", regex=True).str.strip())    
    new_df = new_df.drop_duplicates(subset=["CPT", "Full Description"]).reset_index(drop=True)
    new_df = new_df[~new_df["Full Description"].str.contains("UNLISTED PROCEDURE", case=False, na=False)].reset_index(drop=True)
    addon_mask = (
        new_df["Full Description"].str.contains("LIST SEPARATELY", case=False, na=False) |
        new_df["Full Description"].str.contains("IN ADDITION TO CODE", case=False, na=False))
    new_df["Addon_or_Primary"] = np.where(addon_mask, "ADDON", "PRIMARY")
    # print("Total unique CPT descriptions:", len(new_df))
    new_df_a = new_df[new_df["Addon_or_Primary"] == "ADDON"].reset_index(drop=True)
    new_df_p = new_df[new_df["Addon_or_Primary"] == "PRIMARY"].reset_index(drop=True)
    # print("Total ADDON CPT rows:", len(new_df_a))
    # print("Total PRIMARY CPT rows:", len(new_df_p))
    # model_id = r'/lambda/nfs/NDS1/03_MedicalCoding/all-MiniLM-L6-v2'
    model_id = "sentence-transformers/all-MiniLM-L6-v2"
    ftmodel = SentenceTransformer(model_id)
    ###### FT Embds on DFP
    corpus_texts = new_df_p["Full Description"].tolist()
    embeddings = ftmodel.encode(corpus_texts,convert_to_numpy=True,show_progress_bar=True, normalize_embeddings=True)
    embedding_dim = embeddings.shape[1]
    ftindex = faiss.IndexFlatIP(embedding_dim)
    ftindex.add(embeddings)
    ###### FT Embds on Extra
    new_df_f = pd.read_excel(found_path, sheet_name="EXTRA_STATEMENTS");
    corpus_extras = new_df_f["STATEMENT"].tolist()
    embeddings_extras = ftmodel.encode(corpus_extras,convert_to_numpy=True,show_progress_bar=True, normalize_embeddings=True)
    embedding_dim_extras = embeddings_extras.shape[1]
    ftindex_extras = faiss.IndexFlatIP(embedding_dim_extras)
    ftindex_extras.add(embeddings_extras)
    print("FTModel_loaded")
    ###### Include Tree database here
    tree_database_path = r"/lambda/nfs/NDS1/03_MedicalCoding/Endpoint_SourceCodes/CPT_TREE.xlsx"
    tree_database = pd.read_excel(tree_database_path)    ;    tree_database = tree_database.fillna("NAAAA")
    tree_database.iloc[1:] = tree_database.iloc[1:].applymap(lambda x: x.lower() if isinstance(x, str) else x) # All to uppercase
    tree_main_procedure = list(tree_database["Main Procedure"]) # Choose the values of this column
    all_trees = []           # Will store all the unique main procedures from the database
    if tree_main_procedure:
        for tree_name in tree_main_procedure:
            tree_name_split = tree_name.split("|")
            if tree_name_split:
                for temp_split in tree_name_split:
                    all_trees.append(temp_split.strip())
    # Make the list of main procdures unique
    all_trees_unique = list(set(all_trees)); 
    all_trees_unique.sort() # Sort in alphabetical order
    # Also make the list of addon codes
    addon_rows = tree_database[tree_database['Addon_Primary'] == 'addon'];  #
    addon_codes_list = list(addon_rows["CPT"]) # Addon list
    tree_df_p = tree_database[tree_database["Addon_Primary"] == "primary"].reset_index(drop=True)

#**************************************************************************************************    
    #### MODIFIER MODULE
    modifier_excel_path = r"/lambda/nfs/NDS1/03_MedicalCoding/Endpoint_SourceCodes/Modifierlist.xlsx"
    df_modifier = load_modifier_db(modifier_excel_path)

    return new_df, new_df_a, new_df_p, ftmodel, ftindex, ftindex_extras, all_trees_unique, tree_df_p, tree_database, df_modifier
    
    # return new_df, new_df_a, new_df_p, ftmodel, ftindex, ftindex_extras, all_trees_unique, tree_df_p, tree_database

# Load the modifier database here  
def load_modifier_db(modifier_excel_path):
    df = pd.read_excel(modifier_excel_path)
    df = df.fillna("")

    df["CVSM"] = df["CVSM"].astype(str).str.upper().str.strip()
    df = df[df["CVSM"] == "YES"].reset_index(drop=True)

    df["Modifier"] = df["Modifier"].astype(str).str.strip()
    df["Description"] = df["Description"].astype(str).str.lower().str.strip()
    return df

# Rule based shortlisting
def shortlist_modifiers(statement, df_modifier):
    stmt = statement.lower()
    matched = []
    for _, row in df_modifier.iterrows():
        desc = row["Description"]
        if desc and any(word in stmt for word in desc.split()):
            matched.append(row["Modifier"])
    return list(set(matched))

# LLM based confirmation
def llm_confirm_modifiers(statement, df_modifier):
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
    modifier_block = "\n".join(
        f"{row['Modifier']} : {row['Description']}"
        for _, row in df_modifier.iterrows()
    )
    prompt = f"""
    You are an expert medical coder.
    Your task: Identify applicable CPT modifiers for the given medical procedure statement.
    Rules:
    1. Use ONLY modifiers from the provided modifier list.
    2. Apply a modifier ONLY if it is explicitly and clearly supported by the statement.
    3. Do NOT infer or assume modifiers.
    4. If documentation is insufficient or ambiguous, return EXACTLY: NONE.
    5. If multiple modifiers apply, return them comma separated.
    6. a) If the procedure is documented as bilateral or both sides, return modifier 50 ONLY. Do NOT return LT or RT when 50 is used.
       b) Use LT or RT ONLY if the procedure is unilateral and side is explicitly documented. Do NOT return both LT and RT together.
    7. Do NOT return both 59 and X{{E,P,S,U}} modifiers together. Do NOT return modifier 59 unless a distinct session, site, lesion, or encounter is explicitly stated.
    8. Do NOT apply E/M-only modifiers unless the statement clearly represents an E/M service.
    9. Do NOT apply anesthesia-specific modifiers unless anesthesia services are explicitly stated.
    10. Do NOT apply modifier 51 unless multiple distinct procedures are clearly documented.
    11. Apply assistant surgeon modifiers (80, 81, 82) ONLY if assistant participation is explicitly documented.
    12. Do NOT return modifier 52 unless reduced service is clearly documented. 
    13. Do NOT return modifiers 76 or 77 unless a repeat procedure is explicitly documented.
    14. Do NOT return both 26 and TC together.
    15. Do NOT apply modifiers that are bundled into the CPT description.
    16. Return ONLY modifier codes. No explanations. No extra text.
    
    Modifier List:
    {modifier_block}
    
    Procedure Statement:
    {statement}
    """

    response = client.responses.create(
        model="openai/gpt-oss-120b",
        input=prompt,
        temperature=0.0,
        max_output_tokens=200
    )
    out = response.output_text.strip()
    if out == "NONE":
        return []
    return [m.strip() for m in out.split(",")]

def compute_modifiers(tree_llm_statements, df_modifier):
    all_modifiers = set()
    if not tree_llm_statements:
        return ""
    statements = [
        s.strip() for s in tree_llm_statements.split("\n")
        if s.strip()
    ]

    for stmt in statements:
        shortlist = shortlist_modifiers(stmt, df_modifier)
        if not shortlist:
            continue

        confirmed = llm_confirm_modifiers(stmt, df_modifier)
        for m in confirmed:
            all_modifiers.add(m)

    return ", ".join(sorted(all_modifiers)) if all_modifiers else ""

#**************************************************************************************************

def finetuned_adapter_loader_helper3():
    icddb_path = r"/lambda/nfs/NDS1/03_MedicalCoding/Endpoint_SourceCodes/ICD_Full_Desc_20251204.xlsx"
    SHEETS_TO_USE = ["Sheet1"]
    def find_col(df, target_key):
        norm_target = target_key
        for c in df.columns:
            norm_col = c.strip()
            if norm_col == norm_target:
                return c
        raise KeyError(f"Could not find column for key '{target_key}' in columns: {list(df.columns)}")
    all_parts = []
    for sheet in SHEETS_TO_USE:
        df = pd.read_excel(icddb_path, sheet_name=sheet); 
        icd_col = find_col(df, "ICD"); 
        desc_col = find_col(df, "Full Description")
        mask = (
            df[icd_col].notna() &
            df[desc_col].notna() &
            (df[icd_col].astype(str).str.strip() != "") &
            (df[desc_col].astype(str).str.strip() != ""))
        sub = df.loc[mask, [icd_col, desc_col]].copy()
        sub.columns = ["ICD", "Full Description"]
        all_parts.append(sub)
    if not all_parts: raise RuntimeError("No valid data collected from any sheet.")
    new_df = pd.concat(all_parts, ignore_index=True); new_df = new_df.drop_duplicates(subset=["ICD", "Full Description"]).reset_index(drop=True)
    new_df["ICD"] = new_df["ICD"].astype(str).str.upper().str.strip()
    new_df["Full Description"] = new_df["Full Description"].astype(str).str.upper().str.strip()
    # Remove unwanted characters () , ;
    new_df["Full Description"] = (
        new_df["Full Description"]
        .str.replace(r"[(),;:]", "", regex=True)
        .str.replace(r"\s+", " ", regex=True).str.strip())    
    new_df = new_df.drop_duplicates(subset=["ICD", "Full Description"]).reset_index(drop=True)
    model_id = "sentence-transformers/all-MiniLM-L6-v2"
    ftmodel = SentenceTransformer(model_id)
    corpus_texts = new_df["Full Description"].tolist()
    embeddings = ftmodel.encode(corpus_texts,convert_to_numpy=True,show_progress_bar=True, normalize_embeddings=True)
    embedding_dim = embeddings.shape[1]
    ftindex = faiss.IndexFlatIP(embedding_dim)
    ftindex.add(embeddings)
    print("FTModel_loaded")

    ### Load the modifier DB
    
    return new_df, ftmodel, ftindex


def finetuned_adapter_loader_helper2(query_text, ftmod, ftind, DFP):
    to_k = 15
    q_emb = ftmod.encode([query_text],convert_to_numpy=True, normalize_embeddings=True,show_progress_bar=False)
    scores, indices = ftind.search(q_emb, to_k)
    indices = indices[0]; scores = scores[0]
    results = []
    for idx, sc in zip(indices, scores):
        if idx < 0:
            continue
        row = DFP.iloc[idx]; desc = row["Full Description"];   code = row["CPT"]
        results.append(f"{desc} : {code}")
    
    tok_str = "; ".join(results)
    test_statement = query_text
    client = OpenAI(base_url="http://localhost:8000/v1",api_key="EMPTY")
    first_prompt = "You are an expert medical coder"
    second_prompt = """
    For the given test statement choose the best one that can billed or medically coded from among the given list of candidate description and code.
    Give me the description and code separated by colon (:) strictly and give the description and code as it is do not add anything.
    Also note that the list of candidates is separated by semicolon operator. Stricly do not give any explanation. 
    """
    third_prompt = "\n The test statement is: " + " " + test_statement + ". \n\n The list of candidate are: " + tok_str + "."
    third_prompt = third_prompt.replace(",","").replace("\u202f", " ").replace("/", " ")
    prompt = second_prompt + " " + third_prompt
    # print(prompt)    
    try:
        response = client.responses.create(model= "openai/gpt-oss-120b",
                                           instructions=first_prompt,
                                           input=prompt,reasoning={"effort": "medium"},temperature=0.0, max_output_tokens=10000)
        response = response.output_text
    except: response =" "; # print("Model did not generate")
    try:
        statt,codd = response.split(":")
        statt = statt.strip(); codd = codd.strip()
    except:
        statt = query_text; codd = ""
    return statt, codd

def finetuned_adapter_loader_helper4(query_text, ftmod, ftind, DFP):
    to_k = 10
    q_emb = ftmod.encode([query_text],convert_to_numpy=True, normalize_embeddings=True,show_progress_bar=False)
    scores, indices = ftind.search(q_emb, to_k)
    indices = indices[0]; scores = scores[0]
    results = []
    for idx, sc in zip(indices, scores):
        if idx < 0:
            continue
        row = DFP.iloc[idx]; desc = row["Full Description"];   code = row["ICD"]
        results.append(f"{desc} : {code}")
    
    tok_str = "; ".join(results)
    test_statement = query_text
    client = OpenAI(base_url="http://localhost:8000/v1",api_key="EMPTY")
    first_prompt = "You are an expert medical coder"
    second_prompt = """
    For the given test statement choose the best one that can billed or medically coded from among the given list of candidate description and code.
    Give me the description and code separated by colon (:) strictly and give the description and code as it is do not add anything.
    Also note that the list of candidates is separated by semicolon operator. Stricly do not give any explanation. 
    """
    third_prompt = "\n The test statement is: " + " " + test_statement + ". \n\n The list of candidate are: " + tok_str + "."
    third_prompt = third_prompt.replace(",","").replace("\u202f", " ").replace("/", " ")
    prompt = second_prompt + " " + third_prompt
    # print(prompt)    
    try:
        response = client.responses.create(model= "openai/gpt-oss-120b",
                                           instructions=first_prompt,
                                           input=prompt,reasoning={"effort": "medium"},temperature=0.0, max_output_tokens=10000)
        response = response.output_text
    except: response =" "; # print("Model did not generate")
    try:
        statt,codd = response.split(":")
        statt = statt.strip(); codd = codd.strip()
    except:
        statt = query_text; codd = ""
    return statt, codd

def process_chart_CPT(third_prompt):
    client = OpenAI(base_url="http://localhost:8000/v1",api_key="EMPTY")
    first_prompt = "You are an expert medical coder"
    second_prompt = """
    Extract the confirmed major CPT procedures and their billable CPT codes pairs --> in bullets separated by colon(:) strictly for the following paragraph.
    Note the following:
    1. As per CPT standard logic a procedure statement may require components like: main procedure, anatomical structure, specificity, laterality, medical device, medical condition, area or length or dimension, depth (for instance skin, muscle, bone level etc.).
    2. If the procedure requires components like - number of lesions, defect size, excision/debridement/repair area/length/dimension, stone size, weight of uterus, etc. fetch from
    the chart text and append to the procedure statement.
    3. Also note that certain procedures may need not have any quantity value in the statement as per CPT standard logic.
    4. Also take care to not give the bundled procedure statement and the code. Instead give the major procedure statement and the code.
    5. Give one CPT code per statement, strictly do not provide explanation.
    The paragraph is as follows:
    """
    third_prompt = third_prompt.replace(",","").replace("\u202f", " ").replace(":", " ").replace("/", " ")  
    prompt = second_prompt + " " + third_prompt
    try:
        response = client.responses.create(model= "openai/gpt-oss-120b",
                                           instructions=first_prompt,
                                           input=prompt,reasoning={"effort": "medium"},temperature=0.0, max_output_tokens=20000)

        response = response.output_text       
    except:
        response =" "; print("Model did not generate")
    return response

def process_chart_ICD(third_prompt):
    client = OpenAI(base_url="http://localhost:8000/v1",api_key="EMPTY")
    first_prompt = "You are an expert medical coder"
    second_prompt = """
    I want to extract the confirmed diagnoses and their billable ICD-10-CM code pairs --> in bullets strictly separated by colon (:) for the following paragraph.
    Also do not miss conditions like elevated troponin, elevated condition, history condition, weakness, body mass index, bmi, morbid obesity, overweight, underweight, etc.
    Give one ICD code per statement, strictly do not provide explanation. 
    The paragraph is as follows:
    """
    third_prompt = third_prompt.replace(",","").replace("\u202f", " ").replace(":", " ").replace("/", " ")  
    prompt = second_prompt + " " + third_prompt
    try:
        response = client.responses.create(model="openai/gpt-oss-120b",instructions=first_prompt,
                                           input=prompt,reasoning={"effort": "medium"},temperature=0.0, max_output_tokens=10000
                                           )
        response = response.output_text
        print("Model generated")
    except:
        response =" "
        print("Model did not generate")
    return response


def acquire_CS_CPT(filename_without_txt,mastersummarydf):
    cs_codes = "NOT FOUND"
    if filename_without_txt in mastersummarydf['ENCOUNTER NO'].astype(str).values:
        cpt_raw = mastersummarydf.loc[
            mastersummarydf['ENCOUNTER NO'].astype(str) == filename_without_txt,
            'Customer CPT'].values[0]
        cpt_string = str(cpt_raw).strip()
        if cpt_string.lower() in ["nan", "", "none"]:
            filtered_cpts = []
        else:
            cpt_list = [c.strip() for c in cpt_string.split(',')]
            filtered_cpts = [c for c in cpt_list if not c.startswith(('8', '9'))]
        if len(filtered_cpts) > 1:     cs_codes = ", ".join(filtered_cpts)
        elif len(filtered_cpts) == 1:  cs_codes = filtered_cpts[0]
        else:  cs_codes = "NOT FOUND"
    return cs_codes

def acquire_CS_ICD(filename_without_txt,mastersummarydf):
    cs_codes = "NOT FOUND"
    if filename_without_txt in mastersummarydf['ENCOUNTER NO'].astype(str).values:
        icd_raw = mastersummarydf.loc[
            mastersummarydf['ENCOUNTER NO'].astype(str) == filename_without_txt,
            'Customer ICD'].values[0]
        icd_string = str(icd_raw).strip()
        if icd_string.lower() in ["nan", "", "none"]:
            filtered_icds = []
        else:
            icd_list = [c.strip() for c in icd_string.split(',')]
            filtered_icds = [c for c in icd_list if not c.startswith(('8', '9'))]
        if len(filtered_icds) > 1:     cs_codes = ", ".join(filtered_icds)
        elif len(filtered_icds) == 1:  cs_codes = filtered_icds[0]
        else:  cs_codes = "NOT FOUND"
    return cs_codes
    
def read_chart(input_folder, filename):
    import os
    import chardet
    file_path = os.path.join(input_folder, filename)
    with open(file_path, "rb") as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        encoding = result["encoding"]
    with open(file_path, "r", encoding=encoding, errors="ignore") as f:
        extraction_value = f.read()        
    return extraction_value

def acquire_CPT(chart_text,ftmod, ftind, DFP,model_loader):
    final_response_CPT = process_chart_CPT(chart_text) # Let LLM generate statement and code first
    statements_list = []; # Generated by LLM
    statements_list2 = []; # Chosen by Finetuned LLM
    model_codes_list = [];  # Generated by LLM
    model_codes_list2 = []; # Chosen by Finetuned LLM
    DL_codes_list = []; # Applied LLM Generated statement to CPT DL model
    DL_codes_list2 = [] # Applied Finetune LLM's Generated statement to CPT DL model
    for line in final_response_CPT.split("\n"):
        if ":" in line:
            parts = line.split(":", 1)
            stmt = parts[0].strip();  modelcode = parts[1].strip()
            stmt2,modelcode2 = finetuned_adapter_loader_helper2(stmt,ftmod, ftind, DFP)
            stmt = spinalvertebra_preprocessing(stmt) 
            CPTcode, CPTconfidence, CPTstatement    = DL_testing_CPT(stmt, model_loader)
            CPTcode2, CPTconfidence2, CPTstatement2 = DL_testing_CPT(stmt2, model_loader)
            statements_list.append(stmt);            statements_list2.append(stmt2)
            model_codes_list.append(modelcode);      model_codes_list2.append(modelcode2)
            DL_codes_list.append(CPTcode);           DL_codes_list2.append(CPTcode2)
    statements_str = "\n".join(statements_list);     statements_str2 = "\n".join(statements_list2)
    model_codes_str = ", ".join(model_codes_list);   model_codes_str2 = ", ".join(model_codes_list2)
    dl_codes_str = ", ".join(DL_codes_list);         dl_codes_str2 = ", ".join(DL_codes_list2)
    return final_response_CPT, statements_str, model_codes_str2, dl_codes_str2

def acquire_ICD(chart_text,ftmod_i,ftind_i,DF_ALL_I,model_loader):
    final_response_ICD = process_chart_ICD(chart_text) # Let LLM generate statement and code first
    statements_list = []; # Generated by LLM
    statements_list2 = []; # Chosen by Finetuned LLM
    model_codes_list = [];  # Generated by LLM
    model_codes_list2 = []; # Chosen by Finetuned LLM
    DL_codes_list = []; # Applied LLM Generated statement to ICD DL model
    DL_codes_list2 = [] # Applied Finetune LLM's Generated statement to CPT DL model
    for line in final_response_ICD.split("\n"):
        if ":" in line:
            parts = line.split(":", 1)
            stmt = parts[0].strip();  modelcode = parts[1].strip()
            stmt2,modelcode2 = finetuned_adapter_loader_helper4(stmt,ftmod_i, ftind_i, DF_ALL_I)
            ICDcode, ICDconfidence, ICDstatement    = DL_testing_ICD(stmt, model_loader)
            ICDcode2, ICDconfidence2, ICDstatement2 = DL_testing_ICD(stmt2, model_loader)
            statements_list.append(stmt);            statements_list2.append(stmt2)
            model_codes_list.append(modelcode);      model_codes_list2.append(modelcode2)
            DL_codes_list.append(ICDcode);           DL_codes_list2.append(ICDcode2)
    statements_str = "\n".join(statements_list);     statements_str2 = "\n".join(statements_list2)
    model_codes_str = ", ".join(model_codes_list);   model_codes_str2 = ", ".join(model_codes_list2)
    dl_codes_str = ", ".join(DL_codes_list);         dl_codes_str2 = ", ".join(DL_codes_list2)
    return final_response_ICD, statements_str, model_codes_str2, dl_codes_str2

def getaddon(third_prompt, chart_text):
    """
    Generates CPT add-on codes from a given chart and candidate list.
    Updated prompt ensures exact counting of additional units/lesions.
    """
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
    first_prompt = "You are an expert medical coder."
    # second_prompt = """
    # You are coding the number of billable CPT codes in addition to the first primary procedure according to CPT standard rules.
    # Instructions:
    # 1. You are given a list of candidate codes. Each candidate is formatted as <CPT>:<Full description>, separated by a pipe (|).
    # 2. Count **all additional billable units or lesions beyond the primary procedure exactly** as described in the chart. 
    #    Do not round, estimate, or skip any units.
    # 3. From the chart code the primary first and then count or code the additional procedures.
    # 4. Use the quantities in the candidate description to determine how many times a code should be repeated. This must as per CPT standard billing logic.
    # 5. If the chart does NOT support add-on codes, return exactly: NOT_NEEDED.
    # FORMAT RULES:
    # • Output ONLY CPT codes separated by commas, no narrative text.
    # • Repeat a code exactly as many times as indicated by the chart.
    # • Return NOT_NEEDED exactly if no add-ons apply.
    # Chart text:
    # """
    second_prompt = """
    1. You are given a list of candidate codes. Each candidate is formatted as <CPT>:<Full description>, separated by a pipe (|).
    2. You may need to code one primary CPT code and additional CPT codes for billing exactly.
    3. Use the quantities in the candidate description to determine how many times a code should be repeated. This must as per CPT standard billing logic.
    4. Therefore, give the suitable CPT codes from these candidates as per the chart text.
    OUTPUT FORMAT RULES:
    • Output ONLY CPT codes separated by commas, no narrative text
    • Strictly return NOT_NEEDED exactly if none found suitable.
    Chart text:
    """
    prompt = second_prompt + chart_text + "\n\nCandidate codes:\n" + third_prompt
    try:
        response = client.responses.create(
            model="openai/gpt-oss-120b",
            instructions=first_prompt,
            input=prompt,
            reasoning={"effort": "medium"},
            temperature=0.0,
            max_output_tokens=20000)
        response = response.output_text.strip()
    except Exception as e:
        print("Model did not generate:", e)
        response = ""
    return response


def evaluate_additionalcodes(chart):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    candidate_skintags = """
    11200: Removal of skin tags, multiple fibrocutaneous tags, any area; up to and including 15 lesions | \
    11201: Removal of skin tags, multiple fibrocutaneous tags, any area; each additional 10 lesions, or part thereof (List separately in addition to code for primary procedure)
    """
    candidate_complexrepair = """
    13100: Repair, complex, trunk; 1.1 cm to 2.5 cm | 13101: Repair, complex, trunk; 2.6 cm to 7.5 cm | \
    13102: Repair, complex, trunk; each additional 5 cm or less (List separately in addition to code for primary procedure)
    13120: Repair, complex, scalp, arms, and/or legs; 1.1 cm to 2.5 cm |13121: Repair, complex, scalp, arms, and/or legs; 2.6 cm to 7.5 cm | \
    13122: Repair, complex, scalp, arms, and/or legs; each additional 5 cm or less (List separately in addition to code for primary procedure) | \
    13131: Repair, complex, forehead, cheeks, chin, mouth, neck, axillae, genitalia, hands and/or feet; 1.1 cm to 2.5 cm | \
    13132: Repair, complex, forehead, cheeks, chin, mouth, neck, axillae, genitalia, hands and/or feet; 2.6 cm to 7.5 cm | \
    13133: Repair, complex, forehead, cheeks, chin, mouth, neck, axillae, genitalia, hands and/or feet; each additional 5 cm or less (List separately in addition to code for primary procedure) | \
    13151: Repair, complex, eyelids, nose, ears and/or lips; 1.1 cm to 2.5 cm | 13152: Repair, complex, eyelids, nose, ears and/or lips; 2.6 cm to 7.5 cm | \
    13153: Repair, complex, eyelids, nose, ears and/or lips; each additional 5 cm or less (List separately in addition to code for primary procedure)
    """
    candidate_tatooing = """
    11920: Tattooing, intradermal introduction of insoluble opaque pigments to correct color defects of skin, including micropigmentation; 6.0 sq cm or less | \
    11921: Tattooing, intradermal introduction of insoluble opaque pigments to correct color defects of skin, including micropigmentation; 6.1 to 20.0 sq cm | \
    11922: Tattooing, intradermal introduction of insoluble opaque pigments to correct color defects of skin, including micropigmentation; each additional 20.0 sq cm, or part thereof (List separately in addition to code for primary procedure)
    """
    candidate_osteotomy = """
    22206: Osteotomy of spine, posterior or posterolateral approach, 3 columns, 1 vertebral segment (eg, pedicle/vertebral body subtraction); thoracic | \
    22207: Osteotomy of spine, posterior or posterolateral approach, 3 columns, 1 vertebral segment (eg, pedicle/vertebral body subtraction); lumbar | \
    22208: Osteotomy of spine, posterior or posterolateral approach, 3 columns, 1 vertebral segment (eg, pedicle/vertebral body subtraction); each additional vertebral segment (List separately in addition to code for primary procedure) | \
    22210: Osteotomy of spine, posterior or posterolateral approach, 1 vertebral segment; cervical | 22212: Osteotomy of spine, posterior or posterolateral approach, 1 vertebral segment; thoracic | \
    22214: Osteotomy of spine, posterior or posterolateral approach, 1 vertebral segment; lumbar | \
    22216: Osteotomy of spine, posterior or posterolateral approach, 1 vertebral segment; each additional vertebral segment (List separately in addition to primary procedure) | \
    22220: Osteotomy of spine, including discectomy, anterior approach, single vertebral segment; cervical | \
    22222: Osteotomy of spine, including discectomy, anterior approach, single vertebral segment; thoracic | \
    22224: Osteotomy of spine, including discectomy, anterior approach, single vertebral segment; lumbar | \
    22226: Osteotomy of spine, including discectomy, anterior approach, single vertebral segment; each additional vertebral segment (List separately in addition to code for primary procedure)
    """
    candidate_injection = """
    11900: Injection, intralesional; up to and including 7 lesions | \
    11901: Injection, intralesional; more than 7 lesions | \
    11950: Subcutaneous injection of filling material (eg, collagen); 1 cc or less | \
    11951: Subcutaneous injection of filling material (eg, collagen); 1.1 to 5.0 cc | \
    11952: Subcutaneous injection of filling material (eg, collagen); 5.1 to 10.0 cc | \
    11954: Subcutaneous injection of filling material (eg, collagen); over 10.0 cc | \
    20550: Injection(s); single tendon sheath, or ligament, aponeurosis (eg, plantar \"fascia\") | \
    20551: Injection(s); single tendon origin/insertion | \
    20552: Injection(s); single or multiple trigger point(s), 1 or 2 muscle(s) | \
    20553: Injection(s); single or multiple trigger point(s), 3 or more muscles
    """
    candidate_placement =    """
    19281: Placement of breast localization device(s) (eg, clip, metallic pellet, wire/needle, radioactive seeds), percutaneous; first lesion, including mammographic guidance | \
    19282: Placement of breast localization device(s) (eg, clip, metallic pellet, wire/needle, radioactive seeds), percutaneous; each additional lesion, including mammographic guidance (List separately in addition to code for primary procedure) | \
    19283: Placement of breast localization device(s) (eg, clip, metallic pellet, wire/needle, radioactive seeds), percutaneous; first lesion, including stereotactic guidance | \
    19284: Placement of breast localization device(s) (eg, clip, metallic pellet, wire/needle, radioactive seeds), percutaneous; each additional lesion, including stereotactic guidance (List separately in addition to code for primary procedure) | \
    19285: Placement of breast localization device(s) (eg, clip, metallic pellet, wire/needle, radioactive seeds), percutaneous; first lesion, including ultrasound guidance | \
    19286: Placement of breast localization device(s) (eg, clip, metallic pellet, wire/needle, radioactive seeds), percutaneous; each additional lesion, including ultrasound guidance (List separately in addition to code for primary procedure) | \
    19287: Placement of breast localization device(s) (eg clip, metallic pellet, wire/needle, radioactive seeds), percutaneous; first lesion, including magnetic resonance guidance | \
    19288: Placement of breast localization device(s) (eg clip, metallic pellet, wire/needle, radioactive seeds), percutaneous; each additional lesion, including magnetic resonance guidance (List separately in addition to code for primary procedure)
    """
    candidate_biopsy = """
    19081: Biopsy, breast, with placement of breast localization device(s) (eg, clip, metallic pellet), when performed, and imaging of the biopsy specimen, when performed, percutaneous; first lesion, including stereotactic guidance | \
    19082: Biopsy, breast, with placement of breast localization device(s) (eg, clip, metallic pellet), when performed, and imaging of the biopsy specimen, when performed, percutaneous; each additional lesion, including stereotactic guidance (List separately in addition to code for primary procedure) | \
    19083: Biopsy, breast, with placement of breast localization device(s) (eg, clip, metallic pellet), when performed, and imaging of the biopsy specimen, when performed, percutaneous; first lesion, including ultrasound guidance | \
    19084: Biopsy, breast, with placement of breast localization device(s) (eg, clip, metallic pellet), when performed, and imaging of the biopsy specimen, when performed, percutaneous; each additional lesion, including ultrasound guidance (List separately in addition to code for primary procedure) | \
    19085: Biopsy, breast, with placement of breast localization device(s) (eg, clip, metallic pellet), when performed, and imaging of the biopsy specimen, when performed, percutaneous; first lesion, including magnetic resonance guidance | \
    19086: Biopsy, breast, with placement of breast localization device(s) (eg, clip, metallic pellet), when performed, and imaging of the biopsy specimen, when performed, percutaneous; each additional lesion, including magnetic resonance guidance (List separately in addition to code for primary procedure)
    """
    candidate_graft1 = """
    15100: Split-thickness autograft, trunk, arms, legs; first 100 sq cm or less, or 1% of body area of infants and children | \
    15101: Split-thickness autograft, trunk, arms, legs; each additional 100 sq cm, or each additional 1% of body area of infants and children, or part thereof (List separately in addition to code for primary procedure)
    """
    candidate_graft2 = """
    15271: Application of skin substitute graft to trunk, arms, legs, total wound surface area up to 100 sq cm; first 25 sq cm or less wound surface area | \
    15272: Application of skin substitute graft to trunk, arms, legs, total wound surface area up to 100 sq cm; each additional 25 sq cm wound surface area, or part thereof (List separately in addition to code for primary procedure) | \
    15273: Application of skin substitute graft to trunk, arms, legs, total wound surface area greater than or equal to 100 sq cm; first 100 sq cm wound surface area, or 1% of body area of infants and children | \
    15274: Application of skin substitute graft to trunk, arms, legs, total wound surface area greater than or equal to 100 sq cm; each additional 100 sq cm wound surface area, or part thereof, or each additional 1% of body area of infants and children, or part thereof (List separately in addition to code for primary procedure) | \
    15275: Application of skin substitute graft to face, scalp, eyelids, mouth, neck, ears, orbits, genitalia, hands, feet, and/or multiple digits, total wound surface area up to 100 sq cm; first 25 sq cm or less wound surface area | \
    15276: Application of skin substitute graft to face, scalp, eyelids, mouth, neck, ears, orbits, genitalia, hands, feet, and/or multiple digits, total wound surface area up to 100 sq cm; each additional 25 sq cm wound surface area, or part thereof (List separately in addition to code for primary procedure) | \
    15277: Application of skin substitute graft to face, scalp, eyelids, mouth, neck, ears, orbits, genitalia, hands, feet, and/or multiple digits, total wound surface area greater than or equal to 100 sq cm; first 100 sq cm wound surface area, or 1% of body area of infants and children | \
    15278: Application of skin substitute graft to face, scalp, eyelids, mouth, neck, ears, orbits, genitalia, hands, feet, and/or multiple digits, total wound surface area greater than or equal to 100 sq cm; each additional 100 sq cm wound surface area, or part thereof, or each additional 1% of body area of infants and children, or part thereof (List separately in addition to code for primary procedure)
    """
    candidate_adjacent_tissue_transfer = """    
    14000: Adjacent tissue transfer or rearrangement, trunk; defect 10 sq cm or less | \
    14001: Adjacent tissue transfer or rearrangement, trunk; defect 10.1 sq cm to 30.0 sq cm | \
    14020: Adjacent tissue transfer or rearrangement, scalp, arms and/or legs; defect 10 sq cm or less | \
    14021: Adjacent tissue transfer or rearrangement, scalp, arms and/or legs; defect 10.1 sq cm to 30.0 sq cm | \
    14040: Adjacent tissue transfer or rearrangement, forehead, cheeks, chin, mouth, neck, axillae, genitalia, hands and/or feet; defect 10 sq cm or less | \
    14041: Adjacent tissue transfer or rearrangement, forehead, cheeks, chin, mouth, neck, axillae, genitalia, hands and/or feet; defect 10.1 sq cm to 30.0 sq cm | \
    14060: Adjacent tissue transfer or rearrangement, eyelids, nose, ears and/or lips; defect 10 sq cm or less | \
    14061: Adjacent tissue transfer or rearrangement, eyelids, nose, ears and/or lips; defect 10.1 sq cm to 30.0 sq cm
    """
    candidate_coronary_bypass1 =     """
    33510: Coronary artery bypass, vein only; single coronary venous graft | \
    33511: Coronary artery bypass, vein only; 2 coronary venous grafts | \
    33512: Coronary artery bypass, vein only; 3 coronary venous grafts | \
    33513: Coronary artery bypass, vein only; 4 coronary venous grafts | \
    33514: Coronary artery bypass, vein only; 5 coronary venous grafts | \
    33516: Coronary artery bypass, vein only; 6 or more coronary venous grafts
    33517: Coronary artery bypass, using venous graft(s) and arterial graft(s); single vein graft (List separately in addition to code for primary procedure) | \
    33518: Coronary artery bypass, using venous graft(s) and arterial graft(s); 2 venous grafts (List separately in addition to code for primary procedure) | \
    33519: Coronary artery bypass, using venous graft(s) and arterial graft(s); 3 venous grafts (List separately in addition to code for primary procedure) | \
    33521: Coronary artery bypass, using venous graft(s) and arterial graft(s); 4 venous grafts (List separately in addition to code for primary procedure) | \
    33522: Coronary artery bypass, using venous graft(s) and arterial graft(s); 5 venous grafts (List separately in addition to code for primary procedure) | \
    33523: Coronary artery bypass, using venous graft(s) and arterial graft(s); 6 or more venous grafts (List separately in addition to code for primary procedure)
    """
    candidate_coronary_bypass2 =     """    
    33533: Coronary artery bypass, using arterial graft(s); single arterial graft | \
    33534: Coronary artery bypass, using arterial graft(s); 2 coronary arterial grafts | \
    33535: Coronary artery bypass, using arterial graft(s); 3 coronary arterial grafts | \
    33536: Coronary artery bypass, using arterial graft(s); 4 or more coronary arterial grafts | \
    33517: Coronary artery bypass, using venous graft(s) and arterial graft(s); single vein graft (List separately in addition to code for primary procedure) | \
    33518: Coronary artery bypass, using venous graft(s) and arterial graft(s); 2 venous grafts (List separately in addition to code for primary procedure) | \
    33519: Coronary artery bypass, using venous graft(s) and arterial graft(s); 3 venous grafts (List separately in addition to code for primary procedure) | \
    33521: Coronary artery bypass, using venous graft(s) and arterial graft(s); 4 venous grafts (List separately in addition to code for primary procedure) | \
    33522: Coronary artery bypass, using venous graft(s) and arterial graft(s); 5 venous grafts (List separately in addition to code for primary procedure) | \
    33523: Coronary artery bypass, using venous graft(s) and arterial graft(s); 6 or more venous grafts (List separately in addition to code for primary procedure)
    """
    candidate_partialexcision =    """
    22100: Partial excision of posterior vertebral component (eg, spinous process, lamina or facet) for intrinsic bony lesion, single vertebral segment; cervical | \
    22101: Partial excision of posterior vertebral component (eg, spinous process, lamina or facet) for intrinsic bony lesion, single vertebral segment; thoracic | \
    22102: Partial excision of posterior vertebral component (eg, spinous process, lamina or facet) for intrinsic bony lesion, single vertebral segment; lumbar | \
    22103: Partial excision of posterior vertebral component (eg, spinous process, lamina or facet) for intrinsic bony lesion, single vertebral segment; each additional segment (List separately in addition to code for primary procedure) | \
    22110: Partial excision of vertebral body, for intrinsic bony lesion, without decompression of spinal cord or nerve root(s), single vertebral segment; cervical | \
    22112: Partial excision of vertebral body, for intrinsic bony lesion, without decompression of spinal cord or nerve root(s), single vertebral segment; thoracic | \
    22114: Partial excision of vertebral body, for intrinsic bony lesion, without decompression of spinal cord or nerve root(s), single vertebral segment; lumbar | \
    22116: Partial excision of vertebral body, for intrinsic bony lesion, without decompression of spinal cord or nerve root(s), single vertebral segment; each additional vertebral segment (List separately in addition to code for primary procedure)
    """
    candidate_shavingbiopsy =     """
    11300: Shaving of epidermal or dermal lesion, single lesion, trunk, arms or legs; lesion diameter 0.5 cm or less | \
    11301: Shaving of epidermal or dermal lesion, single lesion, trunk, arms or legs; lesion diameter 0.6 to 1.0 cm | \
    11302: Shaving of epidermal or dermal lesion, single lesion, trunk, arms or legs; lesion diameter 1.1 to 2.0 cm | \
    11303: Shaving of epidermal or dermal lesion, single lesion, trunk, arms or legs; lesion diameter over 2.0 cm | \
    11305: Shaving of epidermal or dermal lesion, single lesion, scalp, neck, hands, feet, genitalia; lesion diameter 0.5 cm or less | \
    11306: Shaving of epidermal or dermal lesion, single lesion, scalp, neck, hands, feet, genitalia; lesion diameter 0.6 to 1.0 cm | \
    11307: Shaving of epidermal or dermal lesion, single lesion, scalp, neck, hands, feet, genitalia; lesion diameter 1.1 to 2.0 cm | \
    11308: Shaving of epidermal or dermal lesion, single lesion, scalp, neck, hands, feet, genitalia; lesion diameter over 2.0 cm
    """
    candidate_destruction =     """
    17000: Destruction (eg, laser surgery, electrosurgery, cryosurgery, chemosurgery, surgical curettement), premalignant lesions (eg, actinic keratoses); first lesion | \
    17003: Destruction (eg, laser surgery, electrosurgery, cryosurgery, chemosurgery, surgical curettement), premalignant lesions (eg, actinic keratoses); second through 14 lesions, each (List separately in addition to code for first lesion) | \
    17004: Destruction (eg, laser surgery, electrosurgery, cryosurgery, chemosurgery, surgical curettement), premalignant lesions (eg, actinic keratoses), 15 or more lesions | \
    17106: Destruction of cutaneous vascular proliferative lesions (eg, laser technique); less than 10 sq cm | \
    17107: Destruction of cutaneous vascular proliferative lesions (eg, laser technique); 10.0 to 50.0 sq cm | \
    17108: Destruction of cutaneous vascular proliferative lesions (eg, laser technique); over 50.0 sq cm | \
    17110: Destruction (eg, laser surgery, electrosurgery, cryosurgery, chemosurgery, surgical curettement), of benign lesions other than skin tags or cutaneous vascular proliferative lesions; up to 14 lesions | \
    17111: Destruction (eg, laser surgery, electrosurgery, cryosurgery, chemosurgery, surgical curettement), of benign lesions other than skin tags or cutaneous vascular proliferative lesions; 15 or more lesions
    """
    candidate_paring_kyphectomy_tethering =    """
    11055: Paring or cutting of benign hyperkeratotic lesion (eg, corn or callus); single lesion | \
    11056: Paring or cutting of benign hyperkeratotic lesion (eg, corn or callus); 2 to 4 lesions | \
    11057: Paring or cutting of benign hyperkeratotic lesion (eg, corn or callus); more than 4 lesions | \
    22818: Kyphectomy, circumferential exposure of spine and resection of vertebral segment(s) (including body and posterior elements); single or 2 segments | \
    22819: Kyphectomy, circumferential exposure of spine and resection of vertebral segment(s) (including body and posterior elements); 3 or more segments | \    
    22836: Anterior thoracic vertebral body tethering, including thoracoscopy, when performed; up to 7 vertebral segments | \
    22837: Anterior thoracic vertebral body tethering, including thoracoscopy, when performed; 8 or more vertebral segments
    """
    candidate_arthrodesis = """
    22800: Arthrodesis, posterior, for spinal deformity, with or without cast; up to 6 vertebral segments | \
    22802: Arthrodesis, posterior, for spinal deformity, with or without cast; 7 to 12 vertebral segments | \
    22804: Arthrodesis, posterior, for spinal deformity, with or without cast; 13 or more vertebral segments | \
    22808: Arthrodesis, anterior, for spinal deformity, with or without cast; 2 to 3 vertebral segments | \
    22810: Arthrodesis, anterior, for spinal deformity, with or without cast; 4 to 7 vertebral segments | \
    22812: Arthrodesis, anterior, for spinal deformity, with or without cast; 8 or more vertebral segments
    """
    candidate_heartcatheter1 =  """
    36560: Insertion of tunneled centrally inserted central venous access device, with subcutaneous port; younger than 5 years of age | \
    36561: Insertion of tunneled centrally inserted central venous access device, with subcutaneous port; age 5 years or older | \
    36565: Insertion of tunneled centrally inserted central venous access device, requiring 2 catheters via 2 separate venous access sites; without subcutaneous port or pump (eg, Tesio type catheter) | \
    36566: Insertion of tunneled centrally inserted central venous access device, requiring 2 catheters via 2 separate venous access sites; with subcutaneous port(s)|\
    """
    candidate_heartcatheter1 =  """
    36568: Insertion of peripherally inserted central venous catheter (PICC), without subcutaneous port or pump, without imaging guidance; younger than 5 years of age | \
    36569: Insertion of peripherally inserted central venous catheter (PICC), without subcutaneous port or pump, without imaging guidance; age 5 years or older | \
    36570: Insertion of peripherally inserted central venous access device, with subcutaneous port; younger than 5 years of age | \
    36571: Insertion of peripherally inserted central venous access device, with subcutaneous port; age 5 years or older | \
    36572: Insertion of peripherally inserted central venous catheter (PICC), without subcutaneous port or pump, including all imaging guidance, image documentation, and all associated radiological supervision and interpretation required to perform the insertion; younger than 5 years of age | \
    36573: Insertion of peripherally inserted central venous catheter (PICC), without subcutaneous port or pump, including all imaging guidance, image documentation, and all associated radiological supervision and interpretation required to perform the insertion; age 5 years or older | \
    36575: Repair of tunneled or non-tunneled central venous access catheter, without subcutaneous port or pump, central or peripheral insertion site
    """
    candidate_radicalresection =  """
    21935: Radical resection of tumor (eg, sarcoma), soft tissue of back or flank; less than 5 cm | \
    21936: Radical resection of tumor (eg, sarcoma), soft tissue of back or flank; 5 cm or greater | \
    23077: Radical resection of tumor (eg, sarcoma), soft tissue of shoulder area; less than 5 cm | \
    23078: Radical resection of tumor (eg, sarcoma), soft tissue of shoulder area; 5 cm or greater | \   
    24077: Radical resection of tumor (eg, sarcoma), soft tissue of upper arm or elbow area; less than 5 cm | \
    24079: Radical resection of tumor (eg, sarcoma), soft tissue of upper arm or elbow area; 5 cm or greater
    """
    candidate_lacerationrepair_litholapaxy =    """
    52317: Litholapaxy: crushing or fragmentation of calculus by any means in bladder and removal of fragments; simple or small (less than 2.5 cm) | \
    52318: Litholapaxy: crushing or fragmentation of calculus by any means in bladder and removal of fragments; complicated or large (over 2.5 cm) | \
    41250: Repair of laceration 2.5 cm or less; floor of mouth and/or anterior two-thirds of tongue | \
    41251: Repair of laceration 2.5 cm or less; posterior one-third of tongue | \
    41252: Repair of laceration of tongue, floor of mouth, over 2.6 cm or complex | \
    42180: Repair, laceration of palate; up to 2 cm | \
    42182: Repair, laceration of palate; over 2 cm or complex
    """
    list_of_activities = [candidate_skintags, candidate_complexrepair, candidate_tatooing,
                          candidate_osteotomy, candidate_injection, candidate_placement,
                          candidate_biopsy, candidate_graft1, candidate_graft2,
                          candidate_adjacent_tissue_transfer, candidate_coronary_bypass1,
                          candidate_coronary_bypass2, candidate_partialexcision, candidate_shavingbiopsy,
                          candidate_destruction, candidate_paring_kyphectomy_tethering,candidate_arthrodesis,
                          candidate_heartcatheter1, candidate_heartcatheter1, candidate_radicalresection,
                           candidate_lacerationrepair_litholapaxy]
    # print((len(list_of_activities)))
    final_addon_codes = []
    def process_candidate(candidate):
            """Wrapper to call getaddon safely."""
            try:
                response = getaddon(candidate, chart)
                if response and "NOT_NEEDED" not in response:
                    return [x.strip() for x in response.split(",")]
            except Exception as e:
                print(f"Error processing candidate: {e}")
            return []
    
    # Using ThreadPoolExecutor to run in parallel
    with ThreadPoolExecutor(max_workers=len(list_of_activities)) as executor:
        futures = [executor.submit(process_candidate, candidate) for candidate in list_of_activities]
        for future in as_completed(futures):
            result = future.result()
            if result:
                final_addon_codes.extend(result)
    return final_addon_codes



def process_chart_CPT_addon(chart_text,modelcode2,DFA):
    # print("Finding addon")
    final_addon_list = [] # We will store all the final list of addon codes here
    cpt_list = []; desc_list = []; candidates = []
    prefix = modelcode2[:3] # "113"
    subdf = DFA[DFA["CPT"].astype(str).str.startswith(prefix)] # DF
    cpt_list = subdf["CPT"].tolist(); 
    desc_list = subdf["Full Description"].tolist()
    if cpt_list:
        for tmp_cpt2, tmp_desc2 in zip(cpt_list,desc_list):
            joined_stat = tmp_cpt2 + ": " + tmp_desc2;  # 11300: Shaving asdfldj
            joined_stat =joined_stat.replace(";"," "); 
            candidates.append(joined_stat) # Example: ["11300:sadasd","14240:akjdhash"]
    if candidates: 
        candidates = "|".join(candidates)  # # Example: "11300:sadasd|14240:akjdhash"
        client = OpenAI(base_url="http://localhost:8000/v1",api_key="EMPTY")
        first_prompt = "You are an expert medical coder"
        second_prompt = """
        Your task is to choose the suitable CPT code(s) for the given text chart from among the given candidate.
        Rules:
        1. The candidate is arranged in the format <CPT>:<Full description>|<CPT>:<Full description>. Two candidates are separated by pipe (|), and there may be only one candidate also.
        2. See whether any of the candidate CPT can be billed by finding relevant context from the given text chart.
        3. These candidate are CPT addon codes and may be reported / repeated / billed n-times.
        4. Note that this addon code's primary code was already reported so your task is to simply check if it can be billed further or not.
        5. Do not give any other code beyond the given candidate CPT codes.
        6. Only give the CPT code strictly separated by comma (,).
        7. If you do not find any CPT code as necessary, just write "NOT_NEEDED" strictly.
        8. Finally, do not give me any explanation.
        The chart text is:
        """
        candidates = candidates.replace(",","").replace("\u202f", " ").replace("/", " ")
        prompt = second_prompt + "\n" + chart_text + "\n\n\n" + "The list of candidates are: " + candidates
        try:
            response = client.responses.create(model= "openai/gpt-oss-120b",
                                               instructions=first_prompt,
                                               input=prompt,reasoning={"effort": "medium"},temperature=0.0, max_output_tokens=20000)
            response = response.output_text
            if "NOT_NEEDED" in response:
                pass  # Just for reference and understanding
            else:
                llm_addons = response.split(",")
                final_addon_list = final_addon_list + llm_addons # Combine it together
        except:
            response =" "; print("Model did not generate")    
    else: 
        response = " "

    return final_addon_list

from sentence_transformers import SentenceTransformer, util
def choose_final(CPT_stats, Model_CPTs_raw, Model_CPTs_FT, DL_CPTs_raw, DL_CPTs_FT, DFP,chart_text,model_loader,ftmod):
    CPT_stats_split = CPT_stats.split("\n") # list format []
    Model_CPTs_raw_split = [item.strip() for item in Model_CPTs_raw.split(",")] # List 1
    Model_CPTs_FT_split = [item.strip() for item in Model_CPTs_FT.split(",")] # List 1
    DL_CPTs_raw_split = [item.strip() for item in DL_CPTs_raw.split(",")] # List 1
    DL_CPTs_FT_split = [item.strip() for item in DL_CPTs_FT.split(",")] # List 1

    DFP["CPT"] = DFP["CPT"].astype(str) # First convert to string properly
    
    final_statements=[]; final_model_CPT = []; score_list = []
    final_matching_not_matching = []; final_GOOD_BAD_SentTransformer = []; final_GOOD_BAD_LLM = [];

    ### First Finalize the perfect CPT codes
    for i in range(len(CPT_stats_split)):
        tmp_stat = CPT_stats_split[i]  # Statement to be tested
        tmp_Model_CPTs_raw_split = Model_CPTs_raw_split[i]
        tmp_Model_CPTs_FT_split = Model_CPTs_FT_split[i]
        tmp_DL_CPTs_raw_split = DL_CPTs_raw_split[i]
        tmp_DL_CPTs_FT_split = DL_CPTs_FT_split[i]

        candidates_lst = []
        df_match_tmp_Model_CPTs_raw_split = DFP[DFP["CPT"] == tmp_Model_CPTs_raw_split]
        if not df_match_tmp_Model_CPTs_raw_split.empty:
            for tmp_i in range(len(df_match_tmp_Model_CPTs_raw_split)):
                row_tmp_Model_CPTs_raw_split = df_match_tmp_Model_CPTs_raw_split.iloc[tmp_i]
                candidate_string1 = f"{row_tmp_Model_CPTs_raw_split['CPT']} : {row_tmp_Model_CPTs_raw_split['Full Description']}"
                candidates_lst.append(candidate_string1)    
            ## To choose the top as the candidate follow the following
            # row_tmp_Model_CPTs_raw_split = df_match_tmp_Model_CPTs_raw_split.iloc[0]
            # candidate_string1 = f"{row_tmp_Model_CPTs_raw_split['CPT']} : {row_tmp_Model_CPTs_raw_split['Full Description']}"
            # candidates_lst.append(candidate_string1)

        
        df_match_tmp_Model_CPTs_FT_split = DFP[DFP["CPT"] == tmp_Model_CPTs_FT_split]
        if not df_match_tmp_Model_CPTs_FT_split.empty:
            for tmp_i2 in range(len(df_match_tmp_Model_CPTs_FT_split)):
                row_tmp_Model_CPTs_FT_split = df_match_tmp_Model_CPTs_FT_split.iloc[tmp_i2]
                candidate_string2 = f"{row_tmp_Model_CPTs_FT_split['CPT']} : {row_tmp_Model_CPTs_FT_split['Full Description']}"
                candidates_lst.append(candidate_string2)
        
        # df_match_tmp_DL_CPTs_raw_split = DFP[DFP["CPT"] == tmp_DL_CPTs_raw_split]
        # if not df_match_tmp_DL_CPTs_raw_split.empty:
        #     row_tmp_DL_CPTs_raw_split = df_match_tmp_DL_CPTs_raw_split.iloc[0]
        #     candidate_string3 = f"{row_tmp_DL_CPTs_raw_split['CPT']} : {row_tmp_DL_CPTs_raw_split['Full Description']}"
        #     candidates_lst.append(candidate_string3)

        
        df_match_tmp_DL_CPTs_FT_split = DFP[DFP["CPT"] == tmp_DL_CPTs_FT_split]
        if not df_match_tmp_DL_CPTs_FT_split.empty:
            for tmp_i4 in range(len(df_match_tmp_DL_CPTs_FT_split)):
                row_tmp_DL_CPTs_FT_split = df_match_tmp_DL_CPTs_FT_split.iloc[tmp_i4]
                candidate_string4 = f"{row_tmp_DL_CPTs_FT_split['CPT']} : {row_tmp_DL_CPTs_FT_split['Full Description']}"
                candidates_lst.append(candidate_string4)

        candidates_lst = list(set(candidates_lst))
        candidates_lst_joined = "|".join(candidates_lst)
    
        client = OpenAI(base_url="http://localhost:8000/v1",api_key="EMPTY")
        first_prompt = "You are an expert medical coder"
        second_prompt = """
        Your task is to choose and give me the best suitable CPT code(s) for the given test procedure statement from among the given candidate(s).
        Rules:
        1. The candidate is arranged in the format <CPT>:<Full description>|<CPT>:<Full description>. Two candidates are separated by pipe (|), and there may be only one candidate also.
        2. Choose the best applicable CPT from among these candidates that can be used for billing perfectly.
        3. Do not give any other code beyond the given candidate CPT codes.
        4. Give only the CPT code <CPT>. Do not give me the description.
        4. Finally, do not give me any explanation.
        The test procedure statement is:
        """
        prompt = second_prompt + "\n" + tmp_stat + "\n\n\n" + "The list of candidates are: " + candidates_lst_joined
        try:
            response = client.responses.create(model= "openai/gpt-oss-120b",
                                               instructions=first_prompt,
                                               input=prompt,reasoning={"effort": "medium"},temperature=0.0, max_output_tokens=20000)
            response = response.output_text
            final_statements.append(tmp_stat)
            final_model_CPT.append(response)
        except: pass

    ## Second determine matching or notmatching, Good/Bad
    for i in range(len(CPT_stats_split)):
        tmp_stat = CPT_stats_split[i]  # Statement to be tested
        tmp_modelcodee = final_model_CPT[i] # Chosen Model CPT Code
        tmp_dlcodee = DL_CPTs_FT_split[i] # DL Code
        if tmp_modelcodee.strip() in tmp_dlcodee.strip(): final_matching_not_matching.append("MATCHED")
        else: final_matching_not_matching.append("NOT MATCHING")
        
        df_match_tmp_modelcodee = DFP[DFP["CPT"] == tmp_modelcodee]
        if not df_match_tmp_modelcodee.empty:
            row_tmp_modelcodee = df_match_tmp_modelcodee.iloc[0]
            fd_statement_modelcode = row_tmp_modelcodee['Full Description']
            ### Apply Sentence Transformer that does vector matching
            emb1 = ftmod.encode(tmp_stat, convert_to_tensor=True, normalize_embeddings=True)
            emb2 = ftmod.encode(fd_statement_modelcode, convert_to_tensor=True, normalize_embeddings=True)
            score = util.cos_sim(emb1, emb2).item(); score = round(score,2)
            score_list.append(str(score))
            if score >= 0.8: 
                final_GOOD_BAD_SentTransformer.append("GOOD")
            else: 
                final_GOOD_BAD_SentTransformer.append("BAD")
            
            ### Apply LLM Matching that does contextual matching
            result_code = tmp_modelcodee + ": " + fd_statement_modelcode
            
            client = OpenAI(base_url="http://localhost:8000/v1",api_key="EMPTY")
            first_prompt = "You are an expert medical coder"
            second_prompt = """
            Check whether the given CPT code is suitable for the given test procedure statement.
            Rules:
            1. If applicable strictly write as "GOOD SUITABLE", otherwise write "BAD NOT SUITABLE".
            2. Finally, do not give me any explanation. Do not give CPT code or the description.
            The test procedure statement is:
            """
            prompt = second_prompt + "\n" + tmp_stat + "\n\n\n" + "The CPT code is: " + result_code
            try:
                response = client.responses.create(model= "openai/gpt-oss-120b",
                                                   instructions=first_prompt,
                                                   input=prompt,reasoning={"effort": "medium"},temperature=0.0, max_output_tokens=20000)
                response = response.output_text
                # response = "FUNCTIONALITY SUSPENDED CURRENTLY"
                if "GOOD" in response: final_GOOD_BAD_LLM.append("GOOD")
                elif "BAD" in response: final_GOOD_BAD_LLM.append("BAD")
                else: final_GOOD_BAD_LLM.append("FUNCTIONALITY SUSPENDED CURRENTLY")
            except:
                final_GOOD_BAD_LLM.append("BAD")
        else:
            score_list.append("CODE NOT FOUND")
            final_GOOD_BAD_SentTransformer.append("CODE NOT FOUND")
            final_GOOD_BAD_LLM.append("CODE NOT FOUND")

    ###### Final operation before writing
    if final_statements:
        final_statements_str = "\n".join(final_statements)
        final_model_CPT_str = ",".join(final_model_CPT)
        score_list_str = ",".join(score_list)
        final_matching_not_matching_str  = ",".join(final_matching_not_matching)
        final_GOOD_BAD_SentTransformer_str =  ",".join(final_GOOD_BAD_SentTransformer)
        final_GOOD_BAD_LLM_str =  ",".join(final_GOOD_BAD_LLM)        
    else:
        final_statements_str = "";   final_model_CPT_str = ""; score_list_str =""  ;final_matching_not_matching_str = "";final_GOOD_BAD_SentTransformer_str = ""; final_GOOD_BAD_LLM_str = ""
    return final_statements_str, final_model_CPT_str, score_list_str, final_matching_not_matching_str, final_GOOD_BAD_SentTransformer_str, final_GOOD_BAD_LLM_str

def choose_final2(CPT_stats, Model_CPTs_FT, DL_CPTs_FT, DFP,chart_text,model_loader,ftmod):
    CPT_stats_split = CPT_stats.split("\n") # list format []
    Model_CPTs_FT_split = [item.strip() for item in Model_CPTs_FT.split(",")] # List 1
    DL_CPTs_FT_split = [item.strip() for item in DL_CPTs_FT.split(",")] # List 2

    DFP["CPT"] = DFP["CPT"].astype(str) # First convert to string properly
    
    final_matching_not_matching = []

    ## Second determine matching or notmatching
    # print("len(CPT_stats_split)", len(CPT_stats_split), CPT_stats)
    # print("len(Model_CPTs_FT_split)", len(Model_CPTs_FT_split), Model_CPTs_FT)
    # print("len(DL_CPTs_FT_split)", len(DL_CPTs_FT_split), DL_CPTs_FT)
    
    for i in range(len(CPT_stats_split)):
        tmp_stat = CPT_stats_split[i]  # Statement to be tested
        tmp_modelcodee = Model_CPTs_FT_split[i] # Model CPT Code
        tmp_dlcodee = DL_CPTs_FT_split[i] # DL Code
        if tmp_modelcodee.strip() in tmp_dlcodee.strip(): 
            final_matching_not_matching.append("MATCHED")
        else: 
            final_matching_not_matching.append("NOT MATCHING")
        

    if final_matching_not_matching:
        final_matching_not_matching_str  = ",".join(final_matching_not_matching)
    else:
        final_matching_not_matching_str = " "

    return final_matching_not_matching_str

    
def acquire_CS_CPT_Genito(filename_without_txt,mastersummarydf):
    cs_codes = "NOT FOUND"
    if filename_without_txt in mastersummarydf['ENCOUNTER NO'].astype(str).values:
        cpt_raw = mastersummarydf.loc[
            mastersummarydf['ENCOUNTER NO'].astype(str) == filename_without_txt,
            'Customer CPT'].values[0]
        cpt_string = str(cpt_raw).strip()
        if cpt_string.lower() in ["nan", "", "none"]:
            filtered_cpts = []
        else:
            cpt_list = [c.strip() for c in cpt_string.split(',')]
            filtered_cpts = [c for c in cpt_list if not c.startswith(('8', '9', "1", "3", "7"))]
        if len(filtered_cpts) > 1:     cs_codes = ", ".join(filtered_cpts)
        elif len(filtered_cpts) == 1:  cs_codes = filtered_cpts[0]
        else:  cs_codes = "NOT FOUND"
    return cs_codes


def acquire_CS_CPT_Gastro(filename_without_txt,mastersummarydf):
    cs_codes = "NOT FOUND"
    if filename_without_txt in mastersummarydf['ENCOUNTER NO'].astype(str).values:
        cpt_raw = mastersummarydf.loc[
            mastersummarydf['ENCOUNTER NO'].astype(str) == filename_without_txt,
            'Customer CPT'].values[0]
        cpt_string = str(cpt_raw).strip()
        if cpt_string.lower() in ["nan", "", "none"]:
            filtered_cpts = []
        else:
            cpt_list = [c.strip() for c in cpt_string.split(',')]
            filtered_cpts = [c for c in cpt_list if not c.startswith(('8', '9', "1", "3", "7"))]
        if len(filtered_cpts) > 1:     cs_codes = ", ".join(filtered_cpts)
        elif len(filtered_cpts) == 1:  cs_codes = filtered_cpts[0]
        else:  cs_codes = "NOT FOUND"
    return cs_codes



def extract_mainprocedure_heading(chart_text):
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
    first_prompt = "You are an expert medical coder"
    second_prompt = """
    Your Task:     Extract the main procedure statement(s) from the given medical chart text.
    Rules that you must follow strictly:
    1. Identify only the main procedure heading(s) — these are typically short, concise titles and not the long descriptive operative narratives.
    2. Most charts contain one main procedure heading; in rare cases, there may be multiple main procedure headings.    
    3. Main procedure headings may be single-word or short phrases, for example:
    **Robotic assisted Laparoscopic Cholecystectomy**, **EGD**, **Esophagogastroduodenoscopy**, **Colonoscopy**.
    4. Do not miss  XRAY statements like **PA, lateral, AP, Oblique views, 2 views of the chest** even if XRAY or XR terms are not mentioned in that statement and also add Radiological Examination in such statements.
    6. If you come across short forms write its expanded form. For instance - CT is computed tomography, CTA is computed tomography angiography, MRI is Magnetic Resonance Imaging, MRA is Magnetic Resonance Angiography.
    7. Extract the heading text exactly as it appears in the chart. Do not rephrase, expand, normalize, or interpret the text.    
    8. Paragraph headings like **Therapeutic Injections:" may be a bigger paragraph having three or more lines. Injection procedure may be performed here. Do not miss to extract them.
    9. Strictly also remember that injections or Arthrocentesis procedure statement can be found without any heading inside the chart, also pickup these procedure statements.
    9. Do not provide any explanation, commentary, or additional text.
    9. If multiple main procedure headings are present:    
        - Output each as a bullet point
        - Separate each bullet with a new line
        - Use a full stop (.) after each statement
    10. If no main procedure heading is found, output exactly:  **MAIN_PROCEDURE_NOT_FOUND**
    11. Output Format (strict):
        - Bullet points only
        - One main procedure per bullet
        - No extra text before or after the output
    The chart text is:
    """
    prompt = second_prompt + " " + chart_text
    try:
        response = client.responses.create(
            model="openai/gpt-oss-120b",instructions=first_prompt,input=prompt,reasoning={"effort": "medium"},temperature=0.0,max_output_tokens=10000)
        response = response.output_text
        response = response.replace(":"," ")
    except: response = ""
    
    return response

def improvemain_statement(extracted_main):
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
    first_prompt = "You are an expert medical coder"
    second_prompt = """
    Your task is to improve the given extracted main procedure statement as per CPT guidelines.    
    Rules to follow:
    1. Do not alter the conceptual meaning of the original procedure statement.
    2. Do not add anything that can alter the primary procedure.
    3. Do not add any new subprocedure or any other part.
    4. Your role is to make the main procedure statement more similar or translated simplified to CPT guidelines descriptions.
    5. Do NOT invent undocumented details.
    6. Output only the improved single-line procedure statement. Do not explain anything.    
    The statement to improve is:
    """
    prompt = second_prompt + extracted_main
    try:
        response = client.responses.create(
            model="openai/gpt-oss-120b",instructions=first_prompt,input=prompt,reasoning={"effort": "medium"},temperature=0.0,max_output_tokens=20000)
        response = response.output_text
    except:
        response = ""

    return response

def say_good_bad(DFP, tmp_CPT_code, tmp_statement, chart_text):
    df_matchd = DFP[DFP["CPT"] == tmp_CPT_code]
    
    matched_cpts_fds = [
        f"{tmp_CPT_code}: {fd}"
        for fd in df_matchd["Full Description"]]

    good_bad_decision = "BAD"
    if matched_cpts_fds:
        for tmp_candidate in matched_cpts_fds:
            client = OpenAI(base_url="http://localhost:8000/v1",api_key="EMPTY")
            first_prompt = "You are an expert medical coder"
            second_prompt = """
            Check whether the given CPT code is suitable for billing for the given test procedure statement.
            Rules:
            1. If applicable, strictly write as "GOOD SUITABLE", otherwise write "BAD NOT SUITABLE".
            2. Finally, do not give me any explanation. Do not give CPT code or the description.
            3. Judge suitability STRICTLY using chart documentation. 
            4. If documentation does NOT fully support the CPT description, answer BAD NOT SUITABLE.
            The test procedure statement is:
            """
            prompt = second_prompt + "\n" + tmp_statement + "\n\n\n" + "The CPT code is: " + tmp_candidate + "\n\n\n" + "The chart text is : " + chart_text
            try:
                response = client.responses.create(model= "openai/gpt-oss-120b",
                                                   instructions=first_prompt,
                                                   input=prompt,reasoning={"effort": "medium"},temperature=0.0, max_output_tokens=10000)
                response = response.output_text
                if "GOOD" in response: 
                    good_bad_decision = "GOOD"
                    break
            except:
                pass

    return good_bad_decision

def extract_mainprocedures(extracted_main):
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
    first_prompt = "You are an expert medical coder"
    second_prompt = """
    Your task is to only the extracted main procedure not the subordinate as per CPT guidelines from the given statement.    
    Rules to follow:
    1. I need the main procedure short phrase or keywords that is performed separately even if they are written in the same statement.
    2. I do not need other components like laterality, level, depth, quantity, or the subordinate procedures in each main procedure.
    3. If you find multiple main procedures that are performed separately strictly give in bullet separated format of new line.
    4. Do NOT invent undocumented details.
    5. Do NOT explain anything.
    The statement is:
    """
    prompt = second_prompt + extracted_main
    try:
        response = client.responses.create(
            model="openai/gpt-oss-120b",instructions=first_prompt,input=prompt,reasoning={"effort": "medium"},temperature=0.0,max_output_tokens=20000)
        response = response.output_text        
    except:
        response = ""
    return response


def find_present_mainprocedures(extracted_main, all_trees_unique):
    filtered = list(filter(None, all_trees_unique))
    text = extracted_main.lower()
    present_mainprocs_list = []
    for term in filtered:
        t = term.lower()
        pattern = r"\b" + re.escape(t) + r"\b"
        if re.search(pattern, text):
            present_mainprocs_list.append(term)
    return present_mainprocs_list

def search_presence(the_options, extracted_main, chart_text):
    if not the_options:
        return ""
    the_options_str = " | ".join(the_options)
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
    system_prompt = "You are an expert medical coder. Only output valid, factual results."
    user_prompt = f"""
    Your task is to select and return ONLY the relevant options from the given list, based on the MAIN PROCEDURE STATEMENT and the CHART TEXT.
    STRICT RULES:
    - You MUST ONLY return values that exist in the provided options list.
    - Return values MUST be exact/verbatim as listed.
    - If you infer quantity, context, or conditions, ensure they match the medical logic described in the chart.
    - DO NOT invent, rewrite, paraphrase, or modify any option.
    - If multiple items apply, join them using a single pipe (|) with NO spaces.
    - If none apply, return EXACTLY: NONE FOUND
    - Do not explain or add commentary.

    Options List:
    {the_options_str}

    Main Heading:
    {extracted_main}

    Chart:
    {chart_text}
    """

    try:
        response = client.responses.create(
            model="openai/gpt-oss-120b",
            instructions=system_prompt,
            input=user_prompt,
            reasoning={"effort": "medium"},
            temperature=0,
            max_output_tokens=2000
        )
        response = response.output_text.strip()
        response = re.sub(r'\s*\|\s*', '|', response)
        return response
    except Exception as e:
        return ""

  
def fetch_tree_parts_matched(matched_df,extracted_main,chart_text):
    """ Acquire parts for the tree rows where main proc is present """
    """ Create a JSON structure of all the tree components using LLM """
    other_procedures_list = list(set(matched_df["Other Procedures"].tolist())) 
    other_procedures_list = "|".join(other_procedures_list);   other_procedures_list = other_procedures_list.split("|")
    other_procedures_list = list(set(other_procedures_list))
    other_procs = search_presence(other_procedures_list,extracted_main,chart_text) # | separated
    
    body_parts_list = list(set(matched_df["Body Parts"].tolist())) 
    body_parts_list = "|".join(body_parts_list);   body_parts_list = body_parts_list.split("|")
    body_parts_list = list(set(body_parts_list))
    body_parts = search_presence(body_parts_list,extracted_main,chart_text) # | separated

    laterality_list = list(set(matched_df["laterality"].tolist())) 
    laterality_list = "|".join(laterality_list);   laterality_list = laterality_list.split("|")
    laterality_list = list(set(laterality_list))
    laterali = search_presence(laterality_list,extracted_main,chart_text) # | separated

    medical_list = list(set(matched_df["Medical Condition"].tolist())) 
    medical_list = "|".join(medical_list);   medical_list = medical_list.split("|")
    medical_list = list(set(medical_list))   
    medicals = search_presence(medical_list,extracted_main,chart_text) # | separated

    withwithout_list = list(set(matched_df["With_Without_For"].tolist())) 
    withwithout_list = "|".join(withwithout_list);   withwithout_list = withwithout_list.split("|")
    withwithout_list = list(set(withwithout_list))
    withwithout = search_presence(withwithout_list,extracted_main,chart_text) # | separated

    spectypestage_list = list(set(matched_df["Specificity_Type_Stage"].tolist())) 
    spectypestage_list = "|".join(spectypestage_list);   spectypestage_list = spectypestage_list.split("|")
    spectypestage_list = list(set(spectypestage_list))
    spectypestage = search_presence(spectypestage_list,extracted_main,chart_text) # | separated
    
    quantity_list = list(set(matched_df["Quantity"].tolist())) 
    quantity_list = "|".join(quantity_list);   quantity_list = quantity_list.split("|")
    quantity_list = list(set(quantity_list))
    quantity = search_presence(quantity_list,extracted_main,chart_text) # | separated
    
    depth_list = list(set(matched_df["Depth"].tolist())) 
    depth_list = "|".join(depth_list);   depth_list = depth_list.split("|")
    depth_list = list(set(depth_list))    
    depth = search_presence(depth_list,extracted_main,chart_text) # | separated

    meddevice_list = list(set(matched_df["Medical Device"].tolist())) 
    meddevice_list = "|".join(meddevice_list);   meddevice_list = meddevice_list.split("|")
    meddevice_list = list(set(meddevice_list))
    meddevice = search_presence(meddevice_list,extracted_main,chart_text) # | separated

    drugcontrast_list = list(set(matched_df["Drug_Contrast_Injection"].tolist())) 
    drugcontrast_list = "|".join(drugcontrast_list);   drugcontrast_list = drugcontrast_list.split("|")
    drugcontrast_list = list(set(drugcontrast_list))    
    drugcontrast = search_presence(drugcontrast_list,extracted_main,chart_text) # | separated

    compart_list = list(set(matched_df["Complete_Partial_Limited"].tolist())) 
    compart_list = "|".join(compart_list);   compart_list = compart_list.split("|")
    compart_list = list(set(compart_list))
    compart = search_presence(compart_list,extracted_main,chart_text) # | separated

    guidance_list = list(set(matched_df["Guidance"].tolist())) 
    guidance_list = "|".join(guidance_list);   guidance_list = guidance_list.split("|")
    guidance_list = list(set(guidance_list))
    guidance = search_presence(guidance_list,extracted_main,chart_text) # | separated

    view_list = list(set(matched_df["View"].tolist())) 
    view_list = "|".join(view_list);   view_list = view_list.split("|")
    view_list = list(set(view_list))
    views = search_presence(view_list,extracted_main,chart_text) # | separated

    age_list = list(set(matched_df["Age"].tolist())) 
    age_list = "|".join(age_list);   age_list = age_list.split("|")
    age_list = list(set(age_list))
    age = search_presence(age_list,extracted_main,chart_text) # | separated

    gender_list = list(set(matched_df["Gender"].tolist())) 
    gender_list = "|".join(gender_list);   gender_list = gender_list.split("|")
    gender_list = list(set(gender_list))    
    gender = search_presence(gender_list,extracted_main,chart_text) # | separated

    return other_procs, body_parts, laterali, medicals, withwithout, spectypestage, quantity, depth, meddevice, drugcontrast, compart, guidance, views, age, gender

def frame_statement_and_code(chart_text, extracted_main, tmp_candidates_joined, model_loader):
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
    system_prompt = "You are an expert medical coder. Only output valid, factual results."
    user_prompt = f"""
    Your task is to select and return ONLY the relevant options from the given list, based on the MAIN PROCEDURE STATEMENT and the CHART TEXT.
    Your task is to select and return ONLY the best suited code from the given candidate which is given in pipe (|) separated format.
    STRICT RULES:
    - You must choose and give one best suited CPT code and its full description statement.
    - If you find quantity, context, or conditions, ensure they match the medical logic described in the chart.
    - Your judgement must be based on the main heading statement and the chart text.
    - You must give in the form <CPT>:<Full Description> in your response with colon (:) separation as shown here.
    - If none apply, return EXACTLY: NONE FOUND
    - Do not explain or add commentary.
    - DO NOT invent, rewrite, paraphrase, or modify any option.

    The candidate options are:
    {tmp_candidates_joined}

    Main Heading:
    {extracted_main}

    Chart:
    {chart_text}
    """

    try:
        response = client.responses.create(
            model="openai/gpt-oss-120b",
            instructions=system_prompt,
            input=user_prompt,
            reasoning={"effort": "medium"},
            temperature=0,
            max_output_tokens=10000)
        response = response.output_text.strip()
        try:
            tree_code, tree_statement = response.split(":")
            tree_DL,_,_ = DL_testing_CPT(tree_statement, model_loader)
        except:
            tree_code=""; tree_statement =""; tree_DL=""

    except Exception as e:
        tree_code=""; tree_statement =""; tree_DL=""    
    
    return tree_code, tree_statement, tree_DL

def tree_method(chart_text, extracted_main, main_procedures, all_trees_unique, tree_df_p):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from openai import OpenAI
    import pandas as pd
    import re
    present_mainprocs_list = find_present_mainprocedures(extracted_main, all_trees_unique)

    tree_code_list = []; tree_statement_list = []; tree_DL_list = []
    matched_rows = []
    
    for tmp_main in present_mainprocs_list:
        filtered_df = tree_df_p[
            tree_df_p["Main Procedure"]
            .str.contains(fr'(^|\|){re.escape(tmp_main)}(\||$)',
                          case=False, na=False)]
        if not filtered_df.empty:
            matched_rows.append(filtered_df.drop_duplicates())
    
    if matched_rows:
        final_filtered_df = pd.concat(matched_rows, ignore_index=True).drop_duplicates()
    
        (other_procs, body_parts, laterali, medicals, withwithout,
         spectypestage, quantity, depth, meddevice, drugcontrast,
         compart, guidance, views, age, gender) = fetch_tree_parts_matched(final_filtered_df, extracted_main, chart_text)
        tree_extracts = {"present_mainprocs_list": present_mainprocs_list, "matched_df": filtered_df,
                 "other_procedures": other_procs, "body_parts": body_parts, "laterality": laterali,
                 "medical_condition": medicals, "withwithout": withwithout, "specificity_type_stage": spectypestage,
                 "quantity": quantity, "depth": depth, "medical_device": meddevice, "drug_contrast_injection": drugcontrast,
                 "complete_partial": compart, "guidance": guidance, "views": views, "age": age, "gender": gender}
    else:
        final_filtered_df = pd.DataFrame()
        other_procs = body_parts = laterali = medicals = withwithout = ""
        spectypestage = quantity = depth = meddevice = drugcontrast = ""
        compart = guidance = views = age = gender = ""
    
    for tmp_main in present_mainprocs_list:
        filtered_df = tree_df_p[
            tree_df_p["Main Procedure"]
            .str.contains(fr'(^|\|){re.escape(tmp_main)}(\||$)', case=False, na=False)]
        if not filtered_df.empty:
            filtered_df = filtered_df.drop_duplicates()
            filtered_df["cand_str"] = filtered_df["CPT"].astype(str) + ": " + filtered_df["Full Description"].astype(str)
            tmp_candidates = filtered_df["cand_str"].tolist()
            tmp_candidates_joined = "|".join(tmp_candidates)
            tree_code, tree_statement, tree_DL = frame_statement_and_code(chart_text, extracted_main, tmp_candidates_joined, model_loader)
            tree_code_list.append(tree_code) ;  tree_statement_list.append(tree_statement) ;  tree_DL_list.append(tree_DL)

    if tree_code_list:     tree_code_str = ", ".join(tree_code_list)
    else: tree_code_str = ""

    if tree_statement_list:     tree_statement_str = ", ".join(tree_statement_list)
    else: tree_statement_str = ""    
        
    if tree_DL_list:     tree_DL_str = ", ".join(tree_DL_list)
    else: tree_DL_str = ""
    
    return tree_code_str, tree_statement_str, tree_DL_str

def fetch_quanties(extracted_main, chart_text):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from openai import OpenAI
    import pandas as pd
    import re    
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
    things_to_extract = ["Number of vertebral segments", 
                         "Number of columns or groups", 
                         "Defect Length of Hernia repair or dimension of the hernia", 
                         "Weight of Uterus", 
                         "Injection level (single or multiple)", 
                         "Debridement area", 
                         "Number of benign lesions",
                         "Number of malignant lesions",
                         "Diameter of lesions",
                         "Number of nails debrided",
                         "Area of tatooing",
                         "Length of repair",
                         "Number of foot digits operated upon",
                         "Single lead / Dual Lead / Multiple Pacemaker Pulse lead generator",
                         "Number of Coronary Venous Graft",
                         "Stage of AJCC colon cancer - Stage 1, 2 or 3",
                         "Number of stab incisions",
                         "Whether one-third, two-third or half of tongue underwent biopsy/excision/glossectomy, etc.", 
                         "Number of sites of RF Ablation",
                         "Number Of Biopsy - single / multiple", 
                         "Number of tumor(s)", 
                         "1-stage or 2-stage reconstruction",
                         "No. of Intramural myomas or weight of fibroid in uterus",
                         "Skull defect size",
                         "Size of grafting",
                         "For radiology study is single contrast / barium or double contrast / high density barium with effervescent",
                         "For Brachytherapy find the number of source (example - 1,2,3, etc)",
                         "Bone density mineral contrast study - Single photon or Dual photon",
                         "Myocardial imaging - Single study / Multiple studies",
                         "Number of body regions involved for osteopathic manipulative treatment",
                         "Number of Spinal regions involved for chiropractic manipulative treatment",
                         "For radiology find the number of VIEW (example: 1 view, 2 views, etc.)",
                         "Age of the patient", 
                         "Age of infant in weeks",
                         "Number of trimester of pregnancy",
                         "Bladder tumor size in numerics",
                         "Bladder tumor size - whether large or small?"
                         "Whether early pregnancy is documented",
                         "Whether hernia is reducible, incarcerated or strangulated? If incarcerated or strangulated type not documented default is reducible",
                         "Whether heria is initial or recurrent is documented"
                        ]

    def worker(myrequired_qty, extracted_main, chart_text):
        system_prompt = "You are an expert medical coder. Only output documented values."
        user_prompt = f"""
        Extract the required quantity ONLY if applicable. 
        Rules:
        1. You are given the extracted procedure statement main heading, desired quantity type and chart text to understand it properly.
        2. Strict format: <desired_qty_name>:<value>
        3. Only output documented facts. See very carefully and give your result.
        4. Do not take history quantity, for example: history of gestational age 14 weeks 2 days.
        5. If NOT applicable for this procedure strictly write in the format <desired_qty_name>:<NOT_REQUIRED_FOR_THIS_PROCEDURE>
        6. If applicable BUT not documented strictly write in the format  <desired_qty_name>:<APPLICABLE_BUT_NONE_DOCUMENTED>
        7. Do NOT explain anything.

        Desired quantity:
        {myrequired_qty}

        Procedure statement Main Heading:
        {extracted_main}

        Chart Text:
        {chart_text}
        """

        try:
            response = client.responses.create(
                model="openai/gpt-oss-120b",
                instructions=system_prompt,
                input=user_prompt,
                reasoning={"effort": "medium"},
                temperature=0,
                max_output_tokens=5000
            )
            return response.output_text.strip()
        except Exception as e:
            return f"{myrequired_qty}: ERROR"

    results = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(worker, qty, extracted_main, chart_text) for qty in things_to_extract]
        for f in as_completed(futures):
            results.append(f.result())

    if results:
        results_str = "; ".join(results)
        parts = [p.strip() for p in results_str.split(";")]       # Filter out not applicable ones
        filtered = [p for p in parts if "NOT_REQUIRED" not in p]
        results_str = "; ".join(filtered)
    else:
        results_str = " "    
    
    return results_str

def fetch_tree_parts2(extracted_main, chart_text):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from openai import OpenAI
    
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")

    tree_columns_to_extract = [
        "the applicable sub procedure(s)",
        "whether hernia is initial or recurrent type",
        "whether hernia is incarcerated or strangulated or reducible type",
        "applicable body part(s) along its associated laterality",
        "applicable medical condition(s)",
        "applicable depth for the primary procedure",
        "applicable drug or contrast or injectate used for the primary procedure",
        "applicable radiological guidance used (example: CT, X Ray, Fluoroscopy, Ultrasound, etc.) for the primary procedure",
        "applicable medical device or instrument for the primary procedure",
        "applicable complete or partial or limited or total procedure used for the primary procedure",
        "whether radiological procedure is with contrast or without contrast for the primary procedure",
        "whether radiology study is single contrast / barium or double contrast / high density barium with effervescent for the primary procedure",
        "whether slit lamp is used",
        "whether anesthesia is applied during the primary procedure",
        "extract benign or malignant condition and the anatomical site as <benign/malignant> - <anatomical location>",
        "whether injection is for epidural or joint or tendon",
        "which is documented **WITHOUT CONTRAST WITH CONTRAST** or **WITH CONTRAST** or **WITHOUT CONTRAST** For example - **WO W contrast** is written as WITHOUT AND WITH CONTRAST",
        ]

    def worker(required_component, extracted_main, chart_text):
        system_prompt = "You are an expert medical coder. Only output documented values."

        user_prompt = f"""
        Your task is to extract ONLY the required component or terms that is documented in the chart for the required component type mentioned below.

        STRICT RULES:
        1. Extract ONLY documented facts from chart (do not invent).
        2. Correct spelling or expand abbreviation if needed.
        3. Output must be strictly comma-separated list.
        4. NO explanation or commentary.
        5. If NOT applicable strictly output:
           <required_component>:<NOT_REQUIRED_FOR_THIS_PROCEDURE>
        6. If applicable BUT not documented output:
           <required_component>:<APPLICABLE_BUT_NONE_DOCUMENTED>

        Required component:
        {required_component}

        Procedure Main Heading:
        {extracted_main}

        Chart:
        {chart_text}
        """

        try:
            resp = client.responses.create(
                model="openai/gpt-oss-120b",
                instructions=system_prompt,
                input=user_prompt,
                reasoning={"effort": "medium"},
                temperature=0,
                max_output_tokens=5000
            )
            return resp.output_text.strip()
        except Exception:
            return f"{required_component}: ERROR"

    results = []

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [
            executor.submit(worker, c, extracted_main, chart_text)
            for c in tree_columns_to_extract
        ]

        for f in as_completed(futures):
            results.append(f.result())

    if results:
        results_str = "; ".join(results)
        parts = [p.strip() for p in results_str.split(";")]
        filtered = [p for p in parts if "NOT_REQUIRED_FOR_THIS_PROCEDURE" not in p]
        results_str = "; ".join(filtered)
    else:
        results_str = " "

    return results_str


    

def fetch_tree_parts(chart_text, extracted_main):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from openai import OpenAI
    import pandas as pd
    import re
    
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
    system_prompt = "You are an expert medical coder. Only output the documented things"
    user_prompt = f"""
    Your task is to only extract the components that I have highlighted in the following **strict rules** in simple comma separated format (,).
    STRICT RULES:
    1. You must only extract the terms that are documented strictly.
    2. Look at the main procedure heading and extract the following things from the chart:
        - applicable sub procedure(s)
        - applicable body part(s) along its associated laterality.
        - applicable medical condition(s)
        - applicable depth
        - applicable drug or contrast or injectate used
        - applicable radiological guidance used (example: CT, X Ray, Fluoroscopy, Ultrasound, etc.)
        - applicable medical device
        - applicable complete or partial or limited or total procedure used.
    3. My goal is to collect the terms that can be attached to these main headings to make it fully complete as per CPT guidelines.
    4. DO NOT invent, rewrite, paraphrase but you can correct spelling or expand abbrieviation to make it proper.
    5. Extract them from the chart and put in simple comma separated format (,)
    6. No duplicacy and do not explain or add commentary.

    The procedure Main Heading is:
    {extracted_main}

    The Chart is:
    {chart_text}
    """
    try:
        response = client.responses.create(
            model="openai/gpt-oss-120b",
            instructions=system_prompt,
            input=user_prompt,
            reasoning={"effort": "medium"},
            temperature=0,
            max_output_tokens=10000)

        response = response.output_text.strip()
    except Exception as e:
        response = ""
    return response
def frame_tree_statements(extracted_main, relevant_parts, chart_text, DFP,model_loader, ftmod,ftindextra):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from openai import OpenAI
    import pandas as pd
    import re
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
    system_prompt = "You are an expert medical coder. Only output the documented things"
    user_prompt = f"""
    Your task is to construct complete CPT procedure statements. Extract only the confirmed, independently
    billable CPT procedures and list them strictly as bullet points in the format:
    
    <Procedure Statement>: <CPT Code>
    
    Do not add any explanation.
    
    STRICT RULES:
    1. Each procedure statement must be fully complete and clinically accurate, matching the CPT coding description standards.
    2. Return only unique, independently billable Genitourinary procedures that are NOT bundled under CPT rules.
    3. Apply CPT bundling rules: when multiple steps combine into a single payable CPT service, output only the final, correct consolidated CPT procedure statement.
    4. Do NOT mutate, rewrite, paraphrase, or guess procedure content. Use only documented details.
    5. Use both:
           - The procedure main heading
           - The relevant extracted parts
       to construct complete statements.
    6. Absolutely DO NOT hallucinate or assume. Only include procedures, subprocedures, guidance, devices, or clinical elements that are explicitly documented. If an element is not clearly written in the chart, it must NOT appear in the CPT statement.
    7. Do not miss to include radiology procedures ONLY if they are independently billable and documented.
    8. For Radiology texts, note that procedure titles may appear under headings like:
           TECHNIQUE:, EXAM:, EXAMS/PROCEDURES:
    9. For Hernia procedures:
       - Explicitly include details such as initial vs recurrent, reducible/incarcerated/strangulated ONLY if documented.
       - If these details are NOT documented, DO NOT infer them.
    11. If no joint or tendon found, Epidural injection considered.
    12. Add either actinic/malignant or sebborheic / benign lesion to the procedure statement if applicable and documented to make sure that the procedure on lesion is on either malignant or benign type.
    13. While making MRI statement take care of **Without Contrast With contrast** or **Without Contrast** or **With Contrast**. For example: "Magnetic Resonance Imaging knee right WO W contrast" is written as"Magnetic Resonance Imaging knee right without and with contrast". Makre sure without and with contrast is not broken up into multiple statetements.
    14. Do not miss procedure like **Nasal Endoscopy** if documented.
    15. Do not add the word complex unless explicity documented as complex
    16. If CPT guidelines allow combining multiple documented actions into one payable statement, create only that single optimized CPT statement.
    17. Each statement must map to exactly ONE CPT code.
    18. Output ONLY the bullet list. No commentary.
    
    Procedure Main Heading:
    {extracted_main}
    
    Relevant documented terms:
    {relevant_parts}
    """
    try:
        response = client.responses.create(
            model="openai/gpt-oss-120b",
            instructions=system_prompt,
            input=user_prompt,
            reasoning={"effort": "medium"},
            temperature=0,
            max_output_tokens=10000)

        response = response.output_text.strip()
        print("Frame_tree_statements_stage1",response)
        
        user_prompt = f"""
        You are a CPT compliance auditor. Your only job is to verify the correctness of the already framed
        procedure statements. Do NOT invent, expand, or create any new procedures.
        
        OUTPUT FORMAT (STRICT):
        <Procedure Statement> **PRIMARY/SECONDARY/UNBILLABLE** : <CPT Code>
        
        Do NOT add explanations.
        
        VERIFICATION RULES:
        1. Compare each framed statement ONLY against:
           - Procedure Main Heading
           - Relevant documented terms
           - Chart Text
           Your job is verification, not re-construction.
        
        2. Do NOT add any missing elements, devices, guidance, or undocumented clinical steps. If needed, only correct wording to match documentation while preserving meaning.

        3. Make sure that you do not miss to include important subprocedure that is joined by the word **WITH** if documented and applicable with the procedure. For example **with slit lamp**.
        
        4. If a statement changes the meaning, overstates, understates, or mutates from what is actually documented → Correct it and output the corrected safe version.
        
        5. Mark Billing Status:
           - **PRIMARY** → Main independently billable core CPT service
           - **SECONDARY** → Legitimately separately billable add-on or additional CPT
           - **ALREADY_BUNDLED** → A real documented procedure, but its payment is bundled into a PRIMARY or SECONDARY CPT under CPT/NCCI bundling rules
           - **UNBILLABLE** → Bundled, incidental, incomplete, undocumented, or CPT disallowed
        
        6. Strictly there must be one CPT code per statement as in the format   <Procedure Statement> **UNBILLABLE** : <CPT Code>
        Here there must not be semicolon (:) after the procedure statement. For example: ***Transurethral steam ablation of the prostate (Rezūm):**PRIMARY**: 53810*** is wrong, 
        the correct way is ***Transurethral steam ablation of the prostate (Rezūm) **PRIMARY**: 53810***. In short the semicolon (:) must be just before the CPT code.
        
        7. You can correct the CPT code for the corrected statement by replacing the previous CPT code. But strictly there must be only one CPT code per statement.

        8. Make sure that unncessary split is not done. For example: Ultrasound of Kidney and Bladder is one CPT code, otherwise if you split up like Ultrasound of Kidney, Ultrasound of Bladder then you are wrong. This is as per CPT guidelines. On the other hand statement like **Colonoscopy with submucosal injection and hot snare polypectomy of cecal polyp and cold snare polypectomy of descending colon polyp** is wrong, it must be split up.
        
        9. DO NOT drop any statements unless absolutely invalid. Keep all bullets but tag correctly.

        10. Strictly make sure that any procedure documented in the procedure main heading is not dropped or missing in the final framed statement. Without this we will miss a CPT code compulsorily so take care of this.
        
        11. Each statement must map to exactly ONE CPT code. For example **Cystoscopy with bladder clot evacuation: 52241 : 52241** is wrong, it must have only one CPT code, the correct way is **Cystoscopy with bladder clot evacuation: 52241**

        
        12. Output ONLY the bullet list. No commentary.
        
        Framed Statements:
        {response}
        
        Procedure Main Heading:
        {extracted_main}
        
        Relevant documented terms:
        {relevant_parts}
        
        Chart:
        {chart_text}
        """

        try:
            response = client.responses.create(
                model="openai/gpt-oss-120b",
                instructions=system_prompt,
                input=user_prompt,
                reasoning={"effort": "medium"},
                temperature=0,
                max_output_tokens=10000)
    
            response = response.output_text.strip()        
            print("Frame_tree_statements_stage2",response)
            
            response_without_unbillable = []
            for myrespo in response.splitlines():
                if "UNBILLABLE" in myrespo or "ALREADY_BUNDLED" in myrespo:
                    pass
                else:
                    myrespo = myrespo.replace("**PRIMARY**"," ").replace("**SECONDARY**"," ").strip()
                    response_without_unbillable.append(myrespo)

            response = "\n".join(response_without_unbillable)
            print("Frame_tree_statements_stage2_without_unbillable",response)
            
            # Filter out extra statements#### Remove extra codes - 1
            mycodes = ["52000"]  # extend as needed #  Bundled codes
            raw_output = response
            filtered_lines = []
            for line in raw_output.splitlines():
                if not any(code in line for code in mycodes):
                    filtered_lines.append(line)
            response = "\n".join(filtered_lines)
    
            # Filter out extra statements - 2
            final_response_lines = []    
            if len(response.strip()) > 0:
                for line22 in response.splitlines():
                    line22 = line22.strip()
                    if not line22:
                        continue            
                    try:
                        statttt, codddd = line22.split(":", 1)
                        statttt = statttt.strip() ;  codddd = codddd.strip()
                        query_vec = ftmod.encode(statttt, convert_to_numpy=True, normalize_embeddings=True).astype("float32")    
                        k = 1
                        scores, idx = ftindextra.search(np.array([query_vec]), k)
                        top_score = float(scores[0][0])
                        top_index = int(idx[0][0])
                        if top_score >= 0.80:   # We do not use this extra
                            print("Warning!! Extra statement detected")
                            # print("Top Score:", top_score)
                            # print("Matched Statement:", corpus_extras[top_index])
                        else:
                            # print("NOT EXTRA")
                            final_response_lines.append(line22)
                    except ValueError:
                        # Means either empty or no colon separation
                        continue
            if final_response_lines:
                response = "\n".join(final_response_lines)        

        except Exception as e:
            response = ""
        
    except Exception as e:
        response = ""

    if len(response.strip())<1:
        main_lines = []
        if "MAIN_PROCEDURE_NOT_FOUND" in extracted_main:
            pass
        else:
            extracted_main_split = extracted_main.splitlines()
            for mysplt in extracted_main_split:
                main_lines.append(mysplt + " : " + "NOT_CODED")
        if main_lines:
            response = "\n".join(main_lines)
        
    return response

def finetuned_adapter_loader_helper10(tree_stats_codes, ftmod, ftind, DFP, relevant_quantities, model_loader):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from openai import OpenAI
    import pandas as pd
    import re
    
    client = OpenAI(base_url="http://localhost:8000/v1",api_key="EMPTY")
    system_prompt = "You are an expert medical coder. Only output documented values."
    statements_formed = [] ; codes_found = []; DL_codes_found = []
    for tmp_line in tree_stats_codes.splitlines():
        try:
            query_text, test_code = tmp_line.split(":")
            to_k = 15
            q_emb = ftmod.encode([query_text],convert_to_numpy=True, normalize_embeddings=True,show_progress_bar=False)
            scores, indices = ftind.search(q_emb, to_k)
            indices = indices[0]; scores = scores[0]
            results = []
            for idx, sc in zip(indices, scores):
                if idx < 0:
                    continue
                row = DFP.iloc[idx]; desc = row["Full Description"];   code = row["CPT"]
                results.append(f"{desc} : {code}")
                    
            candidates_str = "; ".join(results)
            user_prompt = f"""
            For the given procedure statement, choose the SINGLE best CPT code and description
            that can be billed or medically coded from the provided candidate list.
            
            ---------------- RULES ----------------
            1) You are given:
               • The test procedure statement
               • A list of applicable quantity types and values
               • A list of candidate CPT codes with descriptions
            
            2) The applicable quantity string is in the format:
               <desired_qty_name>:<value>; <desired_qty_name>:<value>; ...
               Values may be numeric or descriptive.
            
            3) Quantity usage rules:
               • Use documented quantity values when they are relevant to CPT selection.
               • If the quantity value is **APPLICABLE_BUT_NONE_DOCUMENTED** AND multiple CPT candidates differ ONLY by quantity, you MUST select the CPT with the LOWEST quantity threshold.
               • Never assume or infer undocumented quantities.
                        
            4) If the CPT description clearly does NOT depend on quantity,
               you may ignore the quantity list completely.
            
            5) After selecting the BEST CPT code:
               • Improve the original procedure statement by explicitly including the quantity term or phrase required by the selected CPT description (if applicable).
               • If an exact quantity is NOT documented, use an appropriate qualifying phrase (e.g., “less than or equal to 250 g”) that is written in the best CPT code's description to make the statement complete. This is very important.
               • If an exact quantity IS documented, include it verbatim (e.g., “uterus weight 129 g”).
               • Do NOT add quantities that are not supported by the input.
            
            6) In short adding the appropriate quantity phrase (either verbatim as documented or from the best CPT code's description') is very important for a CPT statement.
    
            7) FINAL OUTPUT FORMAT (STRICT):
            <improved_test_statement>:<BEST_CPT_CODE>
            
            8) DO NOT:
               • explain your reasoning
               • output more than one CPT
               • hallucinate undocumented values
               • paraphrase CPT descriptions
            
            ---------------- INPUTS ----------------
            Procedure Statement:
            {query_text}
            
            Applicable Quantity Types:
            {relevant_quantities}
            
            Candidate CPT Codes:
            {candidates_str}
            
            Output only the final required format.
            """

            try:
                response = client.responses.create(
                    model="openai/gpt-oss-120b",
                    instructions=system_prompt,
                    input=user_prompt,
                    reasoning={"effort": "medium"},
                    temperature=0,
                    max_output_tokens=10000
                )
                response = response.output_text.strip()
                try:
                    stat, cod = response.split(":")
                    CPTcode,_ ,_   = DL_testing_CPT(stat, model_loader)
                    statements_formed.append(stat)
                    codes_found.append(cod)
                    DL_codes_found.append(CPTcode)
                    ###
                    myfluorolist = ["20610"]
                    if any(val in cod for val in myfluorolist):
                        if "without fluoroscopy" in stat.lower() or "without fluoroscopic" in stat.lower():
                            pass
                        elif "fluoroscopy" in stat.lower() or "fluoroscopic" in stat.lower():
                            if "77002" not in codes_found:
                                codes_found.append("77002")                
                except:
                    pass

            except Exception as e:
                pass       
        
        except:
            pass    

    if statements_formed:
        """ 
        Compute modifiers
        

        """
        statements_formed_str = "\n".join(statements_formed)
        codes_found_str = ", ".join(codes_found)
        DL_codes_found_str = ", ".join(DL_codes_found)
    else:
        statements_formed_str = " "; codes_found_str = " "; DL_codes_found_str = " "
            
    return statements_formed_str, codes_found_str, DL_codes_found_str
def tree_and_LLMtechnique(extracted_main,chart_text,mainprocedures,DFP,model_loader, ftmod, ftindextra, ftind):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from openai import OpenAI
    import pandas as pd
    import re
    ## Create a new & summarized chart
    mykeywords = ["uterus", "hernia", "defect", "myoma", "tumor", 
                  "lesion", "biopsy", "graft", "infant", "pregnancy",
                  "repair","vertebral", "column", "incarcerated", "strangulated",
                 "fibroid", "stone", "calculus","calculi","year", "old"]
    keywords_upper = [kw.upper() for kw in mykeywords]
    chart_text_upper = chart_text.upper()
    lines = chart_text_upper.splitlines()
    indices_to_keep = set()
    for i, line in enumerate(lines):
        if any(keyword in line for keyword in keywords_upper):
            indices_to_keep.add(i)
            if i - 1 >= 0:               indices_to_keep.add(i - 1)
            if i + 1 < len(lines):       indices_to_keep.add(i + 1)
    chart_text_summarized = "\n".join(lines[i] for i in sorted(indices_to_keep) if lines[i].strip())

    ## Extract the parts of the tree here
    relevant_parts = fetch_tree_parts2(extracted_main,chart_text)
    relevant_quantities = fetch_quanties(extracted_main, chart_text)    # chart_text chart_text_summarized
    tree_stats_codes = frame_tree_statements(extracted_main, relevant_parts, chart_text, DFP,model_loader, ftmod,ftindextra) # Stage - 1
    tree_llm_statements, tree_llm_codes, tree_dl_codes = finetuned_adapter_loader_helper10(tree_stats_codes, ftmod, ftind, DFP, relevant_quantities, model_loader) # Stage -2 
    return  relevant_parts, relevant_quantities, tree_stats_codes, tree_llm_statements, tree_llm_codes, tree_dl_codes

def process_chart_CPT_Genito(third_prompt,ftmod,ftindextra):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from openai import OpenAI
    import pandas as pd
    import re
    mycodes = ["52000"]  # extend as needed #  Bundled codes
    # print("Oh yesEE")
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")

    first_prompt = "You are an expert medical coder"
    second_prompt = """
    Your task is to frame complete CPT procedure statements. Extract only the confirmed, billable CPT procedures and list them as **bullet points**, with each bullet containing:
    **<Procedure Statement>: <CPT Code>** strictly put it in colon (:) spaced format. Strictly do not give any explanation.
    Rules:
    1. Each procedure statement must be fully complete for Genitourinary CPT coding similar to the full description as per CPT coding standard books.
    2. Do not put phrase in bracket, for example: Right ovarian cystectomy (partial oophorectomy) is wrong, the phrase "partial oophorectomy" should not be there.
    3. Return only unique, independently billable Genitourinary procedures and non-bundled procedure statements.
    4. Do not mutate statements, i want correct procedure statements.
    5. If hysterectomy in your procedure statement, you must always strictly mention uterus weight, include removal of tubes/ovaries or include enterocele repair by studying the chart. if weight is not documented directly write as **250 g or less**. This is very important.
    6. If myomectomy in your procedure statement, you must always strictly include vaginal / abdominal, number of intramural myoma(s), weight of fibroid which is explicity stated in chart. If number and weight  of is not documented write **250 g or less**. This is important.
    7. If CPT guidelines permit then create single procedure statement by combining multiple statements to reduce unncessary codes.
    8. Each bullet must map to **exactly one CPT code**, and strictly do not give any explanation.
    The chart text is:
    """
    # sanitize text
    third_prompt = third_prompt.replace(",", "").replace("\u202f", " ").replace("/", " ")
    prompt = second_prompt + " " + third_prompt
    try:
        response = client.responses.create(
            model="openai/gpt-oss-120b",instructions=first_prompt,input=prompt,reasoning={"effort": "medium"},temperature=0.0,max_output_tokens=20000)
        response = response.output_text
        # print("Stage-1: ", response)
        ## Verification round - 1
        first_prompt = "You are an expert medical coder"
        second_prompt = """
        Your task is to only verify whether the framed CPT procedure statements are correct, complete, non-duplicated, CPT-compliant and does not miss anything. Each line is in the format <Procedure Statement>: <CPT Code>.
        Rules, do not study beyond the following assigned rules:
        1. Keep the frame statement's phrase/wording/structure intact, but if you find it missing anything as per the chart text, correct it, check the given chart text.
        2. If hysterectomy, myomectomy in your procedure statement, you must always strictly mention uterus weight, include removal of tubes/ovaries or include enterocele repair by studying the chart. if weight is not documented directly assume **250 g or less**. This is very important.
        3. If hysterectomy in your procedure statement, correctly state either **total or vaginal or supracervical**. First check if **total** is documented, if yes add it, otherwise search the other two one by one, i.e. **vaginal**, and then **supracervical**
        4. If myomectomy in your procedure statement, you must always strictly include vaginal / abdominal, number of intramural myoma(s), weight of fibroid which is explicity stated in chart. If number and weight  of is not documented write **250 g or less**. terms like **grossly enlarged uterus**,**large anterior fibroid**, **almost 10 cm fibroid** in the chart refer to weight of fibroid **greater than 250 g **. This is important.
        5. Fetch tumor size from chart and add to the statement. If not documented write **small**.
        6. Verify if the lithotripsy and litholapaxy terms are not mixed up or confused by comparing in the chart.             
        7. If litholapaxy in your framed procedure statement, then add size of calculus by fetching from the chart. If not documented write **small**.
        8. If circumcision in your procedure statement, then extract age from the chart and put in the statement. If age or ** less than 28 days **is not documented explicitly first check words like **28 days or older**, if found put it
        otherwise just write **older than 28 days*.
        9. If repair in your procedure statement, the put length quantity in the statement.
        10. In colpopexy or sacrocolpopexy or vault suspension include **laparoscopic** or **laparoscopy**  if documented, this is very important.
        11. For hysteroscopy cases include biopsy in the statement if documented.
        11. If any major, independently billable GU procedure in the chart text is missing, add it.
        12. Output strictly in bullet points in the format <Procedure Statement>: <CPT Code>.
        13. But if you add subprocedures that are not documented you will be compulsorily wrong.
        14. No explanations.
        The framed statements are:
        """
        prompt = second_prompt + response + " \n\n\n The chart text is: " + third_prompt
        try:
            response = client.responses.create(
                model="openai/gpt-oss-120b",instructions=first_prompt,input=prompt,reasoning={"effort": "medium"},temperature=0.0,max_output_tokens=20000)
            response = response.output_text        
            # print("Stage-2: ", response)
            ## Verification round - 2
            first_prompt = "You are an expert medical coder"
            second_prompt = """
            Your task is to verify whether the framed CPT procedure statements is not missing anything as mentioned below. Each line is in the format <Procedure Statement>: <CPT Code>.
            Rules, do not study beyond the following assigned rules:
            1. The most important is to retain any quantity value reported in the original CPT procedure statements, without this your response is wrong.
            1. Do not create any new statements but you can combine the statements to form a legitimate statement using the concept of CPT bundled codes.
            2. Use "laparoscopic" with the procedures Hysterectomy, Myomectomy if documented.
            3. If procedures like Hysterectomy, Myomectomy are documented, if robotic is documented instead of laparoscopic, use laparoscopic in the statement.
            4. Do not include previous surgical procedures.
            5. If **suction and dilation** for pregancy/obstetrics is found in the chart write as **treatment of missed abortion or care of miscarriage** along with the month or trimester documented in the chart.
            6. If non-pregnancy based **suction and dilation** is detected do not include any pregnancy/abortion/miscarriage details.
            7. For pregnancy-related cases compulsorily include trimester, if not documented use *first trimester by default*.
            8. If urethroscopy in the procedure statement, include terms like pyloscopy/pyelogram and cystoscopy/cystourethroscopy if documented in the chart.
            9. if hysteroscopy then do not miss either sampling (biopsy) or endometrial ablation if documented in chart
            10. if excision of hydrocele include spermatic cord in the statement if documented in the chart text
            11. Plasma oval button is a bipolar electrosurgical technique.
            11. And do not hallucinate. stick to the above rules.
            12. Output strictly in bullet points in the format <Procedure Statement>: <CPT Code>.
            11. No explanations.
            The framed statements are:
            """
            prompt = second_prompt + response + " \n\n\n The chart text is: " + third_prompt
            try:
                response = client.responses.create(
                    model="openai/gpt-oss-120b",instructions=first_prompt,input=prompt,reasoning={"effort": "medium"},temperature=0.0,max_output_tokens=20000)
                response = response.output_text        
                # print("Stage-3: ", response)
                second_prompt = """
                Your task is to verify & correct whether the framed CPT procedure is not missing anything. Each line is in the format <Procedure Statement>: <CPT Code>.
                Rules:
                1. Strictly remember to only work on those statements that have or require Cystourethroscopy when chart documents its usage.
                2. So do not strictly touch any statements where Cystourethroscopy is not required or used.
                3. The most important is to keep intact exactly or retain any quantity value or specific things reported in the original CPT procedure statements, without this your response is wrong compulsorily.
                4. Do not add cystourethroscopy into the statement if not documented in the chart.
                5. If use of cystourethroscopy is documented in the chart, then verify whether the following are not missed in the statement, these must be documented in the chart.
                  - ureteroscopy
                  - pyeloscopy/pyelogram
                  - removal of calculus
                  - lithotripsy
                  - biopsy / fulguration
                  - resection of tumor
                  - insertion of stent
                  - DVIU or direct-vision internal urethrotomy
                6. Regarding the complexity, cystourethroscopy statements must be as per CPT guidelines regarding the use of the above subordinate procedures.
                7. Output strictly in bullet points in the format <Procedure Statement>: <CPT Code>.
                8. No explanations.
                The framed statements are:
                """
                prompt = second_prompt + response + " \n\n\n The chart text is: " + third_prompt
                try:
                    response = client.responses.create(
                        model="openai/gpt-oss-120b",instructions=first_prompt,input=prompt,reasoning={"effort": "medium"},temperature=0.0,max_output_tokens=20000)
                    response = response.output_text        
                    print("Stage-4: ", response)
                except Exception as e:
                    print("Model did not generate", e)
                    response = " "  
            except Exception as e:
                print("Model did not generate", e)
                response = " "  

        except Exception as e:
            print("Model did not generate", e)
            response = " "    
        
    except Exception as e:
        print("Model did not generate", e)
        response = " "
    
    # Filter out excluded code. Only one or few example 52000 or fluoroscopy 72000
    raw_output = response
    filtered_lines = []
    for line in raw_output.splitlines():
        if not any(code in line for code in mycodes):
            filtered_lines.append(line)
            
    response = "\n".join(filtered_lines)    

    
    # Filter out the extra statement using ST scoring
    final_response_lines = []    
    if len(response.strip()) > 0:
        for line22 in response.splitlines():
            line22 = line22.strip()
            if not line22:
                continue            
            try:
                statttt, codddd = line22.split(":", 1)
                statttt = statttt.strip() ;  codddd = codddd.strip()
                query_vec = ftmod.encode(statttt, convert_to_numpy=True, normalize_embeddings=True).astype("float32")    
                k = 1
                scores, idx = ftindextra.search(np.array([query_vec]), k)
                top_score = float(scores[0][0])
                top_index = int(idx[0][0])
                if top_score >= 0.80:   # We do not use this extra
                    print("Warning!! Extra statement detected")
                    # print("Top Score:", top_score)
                    # print("Matched Statement:", corpus_extras[top_index])
                else:
                    # print("NOT EXTRA")
                    final_response_lines.append(line22)
            except ValueError:
                # Means either empty or no colon separation
                continue
    if final_response_lines:
        response = "\n".join(final_response_lines)
    return response

def process_chart_CPT_Genito2(mainprocedures, extracted_main,chart_text,ftmod,ftind,DFP):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from openai import OpenAI
    import pandas as pd
    import re
    
    mainprocedures_split = mainprocedures.splitlines()
    mylist = [];  chosen_CPTs = []
    if mainprocedures_split:
        for tmp_line in mainprocedures_split:
            mystatement = tmp_line
            query_emb = ftmod.encode([mystatement], normalize_embeddings=True)
            k = 5
            scores, idx = ftind.search(query_emb, k)
            # print(scores, idx)
        
            for i in idx[0]:   # iterate through top-k indices
                tmp_row_df = DFP.iloc[i]
                tmp_CPT = tmp_row_df["CPT"]
                tmp_CPT = tmp_CPT.strip()
                if tmp_CPT not in chosen_CPTs:
                    tmp_DESC = tmp_row_df["Full Description"]
                    tmp_DESC = tmp_DESC.strip()
                    candidate_statement = tmp_CPT + " : " + tmp_DESC
                    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
                
                    first_prompt = "You are an expert medical coder"
                    second_prompt = """
                    Your task is to decide whether the Candidate CPT code is clinically and documentation-wise suitable for the given chart text.
                    Evaluation Rules (STRICT):
                    1. The Candidate CPT is provided as <CPT>:<Full Description>.
                    2. The “Main Procedure Headline” is only for context — final decision MUST be based on chart text.
                    3. CPT must match the actual documented procedure (type, approach, side, organ, gender context, etc.).
                    4. All required qualifiers MUST be supported in the chart text where applicable (e.g., trimester, age, tumor size, length, weight, number of lesions, laterality, multi-stage vs single stage, robotic vs open, etc.).
                    5. If documentation is incomplete, ambiguous, or missing any required details → return NOT_SUITABLE.
                    6. Do not explain. Do not add extra text. Output ONLY YES_SUITABLE or NOT_SUITABLE.
                    The test statement is:
                    """        
                    prompt = second_prompt + extracted_main + "\n\n\n" + "The CPT candidate is: " + candidate_statement + "\n\n\n" + "The chart text is: " + chart_text
                    try:
                        response = client.responses.create(
                            model="openai/gpt-oss-120b",instructions=first_prompt,input=prompt,reasoning={"effort": "medium"},temperature=0.0,max_output_tokens=20000)
                        response = response.output_text        
                        if "YES_SUITABLE" in response or "YES" in response:
                            myresponse = tmp_DESC + ":" + tmp_CPT
                            mylist.append(myresponse)
                            chosen_CPTs.append(tmp_CPT)
                    except:
                        response = ""

    if len(mylist):
        response = "\n".join(mylist)
    else:
        response = "NONE FOUND"
    
    return response

def check_bundling(statements_formed,extracted_main):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from openai import OpenAI
    import pandas as pd
    import re
    
    # print("Oh yesFF")
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
    first_prompt = "You are an expert medical coder"
    second_prompt = """
    Your task is to verify the already framed CPT procedure statements and correct bundling issues strictly according to CPT guidelines. the framed statements are in **<Procedure Statement>: <CPT Code>** colon (:) spaced format.
    Rules for you:
    1. The most important is to retain any quantity value reported in the original CPT procedure statements, without this your response is wrong.
    2. You must judge all decisions strictly in reference to the extracted MAIN procedure heading. 
    3. If incorrect subprocedure is wrongly included or missed in the framed statements but is present in the main heading include it.
    4. Never create, infer, or introduce any procedure that is not explicitly documented in the main procedure heading.
    5. Do NOT mutate, rewrite, or reword any framed CPT procedure statement. You may ONLY either:
        a) Keep a statement exactly as-is, OR
        b) Exclude a statement entirely.
    6. In the framed CPT procedure statements check if any procedure is bundled with one of the major primary statements. It may also be because redudant statements were formed.
    7. For example: diagnostic cystoscopy, catheter/pump insertion/placement without a major procedure in the statement. Exclude such statements that cannot be billed as per the CPT standard. 
    8.  If a framed CPT statement represents a minor or trivial procedure that does not have an independently billable main procedure context, exclude it.
    9. For bilateral procedure give me the bilateral code and do not give separate statements for left and right.
    11. For hysterectomy include either **removal of tube** or **removal of ovary** in the statement salpingectomy or oophorectomy is documented in the chart.
    10. Finally, keep your response strictly in the **<Procedure Statement>: <CPT Code>** colon (:) spaced format in bullet points or in new lines,  and strictly do not give any explanation.
    11. Each bullet must map to **exactly one CPT code**.
    
    The framed CPT procedure statements is: 
    """
    # sanitize text
    
    prompt = second_prompt + " " + statements_formed + "\n\n\n The extracted procedure main heading is: "+ extracted_main
    try:
        response = client.responses.create(
            model="openai/gpt-oss-120b",instructions=first_prompt,input=prompt,reasoning={"effort": "medium"},temperature=0.0,max_output_tokens=20000)
        response = response.output_text
    except:
        response = statements_formed
    if len(response.strip()) < 1:      # if empty returned then take previous
        response = statements_formed
    if len(response.strip()) < 1:
        response = extracted_main + ": DUMMY"
    
    return response

def acquire_CPT_Genito(extracted_main,chart_text,ftmod, ftind, DFP, DFA,model_loader,ftindextra):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from openai import OpenAI
    import pandas as pd
    import re
    
    final_response_CPT = process_chart_CPT_Genito(chart_text,ftmod,ftindextra) # Let LLM generate statement and code first
    # print("Statements_formed: ",final_response_CPT)
    final_response_CPT = check_bundling(final_response_CPT,extracted_main) #
    
    # print("After checking bundling: ",final_response_CPT) 

    statements_list = []; # Generated by LLM
    statements_list2 = []; # Chosen by Finetuned LLM
    model_codes_list = [];  # Generated by LLM
    model_codes_list2 = []; # Chosen by Finetuned LLM
    DL_codes_list = []; # Applied LLM Generated statement to CPT DL model
    DL_codes_list2 = [] # Applied Finetune LLM's Generated statement to CPT DL model
    Addon_list = []
    for line in final_response_CPT.split("\n"):
        if ":" in line:
            parts = line.split(":", 1)
            stmt = parts[0].strip();  modelcode = parts[1].strip()
            stmt2,modelcode2 = finetuned_adapter_loader_helper2(stmt,ftmod, ftind, DFP) # Primary codes
            stmt = spinalvertebra_preprocessing(stmt) 
            # CPTcode=" "; CPTconfidence=" "; CPTstatement=" ";
            # CPTcode2=" "; CPTconfidence2=" "; CPTstatement2=" ";
            CPTcode, CPTconfidence, CPTstatement    = DL_testing_CPT(stmt, model_loader)
            CPTcode2, CPTconfidence2, CPTstatement2 = DL_testing_CPT(stmt2, model_loader)
            ### Get addon code
            addon = process_chart_CPT_addon(chart_text,modelcode2,DFA) # List format []
            statements_list.append(stmt);            statements_list2.append(stmt2)
            model_codes_list.append(modelcode);      model_codes_list2.append(modelcode2)
            DL_codes_list.append(CPTcode);           DL_codes_list2.append(CPTcode2)
            if addon:
                Addon_list = Addon_list + addon # Concat
    statements_str = "\n".join(statements_list);     statements_str2 = "\n".join(statements_list2)
    model_codes_str = ", ".join(model_codes_list);   model_codes_str2 = ", ".join(model_codes_list2)
    dl_codes_str = ", ".join(DL_codes_list);         dl_codes_str2 = ", ".join(DL_codes_list2)
    addon_codes_str = ", ".join(Addon_list)
    return final_response_CPT, statements_str, model_codes_str, model_codes_str2, dl_codes_str, dl_codes_str2, addon_codes_str

def acquire_CPT_Genito2(mainprocedures,extracted_main,extracted_main_improved,chart_text,ftmod, ftind, DFP, DFA,model_loader,ftindextra):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from openai import OpenAI
    import pandas as pd
    import re
    
    final_response_CPT = process_chart_CPT_Genito2(mainprocedures,extracted_main_improved,chart_text,ftmod,ftind,DFP)     
    # print("After checking bundling: ",final_response_CPT) 

    statements_list = []; # Generated by LLM
    statements_list2 = []; # Chosen by Finetuned LLM
    model_codes_list = [];  # Generated by LLM
    model_codes_list2 = []; # Chosen by Finetuned LLM
    DL_codes_list = []; # Applied LLM Generated statement to CPT DL model
    DL_codes_list2 = [] # Applied Finetune LLM's Generated statement to CPT DL model
    Addon_list = []
    for line in final_response_CPT.split("\n"):
        if ":" in line:
            parts = line.split(":", 1)
            stmt = parts[0].strip();  modelcode = parts[1].strip()
            stmt2,modelcode2 = finetuned_adapter_loader_helper2(stmt,ftmod, ftind, DFP) # Primary codes
            stmt = spinalvertebra_preprocessing(stmt) 
            # CPTcode=" "; CPTconfidence=" "; CPTstatement=" ";
            # CPTcode2=" "; CPTconfidence2=" "; CPTstatement2=" ";
            CPTcode, CPTconfidence, CPTstatement    = DL_testing_CPT(stmt, model_loader)
            CPTcode2, CPTconfidence2, CPTstatement2 = DL_testing_CPT(stmt2, model_loader)
            ### Get addon code
            addon = process_chart_CPT_addon(chart_text,modelcode2,DFA) # List format []
            statements_list.append(stmt);            statements_list2.append(stmt2)
            model_codes_list.append(modelcode);      model_codes_list2.append(modelcode2)
            DL_codes_list.append(CPTcode);           DL_codes_list2.append(CPTcode2)
            if addon:
                Addon_list = Addon_list + addon # Concat
    
    statements_str = "\n".join(statements_list);     statements_str2 = "\n".join(statements_list2)
    model_codes_str = ", ".join(model_codes_list);   model_codes_str2 = ", ".join(model_codes_list2)
    dl_codes_str = ", ".join(DL_codes_list);         dl_codes_str2 = ", ".join(DL_codes_list2)
    addon_codes_str = ", ".join(Addon_list)
    return final_response_CPT, statements_str, model_codes_str, model_codes_str2, dl_codes_str, dl_codes_str2, addon_codes_str

def process_chart_CPT_Gastro(third_prompt,ftmod,ftindextra):
    mycodes = ["52000"]  # extend as needed #  Bundled codes
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")

    first_prompt = "You are an expert medical coder"
    second_prompt = """
    Your task is to frame complete CPT procedure statements. Extract only the confirmed, billable CPT procedures and list them as **bullet points**, with each bullet containing:
    **<Procedure Statement>: <CPT Code>** strictly put it in colon (:) spaced format. Strictly do not give any explanation.
    Rules:
    1. Each procedure statement must be fully complete for Gastroenterology CPT coding similar to the full description as per CPT coding standard books.
    2. Do not put phrase in bracket, for example: Gastric polypectomy (endoscopic removal) is wrong, the phrase "endoscopic removal" should not be there.
    3. Return only unique, independently billable Gastroenterology procedures and non-bundled procedure statements.
    4. Do not mutate statements, i want correct procedure statements.
    5. If EGD is mentioned, write the expanded form **"Esophagogastroduodenoscopy"**.
    6. Do not miss procedures like hernia repair if documented. 
    7. If hernia repair in procedure statement, then add total length of defect from chart and add to the statment. If incase length of defect is not documented just write ** less than 3 cm** by default. This is important.
    8. If hernia repair in procedure statement, then extract **strangulated** or **incarcerated** or **reducible** from chart and add to the statment. This is important.
    9. If hernia repair in procedure statement, then extract **initial or recurrent** from chart and add to the statment. This is important.
    10. If hernia repair is in procedure statement, add laparoscopy in the statement if laparoscopy is documented in the chart text.
    11. If hernia repair is in procedure statement, add the term **abdominal** if suitable and documented in the chart text.
    12. If hernial repair is in procedure statement, add the term **implantation of mesh** if the use of **mesh** is documented.
    13. If CPT guidelines permit then create single procedure statement by combining multiple statements to reduce unncessary codes.
    11. Each bullet must map to **exactly one CPT code**, and strictly do not give any explanation.
    The chart text is:
    """
    # sanitize text
    third_prompt = third_prompt.replace(",", "").replace("\u202f", " ").replace("/", " ")
    prompt = second_prompt + " " + third_prompt
    try:
        response = client.responses.create(
            model="openai/gpt-oss-120b",instructions=first_prompt,input=prompt,reasoning={"effort": "medium"},temperature=0.0,max_output_tokens=20000)
        response = response.output_text
        print("Stage-1: ", response)
        # ## Verification round - 1
        first_prompt = "You are an expert medical coder"
        second_prompt = """
        Your task is to only verify whether the framed CPT procedure statements are correct, complete, non-duplicated, CPT-compliant and does not miss anything. Each line is in the format <Procedure Statement>: <CPT Code>.
        Rules, your scope is to only study within the following assigned rules:
        1. Keep the framed statement's phrase/wording/structure intact, but if you find it missing anything as per the chart text, correct it, check the given chart text.
        2. Take care of the following if either **EGD or esophagogastroduodenoscopy or colonoscopy** in the procedure statement.
        2. If **esophageal dilation balloon** in procedure statement add **EGD or esophagogastroduodenoscopy or colonoscopy**  if suitable and documented in the chart text.
        3. The subprocedure ** collection of specimen by brushing or washing** is different from ** biopsy**, so they must not be mixed in a single statement.
        4. If no suitable subprocedure is documented in the chart, then add ** collection of specimen by brushing or washing** in the statement. This is the default for EGD or esophagogastroduodenoscopy or colonoscopy.
        5. If balloon dilation in procedure statement, check if terms like "scope" or "endoscope" are documented in the chart text, if yes add transendoscopic in the procedure statement.
        6. EGD or esophagogastroduodenoscopy or colonoscopy may be also through **stoma** and must be added to procedure statement if documented in chart. This is because the codes for stoma are different than regular EGD or colonoscopy codes.
        7. Take care to not omit out quantities that are present in the original statements.
        8. If any major, independently billable GU procedure in the chart text is missing, add it. But do not create procedure statements or subprocedure that are not documented.
        9. Output strictly in bullet points in the format <Procedure Statement>: <CPT Code>.
        10. No explanations.
        The framed statements are:
        """
        prompt = second_prompt + response + " \n\n\n The chart text is: " + third_prompt
        try:
            response = client.responses.create(
                model="openai/gpt-oss-120b",instructions=first_prompt,input=prompt,reasoning={"effort": "medium"},temperature=0.0,max_output_tokens=20000)
            response = response.output_text        
            print("Stage-2: ", response)
            ## Verification round - 2
            first_prompt = "You are an expert medical coder"
            second_prompt = """
            Your task is to verify whether the framed CPT procedure statements is not missing anything as mentioned below. Each line is in the format <Procedure Statement>: <CPT Code>.
            Rules, your scope is to only study within the following assigned rules, and strictly perform the corrections if necessary:
            1. Keep the framed statement's phrase/wording/structure intact, but if you find it missing anything as per the chart text, correct it, check the given chart text.
            2. Do not create any new statements but you can combine the statements to form a legitimate statement using the concept of CPT bundled codes.
            3. If hiatal hernia repair or herniorrhaphy is in procedure statement do not terms like **Nissen or Toupet or Fundoplication or esophagogastric** if documented in the chart text.
            4. If hiatal hernia repair or herniorrhaphy is in procedure statement do not terms like **paraesophageal** or **esophagogastric** if documented in the chart text.
            5. If Hemorrhoidectomy in procedure statement, do not miss terms like **2 or more columns or groups** if documented. If it is not documented write by default **single coloumn or group**
            6. If Hemorrhoidectomy in procedure statement, do not miss terms like either fissurectomy or fistulectomy or both of them if documented in the chart text.
            7. Do not miss procedure like "Aquablation", and its CPT code is 0421T Transurethral waterjet ablation of prostate.
            8. If laparoscopic cholecystectomy in procedure statement, then note that indocyanine green imaging does not mean cholangiography. Do not use cholangiography in such statements
            9.If laparoscopic removal of band or gastric band in procedure statement, then check  if revision or removal of gastric restrictive device and subcutaneous ports are documented and add to the procedure statement accordingly to make the statement complete.
            10. Do not miss procedure like Transversus abdominis plane (TAP) block by injection (or anesthesia or injection) if they are documented in the chart.
            11. Take care to not omit out quantities that are present in the original statements.
            12. If any major, independently billable GU procedure in the chart text is missing, add it. But do not create procedure statements or subprocedure that are not documented.
            13. Output strictly in bullet points in the format <Procedure Statement>: <CPT Code>.
            14. No explanations.
            The framed statements are:
            """
            prompt = second_prompt + response + " \n\n\n The chart text is: " + third_prompt
            try:
                response = client.responses.create(
                    model="openai/gpt-oss-120b",instructions=first_prompt,input=prompt,reasoning={"effort": "medium"},temperature=0.0,max_output_tokens=20000)
                response = response.output_text        
                # print("Stage-3: ", response)
            except Exception as e:
                print("Model did not generate", e)
                response = " "  

        except Exception as e:
            print("Model did not generate", e)
            response = " "    
        
    except Exception as e:
        print("Model did not generate", e)
        response = " "

    # Filter out excluded code. Only one or few example 52000 or fluoroscopy 72000
    raw_output = response
    filtered_lines = []
    for line in raw_output.splitlines():
        if not any(code in line for code in mycodes):
            filtered_lines.append(line)
            
    response = "\n".join(filtered_lines)    

   
    # Filter out the extra statement using ST scoring
    final_response_lines = []    
    if len(response.strip()) > 0:
        for line22 in response.splitlines():
            line22 = line22.strip()
            if not line22:
                continue            
            try:
                statttt, codddd = line22.split(":", 1)
                statttt = statttt.strip() ;  codddd = codddd.strip()
                query_vec = ftmod.encode(statttt, convert_to_numpy=True, normalize_embeddings=True).astype("float32")    
                k = 1
                scores, idx = ftindextra.search(np.array([query_vec]), k)
                top_score = float(scores[0][0])
                top_index = int(idx[0][0])
                if top_score >= 0.80:   # We do not use this extra
                    print("Warning!! Extra statement detected")
                    # print("Top Score:", top_score)
                    # print("Matched Statement:", corpus_extras[top_index])
                else:
                    # print("NOT EXTRA")
                    final_response_lines.append(line22)
            except ValueError:
                # Means either empty or no colon separation
                continue
    if final_response_lines:
        response = "\n".join(final_response_lines)               
    return response


def process_chart_CPT_Gastro2(mainprocedures, extracted_main,chart_text,ftmod,ftind,DFP):
    mainprocedures_split = mainprocedures.splitlines()
    mylist = [];  chosen_CPTs = []
    if mainprocedures_split:
        for tmp_line in mainprocedures_split:
            mystatement = tmp_line
            query_emb = ftmod.encode([mystatement], normalize_embeddings=True)
            k = 5
            scores, idx = ftind.search(query_emb, k)        
            for i in idx[0]:   # iterate through top-k indices
                tmp_row_df = DFP.iloc[i]
                tmp_CPT = tmp_row_df["CPT"]
                tmp_CPT = tmp_CPT.strip()
                if tmp_CPT not in chosen_CPTs:
                    tmp_DESC = tmp_row_df["Full Description"]
                    tmp_DESC = tmp_DESC.strip()
                    candidate_statement = tmp_CPT + " : " + tmp_DESC
                    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
                
                    first_prompt = "You are an expert medical coder"
                    second_prompt = """
                    Your task is to decide whether the Candidate CPT code is clinically and documentation-wise suitable for the given chart text.
                    Evaluation Rules (STRICT):
                    1. The Candidate CPT is provided as <CPT>:<Full Description>.
                    2. The “Main Procedure Headline” is only for context — final decision MUST be based on chart text.
                    3. CPT must match the actual documented procedure (type, approach, side, organ, gender context, etc.).
                    4. All required qualifiers MUST be supported in the chart text where applicable (e.g., trimester, age, tumor size, length, weight, defect size, number of lesions, laterality, multi-stage vs single stage, robotic vs open, etc.).
                    5. If documentation is incomplete, ambiguous, or missing any required details → return NOT_SUITABLE.
                    6. Do not explain. Do not add extra text. Output ONLY YES_SUITABLE or NOT_SUITABLE.
                    The test statement is:
                    """        
                    prompt = second_prompt + extracted_main + "\n\n\n" + "The CPT candidate is: " + candidate_statement + "\n\n\n" + "The chart text is: " + chart_text
                    try:
                        response = client.responses.create(
                            model="openai/gpt-oss-120b",instructions=first_prompt,input=prompt,reasoning={"effort": "medium"},temperature=0.0,max_output_tokens=20000)
                        response = response.output_text        
                        if "YES_SUITABLE" in response or "YES" in response:
                            myresponse = tmp_DESC + ":" + tmp_CPT
                            mylist.append(myresponse)
                            chosen_CPTs.append(tmp_CPT)
                    except:
                        response = ""

    if len(mylist):
        response = "\n".join(mylist)
    else:
        response = "NONE FOUND"
    
    return response

def acquire_CPT_Gastro(extracted_main,chart_text,ftmod, ftind, DFP, DFA,model_loader,ftindextra):
    final_response_CPT = process_chart_CPT_Gastro(chart_text,ftmod,ftindextra) 
    statements_list = []; # Generated by LLM
    statements_list2 = []; # Chosen by Finetuned LLM
    model_codes_list = [];  # Generated by LLM
    model_codes_list2 = []; # Chosen by Finetuned LLM
    DL_codes_list = []; # Applied LLM Generated statement to CPT DL model
    DL_codes_list2 = [] # Applied Finetune LLM's Generated statement to CPT DL model
    Addon_list = []
    for line in final_response_CPT.split("\n"):
        if ":" in line:
            parts = line.split(":", 1)
            stmt = parts[0].strip();  modelcode = parts[1].strip()
            stmt2,modelcode2 = finetuned_adapter_loader_helper2(stmt,ftmod, ftind, DFP) # Primary codes
            stmt = spinalvertebra_preprocessing(stmt) 
            # CPTcode=" "; CPTconfidence=" "; CPTstatement=" ";
            # CPTcode2=" "; CPTconfidence2=" "; CPTstatement2=" ";
            CPTcode, CPTconfidence, CPTstatement    = DL_testing_CPT(stmt, model_loader)
            CPTcode2, CPTconfidence2, CPTstatement2 = DL_testing_CPT(stmt2, model_loader)
            ### Get addon code
            addon = process_chart_CPT_addon(chart_text,modelcode2,DFA) # List format []
            statements_list.append(stmt);            statements_list2.append(stmt2)
            model_codes_list.append(modelcode);      model_codes_list2.append(modelcode2)
            DL_codes_list.append(CPTcode);           DL_codes_list2.append(CPTcode2)
            if addon:
                Addon_list = Addon_list + addon # Concat
    statements_str = "\n".join(statements_list);     statements_str2 = "\n".join(statements_list2)
    model_codes_str = ", ".join(model_codes_list);   model_codes_str2 = ", ".join(model_codes_list2)
    dl_codes_str = ", ".join(DL_codes_list);         dl_codes_str2 = ", ".join(DL_codes_list2)
    addon_codes_str = ", ".join(Addon_list)
    return final_response_CPT, statements_str, model_codes_str, model_codes_str2, dl_codes_str, dl_codes_str2, addon_codes_str

def acquire_CPT_Gastro2(mainprocedures,extracted_main,extracted_main_improved,chart_text,ftmod, ftind, DFP, DFA,model_loader,ftindextra):
    final_response_CPT = process_chart_CPT_Gastro2(mainprocedures,extracted_main_improved,chart_text,ftmod,ftind,DFP)     
    statements_list = []; # Generated by LLM
    statements_list2 = []; # Chosen by Finetuned LLM
    model_codes_list = [];  # Generated by LLM
    model_codes_list2 = []; # Chosen by Finetuned LLM
    DL_codes_list = []; # Applied LLM Generated statement to CPT DL model
    DL_codes_list2 = [] # Applied Finetune LLM's Generated statement to CPT DL model
    Addon_list = []
    for line in final_response_CPT.split("\n"):
        if ":" in line:
            parts = line.split(":", 1)
            stmt = parts[0].strip();  modelcode = parts[1].strip()
            stmt2,modelcode2 = finetuned_adapter_loader_helper2(stmt,ftmod, ftind, DFP) # Primary codes
            stmt = spinalvertebra_preprocessing(stmt) 
            # CPTcode=" "; CPTconfidence=" "; CPTstatement=" ";
            # CPTcode2=" "; CPTconfidence2=" "; CPTstatement2=" ";
            CPTcode, CPTconfidence, CPTstatement    = DL_testing_CPT(stmt, model_loader)
            CPTcode2, CPTconfidence2, CPTstatement2 = DL_testing_CPT(stmt2, model_loader)
            ### Get addon code
            addon = process_chart_CPT_addon(chart_text,modelcode2,DFA) # List format []
            statements_list.append(stmt);            statements_list2.append(stmt2)
            model_codes_list.append(modelcode);      model_codes_list2.append(modelcode2)
            DL_codes_list.append(CPTcode);           DL_codes_list2.append(CPTcode2)
            if addon:
                Addon_list = Addon_list + addon # Concat
    
    statements_str = "\n".join(statements_list);     statements_str2 = "\n".join(statements_list2)
    model_codes_str = ", ".join(model_codes_list);   model_codes_str2 = ", ".join(model_codes_list2)
    dl_codes_str = ", ".join(DL_codes_list);         dl_codes_str2 = ", ".join(DL_codes_list2)
    addon_codes_str = ", ".join(Addon_list)
    return final_response_CPT, statements_str, model_codes_str, model_codes_str2, dl_codes_str, dl_codes_str2, addon_codes_str

def acquire_addoncode(tree_llm_statements, CPT_stats, CPT_stats2, ftmod, ftind, DFP, DFA, chart_text):
    combined_stats = tree_llm_statements + "\n" + CPT_stats + "\n" + CPT_stats2
    addoncodes = []
    for line in combined_stats.splitlines():
        stmt2,modelcode2 = finetuned_adapter_loader_helper2(line,ftmod, ftind, DFP) # Primary codes
        addon = process_chart_CPT_addon(chart_text,modelcode2,DFA)
        if addon:
                addoncodes = addoncodes + addon # Concat
    addon_codes_str = ", ".join(addoncodes)
    return addoncodes

def acquire_addoncode2(tree_llm_statements, ftmod, ftind, DFP, DFA, chart_text):
    combined_stats = tree_llm_statements
    addoncodes = []
    for line in combined_stats.splitlines():
        stmt2,modelcode2 = finetuned_adapter_loader_helper2(line,ftmod, ftind, DFP) # Primary codes
        addon = process_chart_CPT_addon(chart_text,modelcode2,DFA)
        if addon:
                addoncodes = addoncodes + addon # Concat
    addon_codes_str = ", ".join(addoncodes)
    return addoncodes

def extract_mainprocedure_statement(chart_text):
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
    system_prompt = "You are an expert medical coder. Only output valid, factual results."
    user_prompt = f"""
    Your Task:     Extract the main procedure statement(s) from the given medical chart text.
    Rules that you must follow strictly:
    1. Identify only the main procedure heading(s) — these are typically short, concise titles and not the long descriptive operative narratives.
    2. Do not miss XRAY statements like **PA, lateral, AP, Oblique views, 2 views of the chest** even if XRAY or XR terms are not mentioned in that statement and also add Radiological Examination in such statements.
    3. Do not miss radiology main procedure statements.
    3. Keep proper spaces between each word.
    4. Write in expanded form if any phrase or words are written in short from. For example:- WO W is Without and With, W/US is With Ultrasound, CT is Computed Tomography, MRI is Magnetic Resonance Imaging, etc.
    5. While expanding do not create any new meaning, the inner meaning must remain the same.
    6. Strictly remember that injections or Arthrocentesis procedure statement can be found without any heading inside the chart, also pickup these procedure statements.
    7. Do not report past or not performed procedure statements.
    8. Strictly do not give me procedure statements which are already reported or bundled in another procedure statement. For example: Ultrasound may be present in another statement.
    9. Do not give me HCPCS CPT procedure statements because it is not a surgical procedure.
    10. Strictly omit procedure statements which are just documented for studying or that deals with past patient history, such as - intepretation, history, etc.
    11. Avoid repetition in main statement unless procedure is performed again and again.    
    12. Do not provide any explanation, commentary, or additional text.
    13. If no main procedure procedure statement is found, output exactly:  **MAIN_PROCEDURE_NOT_FOUND**
    14. Output Format (strict):
        - Bullet points only
        - One procedure statement per bullet
        - No extra text before or after the output
    The Chart is:
    {chart_text}
    """
    try:
        response = client.responses.create(
            model="openai/gpt-oss-120b",
            instructions=system_prompt,
            input=user_prompt,
            reasoning={"effort": "medium"},
            temperature=0,
            max_output_tokens=10000
        )
        response = response.output_text.strip()
        response = re.sub(r'\s*\|\s*', '|', response)
        return response
    except Exception as e:
        return ""    
    return response
def extract_mainprocedure_statement_refining(chart_text, main_statements):
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
    system_prompt = "You are an expert medical coder. Only output valid, factual results."
    user_prompt = f"""
    Your Task:     You are given multiple procedure statement. Your task is to label them as per the following rules.
    Rules that you must follow strictly:
    1. Tag each statement as THE_MAIN_PROCEDURE, BILLABLE, BUNDLED, STUDY_HISTORY_INTERPRETATION.
    2. Assign THE_MAIN_PROCEDURE to the statement to the major procedure that the patient is undergoing.
    3. Assign BILLABLE tag when CPT coding can be done to another procedure.
    4. Assign BUNDLED when it is already present in another bigger procedure statement.
    5. Assign STUDY_HISTORY_INTERPRETATION when the procedure statement is done earlier but just documented so that the physician can understand the patient's condition properly.
    6. Just append one tag at the end of each statement inside ** ** simply.
    7. Strictly remove any injection CPT procedure statements and normal saline infusion that does not have body parts.
    8. Strictly remove CPT pathology statements.
    9. I want only procedure statements that has proper surgical CPT procedure statement.
    7. You are given the list of statement along with the chart.
    8. Strictly return in bullet points without any explanation.

    The procedure statements are :
    {main_statements}

    The chart is:
    {chart_text}
    """
    try:
        response = client.responses.create(
            model="openai/gpt-oss-120b",
            instructions=system_prompt,
            input=user_prompt,
            reasoning={"effort": "medium"},
            temperature=0,
            max_output_tokens=10000
        )
        response = response.output_text.strip()
        response = re.sub(r'\s*\|\s*', '|', response)
        return response
    except Exception as e:
        return ""
    
    return response

def extract_mainprocedure_statement_refining2(chart_text, main_statements):
    main_statements_refined  = []
    if main_statements:
        main_statements_split = main_statements.splitlines()
        for linn in main_statements_split:
            if "STUDY_HISTORY_INTERPRETATION" not in linn:
                main_statements_refined.append(linn)
    if main_statements_refined:
        main_statements_refined_str = "\n".join(main_statements_refined)
    else:
        main_statements_refined_str = main_statements
                

    
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
    system_prompt = "You are an expert medical coder. Only output valid, factual results."
    user_prompt = f"""
    Your Task:
    You are given multiple procedure statements. Your task is to perform corrections as per the rules stated below.
    
    Rules that you must follow strictly:
    
    1. You are given a list of procedure statements with a tag at the end enclosed within ** **
    
    2. Note that the tag -
       - THE_MAIN_PROCEDURE is the clinically dominant procedure that the patient is undergoing.
       - BILLABLE is the procedure statement whose CPT coding can be done separate from THE_MAIN_PROCEDURE.
       - BUNDLED means present in either THE_MAIN_PROCEDURE or BILLABLE.
    
    IMPORTANT CLARIFICATION:
    A "larger" procedure refers to technical and statement completion dominance (what the patient underwent), it refers to the statement with more words, technical detail, or coding richness.
    
    3. Reassign THE_MAIN_PROCEDURE and BILLABLE tags only if they are improperly assigned  based on the technical and statement completion dominance.
    
    4. SUBSUMPTION / MERGE RULE (CRITICAL):
    If one procedure statement is a strict semantic subset of another
    (i.e., it adds no independent billing value and is fully represented by a more precise CPT-codable statement),
    then:
    - Merge the information into a single, complete BILLABLE statement
    - Remove the weaker or redundant statement entirely
    - Return only ONE final procedure statement to avoid overcoding or duplicate billing
    
    5. If any procedure statement is written as BUNDLED but not actually bundled into
    THE_MAIN_PROCEDURE or BILLABLE, attach it appropriately and then remove the BUNDLED statement.
    
    6. Make sure to avoid duplication. Only one authoritative version of a procedure may remain.

    7. Do not convert previous statement's long form to short form.
    
    8. You are given the list of statements along with the chart.
    
    9. Strictly return the final result in bullet points without any explanation.


    The procedure statements are :
    {main_statements_refined_str}

    The chart is:
    {chart_text}
    """
    try:
        response = client.responses.create(
            model="openai/gpt-oss-120b",
            instructions=system_prompt,
            input=user_prompt,
            reasoning={"effort": "medium"},
            temperature=0,
            max_output_tokens=10000
        )
        response = response.output_text.strip()
        response = re.sub(r'\s*\|\s*', '|', response)
        return response
    except Exception as e:
        return ""
    return response
    
def extract_mainprocedure_statement_refining3(chart_text, main_statements):    
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
    system_prompt = "You are an expert medical coder. Only output valid, factual results."
    user_prompt = f"""
    Your Task:
    You are given multiple procedure statements. Your task is to perform corrections as per the rules stated below.
    
    Rules that you must follow strictly:
    1. Simply remove the tags at the end of each statement that is enclosed within ** **
    2. The tag you may find are -  THE_MAIN_PROCEDURE, BILLABLE or BUNDLED.
    3. Strictly remove any statements that are held loose or pure diagnostic or that is not written with CPT main procedure, such as **cytoscopy** or **on q-pump placement**.
    4. Keep previous wordings intact without any change.
    5. Make sure to avoid duplication. Only one authoritative version of a procedure may remain.
    6. Do not convert previous statement's long form to short form.
    7. Do not explain anything.
    8. Strictly return the final result in bullet points without any explanation.

    The procedure statements are :
    {main_statements}

    The chart is:
    {chart_text}
    """
    try:
        response = client.responses.create(
            model="openai/gpt-oss-120b",
            instructions=system_prompt,
            input=user_prompt,
            reasoning={"effort": "medium"},
            temperature=0,
            max_output_tokens=10000
        )
        response = response.output_text.strip()
        response = re.sub(r'\s*\|\s*', '|', response)
        return response
    except Exception as e:
        return ""
    return response