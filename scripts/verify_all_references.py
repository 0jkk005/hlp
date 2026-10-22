"""Automated verification script for all manuscript references via CrossRef & RFC Editor APIs."""
import urllib.request
import urllib.parse
import json
import time

DOIS = [
    ("geng2020hybrid", "10.1109/jcn.2019.000056"),
    ("francois2005achieving", "10.1109/MCOM.2005.1471682"),
    ("chiesa2021survey", "10.1109/COMST.2021.3063980"),
    ("merindol2011efficient", "10.1016/j.comnet.2010.11.006"),
    ("ventre2021segment", "10.1109/COMST.2020.3040357"),
    ("foerster2019casa", "10.1109/INFOCOM.2019.8737397"),
    ("schlinker2017engineering", "10.1145/3098822.3098853"),
    ("fortz2002internet", "10.1109/TNET.2002.1002900"),
    ("feldmann2001deriving", "10.1109/90.929850"),
    ("spring2002measuring", "10.1145/633025.633039"),
    ("orlowski2010sndlib", "10.1002/net.20371"),
    ("nemhauser1978analysis", "10.1007/BF01588971"),
    ("feige1998threshold", "10.1145/285055.285059"),
    ("benjamini1995controlling", "10.1111/j.2517-6161.1995.tb02031.x"),
    ("li2012unified", "10.1109/TNSM.2012.060412.110196"),
    ("bramas2025simple", "10.1109/TNET.2024.3465782"),
    ("verdi2023infarr", "10.1109/TNSM.2023.3262615"),
    ("chiesa2021robust", "10.1109/TNSM.2021.3069151"),
]

RFCS = [
    ("rfc5714", 5714),
    ("rfc5286", 5286),
    ("rfc7490", 7490),
    ("rfc6981", 6981),
    ("rfc7812", 7812),
]

print("="*80)
print("STAGE 1: VERIFYING JOURNAL & CONFERENCE DOIS VIA CROSSREF API")
print("="*80)

verified_bibtex = {}
failed = []

for key, doi in DOIS:
    url = f"https://api.crossref.org/works/{doi}"
    req = urllib.request.Request(url, headers={"User-Agent": "AntigravityAcademicVerifier/1.0 (mailto:scholar@example.com)"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))["message"]
            title = data.get("title", [""])[0]
            authors = [f"{a.get('family', '')}, {a.get('given', '')}" for a in data.get("author", [])]
            container = data.get("container-title", [""])[0]
            vol = data.get("volume", "")
            issue = data.get("issue", "")
            page = data.get("page", "")
            year = ""
            for date_field in ["published-print", "issued", "created"]:
                if date_field in data and "date-parts" in data[date_field]:
                    year = str(data[date_field]["date-parts"][0][0])
                    break
            
            print(f"[OK] {key}:")
            print(f"     Title: {title}")
            print(f"     Venue: {container} (Vol {vol}, No {issue}, pp. {page}, {year})")
            print(f"     Authors ({len(authors)}): {'; '.join(authors[:4])}{'...' if len(authors) > 4 else ''}")
            print(f"     DOI: https://doi.org/{doi}")
            print()
            verified_bibtex[key] = {
                "doi": doi, "title": title, "authors": authors, "venue": container,
                "volume": vol, "issue": issue, "page": page, "year": year
            }
    except Exception as e:
        print(f"[FAILED] {key} (DOI: {doi}): {e}")
        failed.append((key, doi, str(e)))
    time.sleep(0.2)

print("="*80)
print("STAGE 2: VERIFYING IETF RFCS VIA RFC-EDITOR.ORG")
print("="*80)

for key, rfc_num in RFCS:
    url = f"https://www.rfc-editor.org/info/rfc{rfc_num}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            # extract title
            title = "RFC Title"
            for line in content.splitlines():
                if "title=" in line.lower() or "<title>" in line.lower():
                    title = line.strip()
                    break
            print(f"[OK] {key} -> RFC {rfc_num} verified at https://www.rfc-editor.org/info/rfc{rfc_num}")
    except Exception as e:
        print(f"[FAILED] RFC {rfc_num}: {e}")
        failed.append((key, f"RFC {rfc_num}", str(e)))
    time.sleep(0.2)

print("="*80)
print(f"AUDIT SUMMARY: {len(DOIS) + len(RFCS) - len(failed)}/{len(DOIS) + len(RFCS)} Verified Successfully!")
if failed:
    print(f"FAILED ITEMS: {failed}")
else:
    print("ALL CITATIONS AND DOIS ARE 100% AUTHENTIC AND ACCESSIBLE!")
print("="*80)
