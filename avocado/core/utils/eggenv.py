import importlib.metadata
import os
import pathlib


def get_python_path_env_if_egg():
    """
    Returns an environment mapping with an extra PYTHONPATH for the egg or None

    When running Avocado Python modules, the interpreter on the new
    process needs to know where Avocado can be found.  This is usually
    handled by the Avocado installation being available to the
    standard Python installation, but if Avocado is running from an
    uninstalled egg, it needs extra help.

    :returns: environment mapping with an extra PYTHONPATH for the egg or None
    :rtype: os.environ mapping or None
    """
    dist = importlib.metadata.distribution("avocado-framework")
    path = dist.locate_file("")
    if isinstance(path, pathlib.Path):
        return None

    python_path = os.environ.get("PYTHONPATH", "")
    python_path_entries = python_path.split(":")
    if path.root.filename in python_path_entries:
        return None

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{path.root.filename}:{python_path}"
    return env
