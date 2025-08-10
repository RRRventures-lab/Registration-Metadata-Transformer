#!/usr/bin/env python3
"""
Quick script to inspect column names in the MCAT Sample.xlsx file
"""

import pandas as pd
import sys

try:
    file_path = "/Users/gabrielrothschild/Desktop/MCAT Sample.xlsx"
    df = pd.read_excel(file_path)
    print(f"File: {file_path}")
    print(f"Shape: {df.shape}")
    print("\nColumn names:")
    for i, col in enumerate(df.columns, 1):
        print(f"{i:2d}. {col}")
    
    print("\nFirst 3 rows preview:")
    print(df.head(3).to_string())
    
except Exception as e:
    print(f"Error reading file: {e}")
    sys.exit(1)