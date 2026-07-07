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
        self.data_loc_CPT = r"/lambda/nfs/NDS1/03_MedicalCoding/1stDec2025_onwards/CPT_DL/CPT_labs.txt"
        self.dirbiobert = r'/lambda/nfs/NDS1/03_MedicalCoding/biobert-v1.1'
        self.tokenizer_common = AutoTokenizer.from_pretrained(self.dirbiobert)  
        self.model_path_CPT = r"/lambda/nfs/NDS1/03_MedicalCoding/1stDec2025_onwards/CPT_DL/CPT_DL_1stDec2025.pt"

    def Create_DL_Model(self):        
        """ CPT loading process  """
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
        #device = torch.device('cuda' if torch.cuda.is_available() else 'cpu') # Specify gpu usage if available
        # device = torch.device('cpu') # Specify gpu usage if available
        device = torch.device('cuda')
        self.model_CPT = AutoModelForSequenceClassification.from_pretrained(self.dirbiobert, num_labels=num_class_CPT,ignore_mismatched_sizes=True)
        # state_dict_CPT = torch.load(self.model_path_CPT, map_location=torch.device('cpu')) 
        state_dict_CPT = torch.load(self.model_path_CPT, map_location=torch.device('cuda'))
        self.model_CPT.load_state_dict(state_dict_CPT)
        self.model_CPT.to(device)
        print("CPT MODEL LOADED SUCCESSFULLY")
        return self.model_CPT,self.LABELS_CPT,self.tokenizer_common
            
            
            
            
            
            
            
