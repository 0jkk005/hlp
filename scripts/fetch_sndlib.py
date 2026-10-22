"""Automated downloader for authentic SNDlib topologies and empirical NetFlow demand matrices."""
import os
import json
import urllib.request

SNDLIB_BASE_URL = "https://raw.githubusercontent.com/piotrjurkiewicz/topohub/master/data/sndlib"
DEST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "sndlib"))

TARGET_TOPOLOGIES = [
    "abilene",
    "geant",
    "germany50",
    "nobel-eu",
]


def download_sndlib_datasets():
    os.makedirs(DEST_DIR, exist_ok=True)
    print(f"Downloading authentic SNDlib datasets into: {DEST_DIR}")

    for topo in TARGET_TOPOLOGIES:
        for ext in ["json", "gml"]:
            filename = f"{topo}.{ext}"
            url = f"{SNDLIB_BASE_URL}/{filename}"
            dest_path = os.path.join(DEST_DIR, filename)
            try:
                print(f"  Fetching {filename}...")
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    content = resp.read()
                with open(dest_path, "wb") as f:
                    f.write(content)
                print(f"    Saved {filename} ({len(content):,} bytes)")
            except Exception as e:
                print(f"    Error fetching {filename}: {e}")

    print("\nSNDlib dataset acquisition complete!")


if __name__ == "__main__":
    download_sndlib_datasets()
