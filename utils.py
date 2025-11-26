import json
import os
import shlex
import sys
import time
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from rich import print_json
from pydantic import BaseModel, Field
from itertools import cycle
from contextlib import contextmanager


class Turn(BaseModel):
    role: str
    text: str
    raw_chunks: List[Dict[str, Any]] = Field(default_factory=list)


class SessionLog(BaseModel):
    turns: List[Turn] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_turn(self, role: str, text: str, raw_chunks: Optional[List[Dict[str, Any]]] = None) -> None:
        """Append a turn to the log."""
        self.turns.append(Turn(role=role, text=text, raw_chunks=raw_chunks or []))

    def add_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value

# --- Constants and Profile Loading ---
DATA_DIR = os.path.dirname(__file__)
JSON_DIR = os.path.join(DATA_DIR, "json")

COMPANY_MAP = {
    "Well Connect": os.path.join(JSON_DIR, "well_connect.json"),
    "AeroPay": os.path.join(JSON_DIR, "aeropay.json"),
    "MetroGrid Manufacturing": os.path.join(JSON_DIR, "metrogrid.json"),
}


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
    for path in COMPANY_MAP.values():
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f: # path is already absolute
            profiles.append(json.load(f))
    return profiles


PROFILES = load_all_profiles()


def get_company(name: str) -> Dict[str, Any] | None:
    name_lower = name.strip().lower()
    for profile in PROFILES:
        if name_lower in profile.get("company_name", "").lower():
            return profile
    return None


def get_tech_stack(company_name: str) -> Dict[str, Any] | None:
    comp = get_company(company_name)
    if not comp:
        return None
    return comp.get("technology_stack")


def search_companies_by_tech(tech_keyword: str) -> List[str]:
    tech_keyword = tech_keyword.lower()
    matches = []
    for p in PROFILES:
        tech = p.get("technology_stack", {})
        # flatten tech values to a single searchable string

        def flatten(obj):
            if isinstance(obj, dict):
                vals = []
                for v in obj.values():
                    vals.append(flatten(v))
                return " ".join(vals)
            if isinstance(obj, list):
                return " ".join([flatten(x) for x in obj])
            return str(obj)
        tech_blob = flatten(tech).lower()
        if tech_keyword in tech_blob:
            matches.append(p.get("company_name"))
    return matches


def find_person_by_role(company_name: str, role_keyword: str) -> List[Dict[str, Any]]:
    comp = get_company(company_name)
    if not comp:
        return []
    out = []
    for person in comp.get("key_personnel", []):
        if role_keyword.lower() in person.get("role", "").lower() or role_keyword.lower() in person.get("name", "").lower():
            out.append(person)
    return out


def get_assets_by_sensitivity(company_name: str, sensitivity_keyword: str) -> List[Dict[str, Any]]:
    comp = get_company(company_name)
    if not comp:
        return []
    out = []
    for asset in comp.get("key_digital_assets", []):
        if sensitivity_keyword.lower() in str(asset).lower():
            out.append(asset)
    return out

def get_all_personnel(company_name: str) -> List[Dict[str, Any]]:
    """Returns all key personnel for a given company."""
    comp = get_company(company_name)
    if not comp:
        return []
    return comp.get("key_personnel", [])

def get_all_assets(company_name: str) -> List[Dict[str, Any]]:
    """Returns all key digital assets for a given company."""
    comp = get_company(company_name)
    if not comp:
        return []
    return comp.get("key_digital_assets", [])

def get_security_posture(company_name: str) -> Dict[str, Any] | None:
    """Returns the security posture for a given company."""
    comp = get_company(company_name)
    if not comp:
        return None
    return comp.get("security_posture")


def pretty_print(obj):
    if isinstance(obj, (dict, list)):
        print_json(data=obj)
    else:
        print(obj)


def save_session(session: SessionLog, directory: str = "session_logs") -> str:
    """
    Persist a SessionLog to disk as JSON.

    Args:
        session (SessionLog): The session to persist.
        directory (str): Directory for storing logs.

    Returns:
        str: Absolute path to the saved session file.
    """
    if not isinstance(session, SessionLog):
        raise TypeError("save_session expects a SessionLog instance.")

    os.makedirs(directory, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_name = f"Session_log({timestamp}).json"
    path = os.path.join(directory, file_name)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(session.model_dump(), f, indent=2)

    return os.path.abspath(path)

def _animate(stop_event: threading.Event, message: str):
    """Displays a simple loading animation in the console."""
    animation = cycle(['.  ', '.. ', '...', ' ..', '  .'])
    while not stop_event.is_set():
        try:
            # Use len(message) to dynamically adjust clearing space
            sys.stdout.write(f"\r{message} " + next(animation))
            sys.stdout.flush()
            time.sleep(0.2)
        except (IOError, BrokenPipeError):
            # Handle cases where stdout is closed, e.g., during exit
            break
    # Clear the loading line
    sys.stdout.write("\r" + " " * (len(message) + 5) + "\r")
    sys.stdout.flush()

@contextmanager
def loading_indicator(message: str = "Generating response"):
    """A context manager to display a loading animation for a block of code."""
    stop_event = threading.Event()
    loading_thread = threading.Thread(target=_animate, args=(stop_event, message))
    loading_thread.start()
    yield
    stop_event.set()
    loading_thread.join()

def select_company_from_cli() -> Tuple[Dict | None, str | None]:
    """
    Prompts the user to select a company via the CLI and loads its profile.

    Returns:
        A tuple containing the loaded company profile (dict) and its string representation,
        or (None, None) if the selection is invalid.
    """
    print("\nEnter company to perform exercise on:")
    company_options = {str(i + 1): name for i, name in enumerate(COMPANY_MAP.keys())}
    for num, name in company_options.items():
        print(f" {num}: {name}")

    choice = input("Please select one: ").strip()
    company_name = company_options.get(choice)

    if not company_name:
        print("Invalid company selection.")
        return None, None

    company_file = COMPANY_MAP.get(company_name)
    with open(company_file, 'r', encoding='utf-8') as f:
        profile = json.load(f)
    profile_str = json.dumps(profile, indent=2)
    return profile, profile_str

def repl():
    """A simple REPL for querying company profile data."""
    help_text = """
Simple company JSON REPL. Commands:
  - list                                      List all available company names.
  - tech <company_name>                       Get the tech stack for a company.
  - search-tech <keyword>                     Search for companies using a specific technology.
  - person <company_name> <role_keyword>      Find a person by role or name in a company.
  - assets <company_name> <sensitivity_keyword> Get assets by a sensitivity keyword.
  - list-personnel <company_name>             List all personnel for a company.
  - list-assets <company_name>                List all digital assets for a company.
  - security-posture <company_name>           Get the security posture for a company.
  - help                                      Show this help message.
  - exit / quit                               Exit the REPL.

Note: Wrap arguments with spaces in quotes (e.g., tech "Well Connect").
"""
    print(help_text)

    while True:
        try:
            raw = input("> ").strip()
            if not raw:
                continue

            parts = shlex.split(raw)
            cmd = parts[0].lower()
            args = parts[1:]

        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            break
        except ValueError:
            print("Error: Unmatched quote in input.")
            continue

        if cmd in ("exit", "quit"):
            break

        if cmd == "tech" and len(args) == 1:
            ts = get_tech_stack(args[0])
            if ts is None:
                print(f"Company not found: {args[0]}")
            else:
                pretty_print(ts)
        elif cmd == "search-tech" and len(args) == 1:
            matches = search_companies_by_tech(args[0])
            print("Matches:", matches or "None")
        elif cmd == "person" and len(args) >= 2:
            company_name, role_keyword = args[0], " ".join(args[1:])
            persons = find_person_by_role(company_name, role_keyword)
            pretty_print(persons or f"No persons found with role '{role_keyword}' in {company_name}")
        elif cmd == "assets" and len(args) >= 2:
            company_name, sensitivity = args[0], " ".join(args[1:])
            assets = get_assets_by_sensitivity(company_name, sensitivity)
            pretty_print(assets or f"No assets found with '{sensitivity}' in {company_name}")
        elif cmd == "list-personnel" and len(args) == 1:
            personnel = get_all_personnel(args[0])
            pretty_print(personnel or f"No personnel found for {args[0]}")
        elif cmd == "list-assets" and len(args) == 1:
            assets = get_all_assets(args[0])
            pretty_print(assets or f"No assets found for {args[0]}")
        elif cmd == "security-posture" and len(args) == 1:
            posture = get_security_posture(args[0])
            pretty_print(posture or f"No security posture found for {args[0]}")
        elif cmd == "list":
            print([p.get("company_name") for p in PROFILES])
        elif cmd == "help":
            print(help_text)
        else:
            print("Unknown command or incorrect arguments. Type 'help' for usage.")

if __name__ == "__main__":
    if not PROFILES:
        print("No profiles loaded. Ensure JSON files are in the script directory.")
    else:
        repl()
