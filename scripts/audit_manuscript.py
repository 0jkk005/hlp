import re

with open('latex/bare_jrnl.tex', 'r', encoding='utf-8') as f:
    text = f.read()

print(f"Total lines in bare_jrnl.tex: {len(text.splitlines())}")

# Check for em-dashes
em_dashes = [i+1 for i, line in enumerate(text.splitlines()) if '---' in line or '—' in line]
print(f"Em-dashes found on lines: {em_dashes}")

# Check for buzzwords
buzzwords = [
    'crucial', 'slash', 'enormous', 'pivotal', 'delve', 'testament', 
    'harness', 'beacon', 'tapestry', 'game-chang', 'groundbreak', 
    'revolution', 'paramount', 'showcase', 'drastic', 'remarkable',
    'plethora', 'fosters', 'underscores', 'in essence', 'it is worth noting'
]

for bw in buzzwords:
    matches = [(i+1, line.strip()) for i, line in enumerate(text.splitlines()) if re.search(r'\b' + bw, line, re.IGNORECASE)]
    if matches:
        print(f"Buzzword '{bw}' found on lines: {[m[0] for m in matches]}")
        for lnum, line in matches:
            print(f"   Line {lnum}: {line[:100]}")

# Check for remaining \textbf
text_bfs = [(i+1, line.strip()) for i, line in enumerate(text.splitlines()) if r'\textbf' in line]
print(f"\nTotal \\textbf occurrences: {len(text_bfs)}")
for lnum, line in text_bfs:
    print(f"   Line {lnum}: {line[:100]}")

# Check for unclosed environments
opens = re.findall(r'\\begin\{([^}]+)\}', text)
closes = re.findall(r'\\end\{([^}]+)\}', text)
print(f"\nEnvironments begin: {len(opens)}, end: {len(closes)}")
if opens != closes:
    print(f"Open environments: {opens}")
    print(f"Close environments: {closes}")
else:
    print("All LaTeX environments matched and balanced!")
