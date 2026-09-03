import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .path_filters import should_exclude_directory


@dataclass
class DiscoveryResult:
    scanned_files: list[str] = field(default_factory=list)
    total_files: int = 0
    python_files_found: int = 0
    non_python_files: int = 0
    python_files_scanned: int = 0
    python_files_excluded: int = 0
    encountered_exclusions: list[dict[str, Any]] = field(default_factory=list)

def discover_python_files(target_dir: str) -> DiscoveryResult:
    """
    Recursively discovers all .py files in the target directory,
    excluding common non-repository environments and caches,
    while keeping strict accounting of file counts.
    """
    repo_root = Path(os.path.abspath(target_dir))
    result = DiscoveryResult()
    
    for root, dirs, files in os.walk(repo_root):
        current_path = Path(root)
        
        # Identify directories to prune
        to_prune = []
        for d in dirs:
            exclude, reason = should_exclude_directory(current_path / d)
            if exclude:
                to_prune.append((d, reason))
                
        # Prune them and manually count their contents
        for d, reason in to_prune:
            dirs.remove(d)
            pruned_path = current_path / d
            
            dir_py_excluded = 0
            
            for _p_root, _p_dirs, p_files in os.walk(pruned_path):
                result.total_files += len(p_files)
                for f in p_files:
                    if f.endswith(".py"):
                        result.python_files_found += 1
                        result.python_files_excluded += 1
                        dir_py_excluded += 1
                    else:
                        result.non_python_files += 1
                        
            result.encountered_exclusions.append({
                "path": d,
                "reason": reason,
                "python_files_excluded": dir_py_excluded
            })
                        
        # Process files in the current (non-excluded) directory
        result.total_files += len(files)
        for file in files:
            if file.endswith(".py"):
                result.python_files_found += 1
                result.python_files_scanned += 1
                result.scanned_files.append(os.path.join(root, file))
            else:
                result.non_python_files += 1
                
    return result
