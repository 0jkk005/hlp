import re

with open('latex/references.bib', 'r', encoding='utf-8') as f:
    bib = f.read()

# Match entries
entries = re.findall(r'@(\w+)\s*\{\s*([^,]+),\s*(.*?)\n\}', bib, re.DOTALL)
print(f"Parsed {len(entries)} entries:\n")

for entry_type, key, body in entries:
    title_m = re.search(r'title\s*=\s*[\{"](.*?)[}"]', body, re.DOTALL)
    author_m = re.search(r'author\s*=\s*[\{"](.*?)[}"]', body, re.DOTALL)
    year_m = re.search(r'year\s*=\s*[\{"]?(\d{4})[}"]?', body)
    venue_m = re.search(r'(journal|booktitle|howpublished|series)\s*=\s*[\{"](.*?)[}"]', body, re.DOTALL)
    doi_m = re.search(r'doi\s*=\s*[\{"](.*?)[}"]', body)

    title = title_m.group(1).replace('\n', ' ').strip() if title_m else "N/A"
    author = author_m.group(1).replace('\n', ' ').strip() if author_m else "N/A"
    year = year_m.group(1) if year_m else "N/A"
    venue = venue_m.group(2).replace('\n', ' ').strip() if venue_m else "N/A"
    doi = doi_m.group(1).strip() if doi_m else "No DOI"
    print(f"[{key}] ({year})\n  Title: {title}\n  Authors: {author[:80]}...\n  Venue: {venue}\n  DOI: {doi}\n")
