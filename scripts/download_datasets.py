#!/usr/bin/env python3
# ============================================================
# scripts/download_datasets.py
# Downloads all Tamil Nadu climate risk PDF datasets directly.
#
# Usage (from project root):
#   python scripts/download_datasets.py
#   python scripts/download_datasets.py --skip-existing   ← skip already downloaded
#   python scripts/download_datasets.py --check-only      ← just test URLs, no download
#
# After running, drop any extra district PDFs manually into
# data/raw/ then run:  python scripts/setup_db.py
# ============================================================

import argparse
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

# ── Add project root to sys.path ─────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("❌  'requests' not installed. Run:  pip install requests")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("❌  'tqdm' not installed. Run:  pip install tqdm")
    sys.exit(1)

# ── Output directory ──────────────────────────────────────────
RAW_DIR = PROJECT_ROOT / "data" / "raw"

# ============================================================
# DATASET CATALOGUE
# Each entry:  (local_filename, url, description)
# ============================================================
DATASETS = [
    # ── NDMA / National Guidelines ───────────────────────────
    (
        "ndma_flood_management_guidelines.pdf",
        "http://ndma.gov.in/images/guidelines/flood.pdf",
        "NDMA — Flood Management Guidelines (National)"
    ),
    (
        "ndma_urban_flooding_guidelines.pdf",
        "https://ndma.gov.in/sites/default/files/PDF/Guidelines/management_urban_flooding.pdf",
        "NDMA — Urban Flooding Management Guidelines"
    ),
    (
        "ndma_cyclone_management_guidelines.pdf",
        "https://nidm.gov.in/PDF/pubs/NDMA/4.pdf",
        "NDMA — Cyclone Risk Mitigation Guidelines (NIDM)"
    ),
    (
        "ndma_flood_guidelines_nidm.pdf",
        "https://nidm.gov.in/pdf/guidelines/floods.pdf",
        "NIDM — Flood Guidelines (mirror)"
    ),
    (
        "ndma_earthquake_guidelines.pdf",
        "https://nidm.gov.in/PDF/pubs/NDMA/1.pdf",
        "NDMA — Earthquake Management Guidelines (NIDM)"
    ),
    (
        "ndma_heatwave_action_plan.pdf",
        "https://nidm.gov.in/PDF/pubs/NDMA/8.pdf",
        "NDMA — Heat Wave Risk Management Guidelines"
    ),
    (
        "ndma_drought_management.pdf",
        "https://nidm.gov.in/PDF/pubs/NDMA/6.pdf",
        "NDMA — Drought Risk Mitigation Guidelines"
    ),
    (
        "ndma_tsunami_guidelines.pdf",
        "https://nidm.gov.in/PDF/pubs/NDMA/5.pdf",
        "NDMA — Tsunami Risk Management Guidelines"
    ),
    (
        "mohua_urban_flooding_sop.pdf",
        "https://mohua.gov.in/upload/uploadfiles/files/SOP%20Urban%20flooding_5%20May%202017.pdf",
        "MoHUA — Urban Flooding Standard Operating Procedure"
    ),

    # ── Tamil Nadu State Level ────────────────────────────────
    (
        "tamilnadu_flood_cyclone_dm_plan_2023.pdf",
        "https://tnsdma.tn.gov.in/app/webroot/img/document/dm_plan_2023.pdf",
        "TNSDMA — Tamil Nadu State Disaster Management Plan 2023"
    ),

    # ── NIDM Hazard Profiles & Research Papers ────────────────
    (
        "nidm_india_disaster_report_2020.pdf",
        "https://nidm.gov.in/PDF/pubs/India%20Disaster%20Report%202020.pdf",
        "NIDM — India Disaster Report 2020"
    ),
    (
        "nidm_cyclone_risk_profile_tamilnadu.pdf",
        "https://nidm.gov.in/PDF/pubs/Cyclone%20Risk%20Profile%20of%20Tamil%20Nadu.pdf",
        "NIDM — Cyclone Risk Profile of Tamil Nadu"
    ),
    (
        "nidm_flood_risk_profile_tamilnadu.pdf",
        "https://nidm.gov.in/PDF/pubs/Flood%20Risk%20Profile%20of%20Tamil%20Nadu.pdf",
        "NIDM — Flood Risk Profile of Tamil Nadu"
    ),

    # ── IMD / Meteorological ──────────────────────────────────
    (
        "imd_cyclone_preparedness_guidelines.pdf",
        "https://imdpune.gov.in/Weather/Reports/cyclone/Cyclone%20preparedness.pdf",
        "IMD — Cyclone Preparedness Guidelines"
    ),

    # ── WHO / Health Guidelines (relevant for heatwave + flood)
    (
        "who_heatwave_health_action_plan.pdf",
        "https://www.who.int/publications/i/item/WHO-HEP-ECH-PHE-2023.1",
        "WHO — Heat–Health Action Planning Guide"
    ),
    (
        "who_flood_health_guidelines.pdf",
        "https://www.who.int/publications-detail-redirect/flood-manual",
        "WHO — Flooding and Communicable Diseases Fact Sheet"
    ),
]


# ============================================================
# HTTP SESSION WITH RETRY
# ============================================================

def build_session() -> requests.Session:
    """
    Create a requests Session with automatic retry on transient
    HTTP errors (500, 502, 503, 504) and connection issues.
    """
    session = requests.Session()

    retry_strategy = Retry(
        total=4,                          # max 4 retries
        backoff_factor=2,                 # wait 2, 4, 8, 16 seconds
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Mimic a real browser to avoid 403s on government sites
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/pdf,*/*",
    })

    return session


# ============================================================
# DOWNLOAD HELPERS
# ============================================================

def check_url(session: requests.Session, url: str) -> tuple[bool, int, str]:
    """
    HEAD-request a URL to check if it's reachable.
    Returns (ok, status_code, content_type).
    """
    try:
        resp = session.head(url, timeout=15, allow_redirects=True)
        ct = resp.headers.get("Content-Type", "unknown")
        return resp.status_code < 400, resp.status_code, ct
    except requests.RequestException as e:
        return False, 0, str(e)


def download_file(
    session: requests.Session,
    url: str,
    dest_path: Path,
    description: str,
) -> bool:
    """
    Stream-download a file to dest_path, showing a tqdm progress bar.

    Returns True on success, False on failure.
    """
    try:
        resp = session.get(url, stream=True, timeout=60, allow_redirects=True)
        resp.raise_for_status()

        # Check we actually got a PDF (some gov sites return HTML 200 with an error page)
        content_type = resp.headers.get("Content-Type", "")
        total_bytes = int(resp.headers.get("Content-Length", 0))

        if "html" in content_type and total_bytes < 50_000:
            print(f"     ⚠️  Got HTML instead of PDF — server may require login")
            return False

        # Stream to disk with progress bar
        with open(dest_path, "wb") as f, tqdm(
            desc=f"     Downloading",
            total=total_bytes or None,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            leave=False,
            ncols=72,
            colour="green",
        ) as bar:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))

        # Sanity check: downloaded file should be at least 10 KB
        file_size = dest_path.stat().st_size
        if file_size < 10_240:
            print(f"     ⚠️  File too small ({file_size} bytes) — may be an error page")
            dest_path.unlink(missing_ok=True)
            return False

        size_mb = file_size / 1_048_576
        print(f"     ✅  Saved → {dest_path.name}  ({size_mb:.2f} MB)")
        return True

    except requests.HTTPError as e:
        print(f"     ❌  HTTP {e.response.status_code} — {url}")
        dest_path.unlink(missing_ok=True)
        return False

    except requests.ConnectionError:
        print(f"     ❌  Connection error — check internet and try again")
        dest_path.unlink(missing_ok=True)
        return False

    except requests.Timeout:
        print(f"     ❌  Timeout — server too slow")
        dest_path.unlink(missing_ok=True)
        return False

    except Exception as e:
        print(f"     ❌  Unexpected error: {e}")
        dest_path.unlink(missing_ok=True)
        return False


# ============================================================
# MAIN
# ============================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Tamil Nadu climate risk PDF datasets."
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip files that already exist in data/raw/",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only test if URLs are reachable — don't download",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("=" * 62)
    print("  Tamil Nadu Climate Risk — Dataset Downloader")
    print("=" * 62)
    print(f"  Output directory : {RAW_DIR}")
    print(f"  Total datasets   : {len(DATASETS)}")
    if args.check_only:
        print("  Mode             : URL check only (no download)")
    elif args.skip_existing:
        print("  Mode             : Skip already-downloaded files")
    print("=" * 62)

    # Create output directory
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    session = build_session()
    success_count = 0
    skip_count = 0
    fail_count = 0
    failed_files: list[str] = []

    for idx, (filename, url, description) in enumerate(DATASETS, start=1):
        dest_path = RAW_DIR / filename
        print(f"\n[{idx:02d}/{len(DATASETS)}] {description}")
        print(f"     URL  : {url}")

        # ── Check only mode ───────────────────────────────────
        if args.check_only:
            ok, status, ct = check_url(session, url)
            status_icon = "✅" if ok else "❌"
            print(f"     {status_icon}  HTTP {status} | {ct}")
            if ok:
                success_count += 1
            else:
                fail_count += 1
            continue

        # ── Skip existing ─────────────────────────────────────
        if args.skip_existing and dest_path.exists():
            size_mb = dest_path.stat().st_size / 1_048_576
            print(f"     ⏭️   Already exists ({size_mb:.2f} MB) — skipping")
            skip_count += 1
            continue

        # ── Download ──────────────────────────────────────────
        ok = download_file(session, url, dest_path, description)

        if ok:
            success_count += 1
        else:
            fail_count += 1
            failed_files.append(filename)

        # Small delay between requests — be polite to gov servers
        if idx < len(DATASETS):
            time.sleep(1.5)

    # ── Summary ───────────────────────────────────────────────
    print(f"\n{'=' * 62}")
    print("  Download Summary")
    print(f"{'=' * 62}")

    if args.check_only:
        print(f"  URLs reachable   : {success_count}")
        print(f"  URLs failed      : {fail_count}")
    else:
        print(f"  Downloaded       : {success_count}")
        print(f"  Skipped          : {skip_count}")
        print(f"  Failed           : {fail_count}")

    if failed_files:
        print(f"\n  Failed files (download manually):")
        for f in failed_files:
            print(f"    - {f}")

    if not args.check_only and success_count > 0:
        print(f"\n  All PDFs saved to: {RAW_DIR}")
        print(f"\n  Next step — build the vector store:")
        print(f"    python scripts/setup_db.py")

    print("=" * 62)


if __name__ == "__main__":
    main()
