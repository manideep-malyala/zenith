import re
import subprocess
import urllib.parse
from dataclasses import dataclass


@dataclass
class GitMetadata:
    branch: str | None = None
    commit_sha: str | None = None
    url: str | None = None
    host: str | None = None
    owner: str | None = None

def get_git_metadata(repo_path: str) -> GitMetadata:
    """
    Attempts to retrieve git metadata for the given repository path.
    Returns None for fields that cannot be retrieved.
    """
    meta = GitMetadata()
    try:
        # Get commit SHA
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        meta.commit_sha = result.stdout.strip()
        
        # Get branch
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        branch = result.stdout.strip()
        if branch != "HEAD":
            meta.branch = branch
            
        # Get URL
        result = subprocess.run(
            ['git', 'config', '--get', 'remote.origin.url'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        meta.url = result.stdout.strip()
        
        # Parse Host and Owner
        if meta.url:
            # Handle SSH formats like git@github.com:microsoft/apm.git
            if meta.url.startswith("git@") or meta.url.startswith("ssh://"):
                # git@github.com:microsoft/apm.git
                match = re.search(r'[@/]([\w.-]+)[:/]([\w.-]+)/', meta.url)
                if match:
                    meta.host = match.group(1)
                    meta.owner = match.group(2)
            else:
                # HTTP/HTTPS formats like https://github.com/microsoft/apm.git
                parsed = urllib.parse.urlparse(meta.url)
                meta.host = parsed.netloc
                parts = parsed.path.strip('/').split('/')
                if len(parts) >= 2:
                    meta.owner = parts[0]
                    
    except (subprocess.SubprocessError, OSError):
        pass
        
    return meta
