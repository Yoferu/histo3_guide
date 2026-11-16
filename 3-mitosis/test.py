import argparse
import logging
import pathlib
import subprocess
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}


def download_with_curl(file_id: int, dest: pathlib.Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        return
    part = dest.with_suffix(dest.suffix + ".part")
    url = f"https://api.figshare.com/v2/file/download/{file_id}"
    subprocess.run(
        [
            "curl", "-L", "-f", "-#",
            "-A", "Mozilla/5.0 (X11; Linux x86_64)",
            "-H", "Referer: https://figshare.com/",
            url, "-o", str(part),
        ],
        check=True,
    )
    part.replace(dest)


def main():
    parser = argparse.ArgumentParser(description="Download MIDOG++ dataset from Figshare.")
    parser.add_argument("--location", type=str, default="images", help="Target directory.")
    parser.add_argument("--max-images", type=int, default=None, help="Limit number of .tiff images.")
    args = parser.parse_args()

    out_dir = pathlib.Path(args.location)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. جلب ملفات JSON و SQLite من مقالات البيانات الوصفية
    logging.info("Fetching metadata files (MIDOG++.json, MIDOG++.sqlite)...")
    for article_id in (23531118, 23531121):
        files = requests.get(
            f"https://api.figshare.com/v2/articles/{article_id}/files?page_size=100",
            headers=HEADERS,
            timeout=30,
        ).json()
        for f in files:
            logging.info(f"Downloading metadata: {f['name']}")
            download_with_curl(f["id"], out_dir / f["name"])

    logging.info("Searching Figshare Collections for MIDOG++ images...")
    cols = requests.post(
        "https://api.figshare.com/v2/collections/search",
        json={"search_for": "MIDOG++"},
        headers=HEADERS,
        timeout=30,
    ).json()
    col_id = next(c["id"] for c in cols if "MIDOG" in c.get("title", ""))
    arts = requests.get(
        f"https://api.figshare.com/v2/collections/{col_id}/articles?page_size=100",
        headers=HEADERS,
        timeout=30,
    ).json()

    tiffs = []
    for a in arts:
        files = requests.get(
            f"https://api.figshare.com/v2/articles/{a['id']}/files?page_size=1000",
            headers=HEADERS,
            timeout=30,
        ).json()
        tiffs.extend([f for f in files if f["name"].lower().endswith(".tiff")])

    tiffs = sorted(tiffs, key=lambda x: x["name"])
    if args.max_images is not None:
        tiffs = tiffs[: args.max_images]

    logging.info(f"Downloading {len(tiffs)} .tiff images using curl...")
    for idx, t in enumerate(tiffs, 1):
        logging.info(f"[{idx}/{len(tiffs)}] {t['name']}")
        download_with_curl(t["id"], out_dir / t["name"])

    logging.info("Download complete.")


if __name__ == "__main__":
    main()
