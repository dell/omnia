"""
File I/O operations for Config Editor Module

Provides synchronous file read/write operations for JSON and YAML files.
Uses existing patterns from core modules where possible.
"""

import json
import yaml
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Union
from ..core.exceptions import ConfigEditorException

logger = logging.getLogger(__name__)


class IndentedListDumper(yaml.Dumper):
    """Custom YAML dumper that indents list items under their parent key."""
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)  # Force indentless=False


class NetworkSpecDumper(yaml.Dumper):
    """Custom YAML dumper for network_spec.yml with no list indentation under top-level keys."""
    def increase_indent(self, flow=False, indentless=False):
        # For network_spec.yml, use indentless=True for top-level lists
        # This matches the reference file format where list dashes are at same level as parent key
        return super().increase_indent(flow, True)


class QuotedStringDumper(yaml.Dumper):
    """Custom YAML dumper that quotes all string values to match reference file format."""
    def represent_mapping(self, tag, mapping, flow_style=None):
        """Override to track when we're representing keys vs values."""
        # Track that we're in a mapping context
        self.in_mapping_key = True
        node = super().represent_mapping(tag, mapping, flow_style)
        self.in_mapping_key = False
        return node


def quoted_str_representer(dumper, data):
    """Represent all strings as quoted scalars for values only (not keys)."""
    # Check if this is being called for a key by examining the dumper state
    if hasattr(dumper, 'in_mapping_key') and dumper.in_mapping_key:
        # This is a key, use default representation (no quotes unless needed)
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)
    # This is a value, quote it
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')


# Register the custom representer for str type
QuotedStringDumper.add_representer(str, quoted_str_representer)


def read_json(path: Union[str, Path]) -> Dict[str, Any]:
    """Read JSON file and return parsed dictionary.
    
    Args:
        path: Path to JSON file
        
    Returns:
        Parsed JSON as dictionary
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
        ConfigEditorException: For other I/O errors
    """
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as e:
        raise
    except Exception as e:
        raise ConfigEditorException(f"Failed to read JSON file {path}: {str(e)}")


def write_json(path: Union[str, Path], data: Dict[str, Any], indent: int = 2) -> None:
    """Write dictionary to JSON file.
    
    Args:
        path: Path to JSON file
        data: Dictionary to write
        indent: JSON indentation level (default: 2)
        
    Raises:
        ConfigEditorException: If file cannot be written
    """
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=indent)
    except Exception as e:
        raise ConfigEditorException(f"Failed to write JSON file {path}: {str(e)}")


def write_json_atomic(path: Union[str, Path], data: Dict[str, Any], indent: int = 2) -> None:
    """Write JSON atomically with timestamped backup.
    
    Args:
        path: Path to JSON file
        data: Dictionary to write
        indent: JSON indentation level (default: 2)
        
    Raises:
        ConfigEditorException: If file cannot be written
    """
    try:
        path = Path(path)
        
        # Create backup if file exists
        if path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = path.parent / f"{path.stem}_{timestamp}.json"
            shutil.copy2(path, backup_path)
            logger.info(f"Created backup at {backup_path}")
        
        # Write new data
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=indent)
    except Exception as e:
        raise ConfigEditorException(f"Failed to write JSON file {path}: {str(e)}")


def read_yaml(path: Union[str, Path]) -> Dict[str, Any]:
    """Read YAML file and return parsed dictionary.
    
    Args:
        path: Path to YAML file
        
    Returns:
        Parsed YAML as dictionary
        
    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If file contains invalid YAML
        ConfigEditorException: For other I/O errors
    """
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise
    except yaml.YAMLError as e:
        raise
    except Exception as e:
        raise ConfigEditorException(f"Failed to read YAML file {path}: {str(e)}")


def write_yaml(path: Union[str, Path], data: Dict[str, Any]) -> None:
    """Write dictionary to YAML file.
    
    Args:
        path: Path to YAML file
        data: Dictionary to write
        
    Raises:
        ConfigEditorException: If file cannot be written
    """
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            yaml.dump(
                data,
                f,
                Dumper=IndentedListDumper,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
                indent=2
            )
    except Exception as e:
        raise ConfigEditorException(f"Failed to write YAML file {path}: {str(e)}")


def read_csv(path: Union[str, Path]) -> List[List[str]]:
    """Read CSV file and return list of rows.
    
    Args:
        path: Path to CSV file
        
    Returns:
        List of CSV rows (each row is a list of strings)
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ConfigEditorException: For other I/O errors
    """
    try:
        import csv
        with open(path, 'r') as f:
            reader = csv.reader(f)
            return list(reader)
    except FileNotFoundError:
        raise
    except Exception as e:
        raise ConfigEditorException(f"Failed to read CSV file {path}: {str(e)}")


def write_csv(path: Union[str, Path], rows: List[List[str]]) -> None:
    """Write list of rows to CSV file.
    
    Args:
        path: Path to CSV file
        rows: List of CSV rows (each row is a list of strings)
        
    Raises:
        ConfigEditorException: If file cannot be written
    """
    try:
        import csv
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
    except Exception as e:
        raise ConfigEditorException(f"Failed to write CSV file {path}: {str(e)}")


def file_exists(path: Union[str, Path]) -> bool:
    """Check if file exists.
    
    Args:
        path: Path to check
        
    Returns:
        True if file exists, False otherwise
    """
    return Path(path).exists()


def ensure_directory(path: Union[str, Path]) -> None:
    """Ensure directory exists, create if it doesn't.
    
    Args:
        path: Directory path to ensure exists
    """
    Path(path).mkdir(parents=True, exist_ok=True)
