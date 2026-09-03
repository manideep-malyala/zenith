import os
from dataclasses import dataclass, field


@dataclass
class MetadataFact:
    project_root: str
    files_present: set[str] = field(default_factory=set)
    directories_present: set[str] = field(default_factory=set)
    has_docker: bool = False
    has_k8s: bool = False
    has_ci: bool = False

class RepositoryScanner:
    def __init__(self, project_root: str):
        self.project_root = project_root
        
    def scan(self) -> MetadataFact:
        fact = MetadataFact(project_root=self.project_root)
        if not os.path.exists(self.project_root):
            return fact
            
        for item in os.listdir(self.project_root):
            path = os.path.join(self.project_root, item)
            if os.path.isfile(path):
                fact.files_present.add(item.lower())
            elif os.path.isdir(path):
                fact.directories_present.add(item.lower())
                
        # Check subdirectories for specific config
        if os.path.isdir(os.path.join(self.project_root, ".github", "workflows")):
            fact.has_ci = True
            
        if "dockerfile" in fact.files_present or "docker-compose.yml" in fact.files_present:
            fact.has_docker = True
            
        if "k8s" in fact.directories_present or "kubernetes" in fact.directories_present:
            fact.has_k8s = True
            
        return fact
