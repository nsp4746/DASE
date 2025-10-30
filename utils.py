import json
import os
from typing import Any, Dict, List

DATA_DIR = os.path.dirname(__file__)
FILES = ["well_connect.json","aeropay.json","metrogrid.json"]

def read_from_file(filepath):
    """
    Reads content from a specified file and returns it.

    Args:
        filepath (str): The path to the file to be read.

    Returns:
        str: The content of the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If an I/O error occurs during reading.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
        raise
    except IOError as e:
        print(f"Error reading file '{filepath}': {e}")
        raise

def load_all_profiles(data_dir: str = DATA_DIR) -> List[Dict[str, Any]]:
    """
    Loads and aggregates profiles from multiple JSON files in the specified directory.

    Args:
        data_dir (str): The directory containing the JSON files.

    Returns:
        List[Dict[str, Any]]: A list of profiles loaded from the JSON files.    
    """
    profiles = []
    for fname in FILES:
        path = os.path.join(data_dir, fname)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            profiles.append(json.load(f))
    return profiles

PROFILES = load_all_profiles()

print(PROFILES)
