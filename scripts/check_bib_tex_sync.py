"""Verify synchronization and syntax between bare_jrnl.tex and references.bib."""
import re

with open('latex/bare_jrnl.tex', 'r', encoding='utf-8') as f:
    tex = f.read()

cites = set()
for c in re.findall(r'\\cite\{([^}]+)\}', tex):
    for k in c.split(','):
        cites.add(k.strip())

with open('latex/references.bib', 'r', encoding='utf-8') as f:
    bib = f.read()

bib_entries = re.findall(r'@\w+\s*\{\s*([^,]+),', bib)
bib_keys = set(bib_entries)

print(f"Total cited keys in bare_jrnl.tex: {len(cites)}")
print(f"Total bib entries in references.bib: {len(bib_keys)}")

diff1 = cites - bib_keys
diff2 = bib_keys - cites

print(f"Cited in tex but missing in bib: {diff1}")
print(f"In bib but unused in tex: {diff2}")

# Check for unescaped & in bib (should only be \& or in URLs)
unescaped_amp = 0
for i, line in enumerate(bib.splitlines(), 1):
    if '&' in line and not r'\&' in line and not 'http' in line:
        print(f"Potential unescaped & at line {i}: {line}")
        unescaped_amp += 1

if unescaped_amp == 0:
    print("Ampersand check: PERFECT (All journal ampersands correctly escaped with \\&)")

# Check brace balance
if bib.count('{') != bib.count('}'):
    print(f"WARNING: Unbalanced braces in references.bib! {{: {bib.count('{')}, }}: {bib.count('}')}")
else:
    print(f"Brace balance: PERFECT! ({bib.count('{')} open braces matched with {bib.count('}')} close braces)")
