import sys
new_path = 'D://Medical_Coding_Project' # PREPROCESSING FILE PATH
sys.path.append(new_path) 


import pandas as pd
from detection_fns_surgery import main_execute_single, main_execute_single_icd, main_execute_single_cpt, main_execute_single_hcpcs
from glob import glob
from collections import defaultdict
from datetime import datetime
import os
import csv
import time


""" Load the DL model """
from DL_MODEL import *                    

class ModelLoader:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelLoader, cls).__new__(cls)
            cls._instance.load_models()
        return cls._instance

    def load_models(self):
            dl_object = DL_Model_ICD_CPT()
            self.model_ICD, self.LABELS_ICD, self.model_CPT, self.LABELS_CPT, self.model_HCPCS_J, self.LABELS_HCPCS_J, self.tokenizer_common = dl_object.Create_DL_Model()


from flask import Flask, jsonify  # Load the flask library 


# Create an instance of ModelLoader
model_loader = ModelLoader()      # This feature loads our Deep Learning model
app = Flask(__name__)             # Create the app using Flask API


# Define a route for the ICD endpoint
@app.route('/ENDPOINT_DL_ICD/<icd_stat>', methods=['GET'])
def get_icd_codes(icd_stat):
    mydiag = icd_stat
    mydiag = mydiag.lower()
    mydiagnosis = [mydiag]
    ICD_Codes2,ICD_Confs2 = main_execute_single_icd(mydiagnosis,model_loader.model_ICD, model_loader.tokenizer_common, model_loader.LABELS_ICD)
    results_ICD_codes = {
        'ICD_STATEMENT': mydiag,
        'ICD_CODE': ICD_Codes2,
        'ICD_CODE_CONFIDENCE': ICD_Confs2
    }
    return jsonify(results_ICD_codes), 200

# Define a route for the CPT endpoint
@app.route('/ENDPOINT_DL_CPT/<cpt_stat>', methods=['GET'])
def get_cpt_codes(cpt_stat):
    myproc = cpt_stat
    myproc = myproc.lower()
    myprocedure = [myproc]
    CPT_Codes2,CPT_Confs2 = main_execute_single_cpt(myprocedure,model_loader.model_CPT, model_loader.tokenizer_common, model_loader.LABELS_CPT)
    results_CPT_codes = {
        'CPT_STATEMENT': myproc,
        'CPT_CODE': CPT_Codes2,
        'CPT_CODE_CONFIDENCE': CPT_Confs2
    }
    return jsonify(results_CPT_codes), 200

# Define a route for the HCPCS endpoint
@app.route('/ENDPOINT_DL_HCPCS/<hcpcs_stat>', methods=['GET'])
def get_hcpcs_codes(hcpcs_stat):
    myhcpcs = hcpcs_stat
    myhcpcs = myhcpcs.lower()
    myprocedure_hcpcs = [myhcpcs]
    HCPCS_Codes2,HCPCS_Confs2 = main_execute_single_hcpcs(myprocedure_hcpcs,model_loader.model_HCPCS_J, model_loader.tokenizer_common, model_loader.LABELS_HCPCS_J)
    results_HCPCS_codes = {
        'HCPCS_STATEMENT': myhcpcs,
        'HCPCS_CODE': HCPCS_Codes2,
        'HCPCS_CODE_CONFIDENCE': HCPCS_Confs2
    }
    return jsonify(results_HCPCS_codes), 200

if __name__ == '__main__':
    # Run the Flask app on localhost and port 5000 (default)
    #app.run(debug=True)  # Set debug=True for development purposes
    app.run(host='172.16.1.34', port=5000, debug=False)

