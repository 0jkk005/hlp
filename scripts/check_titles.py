import re

with open('latex/references.bib', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's inspect each entry
entries = re.split(r'\n@', text)
for entry in entries:
    if not entry.strip():
        continue
    key = entry.split('{')[1].split(',')[0].strip()
    # find title
    m = re.search(r'title\s*=\s*\{([^\n]+)\}', entry)
    if not m:
        m = re.search(r'title\s*=\s*\{(.+?)\},', entry, re.DOTALL)
    if m:
        t = m.group(1).strip()
        o = t.count('{')
        c = t.count('}')
        if o != c:
            print(f"Brace mismatch in [{key}]: {t} ({o} != {c})")
        else:
            print(f"OK [{key}]: {t}")
    else:
        print(f"NO TITLE FOUND in [{key}]")
