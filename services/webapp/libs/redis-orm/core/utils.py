"""
Internal utilities for Redis ORM.
Self-contained implementations without external dependencies.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict
from nanoid import generate as nanoid_generate


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name."""
    return logging.getLogger(name)


def now() -> str:
    """Generate current timestamp as ISO 8601 string."""
    current_time = datetime.now(timezone.utc)
    return current_time.strftime('%Y-%m-%dT%H:%M:%SZ')


ALPHABET = '0123456789abcdef'
def new_id(size=10) -> str:
    '''Generates Random ID, suited for Internal Object IDs'''
    return nanoid_generate(ALPHABET, size)


def flatten(data: Dict[str, Any], prefix: str = "", out: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Recursively flattens a nested dictionary.

    Args:
        data: The dictionary to flatten.
        prefix: The prefix to prepend to each key.
        out: The dictionary to store the flattened data.

    Returns:
        A flattened dictionary where nested keys are concatenated with colons.
    """
    if out is None:
        out = {}
        
    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{prefix}:{k}".strip(":")
            flatten(v, new_key, out)
    else:
        out[prefix] = data
        
    return out


def unflatten(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reconstructs a nested dictionary from a flattened dictionary.

    Args:
        d: The flattened dictionary where keys are concatenated with colons.

    Returns:
        A nested dictionary reconstructed from the flattened dictionary.
    """
    result = {}
    for k, v in d.items():
        keys = k.split(':')
        temp = result
        for key in keys[:-1]:
            if key not in temp or not isinstance(temp[key], dict):
                temp[key] = {}
            temp = temp[key]
        final_key = keys[-1]
        temp[final_key] = v
    
    return result 