"""
QASIC Digital Twin Utilities
Helper functions and utilities for the digital twin platform
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
import logging

def setup_logging(level: str = "INFO") -> logging.Logger:
    """Setup logging for the digital twin platform"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('digital_twin.log')
        ]
    )
    return logging.getLogger('digital_twin')

def compute_design_hash(design_data: Dict[str, Any]) -> str:
    """Compute SHA256 hash of design for caching purposes"""
    # Create a normalized JSON string for consistent hashing
    normalized_json = json.dumps(design_data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(normalized_json.encode('utf-8')).hexdigest()

def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Load and parse a JSON file"""
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json_file(data: Dict[str, Any], file_path: Path, indent: int = 2) -> None:
    """Save data to a JSON file"""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=indent)

def ensure_directory(path: Path) -> None:
    """Ensure a directory exists, creating it if necessary"""
    path.mkdir(parents=True, exist_ok=True)

def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.1f}s"

def validate_file_exists(file_path: Path, description: str = "File") -> None:
    """Validate that a file exists, raising FileNotFoundError if not"""
    if not file_path.exists():
        raise FileNotFoundError(f"{description} not found: {file_path}")

def get_file_size_mb(file_path: Path) -> float:
    """Get file size in megabytes"""
    return file_path.stat().st_size / (1024 * 1024)

def create_backup_file(file_path: Path) -> Path:
    """Create a backup of a file with timestamp"""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.with_suffix(f".backup_{timestamp}{file_path.suffix}")
    backup_path.write_text(file_path.read_text())
    return backup_path