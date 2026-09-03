from .models import Finding


def validate_finding_evidence(finding: Finding, valid_relationship_ids: set[str]) -> bool:
    """Validates that a finding adheres to the evidence rules:

    - For structural GoF patterns: requires non-empty, valid relationship IDs.
    - For negative/risk patterns like dead code: allows AST fact references / empty graph edges.
    """
    if finding.detector_id == "dead_code":
        return True

    if not finding.evidence_relationship_ids:
        return False

    for ev_id in finding.evidence_relationship_ids:
        if ev_id not in valid_relationship_ids:
            return False

    return True
