
def flatten(data, prefix="", out=None):
    """
    Recursively flattens a nested dictionary.

    Args:
        data (dict): The dictionary to flatten.
        prefix (str, optional): The prefix to prepend to each key. Defaults to "".
        out (dict, optional): The dictionary to store the flattened data. Defaults to None.

    Returns:
        dict: A flattened dictionary where nested keys are concatenated into a single key with periods.
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


def unflatten(d):
    """
    Reconstructs a nested dictionary from a flattened dictionary.

    Args:
        d (dict): The flattened dictionary where keys are concatenated with periods.

    Returns:
        dict: A nested dictionary reconstructed from the flattened dictionary.
    """
    result = {}
    for k, v in d.items():
        keys = k.split(':')
        temp = result
        for key in keys[:-1]:
            if key not in temp or not isinstance(temp[key], dict):
                temp[key] = {}
            temp = temp[key]
        temp[keys[-1]] = v
    return result