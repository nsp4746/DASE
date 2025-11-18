import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from rich import print_json
from pydantic import BaseModel, Field


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

DATA_DIR = os.path.dirname(__file__)
FILES = [".\\json\\well_connect.json", ".\\json\\aeropay.json", ".\\json\\metrogrid.json"]


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

def repl():
    print("Simple company JSON REPL. Examples:\n - tech AeroPay\n - search-tech aws\n - person 'AeroPay' 'CTO'\n - assets 'Well-Connect' PHI\n - exit")
    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            break
        if not raw:
            continue
        if raw.lower() in ("exit", "quit"):
            break
        parts = raw.split()
        cmd = parts[0].lower()
        args = parts[1:]
        if cmd == "tech" and args:
            name = " ".join(args)
            ts = get_tech_stack(name)
            if ts is None:
                print(f"Company not found: {name}")
            else:
                pretty_print(ts)
        elif cmd == "search-tech" and args:
            kw = " ".join(args)
            matches = search_companies_by_tech(kw)
            print("Matches:", matches or "None")
        elif cmd == "person" and len(args) >= 2:
            name = args[0]
            role_kw = " ".join(args[1:])
            persons = find_person_by_role(name, role_kw)
            pretty_print(persons or f"No persons found with role '{role_kw}' in {name}")
        elif cmd == "assets" and len(args) >= 2:
            name = args[0]
            sens = " ".join(args[1:])
            assets = get_assets_by_sensitivity(name, sens)
            pretty_print(assets or f"No assets found with '{sens}' in {name}")
        elif cmd == "list":
            print([p.get("company_name") for p in PROFILES])
        else:
            print("Unknown command. Try: tech, search-tech, person, assets, list, exit")

if __name__ == "__main__":
    if not PROFILES:
        print("No profiles loaded. Ensure JSON files are in the script directory.")
    else:
        repl()
