import json
from collections import Counter
from pathlib import Path

DATASET_PATH = (
    Path(__file__).resolve().parents[2] / "datasets" / "message_classification.jsonl"
)

records = [
    json.loads(line)
    for line in DATASET_PATH.read_text(encoding="utf-8").splitlines()
    if line.strip()
]

assert len(records) == 20, f"Expected 20 records, got {len(records)}"

ids = [record["id"] for record in records]
assert len(ids) == len(set(ids)), "Duplicate IDs found"

categories = Counter(record["expected_category"] for record in records)
assert categories == {"pregunta": 10, "queja": 10}, categories

for record in records:
    assert record["input"].strip(), f"Empty input in {record['id']}"
    assert record["case_type"].strip(), f"Missing case type in {record['id']}"

print(f"Dataset validated: {len(records)} records")
print(f"Categories: {dict(categories)}")
