#!/usr/bin/env python3
"""
Topic Migration Script for Paper Explorer

Operations:
- DELETE: Remove topics and all associated papers
- MERGE: Combine multiple topics into one
- RENAME: Change topic names

Usage:
    python migrate_topics.py --dry-run   # Preview changes
    python migrate_topics.py             # Execute migration
"""

import json
import gzip
import csv
import argparse
import shutil
from pathlib import Path
from typing import Set, Dict, List, Tuple
from collections import defaultdict

# =============================================================================
# CONFIGURATION
# =============================================================================

TOPICS_TO_DELETE: Set[str] = {
    "altimetry",
    "bias_correction",
    "comparative_studies",
    "data_assimilation",
    "hec",
    "iot",
    "nwp",
    "rhessys",
    "surrogate",
    "wrf",
    "satellite-application-et",
    "satellite-application-ET",
    "satellite-application-discharge",
    "satellite-application-flood",
    "satellite-application-rainfall-hydrological-modelling",
}

# source -> target
TOPICS_TO_MERGE: Dict[str, str] = {
    "dynamic-calibration": "optimization",
    "optimization-tool": "optimization",
    "soil-erosion": "sediment",
    "web-mapping-development": "software-development",
    "storage-structure": "reservoir",
}

# old -> new
TOPICS_TO_RENAME: Dict[str, str] = {
    "wavelet": "frequency-analysis",
    "satellite-application-grace": "grace",
}

# =============================================================================
# PATHS
# =============================================================================

BASE_PATH = Path(__file__).parent.parent
JSON_DIR = BASE_PATH / "data" / "databases" / "json"
CSV_DIR = BASE_PATH / "data" / "databases" / "csv"
UPLOAD_DIR = BASE_PATH / "data" / "databases" / "upload"
DATA_REPO_PATH = BASE_PATH.parent / "paper-explorer-data" / "papers"

TOPIC_CSV = CSV_DIR / "unique_topic.csv"
PAPER_ID_CSV = CSV_DIR / "unique_paper_id.csv"

# =============================================================================
# CLASSES
# =============================================================================


class MigrationStats:
    def __init__(self):
        self.papers_deleted = 0
        self.papers_merged = 0
        self.papers_renamed = 0
        self.deleted_paper_ids: Set[str] = set()
        self.topics_deleted: Set[str] = set()
        self.topics_merged: Dict[str, int] = defaultdict(int)
        self.topics_renamed: Dict[str, int] = defaultdict(int)

    def print_summary(self):
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"\nPapers deleted: {self.papers_deleted}")
        print(f"Papers with merged topics: {self.papers_merged}")
        print(f"Papers with renamed topics: {self.papers_renamed}")
        print(f"\nDeleted paper IDs collected: {len(self.deleted_paper_ids)}")

        if self.topics_deleted:
            print(f"\nTopics deleted ({len(self.topics_deleted)}):")
            for topic in sorted(self.topics_deleted):
                print(f"  - {topic}")

        if self.topics_merged:
            print(f"\nTopics merged:")
            for merge, count in sorted(self.topics_merged.items()):
                print(f"  - {merge}: {count} papers")

        if self.topics_renamed:
            print(f"\nTopics renamed:")
            for rename, count in sorted(self.topics_renamed.items()):
                print(f"  - {rename}: {count} papers")


class TopicMigrator:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.stats = MigrationStats()
        self.final_topics: Set[str] = set()

    def run(self):
        """Execute the full migration."""
        prefix = "[DRY RUN] " if self.dry_run else ""
        print(f"{prefix}Starting topic migration...")
        print(f"  JSON directory: {JSON_DIR}")
        print(f"  CSV directory: {CSV_DIR}")

        # Process each JSON file
        json_files = sorted(JSON_DIR.glob("*.json"))
        print(f"\nFound {len(json_files)} JSON files to process")

        for json_file in json_files:
            self.process_json_file(json_file)

        # Update topic CSV
        self.update_topic_csv()

        # Update paper ID CSV
        self.update_paper_id_csv()

        # Compress and copy files
        self.regenerate_compressed()

        # Print summary
        self.stats.print_summary()

        if self.dry_run:
            print("\n[DRY RUN] No changes were made to any files.")
        else:
            print("\nMigration completed successfully!")

    def process_paper(self, paper: dict) -> Tuple[dict | None, str]:
        """
        Process a single paper's topics.
        Returns: (modified_paper or None if deleted, action_taken)
        """
        if "topic" not in paper or not paper["topic"]:
            return paper, "unchanged"

        original_topics = set(paper["topic"])
        paper_id = paper.get("id", "unknown")

        # Check if paper should be deleted
        if original_topics & TOPICS_TO_DELETE:
            self.stats.papers_deleted += 1
            self.stats.deleted_paper_ids.add(paper_id)
            for topic in original_topics & TOPICS_TO_DELETE:
                self.stats.topics_deleted.add(topic)
            return None, "deleted"

        # Process remaining papers for merge/rename
        new_topics = []
        merged = False
        renamed = False

        for topic in paper["topic"]:
            # Check for merge
            if topic in TOPICS_TO_MERGE:
                target = TOPICS_TO_MERGE[topic]
                if target not in new_topics:
                    new_topics.append(target)
                self.stats.topics_merged[f"{topic} -> {target}"] += 1
                merged = True
            # Check for rename
            elif topic in TOPICS_TO_RENAME:
                target = TOPICS_TO_RENAME[topic]
                if target not in new_topics:
                    new_topics.append(target)
                self.stats.topics_renamed[f"{topic} -> {target}"] += 1
                renamed = True
            else:
                if topic not in new_topics:
                    new_topics.append(topic)

        # Update paper's topics
        paper["topic"] = new_topics

        # Track final topics
        for topic in new_topics:
            self.final_topics.add(topic)

        if merged:
            self.stats.papers_merged += 1
            return paper, "merged"
        elif renamed:
            self.stats.papers_renamed += 1
            return paper, "renamed"
        else:
            return paper, "unchanged"

    def process_json_file(self, json_path: Path):
        """Process a single JSON file."""
        print(f"\nProcessing {json_path.name}...")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        papers = data.get("papers", [])
        original_count = len(papers)

        new_papers = []
        deleted_count = 0
        merged_count = 0
        renamed_count = 0

        for paper in papers:
            processed_paper, action = self.process_paper(paper)

            if processed_paper is None:
                deleted_count += 1
            else:
                new_papers.append(processed_paper)
                if action == "merged":
                    merged_count += 1
                elif action == "renamed":
                    renamed_count += 1

        print(f"  Original papers: {original_count}")
        print(f"  Papers deleted: {deleted_count}")
        print(f"  Papers merged: {merged_count}")
        print(f"  Papers renamed: {renamed_count}")
        print(f"  Final papers: {len(new_papers)}")

        if not self.dry_run:
            data["papers"] = new_papers
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  Saved: {json_path}")

    def update_topic_csv(self):
        """Update the unique_topic.csv file."""
        print("\nUpdating topic CSV...")

        # Load existing topics
        existing_topics: Set[str] = set()
        with open(TOPIC_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['name']:
                    existing_topics.add(row['name'])

        print(f"  Existing topics: {len(existing_topics)}")

        # Calculate new topic list
        # Start with existing topics
        new_topics = existing_topics.copy()

        # Remove deleted topics
        new_topics -= TOPICS_TO_DELETE

        # Remove merge source topics
        new_topics -= set(TOPICS_TO_MERGE.keys())

        # Remove renamed source topics
        new_topics -= set(TOPICS_TO_RENAME.keys())

        # Add merge target topics
        new_topics |= set(TOPICS_TO_MERGE.values())

        # Add rename target topics
        new_topics |= set(TOPICS_TO_RENAME.values())

        # Also include any topics found in the processed papers
        new_topics |= self.final_topics

        print(f"  Final topics: {len(new_topics)}")

        # Show what's being removed/added
        removed = existing_topics - new_topics
        added = new_topics - existing_topics

        if removed:
            print(f"  Topics removed ({len(removed)}):")
            for t in sorted(removed):
                print(f"    - {t}")

        if added:
            print(f"  Topics added ({len(added)}):")
            for t in sorted(added):
                print(f"    + {t}")

        if not self.dry_run:
            with open(TOPIC_CSV, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['name'])
                for topic in sorted(new_topics):
                    writer.writerow([topic])
                # Add empty row at end (as in original)
                writer.writerow([''])
            print(f"  Saved: {TOPIC_CSV}")

    def update_paper_id_csv(self):
        """Remove deleted paper IDs from unique_paper_id.csv."""
        print("\nUpdating paper ID CSV...")

        if not self.stats.deleted_paper_ids:
            print("  No paper IDs to remove")
            return

        # Load existing IDs
        existing_ids: Set[str] = set()
        with open(PAPER_ID_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['id']:
                    existing_ids.add(row['id'])

        print(f"  Existing paper IDs: {len(existing_ids)}")

        # Remove deleted IDs
        new_ids = existing_ids - self.stats.deleted_paper_ids
        removed_count = len(existing_ids) - len(new_ids)

        print(f"  Paper IDs to remove: {len(self.stats.deleted_paper_ids)}")
        print(f"  Paper IDs actually removed: {removed_count}")
        print(f"  Final paper IDs: {len(new_ids)}")

        if not self.dry_run:
            with open(PAPER_ID_CSV, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['id'])
                for paper_id in sorted(new_ids):
                    writer.writerow([paper_id])
            print(f"  Saved: {PAPER_ID_CSV}")

    def regenerate_compressed(self):
        """Regenerate gzipped files and copy to data repo."""
        print("\nRegenerating compressed files...")

        if self.dry_run:
            print("  [DRY RUN] Skipping compression")
            return

        # Ensure upload directory exists
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        for json_path in sorted(JSON_DIR.glob("*.json")):
            # Compress to upload directory
            gz_path = UPLOAD_DIR / f"{json_path.stem}.json.gz"

            with open(json_path, 'r', encoding='utf-8') as f:
                data = f.read()

            with gzip.open(gz_path, 'wt', encoding='utf-8', compresslevel=9) as f:
                f.write(data)

            print(f"  Compressed: {gz_path}")

            # Copy to data repo if it exists
            if DATA_REPO_PATH.exists():
                dest_path = DATA_REPO_PATH / f"{json_path.stem}.json.gz"
                shutil.copy2(gz_path, dest_path)
                print(f"  Copied to: {dest_path}")
            else:
                print(f"  Warning: Data repo not found at {DATA_REPO_PATH}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Migrate topics in Paper Explorer database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files"
    )
    args = parser.parse_args()

    migrator = TopicMigrator(dry_run=args.dry_run)
    migrator.run()


if __name__ == "__main__":
    main()
