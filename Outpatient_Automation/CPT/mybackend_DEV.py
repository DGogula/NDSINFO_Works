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
print("mybackend_DEV loaded")

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
        f"Diagnosis: {CPT_Data}")
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
    
####==================================================================
# def finetuned_adapter_loader_helper1():
#     cptdb_path = r"/lambda/nfs/NDS1/03_MedicalCoding/Endpoint_SourceCodes/CPTDB.xlsx"
#     SHEETS_TO_USE = ["Full_tree","Radio","Wound_care","Addon_Primary","cpt_descriptions","Sheet1","dec25"]
#     def find_col(df, target_key):
#         norm_target = target_key
#         for c in df.columns:
#             norm_col = c.strip()
#             if norm_col == norm_target:
#                 return c
#         raise KeyError(f"Could not find column for key '{target_key}' in columns: {list(df.columns)}")
#     all_parts = []
#     for sheet in SHEETS_TO_USE:
#         # print("sheet:",sheet)
#         df = pd.read_excel(cptdb_path, sheet_name=sheet); cpt_col = find_col(df, "CPT"); desc_col = find_col(df, "Full Description")
#         mask = (
#             df[cpt_col].notna() &
#             df[desc_col].notna() &
#             (df[cpt_col].astype(str).str.strip() != "") &
#             (df[desc_col].astype(str).str.strip() != ""))
#         sub = df.loc[mask, [cpt_col, desc_col]].copy()
#         sub.columns = ["CPT", "Full Description"]
#         all_parts.append(sub)
#     if not all_parts: raise RuntimeError("No valid data collected from any sheet.")
#     new_df = pd.concat(all_parts, ignore_index=True); new_df = new_df.drop_duplicates(subset=["CPT", "Full Description"]).reset_index(drop=True)
#     new_df["CPT"] = new_df["CPT"].astype(str).str.upper().str.strip()
#     new_df["Full Description"] = new_df["Full Description"].astype(str).str.upper().str.strip()
#     # Remove unwanted characters () , ;
#     new_df["Full Description"] = (
#         new_df["Full Description"]
#         .str.replace(r"[(),;:]", "", regex=True)
#         .str.replace(r"\s+", " ", regex=True).str.strip())    
#     new_df = new_df.drop_duplicates(subset=["CPT", "Full Description"]).reset_index(drop=True)
#     new_df = new_df[~new_df["Full Description"].str.contains("UNLISTED PROCEDURE", case=False, na=False)].reset_index(drop=True)
#     addon_mask = (
#         new_df["Full Description"].str.contains("LIST SEPARATELY", case=False, na=False) |
#         new_df["Full Description"].str.contains("IN ADDITION TO CODE", case=False, na=False))
#     new_df["Addon_or_Primary"] = np.where(addon_mask, "ADDON", "PRIMARY")
#     # print("Total unique CPT descriptions:", len(new_df))
#     new_df_a = new_df[new_df["Addon_or_Primary"] == "ADDON"].reset_index(drop=True)
#     new_df_p = new_df[new_df["Addon_or_Primary"] == "PRIMARY"].reset_index(drop=True)
#     # print("Total ADDON CPT rows:", len(new_df_a))
#     # print("Total PRIMARY CPT rows:", len(new_df_p))
#     # model_id = r'/lambda/nfs/NDS1/03_MedicalCoding/all-MiniLM-L6-v2'
#     model_id = "sentence-transformers/all-MiniLM-L6-v2"
#     ftmodel = SentenceTransformer(model_id)
#     corpus_texts = new_df_p["Full Description"].tolist()
#     embeddings = ftmodel.encode(corpus_texts,convert_to_numpy=True,show_progress_bar=True, normalize_embeddings=True)
#     embedding_dim = embeddings.shape[1]
#     ftindex = faiss.IndexFlatIP(embedding_dim)
#     ftindex.add(embeddings)
#     print("FTModel_loaded")
#     return new_df, new_df_a, new_df_p, ftmodel, ftindex
####==================================================================

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
    return new_df, new_df_a, new_df_p, ftmodel, ftindex, ftindex_extras

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
    candidate_paring_kyphectomy_tethering =   """
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

#########################################  LATEST ADDITION  ######################################################

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


def acquire_CS_CPT_Radio(filename_without_txt,mastersummarydf):
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
            filtered_cpts = [c for c in cpt_list if not c.startswith(('8', '9', "1", "2", "3", "4", "5"))]
        if len(filtered_cpts) > 1:     cs_codes = ", ".join(filtered_cpts)
        elif len(filtered_cpts) == 1:  cs_codes = filtered_cpts[0]
        else:  cs_codes = "NOT FOUND"
    return cs_codes
def acquire_CS_CPT_CT(filename_without_txt,mastersummarydf):
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
            filtered_cpts = [c for c in cpt_list if not c.startswith(('8', '9', "1", "3"))]
        if len(filtered_cpts) > 1:     cs_codes = ", ".join(filtered_cpts)
        elif len(filtered_cpts) == 1:  cs_codes = filtered_cpts[0]
        else:  cs_codes = "NOT FOUND"
    return cs_codes
    
def acquire_CS_CPT_Respiratory(filename_without_txt,mastersummarydf):
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
            filtered_cpts = [c for c in cpt_list if not c.startswith(('8', '9', "1","4","5","7"))]
        if len(filtered_cpts) > 1:     cs_codes = ", ".join(filtered_cpts)
        elif len(filtered_cpts) == 1:  cs_codes = filtered_cpts[0]
        else:  cs_codes = "NOT FOUND"
    return cs_codes

def acquire_CS_CPT_NEURO(filename_without_txt,mastersummarydf):
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
            filtered_cpts = [c for c in cpt_list if not c.startswith(('8', '9', "1", "3","7"))]
        if len(filtered_cpts) > 1:     cs_codes = ", ".join(filtered_cpts)
        elif len(filtered_cpts) == 1:  cs_codes = filtered_cpts[0]
        else:  cs_codes = "NOT FOUND"
    return cs_codes

def acquire_CS_CPT_Pain(filename_without_txt,mastersummarydf):
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
            filtered_cpts = [c for c in cpt_list if not c.startswith(("1","7","8","9"))]
        if len(filtered_cpts) > 1:     cs_codes = ", ".join(filtered_cpts)
        elif len(filtered_cpts) == 1:  cs_codes = filtered_cpts[0]
        else:  cs_codes = "NOT FOUND"
    return cs_codes

#####  Use specialization-specific points e.g. point 3  #####
def extract_mainprocedure_heading(chart_text):
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
    first_prompt = "You are an expert medical coder"
    second_prompt = """
    Your Task:     Extract the main procedure statement(s) from the given medical chart text.
    Rules that you must follow strictly:
    1. Identify only the main procedure heading(s) — these are typically short, concise titles and not the long descriptive operative narratives.
    2. Most charts contain one main procedure heading; in rare cases, there may be multiple main procedure headings.    
    3. Main CT procedure headings may include (but are not limited to):
       **CT Head**, **CT Head without Contrast**, **CT Chest**, **CT Chest with Contrast**, **CT Abdomen**, **CT Abdomen and Pelvis**, **CT Abdomen and Pelvis with Contrast**,
       **CT Cervical Spine**, **CT Thoracic Spine**, **CT Lumbar Spine**, **CT Angiography Head**, **CT Angiography Chest**, **CT Angiography Abdomen and Pelvis**.
    4. Extract the heading text exactly as it appears in the chart. Do not rephrase, expand, normalize, or interpret the text.    
    5. Do not provide any explanation, commentary, or additional text.
    6. If multiple main procedure headings are present:    
        - Output each as a bullet point
        - Separate each bullet with a new line
        - Use a full stop (.) after each statement
    7. If no main procedure heading is found, output exactly:  **MAIN_PROCEDURE_NOT_FOUND**
    8. Output Format (strict):    
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
    except: response = ""
    
    return response

def improvemain_statement(extracted_main):
    client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
    first_prompt = "You are an expert medical coder"
    second_prompt = """
    Your task is to improve the given extracted main procedure statement as per CPT guidelines.    
    Rules to follow:
    1. Do not alter the conceptual meaning of the original procedure statement.
    2. Make the statement clinically accurate, CPT-aligned, and professionally phrased as per CPT guidelines and CPT description.
    3. Clarify approach, laterality, organ, staging, and any missing clinically essential context if it is clearly implied.
    4. Do NOT invent undocumented details.
    5. Use standard medical terminology and CPT-consistent wording.
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

