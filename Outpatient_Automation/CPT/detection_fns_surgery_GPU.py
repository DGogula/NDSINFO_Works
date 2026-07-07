import sys
# import stanza
import os   
import shutil   
import torch
import transformers
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModel
from torch.optim import AdamW
from transformers import BertConfig
import torch.nn.functional as F 
  
# new_path = 'D://Medical_Coding_Project' # PREPROCESSING FILE PATH
new_path = r"F:\MedicalCoding"
sys.path.append(new_path) 
  

def detector(mystr,model_CPT,tokenizer_CPT,LABELS_CPT):
  mytestlist = []
  mytestlist.append(mystr) # This list will hold only one code
  for i in range(len(mytestlist)):    # Loop over the number of test inputs
    t=str(mytestlist[i])              # Load the test input using index and convert it to string
    t_joined=t # Use either this or above
    encoding=tokenizer_CPT(t_joined,truncation=True,padding='max_length',max_length=50) # Perform encoding
    input_ids = encoding['input_ids']   # Encoding using 'input_ids'
    attention_mask = encoding['attention_mask'] # Encoding using 'attention_mask'
    input_ids_tensor = torch.tensor(input_ids).unsqueeze(0).to('cuda')   # Transfer data to gpu or cpu
    attention_mask_tensor = torch.tensor(attention_mask).unsqueeze(0).to('cuda')   # Transfer attention mask to gpu or cpu
    model_CPT.eval()  # Set the model to evaluation mode
    with torch.no_grad():   # Remove the gradients during evaluation mode
      output_CPT = model_CPT(input_ids_tensor, attention_mask_tensor) # Test the input_ids_tensor encoded data with the CPT model
      # Fetch the prediction labels
      prediction_CPT = F.softmax(output_CPT.logits, dim=1)  # Perform softmax normalization operation on the predicted logits
      top5_preds, top5_indices = torch.topk(prediction_CPT, k=1, dim=1) # Fetch the top 3 predictions
      confidence_scores_CPT = torch.abs(torch.sort(prediction_CPT, descending=True)[0][:, 0] - torch.sort(prediction_CPT, descending=True)[0][:, 1])
      confidence_scores_CPT = confidence_scores_CPT.item()
      temp_str = ' '    # This will hold the predicted codes
      for j in range(1):  # Fetch top 3 predictions
        a_CPT = top5_indices[0][j].item()
        matching_key_CPT = list(LABELS_CPT.keys())[list(LABELS_CPT.values()).index(a_CPT)]
        #matching_key_CPT = matching_key_CPT.upper()
        temp_str = temp_str+' '+matching_key_CPT # To be appended
        temp_str = temp_str.strip()
  return temp_str,confidence_scores_CPT # Return the predicted code


def detector_CPT_topk(mystr,model_CPT,tokenizer_CPT,LABELS_CPT):
  mytestlist = []
  mytestlist.append(mystr) # This list will hold only one code
  for i in range(len(mytestlist)):    # Loop over the number of test inputs
    t=str(mytestlist[i])              # Load the test input using index and convert it to string
    t_joined=t # Use either this or above
    encoding=tokenizer_CPT(t_joined,truncation=True,padding='max_length',max_length=50) # Perform encoding
    input_ids = encoding['input_ids']   # Encoding using 'input_ids'
    attention_mask = encoding['attention_mask'] # Encoding using 'attention_mask'
    input_ids_tensor = torch.tensor(input_ids).unsqueeze(0).to('cuda')   # Transfer data to gpu or cpu
    attention_mask_tensor = torch.tensor(attention_mask).unsqueeze(0).to('cuda')   # Transfer attention mask to gpu or cpu
    model_CPT.eval()  # Set the model to evaluation mode
    with torch.no_grad():   # Remove the gradients during evaluation mode
      output_CPT = model_CPT(input_ids_tensor, attention_mask_tensor) # Test the input_ids_tensor encoded data with the CPT model
      # Fetch the prediction labels
      prediction_CPT = F.softmax(output_CPT.logits, dim=1)  # Perform softmax normalization operation on the predicted logits
      top5_preds, top5_indices = torch.topk(prediction_CPT, k=10, dim=1) # Fetch the top 3 predictions
      confidence_scores_CPT = torch.abs(torch.sort(prediction_CPT, descending=True)[0][:, 0] - torch.sort(prediction_CPT, descending=True)[0][:, 1])
      confidence_scores_CPT = confidence_scores_CPT.item()
      confidence_scores_CPT = round(confidence_scores_CPT,2)
      temp_str = ' '    # This will hold the predicted codes
      temp_confs = ' '
      for j in range(10):  # Fetch top 3 predictions
        a_CPT = top5_indices[0][j].item()
        matching_key_CPT = list(LABELS_CPT.keys())[list(LABELS_CPT.values()).index(a_CPT)]
        #matching_key_CPT = matching_key_CPT.upper()
        temp_str = temp_str+' '+matching_key_CPT # To be appended
        temp_str = temp_str.strip()
        temp_confs = temp_confs+' '+str(confidence_scores_CPT)
        temp_confs = temp_confs.strip()
        
  return temp_str,temp_confs # Return the predicted code


def detectorHCPCS(mystr,model_HCPCS_J,tokenizer_HCPCS,LABELS_HCPCS_J):
  mytestlist = []
  mytestlist.append(mystr) # This list will hold only one code
  for i in range(len(mytestlist)):    # Loop over the number of test inputs
    t=str(mytestlist[i])              # Load the test input using index and convert it to string
    t_joined=t # Use either this or above
    encoding=tokenizer_HCPCS(t_joined,truncation=True,padding='max_length',max_length=50) # Perform encoding
    input_ids = encoding['input_ids']   # Encoding using 'input_ids'
    attention_mask = encoding['attention_mask'] # Encoding using 'attention_mask'
    input_ids_tensor = torch.tensor(input_ids).unsqueeze(0).to('cuda')   # Transfer data to gpu or cpu
    attention_mask_tensor = torch.tensor(attention_mask).unsqueeze(0).to('cuda')   # Transfer attention mask to gpu or cpu
    model_HCPCS_J.eval()  # Set the model to evaluation mode
    with torch.no_grad():   # Remove the gradients during evaluation mode
      output_HCPCS = model_HCPCS_J(input_ids_tensor, attention_mask_tensor) # Test the input_ids_tensor encoded data with the HCPCS model
      # Fetch the prediction labels
      prediction_HCPCS = F.softmax(output_HCPCS.logits, dim=1)  # Perform softmax normalization operation on the predicted logits
      top5_preds, top5_indices = torch.topk(prediction_HCPCS, k=1, dim=1) # Fetch the top 3 predictions
      confidence_scores_HCPCS = torch.abs(torch.sort(prediction_HCPCS, descending=True)[0][:, 0] - torch.sort(prediction_HCPCS, descending=True)[0][:, 1])
      confidence_scores_HCPCS = confidence_scores_HCPCS.item()
      temp_str = ' '    # This will hold the predicted codes
      for j in range(1):  # Fetch top 3 predictions
        a_HCPCS = top5_indices[0][j].item()
        matching_key_HCPCS = list(LABELS_HCPCS_J.keys())[list(LABELS_HCPCS_J.values()).index(a_HCPCS)]
        #matching_key_CPT = matching_key_CPT.upper()
        temp_str = temp_str+' '+matching_key_HCPCS # To be appended
        temp_str = temp_str.strip()
  return temp_str,confidence_scores_HCPCS # Return the predicted code


"""
# We use several layers of rules to derive the code(s). 
def testfiICD(diag_list,model_ICD,tokenizer_ICD,LABELS_ICD):            # loop goes upto the number of test inputs
  fin_code = ""
  for i in range(len(diag_list)):
    diagnosis = diag_list[i]; diagnosis = diagnosis.lower() 
    temp = detectorICD(diagnosis,model_ICD,tokenizer_ICD,LABELS_ICD) ; 
    fin_code = fin_code+" "+temp
  return fin_code


def testfiCPT(proc_list,model_CPT,tokenizer_CPT,LABELS_CPT):          # loop goes upto the number of test inputs
  fin_code = ""
  for i in range(len(proc_list)):
    procedure = proc_list[i]        
    procedure = procedure.lower()   
    temp = detector(procedure,model_CPT,tokenizer_CPT,LABELS_CPT)
    fin_code = fin_code +" "+temp      
  return fin_code

"""

# Function to create folder if it does not exist
def create_folder_if_not_exists(path, folder_name):
    folder_path = os.path.join(path, folder_name)
    if not os.path.exists(folder_path):
        os.mkdir(folder_path)
        print(f"Folder '{folder_name}' created at '{path}'.")
    else:
        print(f"Folder '{folder_name}' already exists at '{path}'.")


# We use several layers of rules to derive the code(s). 
def testfiICD(diag_list,model_ICD,tokenizer_ICD,LABELS_ICD):            # loop goes upto the number of test inputs
  fin_code = ""; fin_conf=""
  for i in range(len(diag_list)):
    diagnosis = diag_list[i]; 
    diagnosis = diagnosis.lower() 
    temp,confd = detectorICD(diagnosis,model_ICD,tokenizer_ICD,LABELS_ICD) ; 
    confd = round(confd,4)*100
    fin_code = fin_code+" "+temp
    #fin_conf = fin_conf+" "+str(confd)  # Store the confidence in str format
  return fin_code,confd


def testfiCPT(proc_list,model_CPT,tokenizer_CPT,LABELS_CPT):          # loop goes upto the number of test inputs
  fin_code = ""
  for i in range(len(proc_list)):
    procedure = proc_list[i]        
    procedure = procedure.lower()   
    temp,confd = detector(procedure,model_CPT,tokenizer_CPT,LABELS_CPT)
    confd = round(confd,4)*100
    fin_code = fin_code +" "+temp
  return fin_code,confd


def testfiCPT_topK(proc_list,model_CPT,tokenizer_CPT,LABELS_CPT):          # loop goes upto the number of test inputs
  fin_code = ""
  for i in range(len(proc_list)):
    procedure = proc_list[i]        
    procedure = procedure.lower()   
    codess,confds = detector_CPT_topk(procedure,model_CPT,tokenizer_CPT,LABELS_CPT)
    fin_code = fin_code +" "+codess
  return fin_code,confds


def testfiHCPCS(hcpcs_list,model_HCPCS_J,tokenizer_HCPCS,LABELS_HCPCS_J):          # loop goes upto the number of test inputs
  fin_code = ""
  for i in range(len(hcpcs_list)):
    procedure_hcpcs = hcpcs_list[i]        
    procedure_hcpcs = procedure_hcpcs.lower()   
    temp,confd = detectorHCPCS(procedure_hcpcs,model_HCPCS_J,tokenizer_HCPCS,LABELS_HCPCS_J)
    confd = round(confd,4)*100
    fin_code = fin_code +" "+temp
  return fin_code,confd


def main_execute_direct_database_flow_icd(diag_statement,model_ICD,tokenizer_ICD,LABELS_ICD):
    ICD_Codes3 = ""; CPT_Codes3 = ""  # Initialize them.
    ICD_codes = []; diag_broks = []  
    diagnosis = diag_statement.lower()
    ICDresult_code = testfiICD([diagnosis],model_ICD,tokenizer_ICD,LABELS_ICD); ICDresult_code = ICDresult_code.upper()
    ICD_codes.append(ICDresult_code)   
    #diag_broks.append(broken_list)
    ICD_Codes2 = "".join(ICD_codes)
    ICD_Codes2 = list(set(ICD_Codes2.split()))
    ICD_Codes3 = "|".join(ICD_Codes2)
    return ICD_Codes3


def main_execute_direct_database_flow_cpt(proc_statement,model_CPT,tokenizer_CPT,LABELS_CPT):
    CPT_codes = []
    procedure = proc_statement.lower() 
    CPTresult_code = testfiCPT([procedure],model_CPT,tokenizer_CPT,LABELS_CPT); CPTresult_code = CPTresult_code.upper()
    CPT_codes.append(CPTresult_code)
    CPT_Codes2 = "".join(CPT_codes)
    CPT_Codes2 = list(set(CPT_Codes2.split()))
    CPT_Codes3 = "|".join(CPT_Codes2)
    return CPT_Codes3

""" ICD Testing function """ 
def detectorICD(mystr,model_ICD,tokenizer_ICD,LABELS_ICD):
  mytestlist = []
  mytestlist.append(mystr) # This list will hold only one code
  for i in range(len(mytestlist)):    # Loop over the number of test inputs
    t=str(mytestlist[i])      # Load the test input using index and convert it to string
    t_joined=t # Use either this or above
    encoding=tokenizer_ICD(t_joined,truncation=True,padding='max_length',max_length=50) # Perform encoding
    input_ids = encoding['input_ids']     # Encoding using 'input_ids'
    attention_mask = encoding['attention_mask']     # Encoding using 'attention_mask'
    input_ids_tensor = torch.tensor(input_ids).unsqueeze(0).to('cuda')    # Transfer data to gpu or cpu
    attention_mask_tensor = torch.tensor(attention_mask).unsqueeze(0).to('cuda')  # Transfer attention mask to gpu or cpu
    model_ICD.eval()    # Set the model to evaluation mode
    with torch.no_grad():   # Remove the gradients during evaluation mode
      output_ICD = model_ICD(input_ids_tensor, attention_mask_tensor) # Test the input_ids_tensor encoded data with the CPT model
      # Fetch the prediction labels
      prediction_ICD = F.softmax(output_ICD.logits, dim=1)   # Perform softmax normalization operation on the predicted logits
      top5_preds, top5_indices = torch.topk(prediction_ICD, k=1, dim=1) # Fetch the top k predictions
      confidence_scores_ICD = torch.abs(torch.sort(prediction_ICD, descending=True)[0][:, 0] - torch.sort(prediction_ICD, descending=True)[0][:, 1])
      confidence_scores_ICD = confidence_scores_ICD.item()
      temp_str = ' '    # This will hold the predicted codes
      for j in range(1):  # Loop over the top k predictions
        a_ICD = top5_indices[0][j].item()
        matching_key_ICD = list(LABELS_ICD.keys())[list(LABELS_ICD.values()).index(a_ICD)]
        #matching_key_ICD = matching_key_ICD.upper()
        temp_str = temp_str+' '+matching_key_ICD # To be appended
        temp_str = temp_str.strip()
    temp_str = temp_str.replace("s52.252c s52.352c","s52.252c")
  return temp_str,confidence_scores_ICD


"""  Main execution sequence DL_IN folder to DL_OUT folder """
def main_execute(model_ICD,tokenizer_ICD,LABELS_ICD,model_CPT,tokenizer_CPT,LABELS_CPT):
    root_path = "//dev-dc02//MCODING//DL_IN//"
    client_ED = root_path+"CLIENT_ED//"
    client_EM = root_path+"CLIENT_EM//"
    client_ORT = root_path+"CLIENT_ORT//"
    client_PM = root_path+"CLIENT_PM//"
    client_RAD = root_path+"CLIENT_RAD//"
    client_SUR = root_path+"CLIENT_SUR//"
    client_WC = root_path+"CLIENT_WC//"
    all_paths = [client_ED,client_EM,client_ORT,client_PM,client_RAD,client_SUR,client_WC]

    # Create the OVER folders if does not exist
    folder_to_check = "OVER"
    for mypath_folder in all_paths:
        create_folder_if_not_exists(mypath_folder, folder_to_check)  # Create folder if not exist
        

    for mypath in all_paths:
        if os.path.exists(mypath):
            print("path exist", mypath)
            files_in_folder = os.listdir(mypath)
            csvtxt_files = [file for file in files_in_folder if file.endswith('.txt')]
            total_statements_count = 0 # Initialized initially
            for i in range(len(csvtxt_files)):
                file = csvtxt_files[i]
                DL_IN_path = mypath+file
                outpath = DL_IN_path.replace("DL_IN","DL_OUT")
                with open(DL_IN_path, encoding="unicode_escape") as f1:
                    test_data = f1.read().split("\n")[:-1]
                check_whether_ICD_or_CPT = " ".join(test_data) 
                if "ICD_STATEMENT" in check_whether_ICD_or_CPT or "Diagnosis" in check_whether_ICD_or_CPT:  # Checks whether we require ICD / CPT 
                    j = 0
                    data_to_write_to_csvtext = []
                    for j in range(len(test_data)):
                        line = test_data[j]
                        if j==0:
                            first_line = "FILE_NAME"+"\t"+"MR_LD_ID"+"\t"+"CODE_ID"+"\t"+"DIAGNOSIS"+"\t"+"ICD_CODE"
                            data_to_write_to_csvtext.append(first_line)
                        else:        
                            ICD_inp = ""; final_ICDcode ="";
                            filename,MR_LD_ID,MR_IDT_ID,ICD_inp = line.split("\t")
                            if ICD_inp: 
                                ICD_codes = []; diag_broks = []  # Fetch the processed broken up text list
                                diagnosis = ICD_inp.lower()         
                                ICDresult_code,broken_list = testfiICD([diagnosis],model_ICD,tokenizer_ICD,LABELS_ICD); ICDresult_code = ICDresult_code.upper()
                                ICD_codes.append(ICDresult_code)   
                                diag_broks.append(broken_list)
                                ICD_Codes2 = "".join(ICD_codes)
                                ICD_Codes2 = list(set(ICD_Codes2.split()))
                                final_ICDcode = "|".join(ICD_Codes2)
                                print(final_ICDcode)
                            final_form_ICD = line+"\t"+final_ICDcode
                            data_to_write_to_csvtext.append(final_form_ICD)
                    with open(outpath, 'w', encoding="utf-8") as fp2: # Store into the variable
                      for j2 in range(len(data_to_write_to_csvtext)): # Chose using the index j2 from the final_CPTs variable
                        texttt2 = data_to_write_to_csvtext[j2]      # Write into the text file
                        fp2.write("%s\n" % texttt2)
                      print('Done')    
                
                elif "CPT_STATEMENT" in check_whether_ICD_or_CPT or "Procedure" in check_whether_ICD_or_CPT:     
                    j = 0
                    data_to_write_to_csvtext_CPT = []
                    for j in range(len(test_data)):
                        line = test_data[j]
                        if j==0:
                            first_line = "FILE_NAME"+"\t"+"MR_LD_ID"+"\t"+"CODE_ID"+"\t"+"PROCEDURE"+"\t"+"CPT_CODE"
                            data_to_write_to_csvtext_CPT.append(first_line)
                        else:        
                            CPT_inp = ""; final_CPTcode = ""
                            filename,MR_LD_ID,MR_CMD_ID,CPT_inp = line.split("\t")
                            if CPT_inp:
                                CPT_codes = []
                                procedure = CPT_inp.lower()
                                CPTresult_code = testfiCPT([procedure],model_CPT,tokenizer_CPT,LABELS_CPT); CPTresult_code = CPTresult_code.upper()
                                CPT_codes.append(CPTresult_code)
                                CPT_Codes2 = "".join(CPT_codes)
                                CPT_Codes2 = list(set(CPT_Codes2.split()))
                                final_CPTcode = "|".join(CPT_Codes2)
                                print(final_CPTcode)
                            final_form_CPT = line+"\t"+final_CPTcode
                            data_to_write_to_csvtext_CPT.append(final_form_CPT)
                    
                    with open(outpath, 'w', encoding="utf-8") as fp2: # Store into the variable
                      for j2 in range(len(data_to_write_to_csvtext_CPT)): # Chose using the index j2 from the final_CPTs variable
                        texttt2 = data_to_write_to_csvtext_CPT[j2]      # Write into the text file
                        fp2.write("%s\n" % texttt2)
                      print('Done')    
            
                # move file .txt file into the OVER folder after processing the file
                target_path = mypath+"OVER//"
                shutil.move(DL_IN_path, target_path)
        else:
            print("path does not exist",mypath)
    """  Main execution sequence  """
def main_execute(model_ICD,tokenizer_ICD,LABELS_ICD,model_CPT,tokenizer_CPT,LABELS_CPT):
    root_path = "//dev-dc02//MCODING//DL_IN//"
    client_ED = root_path+"CLIENT_ED//"
    client_EM = root_path+"CLIENT_EM//"
    client_EMT = root_path+"CLIENT_EMT//"
    client_ORT = root_path+"CLIENT_ORT//"
    client_PM = root_path+"CLIENT_PM//"
    client_RAD = root_path+"CLIENT_RAD//"
    client_SUR = root_path+"CLIENT_SUR//"
    client_WC = root_path+"CLIENT_WC//"
    all_paths = [client_ED,client_EM,client_EMT,client_ORT,client_PM,client_RAD,client_SUR,client_WC]

    # Create the OVER folders if does not exist
    folder_to_check = "OVER"
    for mypath_folder in all_paths:
        create_folder_if_not_exists(mypath_folder, folder_to_check)  # Create folder if not exist
        

    for mypath in all_paths:
        if os.path.exists(mypath):
            print("path exist", mypath)
            files_in_folder = os.listdir(mypath)
            csvtxt_files = [file for file in files_in_folder if file.endswith('.txt')]
            total_statements_count = 0 # Initialized initially
            for i in range(len(csvtxt_files)):
                file = csvtxt_files[i]
                DL_IN_path = mypath+file
                outpath = DL_IN_path.replace("DL_IN","DL_OUT")
                with open(DL_IN_path, encoding="utf-8") as f1:
                    test_data = f1.read().split("\n")[:-1]
                check_whether_ICD_or_CPT = " ".join(test_data) 
                if "ICD_STATEMENT" in check_whether_ICD_or_CPT or "Diagnosis" in check_whether_ICD_or_CPT:  # Checks whether we require ICD / CPT 
                    j = 0
                    data_to_write_to_csvtext = []
                    for j in range(len(test_data)):
                        line = test_data[j]
                        if j==0:
                            first_line = "FILE_NAME"+"\t"+"MR_LD_ID"+"\t"+"CODE_ID"+"\t"+"DIAGNOSIS"+"\t"+"ICD_CODE"
                            data_to_write_to_csvtext.append(first_line)
                        else:        
                            ICD_inp = ""; final_ICDcode ="";
                            filename,MR_LD_ID,MR_IDT_ID,ICD_inp = line.split("\t")
                            if ICD_inp: 
                                ICD_codes = []; diag_broks = []  # Fetch the processed broken up text list
                                diagnosis = ICD_inp.lower()
                                ICDresult_code,broken_list = testfiICD([diagnosis],model_ICD,tokenizer_ICD,LABELS_ICD); ICDresult_code = ICDresult_code.upper()
                                ICD_codes.append(ICDresult_code)   
                                diag_broks.append(broken_list)
                                ICD_Codes2 = "".join(ICD_codes)
                                ICD_Codes2 = list(set(ICD_Codes2.split()))
                                final_ICDcode = "|".join(ICD_Codes2)
                                print(final_ICDcode)
                            final_form_ICD = line+"\t"+final_ICDcode
                            data_to_write_to_csvtext.append(final_form_ICD)
                    with open(outpath, 'w', encoding="utf-8") as fp2: # Store into the variable
                      for j2 in range(len(data_to_write_to_csvtext)): # Chose using the index j2 from the final_CPTs variable
                        texttt2 = data_to_write_to_csvtext[j2]      # Write into the text file
                        fp2.write("%s\n" % texttt2)
                      print('Done')    
                
                elif "CPT_STATEMENT" in check_whether_ICD_or_CPT or "Procedure" in check_whether_ICD_or_CPT:     
                    j = 0
                    data_to_write_to_csvtext_CPT = []
                    for j in range(len(test_data)):
                        line = test_data[j]
                        if j==0:
                            first_line = "FILE_NAME"+"\t"+"MR_LD_ID"+"\t"+"CODE_ID"+"\t"+"PROCEDURE"+"\t"+"CPT_CODE"
                            data_to_write_to_csvtext_CPT.append(first_line)
                        else:        
                            CPT_inp = ""; final_CPTcode = ""
                            filename,MR_LD_ID,MR_CMD_ID,CPT_inp = line.split("\t")
                            if CPT_inp:
                                CPT_codes = []
                                procedure = CPT_inp.lower()
                                CPTresult_code = testfiCPT([procedure],model_CPT,tokenizer_CPT,LABELS_CPT); CPTresult_code = CPTresult_code.upper()
                                CPT_codes.append(CPTresult_code)
                                CPT_Codes2 = "".join(CPT_codes)
                                CPT_Codes2 = list(set(CPT_Codes2.split()))
                                final_CPTcode = "|".join(CPT_Codes2)
                                print(final_CPTcode)
                            final_form_CPT = line+"\t"+final_CPTcode
                            data_to_write_to_csvtext_CPT.append(final_form_CPT)
                    
                    with open(outpath, 'w', encoding="utf-8") as fp2: # Store into the variable
                      for j2 in range(len(data_to_write_to_csvtext_CPT)): # Chose using the index j2 from the final_CPTs variable
                        texttt2 = data_to_write_to_csvtext_CPT[j2]      # Write into the text file
                        fp2.write("%s\n" % texttt2)
                      print('Done')    
                # move file .txt file into the OVER folder after processing the file
                target_path = mypath+"OVER//"
                shutil.move(DL_IN_path, target_path)
        else:
            print("path does not exist",mypath)
    


def main_execute_single(mydiagnosis,myprocedure,model_ICD,tokenizer_ICD,LABELS_ICD,model_CPT,tokenizer_CPT,LABELS_CPT):
    ICD_Codes2 = ""; CPT_Codes2 = ""  # Intialised 
    if mydiagnosis:
        myICD_codes = []
        for mydiag in mydiagnosis:
            mydiag = mydiag.lower(); 
            ICDresult = testfiICD([mydiag],model_ICD,tokenizer_ICD,LABELS_ICD); 
            ICDresult = ICDresult.upper(); 
            myICD_codes.append(ICDresult)   
        ICD_Codes2 = "".join(myICD_codes) ; #ICD_Codes2 = list(set(ICD_Codes2.split())) ; 
        #final_ICDcode = "|".join(ICD_Codes2) ; #print(final_ICDcode)        
    if myprocedure:
        myCPT_codes = []
        for myproc in myprocedure:
            myproc = myproc.lower(); 
            CPTresult = testfiCPT([myproc],model_CPT,tokenizer_CPT,LABELS_CPT); CPTresult = CPTresult.upper() ; myCPT_codes.append(CPTresult)    
        CPT_Codes2 = "".join(myCPT_codes) ; #CPT_Codes2 = list(set(CPT_Codes2.split())) ; 
        #final_CPTcode = "|".join(CPT_Codes2) ; #print(final_CPTcode)        
    return ICD_Codes2, CPT_Codes2


def main_execute_single_icd(mydiagnosis,model_ICD,tokenizer_ICD,LABELS_ICD):
    ICD_Codes2 = ""; ICDconfidence2 = ""
    myICD_codes = []; myICD_confidence = []
    for mydiag in mydiagnosis:
        mydiag = mydiag.lower(); 
        ICDresult,ICDconfidence = testfiICD([mydiag],model_ICD,tokenizer_ICD,LABELS_ICD); 
        ICDresult = ICDresult.upper(); 
        myICD_codes.append(ICDresult)
        myICD_confidence.append(ICDconfidence)
    ICD_Codes2 = "".join(myICD_codes) ; #ICD_Codes2 = list(set(ICD_Codes2.split())) ; 
    #final_ICDcode = "|".join(ICD_Codes2) ; #print(final_ICDcode)        
    #ICDconfidence2 = "".join(myICD_confidence)
    return ICD_Codes2,ICDconfidence

# def main_execute_single_cpt(myprocedure,model_CPT,tokenizer_CPT,LABELS_CPT):
#     CPT_Codes2 = ""; CPTconfidence2 = ""
#     myCPT_codes = []; myCPT_confidence = []
#     for myproc in myprocedure:
#         myproc = myproc.lower(); 
#         CPTresult,CPTconfidence = testfiCPT([myproc],model_CPT,tokenizer_CPT,LABELS_CPT); 
#         CPTresult = CPTresult.upper() ; 
#         myCPT_codes.append(CPTresult)
#         myCPT_confidence.append(CPTconfidence)
        
#     CPT_Codes2 = "".join(myCPT_codes) ; #CPT_Codes2 = list(set(CPT_Codes2.split())) ; 
#     #final_CPTcode = "|".join(CPT_Codes2) ; #print(final_CPTcode)        
#     return CPT_Codes2,CPTconfidence

def main_execute_single_cpt(myprocedure,model_CPT,tokenizer_CPT,LABELS_CPT):
    CPT_Codes2 = ""; CPTconfidence2 = ""
    myCPT_codes = []; myCPT_confidence = []
    for myproc in myprocedure:
        myproc = myproc.lower(); 
        CPTresult,CPTconfidence = testfiCPT([myproc],model_CPT,tokenizer_CPT,LABELS_CPT); 
        CPTresult = CPTresult.upper() ; 
        myCPT_codes.append(CPTresult)
        myCPT_confidence.append(str(round(CPTconfidence,2)))
        
    CPT_Codes2 = " ".join(myCPT_codes) ; #CPT_Codes2 = list(set(CPT_Codes2.split())) ; 
    CPTconfidence2 = " ".join(myCPT_confidence) ; #CPT_Codes2 = list(set(CPT_Codes2.split())) ; 
    
    #final_CPTcode = "|".join(CPT_Codes2) ; #print(final_CPTcode)        
    return CPT_Codes2,CPTconfidence2

# Top-10 codes
def main_execute_single_cpt_topK(myprocedure,model_CPT,tokenizer_CPT,LABELS_CPT):
    CPT_Codes2 = ""; CPTconfidence2 = ""
    myCPT_codes = []; myCPT_confidence = []
    for myproc in myprocedure:
        myproc = myproc.lower(); 
        CPTresult,CPTconfidence = testfiCPT_topK([myproc],model_CPT,tokenizer_CPT,LABELS_CPT); 
        CPTresult = CPTresult.upper() ; 
        myCPT_codes.append(CPTresult)
        myCPT_confidence.append(CPTconfidence)
        
    CPT_Codes2 = " ".join(myCPT_codes) ; #CPT_Codes2 = list(set(CPT_Codes2.split())) ; 
    CPTconfidence2 = " ".join(myCPT_confidence) ; #CPT_Codes2 = list(set(CPT_Codes2.split())) ; 
    
    #final_CPTcode = "|".join(CPT_Codes2) ; #print(final_CPTcode)        
    return CPT_Codes2,CPTconfidence2


def main_execute_single_hcpcs(myhcpcs_statment,model_HCPCS_J,tokenizer_HCPCS,LABELS_HCPCS_J):
    HCPCS_Codes2 = ""; HCPCSconfidence2 = ""
    myHCPCS_codes = []; myHCPCS_confidence = []
    for myhcpcs in myhcpcs_statment:
        myhcpcs = myhcpcs.lower(); 
        HCPCSresult,HCPCSconfidence = testfiHCPCS([myhcpcs],model_HCPCS_J,tokenizer_HCPCS,LABELS_HCPCS_J); 
        HCPCSresult = HCPCSresult.upper() 
        myHCPCS_codes.append(HCPCSresult)
        myHCPCS_confidence.append(str(round(HCPCSconfidence,2)))
        
    HCPCS_Codes2 = " ".join(myHCPCS_codes) 
    HCPCSconfidence2 = " ".join(myHCPCS_confidence) 
    
    #final_CPTcode = "|".join(CPT_Codes2) ; #print(final_CPTcode)        
    return HCPCS_Codes2,HCPCSconfidence2



def find_CPT_CODE_improved(sentt2_ori,model_CPT,tokenizer_CPT,LABELS_CPT):
    CPT_Code = ""; CPT_Conf=""
    chosen_CPT_Code = ""; chosen_CPT_Conf = ""  # Initializing placeholder variables to hold codes and confidence
    sentt2 = sentt2_ori
    if "left" in sentt2:
        statement1 = sentt2.replace("left","") # Statement does not have "left" word
        statement2 = sentt2                    # Statement has "left" word
        # Test with statement1
        CPT_Code_s1,CPT_Conf_s1 = main_execute_single_cpt([statement1],model_CPT,tokenizer_CPT,LABELS_CPT)
        CPT_Conf_s1 = float(CPT_Conf_s1)
        # Test with statement2
        CPT_Code_s2,CPT_Conf_s2 = main_execute_single_cpt([statement2],model_CPT,tokenizer_CPT,LABELS_CPT)
        CPT_Conf_s2 = float(CPT_Conf_s2)
        # Choose the best one
        if CPT_Code_s1 == CPT_Code_s2:   # If both codes are same, then choose any one.
            chosen_CPT_Code = CPT_Code_s1     # Choose any one
            if CPT_Conf_s1 > CPT_Conf_s2:  # choose the higher score
                chosen_CPT_Conf = CPT_Conf_s1
            else: chosen_CPT_Conf = CPT_Conf_s2
        else:  # if the two are different, then choose the higher scoring code
            if CPT_Conf_s1 > CPT_Conf_s2:
                chosen_CPT_Code = CPT_Code_s1
                chosen_CPT_Conf = CPT_Conf_s1
            else:
                chosen_CPT_Code = CPT_Code_s2
                chosen_CPT_Conf = CPT_Conf_s2
    elif "right" in sentt2:
        statement1 = sentt2.replace("right","") # Statement does not have "right" word
        statement2 = sentt2                    # Statement has "right" word
        # Test with statement1
        CPT_Code_s1,CPT_Conf_s1 = main_execute_single_cpt([statement1],model_CPT,tokenizer_CPT,LABELS_CPT)
        CPT_Conf_s1 = float(CPT_Conf_s1)
        # Test with statement2
        CPT_Code_s2,CPT_Conf_s2 = main_execute_single_cpt([statement2],model_CPT,tokenizer_CPT,LABELS_CPT)
        CPT_Conf_s2 = float(CPT_Conf_s2)
        # Choose the best one
        if CPT_Code_s1 == CPT_Code_s2:   # If both codes are same, then choose any one.
            chosen_CPT_Code = CPT_Code_s1     # Choose any one
            if CPT_Conf_s1 > CPT_Conf_s2:  # choose the higher score
                chosen_CPT_Conf = CPT_Conf_s1
            else: chosen_CPT_Conf = CPT_Conf_s2
        else:  # if the two are different, then choose the higher scoring code
            if CPT_Conf_s1 > CPT_Conf_s2:
                chosen_CPT_Code = CPT_Code_s1
                chosen_CPT_Conf = CPT_Conf_s1
            else:
                chosen_CPT_Code = CPT_Code_s2
                chosen_CPT_Conf = CPT_Conf_s2
    else: # if either left or right is not mentioned, then we pass as it is
        CPT_Code_s1,CPT_Conf_s1 = main_execute_single_cpt([sentt2],model_CPT,tokenizer_CPT,LABELS_CPT)
        CPT_Conf_s1 = float(CPT_Conf_s1)
        chosen_CPT_Code = CPT_Code_s1
        chosen_CPT_Conf = CPT_Conf_s1

    CPT_Code = CPT_Code+" "+chosen_CPT_Code; CPT_Code = CPT_Code.replace("27125","27236")  # This for all hemiarthroplasty as per feedback from medical coder
    CPT_Conf = CPT_Conf +" "+str(chosen_CPT_Conf)
    tmp_aws_split_upgrade = sentt2
    return CPT_Code,CPT_Conf








