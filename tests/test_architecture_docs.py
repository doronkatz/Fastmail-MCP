from pathlib import Path

DOC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "system-architecture-deployment-plan.md"
)

REQUIRED_SNIPPETS = [
    "# System Architecture and Deployment Plan",
    "## Component Responsibilities",
    "## Data Flow",
    "## Configuration and Secrets",
    "## Observability Strategy",
    "### Local deployment",
    "### Azure deployment",
    "```mermaid",
]


def test_architecture_doc_exists() -> None:
    assert DOC_PATH.exists(), "Expected architecture doc to exist"


def test_architecture_doc_has_required_sections() -> None:
    content = DOC_PATH.read_text(encoding="utf-8")
    missing = [snippet for snippet in REQUIRED_SNIPPETS if snippet not in content]
    assert not missing, f"Missing required sections/snippets: {missing}"
