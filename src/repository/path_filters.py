from pathlib import Path

ALWAYS_EXCLUDE: set[str] = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".eggs",
    "node_modules",
    "build",
    "dist"
}

CONDITIONAL_EXCLUDE: set[str] = {
    "env",
    "ENV",
    "venv",
    ".venv",
    "virtualenv"
}

def is_virtual_environment(directory: Path) -> bool:
    """
    Checks if a directory looks like a Python virtual environment.
    """
    return (
        (directory / "pyvenv.cfg").exists()
        or (directory / "bin" / "python").exists()
        or (directory / "bin" / "python3").exists()
        or (directory / "Scripts" / "python.exe").exists()
    )

def should_exclude_directory(path: Path) -> tuple[bool, str | None]:
    """
    Checks if a given directory path should be excluded from scanning.
    Returns a tuple of (should_exclude: bool, reason: str | None).
    """
    name = path.name
    
    if name in ALWAYS_EXCLUDE:
        if name == ".git":
            return True, "repository_metadata"
        return True, "cache_or_build_directory"
        
    if name in CONDITIONAL_EXCLUDE and is_virtual_environment(path):
        return True, "virtual_environment_detected"
            
    return False, None
