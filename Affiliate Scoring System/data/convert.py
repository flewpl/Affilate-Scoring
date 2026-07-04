import re
from pathlib import Path

import pandas as pd

# Input/output paths, relative to this script's location
BASE_DIR = Path(__file__).resolve().parent
input_file = BASE_DIR / "affiliates_dump.sql"
output_file = BASE_DIR / "affiliates_data.csv"

with open(input_file, 'r', encoding='utf-16') as f:
    content = f.read()

# Extract everything inside VALUES (...);
# This works reliably even for multi-line INSERT statements
match = re.search(r"VALUES\s*\((.*?)\);", content, re.DOTALL)
if match:
    values_str = match.group(1)
    # Split into individual records on ),(
    rows_data = re.split(r'\),\s*\(', values_str)
    
    data = []
    for row in rows_data:
        # Strip parentheses and split on commas that are NOT inside quotes
        clean_row = re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", row.strip("()"))
        # Clean up values: strip quotes and extra whitespace
        data.append([val.strip().strip("'\"") for val in clean_row])
    
    columns = ["id", "name", "profile_name", "clicks", "registrations", 
               "ftd_count", "reg_rate", "ftd_rate", "ngr_per_ftd", 
               "total_ngr", "retention_30d"]
    
    df = pd.DataFrame(data, columns=columns)
    df.to_csv(output_file, index=False)
    print(f"Done! File saved as {output_file}")
else:
    print("Could not find a data block. Check the file contents.")