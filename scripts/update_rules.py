#!/usr/bin/env python3
"""
Download the latest Magic: The Gathering Comprehensive Rules.

Usage:
    python scripts/update_rules.py

This script downloads the latest Comprehensive Rules from Wizards of the Coast
and saves them to src/data/raw_docs/mtg_rules.txt. After downloading, you should
rebuild the FAISS index:

    python src/cli/main.py --refresh_db
"""

import os
import re
import sys
import requests

# Known recent CR URLs — Wizards uses a consistent pattern
# Update this list when new versions are released
KNOWN_URLS = [
    "https://media.wizards.com/2025/downloads/MagicCompRules%2020250207.txt",
    "https://media.wizards.com/2024/downloads/MagicCompRules%2020241101.txt",
    "https://media.wizards.com/2024/downloads/MagicCompRules%2020240802.txt",
    "https://media.wizards.com/2024/downloads/MagicCompRules%2020240607.txt",
    "https://media.wizards.com/2024/downloads/MagicCompRules%2020240308.txt",
    "https://media.wizards.com/2023/downloads/MagicCompRules%2020231117.txt",
]

OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "src", "data", "raw_docs", "mtg_rules.txt"
)


def download_rules() -> bool:
    """Try each known URL until one succeeds."""
    for url in KNOWN_URLS:
        print(f"Trying: {url}")
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                content = resp.text
                # Verify it looks like the CR
                if "Magic: The Gathering Comprehensive Rules" in content[:500]:
                    # Extract effective date
                    date_match = re.search(r"effective as of (\w+ \d+, \d{4})", content)
                    date_str = date_match.group(1) if date_match else "unknown date"

                    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"\nDownloaded Comprehensive Rules (effective {date_str})")
                    print(f"Saved to: {OUTPUT_PATH}")
                    print(f"File size: {len(content):,} characters")
                    return True
                else:
                    print(f"  Content doesn't look like CR, skipping...")
            else:
                print(f"  HTTP {resp.status_code}, trying next...")
        except requests.RequestException as e:
            print(f"  Failed: {e}, trying next...")

    return False


def main():
    print("Downloading latest Magic: The Gathering Comprehensive Rules...\n")

    if download_rules():
        print("\nNext steps:")
        print("  1. Rebuild the FAISS index: python src/cli/main.py --refresh_db")
        print("  2. Test with: python src/cli/main.py --query_text 'What is trample?'")
    else:
        print("\nFailed to download from any known URL.")
        print("The Comprehensive Rules URL may have changed.")
        print("Check https://magic.wizards.com/en/rules for the latest URL,")
        print("then add it to KNOWN_URLS in this script.")
        sys.exit(1)


if __name__ == "__main__":
    main()
