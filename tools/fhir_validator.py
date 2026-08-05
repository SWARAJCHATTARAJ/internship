from typing import Any, List


def validate_fhir_draft(resource: Any) -> List[str]:
    if not isinstance(resource, dict):
        return ["FHIR draft must be a JSON object."]

    resource_type = resource.get("resourceType")
    errors: List[str] = []

    if resource_type == "Condition":
        if not resource.get("code"):
            errors.append("Condition.code is required.")
        if not resource.get("subject"):
            errors.append("Condition.subject is required.")
    elif resource_type == "MedicationStatement":
        if not resource.get("status"):
            errors.append("MedicationStatement.status is required.")
        if not resource.get("medicationCodeableConcept"):
            errors.append("MedicationStatement.medicationCodeableConcept is required.")
    elif resource_type == "Procedure":
        if not resource.get("status"):
            errors.append("Procedure.status is required.")
        if not resource.get("code"):
            errors.append("Procedure.code is required.")
    elif resource_type == "Observation":
        if not resource.get("status"):
            errors.append("Observation.status is required.")
        if not resource.get("code"):
            errors.append("Observation.code is required.")
    elif resource_type == "Bundle":
        if not isinstance(resource.get("entry"), list):
            errors.append("Bundle.entry must be a list.")
    else:
        errors.append(f"Unsupported resource type: {resource_type}")

    return errors
