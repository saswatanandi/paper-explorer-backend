"""
same as gscholar.py but without printing to console

This script uses the uc module to scrape information from Google Scholar.
It initializes a browser, searches for a paper, and then extracts relevant information.
The script can be run as a standalone script or imported as a module.
"""

import nodriver as uc
import asyncio
import json
import datetime
import re
import unicodedata
import os
import sys
import shutil
from urllib.parse import quote
from bs4 import BeautifulSoup

class GoogleScholarScraper:
    def __init__(self, browser_path=None):
        self.browser = None
        self.browser_path = browser_path or self._resolve_browser_path()
        self.initialized = False

    @staticmethod
    def _resolve_browser_path():
        """
        Resolve a Chrome/Chromium executable path cross-platform.

        Priority:
        1) PAPER_EXPLORER_BROWSER_PATH (must exist)
        2) OS-specific well-known paths
        3) PATH lookup for common chrome/chromium executables
        """
        override = os.environ.get("PAPER_EXPLORER_BROWSER_PATH", "").strip()
        if override:
            if os.path.exists(override):
                return override
            raise FileNotFoundError(
                f"PAPER_EXPLORER_BROWSER_PATH is set but does not exist: {override}"
            )

        candidates = []

        if sys.platform == "darwin":
            candidates.extend(
                [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    "/Applications/Chromium.app/Contents/MacOS/Chromium",
                ]
            )
        else:
            candidates.extend(
                [
                    "/home/sn/chrome/opt/google/chrome/chrome",
                    "/usr/bin/google-chrome",
                    "/usr/bin/google-chrome-stable",
                    "/usr/bin/chromium",
                    "/usr/bin/chromium-browser",
                ]
            )

        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
            path = shutil.which(name)
            if path:
                candidates.append(path)

        for path in candidates:
            if path and os.path.exists(path):
                return path

        raise FileNotFoundError(
            "Could not find a Chrome/Chromium executable. "
            "Set PAPER_EXPLORER_BROWSER_PATH (macOS example: "
            "'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')."
        )

    async def initialize(self):
        """Initialize browser once"""
        if not self.initialized:
            print("Starting browser...")
            self.browser = await uc.start(
                browser_executable_path=self.browser_path,
                headless=False,
                browser_args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--no-default-browser-check"
                ]
            )
            self.initialized = True
            return True
        return False

    async def search_paper(self, paper_title):
        """Search for a paper while reusing the same browser instance"""
        if not self.initialized:
            await self.initialize()

        paper_info = {
            "title": paper_title,
            "authors": [],
            "year": "",
            "abstract": "",
            "url": "",
            "journal": "",
            "citations": 0,
            "date_created": datetime.datetime.now().strftime("%Y-%m-%d")
        }

        try:
            # Search for the paper on Google Scholar
            encoded_title = quote(f'{paper_title}')
            search_url = f"https://scholar.google.com/scholar?q={encoded_title}"
            # print(f"Navigating to: {search_url}")

            page = await self.browser.get(search_url)
            await asyncio.sleep(3.0)

            # CAPTCHA handling - only needed once per session
            html_content = await page.get_content()
            if any(term in html_content.lower() for term in ['captcha', 'robot', 'unusual traffic']):
                print("\n==== CAPTCHA DETECTED! ====")
                print("Please solve the CAPTCHA in the browser window.")
                input("\nPress ENTER after solving CAPTCHA and seeing search results...\n")

                # Reload page to get fresh results
                page = await self.browser.get(search_url)
                await asyncio.sleep(5.0)
                html_content = await page.get_content()

            # Parse content with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            # [Rest of the parsing code remains unchanged]
            search_results = soup.select('.gs_r')
            if not search_results:
                print("No results found with quoted search, trying without quotes...")
                encoded_title_no_quotes = quote(paper_title)
                alt_search_url = f"https://scholar.google.com/scholar?q={encoded_title_no_quotes}"
                page = await self.browser.get(alt_search_url)
                await asyncio.sleep(3.0)

                html_content = await page.get_content()
                soup = BeautifulSoup(html_content, 'html.parser')
                search_results = soup.select('.gs_r')

            if not search_results:
                print("No results found.")
                return paper_info

            # Process the first result
            first_result = search_results[0]

            # [Rest of the extraction code remains unchanged]
            # Extract title and URL
            title_elem = first_result.select_one('.gs_rt a')
            if title_elem:
                paper_info["title"] = clean_text(title_elem.text)
                paper_info["url"] = title_elem.get('href', '')
                # print(f"Found title: {paper_info['title']}")

            # Extract full abstract (checking multiple locations)
            # First try to get the full abstract from the expanded view
            full_abstract_elem = first_result.select_one('.gs_fma_abs')
            summary_abstract_elem = first_result.select_one('.gs_rs')

            # When extracting the full abstract:
            if full_abstract_elem:
                # Remove any interior divs that might contain unwanted content
                for div in full_abstract_elem.find_all('div', class_='gs_fma_grad'):
                    div.decompose()

                # Remove the publisher footer div
                for div in full_abstract_elem.find_all('div', class_='gs_fma_fons'):
                    div.decompose()

                abstract_text = clean_text(full_abstract_elem.get_text(separator=' ', strip=True))
                paper_info["abstract"] = abstract_text
                # print(f"Extracted full abstract ({len(abstract_text)} chars)")
            elif summary_abstract_elem:
                abstract_text = clean_text(summary_abstract_elem.text)
                # Remove trailing ellipsis if present
                if abstract_text.endswith("..."):
                    abstract_text = abstract_text[:-3].strip()
                paper_info["abstract"] = abstract_text
                # print(f"Extracted summary abstract: {abstract_text[:80]}...")

            # Extract authors, year, and journal information more carefully
            # First try the full format display (which appears in the expanded view)
            authors_list = []
            journal_name = ""
            publication_year = ""

            # Check for detailed author/publication info in the gs_fma_p div
            detailed_info = first_result.select_one('.gs_fma_p')
            if detailed_info:
                # Extract authors from gs_fmaa div
                author_div = detailed_info.select_one('.gs_fmaa')
                if author_div:
                    # Get full text with all authors
                    author_text = clean_text(author_div.get_text())

                    # Split by commas to get individual authors
                    raw_authors = [a.strip() for a in author_text.split(',')]

                    # Clean up the last author if it contains ellipsis
                    if raw_authors and ('…' in raw_authors[-1] or '...' in raw_authors[-1]):
                        # Remove any trailing ellipsis from the last author
                        last_author = re.sub(r'[…\.]+$', '', raw_authors[-1]).strip()
                        raw_authors[-1] = last_author

                    # Remove any empty strings
                    authors_list = [author for author in raw_authors if author]

                # Extract journal info from the text after authors
                if author_div:
                    next_text = author_div.next_sibling
                    if next_text:
                        publication_info = clean_text(next_text)
                        journal_parts = publication_info.split('•')
                        if len(journal_parts) >= 1:
                            journal_and_year = clean_text(journal_parts[0])
                            year_match = re.search(r'\b(19|20)\d{2}\b', journal_and_year)
                            if year_match:
                                publication_year = year_match.group(0)
                                journal_name = journal_and_year.replace(publication_year, '').strip(' ,')
                            else:
                                journal_name = journal_and_year

                        if len(journal_parts) >= 2:
                            publisher = clean_text(journal_parts[1])
                            # Only use publisher if we couldn't find a journal name
                            if not journal_name:
                                journal_name = publisher

            # If we couldn't get info from detailed view, use the standard view
            if not authors_list or not journal_name:
                byline_elem = first_result.select_one('.gs_a')
                if byline_elem:
                    byline_text = clean_text(byline_elem.text)
                    # print(f"Found byline: {byline_text}")

                    # Extract authors
                    if " - " in byline_text:
                        authors_section = byline_text.split(" - ")[0]
                        temp_authors = [clean_text(author) for author in authors_section.split(", ")
                                    if author and author != "…"]

                        # Only update if we didn't already find authors
                        if not authors_list:
                            authors_list = temp_authors

                    # Extract year if not already found
                    if not publication_year:
                        year_match = re.search(r'\b(19|20)\d{2}\b', byline_text)
                        if year_match:
                            publication_year = year_match.group(0)

                    # Extract journal if not already found
                    if not journal_name:
                        parts = byline_text.split(" - ")
                        if len(parts) > 1:
                            journal_part = clean_text(parts[1])
                            # Check if the part has the journal name
                            # Often format is: journal_name, year - publisher
                            if "," in journal_part:
                                journal_name = journal_part.split(",")[0].strip()
                            else:
                                journal_name = journal_part

                            # If we extracted a year, make sure it's not part of the journal name
                            if publication_year and publication_year in journal_name:
                                journal_name = journal_name.replace(publication_year, "").strip(" ,")

            # Check for publisher info in the footer (often more accurate for journal name)
            publisher_div = first_result.select_one('.gs_fma_fon')
            if publisher_div and not journal_name:
                publisher_name = clean_text(publisher_div.text)
                # Only use publisher as journal if we couldn't find a journal name
                if not journal_name:
                    journal_name = publisher_name

            # Extract citation count
            for link in first_result.select('a'):
                if 'Cited by' in link.text:
                    citation_match = re.search(r'Cited by (\d+)', link.text)
                    if citation_match:
                        paper_info["citations"] = int(citation_match.group(1))
                        break

            # Update paper info with the collected data
            paper_info["authors"] = authors_list
            paper_info["journal"] = journal_name
            paper_info["year"] = publication_year


            # Ensure authors are in "First Last" format
            cleaned_authors = []
            for author in paper_info["authors"]:
                if "," in author:
                    parts = [p.strip() for p in author.split(",", 1)]
                    if len(parts) == 2:
                        cleaned_authors.append(f"{parts[1]} {parts[0]}")
                    else:
                        cleaned_authors.append(author)
                else:
                    cleaned_authors.append(author)

            paper_info["authors"] = cleaned_authors
            # print("Scraping complete!")

            # print(f"Extracted journal: {journal_name}")
            # print(f"Extracted year: {publication_year}")
            # print(f"Extracted authors: {cleaned_authors}")
            # print(f"Extracted abstract: {abstract_text}")
            # print(f"Extracted citations: {paper_info['citations']}")
            # print(f"Extracted URL: {paper_info['url']}")

        except Exception as e:
            print(f"Error during scraping: {str(e)}")
            import traceback
            traceback.print_exc()

        return paper_info

    async def close(self):
        """
        Terminate the Nodriver browser and make sure the underlying
        chromium process has *really* exited before the asyncio loop
        shuts down – this removes the
            RuntimeError: Event loop is closed
        traceback.
        """
        if not (self.browser and self.initialized):
            return

        print("Closing browser...")

        # ── 1. ask Nodriver to close the browser window ─────────────────────
        for attr in ("close", "quit"):
            meth = getattr(self.browser, attr, None)
            if callable(meth):
                result = meth()
                if asyncio.iscoroutine(result):
                    await result
                break                                            # done

        # ── 2. ALWAYS wait until the real chromium process is gone ──────────
        proc = getattr(self.browser, "proc", None)               # present in every build
        if proc and proc.returncode is None:                     # still running?
            await proc.wait()                                    # ← crucial line

        # ── 3. tidy up our own state ────────────────────────────────────────
        self.browser = None
        self.initialized = False

def clean_text(text):
    """Clean and normalize text."""
    # [Function remains unchanged]
    if not text:
        return ""
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace(" ", " ")
    text = re.sub(r'<[^>]+>', '', text)
    return text

'''
async def process_papers():
    # Create scraper once
    scraper = GoogleScholarScraper()

    # Initialize browser
    await scraper.initialize()

    # List of papers to search
    paper_titles = [
        "Paper title 1",
        "Paper title 2",
        "Paper title 3"
    ]

    results = []
    for title in paper_titles:
        paper_info = await scraper.search_paper(title)
        results.append(paper_info)

    # Close browser when done
    await scraper.close()
    return results

if __name__ == "__main__":
    loop = uc.loop()
    results = loop.run_until_complete(process_papers())
'''    
