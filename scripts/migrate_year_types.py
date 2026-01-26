#!/usr/bin/env python3
"""One-time migration to convert year fields from string to integer."""

import json
import gzip
import os
from pathlib import Path


def migrate_json_file(json_path: Path, upload_dir: Path):
    """Migrate year fields and regenerate compressed file."""
    print(f"Processing: {json_path.name}")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    modified = 0
    for paper in data.get('papers', []):
        if 'year' in paper and isinstance(paper['year'], str):
            try:
                paper['year'] = int(paper['year'])
                modified += 1
            except ValueError:
                print(f"  Warning: Could not convert '{paper['year']}' for: {paper.get('title', 'Unknown')[:50]}")

    # Save updated JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Regenerate compressed file
    gz_path = upload_dir / f"{json_path.stem}.json.gz"
    with gzip.open(gz_path, 'wb', compresslevel=9) as f:
        f.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    print(f"  Migrated {modified} papers, saved to {gz_path}")


def main():
    script_dir = Path(__file__).parent
    json_dir = script_dir / "../data/databases/json"
    upload_dir = script_dir / "../data/databases/upload"

    # Ensure upload directory exists
    upload_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(json_dir.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {json_dir}")
        return

    for json_file in json_files:
        migrate_json_file(json_file, upload_dir)

    print("\nDone! Now copy .gz files to paper-explorer-data/papers/ and commit.")


if __name__ == "__main__":
    main()
