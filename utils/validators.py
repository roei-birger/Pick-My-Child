"""
Validators - Input validation utilities
"""
import re
from typing import Tuple, Optional
from pathlib import Path


def validate_event_code(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate event code format
    
    Returns:
        (is_valid, error_message)
    """
    # Expected format: EVT-XXXXX (5 digits)
    pattern = r'^EVT-\d{5}$'
    
    if not code:
        return False, "מספר אירוע לא יכול להיות ריק"
    
    if not re.match(pattern, code.upper()):
        return False, "פורמט מספר אירוע לא תקין. הפורמט הצפוי: EVT-12345"
    
    return True, None


def validate_person_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate person name
    
    Returns:
        (is_valid, error_message)
    """
    if not name or not name.strip():
        return False, "שם לא יכול להיות ריק"
    
    if len(name.strip()) < 2:
        return False, "שם חייב להכיל לפחות 2 תווים"
    
    if len(name.strip()) > 50:
        return False, "שם ארוך מדי (מקסימום 50 תווים)"
    
    return True, None


def validate_image_file(file_path: Path) -> Tuple[bool, Optional[str]]:
    """
    Validate image file
    
    Returns:
        (is_valid, error_message)
    """
    if not file_path.exists():
        return False, "הקובץ לא נמצא"
    
    # Check file extension
    valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
    if file_path.suffix.lower() not in valid_extensions:
        return False, f"סוג קובץ לא נתמך. קבצים נתמכים: {', '.join(valid_extensions)}"
    
    # Check file size (max 10MB for individual images)
    max_size = 10 * 1024 * 1024  # 10MB
    if file_path.stat().st_size > max_size:
        return False, "קובץ גדול מדי (מקסימום 10MB)"
    
    return True, None


def validate_zip_file(file_size_bytes: int, max_size_mb: int) -> Tuple[bool, Optional[str]]:
    """
    Validate ZIP file size
    
    Returns:
        (is_valid, error_message)
    """
    max_bytes = max_size_mb * 1024 * 1024
    
    if file_size_bytes > max_bytes:
        return False, f"קובץ ZIP גדול מדי. המקסימום המותר: {max_size_mb}MB"
    
    if file_size_bytes == 0:
        return False, "קובץ ZIP ריק"
    
    return True, None


def generate_event_code() -> str:
    """Generate unique event code (EVT-XXXXX)"""
    import random
    
    # Generate 5-digit random number
    code_number = random.randint(10000, 99999)
    
    return f"EVT-{code_number}"


def format_confidence_percentage(confidence: float) -> str:
    """
    Format confidence score as percentage
    
    Args:
        confidence: Float between 0 and 1
    
    Returns:
        Formatted string like "85%"
    """
    return f"{int(confidence * 100)}%"


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Returns:
        Formatted string like "2.5 MB"
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters
    
    Returns:
        Safe filename
    """
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    return filename
