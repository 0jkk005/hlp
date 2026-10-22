import re

with open('latex/bare_jrnl.tex', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('latex/references.bib', 'r', encoding='utf-8') as f:
    bib = f.read()

bib_keys = set(re.findall(r'@\w+\{([^,]+),', bib))

citations_found = {}
for i, line in enumerate(lines, 1):
    cites = re.findall(r'\\cite\{([^}]+)\}', line)
    for c in cites:
        for k in c.split(','):
            k = k.strip()
            if k not in citations_found:
                citations_found[k] = []
            citations_found[k].append((i, line.strip()))

print(f"Total unique keys cited in text: {len(citations_found)}")
for k in sorted(citations_found.keys()):
    locs = [f"L{loc[0]}" for loc in citations_found[k]]
    in_bib = "FOUND IN BIB" if k in bib_keys else "MISSING IN BIB"
    print(f"{k:<25} | {in_bib:<15} | cited at: {', '.join(locs)}")
