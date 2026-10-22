"""
Deep DOI Verification Script for IEEE Transactions Manuscript.
Validates every citation against CrossRef API and tests HTTP resolution.
"""
import urllib.request
import json
import time
import ssl

ctx = ssl.create_default_context()

dois_to_check = [
    ("geng2020hybrid", "10.1109/jcn.2019.000056"),
    ("francois2005achieving", "10.1145/1070873.1070877"),
    ("chiesa2021survey", "10.1109/COMST.2021.3063980"),
    ("merindol2011efficient", "10.1016/j.comnet.2010.11.005"),
    ("ventre2021segment", "10.1109/comst.2020.3036826"),
    ("foerster2019casa", "10.1109/infocom.2019.8737438"),
    ("schlinker2017engineering", "10.1145/3098822.3098853"),
    ("fortz2002optimizing", "10.1109/jsac.2002.1003042"),
    ("fortz2002internet", "10.1109/TNET.2002.1002900"),
    ("feldmann2001deriving", "10.1109/90.929850"),
    ("spring2002measuring", "10.1145/633025.633039"),
    ("orlowski2010sndlib", "10.1002/net.20371"),
    ("nemhauser1978analysis", "10.1007/BF01588971"),
    ("feige1998threshold", "10.1145/285055.285059"),
    ("benjamini1995controlling", "10.1111/j.2517-6161.1995.tb02031.x"),
    ("li2012unified", "10.1109/tnsm.2012.070512.110138"),
    ("bramas2025simple", "10.1109/ton.2025.3534332"),
    ("verdi2023infarr", "10.1109/tnsm.2023.3283459"),
    ("chiesa2021robust", "10.1109/TNSM.2021.3069151"),
    ("merling2021rolps", "10.1109/tnsm.2021.3090843"),
]

print("=" * 90)
print("DEEP DOI VERIFICATION VIA CROSSREF METADATA & DOI RESOLUTION")
print("=" * 90)

results = []

for key, doi in dois_to_check:
    print(f"\nVerifying [{key}] -> DOI: {doi} ...")
    api_url = f"https://api.crossref.org/works/{doi}"
    req = urllib.request.Request(
        api_url,
        headers={"User-Agent": "AntigravityAcademicVerifier/2.0 (mailto:scholar_verify@academic-research.org)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))["message"]
            title = data.get("title", [""])[0] if data.get("title") else ""
            author_list = data.get("author", [])
            authors = [f"{a.get('family', '')}, {a.get('given', '')}".strip(", ") for a in author_list]
            venue = data.get("container-title", [""])[0] if data.get("container-title") else ""
            volume = data.get("volume", "")
            issue = data.get("issue", "")
            page = data.get("page", "")
            publisher = data.get("publisher", "")
            year = ""
            for df in ["published-print", "issued", "created", "published-online"]:
                if df in data and "date-parts" in data[df] and data[df]["date-parts"][0]:
                    year = str(data[df]["date-parts"][0][0])
                    break
            
            # Now verify resolution through dx.doi.org
            resolve_url = f"https://doi.org/{doi}"
            res_req = urllib.request.Request(resolve_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(res_req, timeout=12, context=ctx) as res_resp:
                final_url = res_resp.geturl()
                http_code = res_resp.getcode()
            
            print(f"  [STATUS: SUCCESS (HTTP {http_code})]")
            print(f"  Title:     {title}")
            print(f"  Authors:   {'; '.join(authors[:4])}{'...' if len(authors) > 4 else ''} ({len(authors)} total)")
            print(f"  Venue:     {venue}")
            print(f"  Volume/Issue/Page/Year: Vol. {volume}, No. {issue}, pp. {page}, Year {year}")
            print(f"  Publisher: {publisher}")
            print(f"  Resolves:  {final_url[:80]}...")
            
            results.append({
                "key": key,
                "doi": doi,
                "status": "VERIFIED",
                "title": title,
                "authors": authors,
                "venue": venue,
                "volume": volume,
                "issue": issue,
                "page": page,
                "year": year,
                "publisher": publisher,
                "final_url": final_url
            })
    except Exception as e:
        print(f"  [STATUS: FAILED] Error: {e}")
        results.append({
            "key": key,
            "doi": doi,
            "status": f"FAILED: {e}"
        })
    time.sleep(0.3)

print("\n" + "=" * 90)
print("AUDIT COMPLETE")
print("=" * 90)
with open("scripts/doi_verification_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
