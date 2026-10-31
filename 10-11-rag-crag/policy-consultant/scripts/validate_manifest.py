"""CLI entry point: validate config/corpus-manifest.yaml.

The validation rules themselves live in policy_consultant.corpus_manifest,
where they can be imported and unit-tested directly; this script only wires
them to the command line.
"""

from pathlib import Path

from policy_consultant.corpus_manifest import load_documents, validate_manifest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_ROOT / "config" / "corpus-manifest.yaml"


def main() -> None:
    documents = load_documents(MANIFEST_PATH)
    print(validate_manifest(documents, PROJECT_ROOT))


if __name__ == "__main__":
    main()
