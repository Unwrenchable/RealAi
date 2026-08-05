#!/usr/bin/env python3
"""
Stub to satisfy existing imports in your pipeline.
The real heavy lifting is done by build_datasets.py
"""

import json
from pathlib import Path

def extract_data(output_path="dataset.jsonl"):
    """Placeholder - main work is in build_datasets.py"""
    print("✅ extract_agent_tool_data stub called - use build_datasets.py for full extraction")
    # You can call the main builder from here if you want
    try:
        from build_datasets import build_dataset
        build_dataset()
    except Exception as e:
        print(f"Note: {e}")

if __name__ == "__main__":
    extract_data()