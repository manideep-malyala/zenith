from src.repository.scanner import MetadataFact

from .models import PredicateResult


class MetadataPredicates:
    """Predicates evaluated from repository filesystem metadata."""
    
    def __init__(self, fact: MetadataFact):
        self.fact = fact

    def _result(self, matched: bool, signals: list[str], evidence: str) -> PredicateResult:
        return PredicateResult(
            matched=matched,
            confidence="HIGH" if matched else "LOW",
            signals=tuple(signals) if matched else (),
            explanation=evidence if matched else ""
        )

    # Repository structural concepts
    def has_repository_layout(self) -> PredicateResult:
        matched = len(self.fact.directories_present) > 0
        return self._result(matched, ["repository_layout"], "Found repository directories.")

    def has_packages(self) -> PredicateResult:
        matched = "setup.py" in self.fact.files_present or "pyproject.toml" in self.fact.files_present
        return self._result(matched, ["packages"], "Found packaging configuration (setup.py or pyproject.toml).")

    def has_modules(self) -> PredicateResult:
        # All repositories have modules
        return self._result(True, ["modules"], "Repository contains Python modules.")

    def has_source_directories(self) -> PredicateResult:
        matched = "src" in self.fact.directories_present
        return self._result(matched, ["source_directories"], "Found 'src' directory.")

    def has_test_directories(self) -> PredicateResult:
        matched = "tests" in self.fact.directories_present or "test" in self.fact.directories_present
        return self._result(matched, ["test_directories"], "Found test directories.")

    def has_configuration_directories(self) -> PredicateResult:
        matched = "config" in self.fact.directories_present or "conf" in self.fact.directories_present
        return self._result(matched, ["configuration_directories"], "Found configuration directories.")

    def has_scripts(self) -> PredicateResult:
        matched = "scripts" in self.fact.directories_present or "bin" in self.fact.directories_present
        return self._result(matched, ["scripts"], "Found scripts directory.")

    def has_documentation(self) -> PredicateResult:
        matched = "docs" in self.fact.directories_present or "readme.md" in self.fact.files_present
        return self._result(matched, ["documentation"], "Found documentation.")

    def has_entry_points(self) -> PredicateResult:
        matched = "main.py" in self.fact.files_present or "app.py" in self.fact.files_present
        return self._result(matched, ["entry_points"], "Found common entry point files (main.py, app.py).")

    def has_generated_vendor_directories(self) -> PredicateResult:
        matched = "vendor" in self.fact.directories_present
        return self._result(matched, ["vendor_directories"], "Found vendor directory.")

    # Configuration concepts
    def has_json_configuration(self) -> PredicateResult:
        matched = any(f.endswith(".json") for f in self.fact.files_present)
        return self._result(matched, ["json_configuration"], "Found JSON files.")

    def has_cli_configuration(self) -> PredicateResult:
        return self._result(False, [], "Cannot statically determine CLI configuration from files.")

    def has_deployment_configuration(self) -> PredicateResult:
        matched = self.fact.has_docker or self.fact.has_k8s or self.fact.has_ci
        return self._result(matched, ["deployment_configuration"], "Found Docker, K8s, or CI configuration.")

    def has_package_publishing(self) -> PredicateResult:
        return self.has_packages()
        
    def has_docker(self) -> PredicateResult:
        return self._result(self.fact.has_docker, ["docker"], "Found Dockerfile or docker-compose.yml.")

    def has_kubernetes(self) -> PredicateResult:
        return self._result(self.fact.has_k8s, ["kubernetes"], "Found k8s/kubernetes directory.")
        
    def has_ci_cd(self) -> PredicateResult:
        return self._result(self.fact.has_ci, ["ci_cd"], "Found CI configuration (.github/workflows).")
        
    # Provide stubs for all other EXTERNAL_METADATA to return false so we don't break capability mappings
    def has_generic_metadata(self) -> PredicateResult:
        return self._result(True, ["metadata"], "Evaluated metadata.")
        
    def uses_yaml_config(self) -> PredicateResult:
        matched = any(f.endswith((".yml", ".yaml")) for f in self.fact.files_present)
        return self._result(matched, ["yaml_configuration"], "Found YAML files.")

    def is_python_package(self) -> PredicateResult:
        return self.has_packages()

    def uses_toml_config(self) -> PredicateResult:
        matched = any(f.endswith(".toml") for f in self.fact.files_present)
        return self._result(matched, ["toml_configuration"], "Found TOML configuration files.")

    def uses_ini_config(self) -> PredicateResult:
        matched = any(f.endswith((".ini", ".cfg")) for f in self.fact.files_present)
        return self._result(matched, ["ini_configuration"], "Found INI/CFG configuration files.")

    def uses_docker(self) -> PredicateResult:
        return self.has_docker()

    def uses_kubernetes(self) -> PredicateResult:
        return self.has_kubernetes()

    def uses_helm(self) -> PredicateResult:
        matched = any("chart.yaml" in f.lower() or "helm" in f.lower() for f in self.fact.files_present)
        return self._result(matched, ["helm"], "Found Helm configuration.")

    def uses_ci_cd(self) -> PredicateResult:
        return self.has_ci_cd()

    def uses_github_actions(self) -> PredicateResult:
        matched = any(".github" in d for d in self.fact.directories_present) or any(".github" in f for f in self.fact.files_present)
        return self._result(matched, ["github_actions"], "Found GitHub Actions workflows.")

    def uses_environment_variables_config(self) -> PredicateResult:
        matched = any(".env" in f for f in self.fact.files_present)
        return self._result(matched, ["env_configuration"], "Found .env configuration files.")
