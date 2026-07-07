import sys
sys.path.append('/usr/lib/python3/dist-packages')  # For torchvision
sys.path.append('/home/ubuntu/.local/lib/python3.12/site-packages')  # For transformers
import random, torch, transformers, time, re
from collections import Counter
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModel
from torch.optim import AdamW
from transformers import BertConfig
import torch.nn.functional as F 
import numpy as np; import pandas as pd     

class DL_Model_ICD_CPT:
    def __init__(self): 
        self.dirbiobert = r'/lambda/nfs/NDS1/03_MedicalCoding/biobert-v1.1'
        self.tokenizer_common = AutoTokenizer.from_pretrained(self.dirbiobert)  
        self.data_loc_ICD = r"/lambda/nfs/NDS1/03_MedicalCoding/ICD_DLModel/6oct25/ICD_labs_6thOct25.txt"
        self.model_path_ICD = r"/lambda/nfs/NDS1/03_MedicalCoding/ICD_DLModel/6oct25/ICD_trained.pt"
        self.data_loc_CPT = r"/lambda/nfs/NDS1/03_MedicalCoding/1stDec2025_onwards/CPT_DL/CPT_labs.txt"        
        self.model_path_CPT = r"/lambda/nfs/NDS1/03_MedicalCoding/1stDec2025_onwards/CPT_DL/CPT_DL_1stDec2025.pt"


    def Create_DL_Model(self):        
        """ CPT loading process """
        with open(self.data_loc_CPT, encoding="utf-8") as f_CPT:
            lines_CPT = f_CPT.read().split("\n")[:-1]
        list_targetclass_CPT = []
        for line_CPT in lines_CPT:
            targetclass_CPT = line_CPT.split("\t")
            targetclass_CPT = line_CPT.lower()
            list_targetclass_CPT.append(targetclass_CPT)
        LABELS_CPT = {}
        for i_CPT, label_CPT in enumerate(list_targetclass_CPT):
            LABELS_CPT[label_CPT] = i_CPT
        self.LABELS_CPT = LABELS_CPT
        num_class_CPT = len(list_targetclass_CPT) 
        seed_CPT = 42
        random.seed(seed_CPT)
        torch.manual_seed(seed_CPT)
        device = torch.device('cpu')
        self.model_CPT = AutoModelForSequenceClassification.from_pretrained(self.dirbiobert, num_labels=num_class_CPT,ignore_mismatched_sizes=True)
        state_dict_CPT = torch.load(self.model_path_CPT, map_location=torch.device('cpu'))
        self.model_CPT.load_state_dict(state_dict_CPT)
        self.model_CPT.to(device)
        print("CPT MODEL LOADED SUCCESSFULLY ON CPU")
        
        """ ICD loading process  """
        with open(self.data_loc_ICD, encoding="utf-8") as f_ICD:
            lines_ICD = f_ICD.read().split("\n")[:-1]
        list_targetclass_ICD = []
        for line_ICD in lines_ICD:
            targetclass_ICD = line_ICD.split("\t")
            targetclass_ICD = line_ICD.lower()    
            list_targetclass_ICD.append(targetclass_ICD)
        LABELS_ICD = {}
        for i_ICD, label_ICD in enumerate(list_targetclass_ICD):
            LABELS_ICD[label_ICD] = i_ICD
        self.LABELS_ICD = LABELS_ICD
        num_class_ICD = len(list_targetclass_ICD)
        seed_ICD = 42
        random.seed(seed_ICD) 
        torch.manual_seed(seed_ICD)
        device = torch.device('cpu')
        self.model_ICD = AutoModelForSequenceClassification.from_pretrained(self.dirbiobert, num_labels=num_class_ICD,ignore_mismatched_sizes=True)
        state_dict_icd = torch.load(self.model_path_ICD, map_location=torch.device('cpu'))
        self.model_ICD.load_state_dict(state_dict_icd)
        self.model_ICD.to(device)
        print("ICD MODEL LOADED SUCCESSFULLY ON CPU")
        return self.model_ICD,self.LABELS_ICD,self.model_CPT,self.LABELS_CPT,self.tokenizer_common
           
          
            
            
            
            
            
            
            
            
