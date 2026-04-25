"""
Downloads all raw data files from the team's shared Google Drive folder.
Uses gdown.download_folder() — no per-file IDs needed.

Usage:
    python download_data.py
"""
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
import gdown

load_dotenv()

GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID", "16PqSr1GCyt3UsE1_REmD2bYKGVbvvtk6")

RAW_DIR = Path("data/raw")
NB_ORIGINAL_DIR = Path("notebooks/_original")

# Mapping: filename (as downloaded) → final destination
# gdown places files flat in the output dir; we sort them after download
DATA_FILES = {
    "raw_mobile_money.parquet": RAW_DIR / "raw_mobile_money.parquet",
    "stg_mobile_money.parquet": RAW_DIR / "stg_mobile_money.parquet",
    "customer_profiles.json":   RAW_DIR / "customer_profiles.json",
    "ewallet_transactions.xml": RAW_DIR / "ewallet_transactions.xml",
}
NOTEBOOK_FILES = {
    "Nigerian_E_wallet.ipynb":                   NB_ORIGINAL_DIR / "Nigerian_E_wallet.ipynb",
    "EDA_Nigerian_Banking_Mobile_Money.ipynb":    NB_ORIGINAL_DIR / "EDA_Nigerian_Banking_Mobile_Money.ipynb",
    "Customer_Profiles_Ingestion_EDA_(3).ipynb": NB_ORIGINAL_DIR / "Customer_Profiles_Ingestion_EDA.ipynb",
    "pipeline_xml.ipynb":                        NB_ORIGINAL_DIR / "pipeline_xml.ipynb",
    "EWallet_XML.docx":                          NB_ORIGINAL_DIR / "EWallet_XML.docx",
}
ALL_FILES = {**DATA_FILES, **NOTEBOOK_FILES}

def already_have_all():
    return all(dest.exists() for dest in ALL_FILES.values())

def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    NB_ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)

    if already_have_all():
        print("[OK] All files already present — nothing to download.")
        return

    tmp_dir = Path("data/_gdrive_tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    print(f"[DOWNLOAD] Fetching Drive folder {GDRIVE_FOLDER_ID} ...")
    gdown.download_folder(
        id=GDRIVE_FOLDER_ID,
        output=str(tmp_dir),
        quiet=False,
        use_cookies=False,
    )

    # Walk tmp_dir recursively and move files to their destinations.
    # Drive sometimes prefixes files with "Copy of " — strip it for lookup.
    moved, skipped, unknown = [], [], []
    for src in tmp_dir.rglob("*"):
        if not src.is_file():
            continue
        name = src.name
        canonical = name.removeprefix("Copy of ").strip()
        key = name if name in ALL_FILES else canonical
        if key in ALL_FILES:
            dest = ALL_FILES[key]
            if dest.exists():
                skipped.append(name)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest))
                moved.append(f"{name} → {dest}")
        else:
            unknown.append(str(src))

    shutil.rmtree(tmp_dir, ignore_errors=True)

    print("\n=== Download summary ===")
    for m in moved:
        print(f"  [MOVED]   {m}")
    for s in skipped:
        print(f"  [EXISTS]  {s}")
    for u in unknown:
        print(f"  [UNKNOWN] {u} (left in tmp, now deleted)")

    missing = [name for name, dest in ALL_FILES.items() if not dest.exists()]
    if missing:
        print(f"\n[WARNING] Still missing: {missing}")
        print("  Check Drive permissions or re-run download_data.py")
    else:
        print("\n[DONE] All files present.")

if __name__ == "__main__":
    main()
