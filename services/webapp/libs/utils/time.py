import time
from datetime import datetime


def now(iso_format=False):
    """
    Get current timestamp.
    
    Args:
        iso_format (bool): If True, return ISO formatted date string
                          If False, return millisecond timestamp
    
    Returns:
        str: ISO formatted timestamp if iso_format=True
        int: Millisecond timestamp if iso_format=False
    """
    if iso_format:
        return datetime.now().isoformat()  # Returns ISO string
    else:
        return int(time.time() * 1000)  # Returns millisecond timestamp


 