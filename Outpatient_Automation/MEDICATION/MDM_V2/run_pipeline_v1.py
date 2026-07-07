import subprocess
import sys
from fixed_variable3 import chart_count_date, chart_path, medication_path, Target, target_path

if __name__=="__main__":
    print(f"Started >> {chart_count_date}")
    print(f"Chart Path >> {chart_path}")
    print(f"Medication Path >> {medication_path}")
    if Target:
        print(f"Target: {Target}, Target Path: {target_path}")
    ##### AHFL, CSCC, CSM, BCS, BFS, MSMC
    scripts = [
    "chart_process_v1.py",
    "Medication_ANP_Extract_v3_4.py",
    "mdm_level_extraction_v4.py"
    ]

    # ### WA, NLO, MCE, WH
    # scripts = [
    # "chart_process_v1.py",
    # "Medication_ANP_Extract_v4_1.py",
    # "mdm_level_extraction_v4.py"
    # ]

    try:
        for script in scripts:
            print(f"\n>>> Running {script} ...")
            result = subprocess.run(["python", script], check=True)
            print(f"✅ Completed: {script}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error while running {script}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
        sys.exit(1)
