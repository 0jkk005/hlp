"""Automated downloader for authentic University of Washington / CAIDA Rocketfuel maps."""
import os
import io
import tarfile
import urllib.request
import networkx as nx

URL = "https://research.cs.washington.edu/networking/rocketfuel/maps/rocketfuel_maps_cch.tar.gz"
DEST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "rocketfuel"))

MAPPING = {
    "3967.cch": "Exodus.cch",
    "3967.r0.cch": "Exodus.r0.cch",
    "1221.cch": "Telstra.cch",
    "1221.r0.cch": "Telstra.r0.cch",
    "3257.cch": "Tiscali.cch",
    "3257.r0.cch": "Tiscali.r0.cch",
    "1239.cch": "Sprint.cch",
    "1239.r0.cch": "Sprint.r0.cch",
}


def download_and_extract():
    os.makedirs(DEST_DIR, exist_ok=True)
    print(f"Fetching official Rocketfuel maps from:\n  {URL}")
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    print(f"Downloaded {len(data):,} bytes. Extracting target topologies...")

    tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
    for src_name, dst_name in MAPPING.items():
        try:
            f = tf.extractfile(src_name)
            if f is not None:
                content = f.read()
                out_path = os.path.join(DEST_DIR, dst_name)
                with open(out_path, "wb") as out:
                    out.write(content)
                print(f"  Extracted: {src_name} -> {dst_name} ({len(content):,} bytes)")
        except KeyError:
            print(f"  Warning: {src_name} not found in archive.")

    # Also make a Sprint315.cch alias for compatibility
    sprint_src = os.path.join(DEST_DIR, "Sprint.cch")
    sprint315_dst = os.path.join(DEST_DIR, "Sprint315.cch")
    if os.path.exists(sprint_src) and not os.path.exists(sprint315_dst):
        with open(sprint_src, "rb") as sf, open(sprint315_dst, "wb") as df:
            df.write(sf.read())
        print("  Created alias: Sprint.cch -> Sprint315.cch")

    print("\nRocketfuel extraction complete!")


if __name__ == "__main__":
    download_and_extract()
