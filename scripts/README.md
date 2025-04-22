# Legacy Data Pipeline

This directory contains scripts for processing legacy CSV data, enriching it with metadata from Google Scholar, and categorizing papers into appropriate JSON files.

## Scripts

- `legacy_data_pipeline.py`: Main script for processing CSV files
- `scholarly_scraper.py`: Module for fetching metadata from Google Scholar
- `test_scholarly_scraper.py`: Test script for the scholarly scraper

## Usage

### Process all CSV files

```bash
python legacy_data_pipeline.py
```

### Process a specific topic

```bash
python legacy_data_pipeline.py --topic flood
```

### Test the scholarly scraper

```bash
python test_scholarly_scraper.py
```

## Notes

- The script will skip papers that are already in the unique papers database.
- Google Scholar has rate limits, so the script includes delays between requests.
- If you encounter CAPTCHA or blocking issues, try running the script with fewer papers at a time.
