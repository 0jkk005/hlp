import urllib.request
import urllib.parse
import json
import time

titles = [
    "Achieving sub-second IGP convergence in large IP networks",
    "An efficient algorithm to enable path diversity in link state routing networks",
    "CASA: Congestion and Stretch Aware Static Fast Rerouting",
    "Internet traffic engineering by optimizing OSPF weights",
    "Segment Routing: A Comprehensive Survey of Research Activities, Standardization Efforts, and Implementation Results",
    "A Unified Approach to Routing Protection in IP Networks",
    "A Simple and General Operational Framework to Deploy Optimal Routes With Source Routing",
    "InFaRR: In-Network Fast ReRouting",
    "Robust LFA Protection for Software-Defined Networks (RoLPS)",
]

print("Searching CrossRef API by Exact Title...")
for title in titles:
    query_url = f"https://api.crossref.org/works?query.title={urllib.parse.quote(title)}&rows=1"
    req = urllib.request.Request(query_url, headers={"User-Agent": "AntigravityVerifier/1.0 (mailto:scholar@example.com)"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))["message"]["items"]
            if data:
                item = data[0]
                matched_title = item.get("title", [""])[0]
                doi = item.get("DOI")
                authors = [a.get("family", "") for a in item.get("author", [])]
                venue = item.get("container-title", [""])[0]
                year = ""
                for df in ["published-print", "issued", "created"]:
                    if df in item and "date-parts" in item[df]:
                        year = item[df]["date-parts"][0][0]
                        break
                print(f"QUERY: {title}")
                print(f"FOUND: {matched_title}")
                print(f"DOI:   {doi}")
                print(f"AUTH:  {', '.join(authors[:4])}")
                print(f"VENUE: {venue} ({year})")
                print("-" * 70)
            else:
                print(f"NOT FOUND: {title}")
    except Exception as e:
        print(f"ERROR: {title}: {e}")
    time.sleep(0.3)
