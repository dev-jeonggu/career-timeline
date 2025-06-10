import pandas as pd
import json
import shutil
import os
import time

def load_json(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        return pd.DataFrame(json.load(f))

def clean_output_dir(path="output"):
    if os.path.exists(path):
        print("🧹 기존 output 폴더 삭제 중...")
        shutil.rmtree(path)
        time.sleep(0.5)
        print("✅ 기존 파일 삭제 완료")
