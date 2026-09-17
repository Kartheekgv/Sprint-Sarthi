import pytest
from pydantic import ValidationError

from app.schemas.provenance import ProvenanceValue, SourceReference


def test_extracted_provenance_requires_a_source():
    with pytest.raises(ValidationError):
        ProvenanceValue[str](value="Authentication", origin="extracted", confidence=0.9)


def test_unsupported_inference_requires_review():
    with pytest.raises(ValidationError):
        ProvenanceValue[str](value="High", origin="inferred", confidence=0.6)


def test_source_grounded_value_is_valid():
    reference = SourceReference(
        document_id="DOC-001",
        file_name="requirements.md",
        section_heading="Authentication",
        chunk_id="CHUNK-001",
        quoted_text="Administrators approve access requests.",
    )
    value = ProvenanceValue[str](
        value="Administrators approve access requests",
        origin="extracted",
        confidence=0.95,
        source_references=[reference],
    )
    assert value.requires_review is False