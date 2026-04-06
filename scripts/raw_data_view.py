import os
import json
import pandas as pd

from src.core.config import get_settings

settings = get_settings()
folder_10 = settings.DATA_RAW_DIR / "form10"
folder_13 = settings.DATA_RAW_DIR / "form13"

first_file_name = os.listdir(folder_10)[1]
data = json.load(open(folder_10 / first_file_name))

print(f"amoutn of files: {len(os.listdir(folder_10))}")
for k, v in data.items():
    print(f"FIELD {k, v}")

forms_13_path = folder_13 / "form13.csv"
df = pd.read_csv(forms_13_path)
df.info()
print(df.head(-1))
