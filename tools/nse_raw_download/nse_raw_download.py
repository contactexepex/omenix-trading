"""Downloads NSE's daily files for the research into your fno-research folder:

- F&O files in the current format, 1 Jan 2024 to today;
- F&O files in the old format, 1 Jan 2019 to 5 Jul 2024 (NSE's last old-format day);
- NSE's daily index closes (NIFTY 50, NIFTY Bank, India VIX and others), 1 Jan 2019 to today;
- NSE's daily participant-wise open interest (client, DII, FII, pro), 1 Jan 2019 to today.

Run it with no options:   python nse_raw_download.py
It asks which folder to use (press Enter for the folder you are in). That's all. Files you already have are kept and
skipped, so if it stops, just run it again. The original files are saved unchanged; the research code reads both
formats into one (fno/fo_bhavcopy.py in the repository).
"""

from __future__ import annotations

import csv
import hashlib
import platform
import ssl
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

NSE = "https://nsearchives.nseindia.com/content/"
MONTH_CODES = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")


@dataclass(frozen=True)
class Dataset:
    """One kind of daily NSE file: its name, address and folder (the same layout as fno/storage, tested there)."""

    label: str
    url: str  # format string: day, mon, filename
    filename: str  # format string: day, mon
    folder: str
    first: date
    last: date | None = None  # None: still published

    def name_for(self, day: date) -> str:
        return self.filename.format(day=day, mon=MONTH_CODES[day.month - 1])

    def path_for(self, day: date) -> str:
        return f"{self.folder}/{day:%Y}/{day:%m}/{self.name_for(day)}"

    def url_for(self, day: date) -> str:
        return self.url.format(day=day, mon=MONTH_CODES[day.month - 1], filename=self.name_for(day))

    def covers(self, day: date) -> bool:
        return self.first <= day and (self.last is None or day <= self.last)


CURRENT_FO = Dataset(
    "F&O (current format)",
    NSE + "fo/{filename}",
    "BhavCopy_NSE_FO_0_0_0_{day:%Y%m%d}_F_0000.csv.zip",
    "raw/nse/derivatives/fo-bhavcopy",
    date(2024, 1, 1),
)
OLD_FO = Dataset(
    "F&O (old format)",
    NSE + "historical/DERIVATIVES/{day:%Y}/{mon}/{filename}",
    "fo{day:%d}{mon}{day:%Y}bhav.csv.zip",
    "raw/nse/derivatives/fo-bhavcopy-legacy",
    date(2019, 1, 1),
    date(2024, 7, 5),
)
INDEX_CLOSE = Dataset(
    "index closes", NSE + "indices/{filename}", "ind_close_all_{day:%d%m%Y}.csv", "raw/nse/indices/index-close",
    date(2019, 1, 1),
)  # fmt: skip
PARTICIPANT_OI = Dataset(
    "participant open interest", NSE + "nsccl/{filename}", "fao_participant_oi_{day:%d%m%Y}.csv",
    "raw/nse/derivatives/participant-oi", date(2019, 1, 1),
)  # fmt: skip
FO_DATASETS = (CURRENT_FO, OLD_FO)
MANIFESTS = {CURRENT_FO: "manifest.csv", PARTICIPANT_OI: "manifest_participant_oi.csv"}  # NSE files' SHA-256
FIRST_DAY = date(2019, 1, 1)
NO_FILE_LOG = "nse-days-without-files.txt"  # next to the raw folder, so a re-run does not ask NSE again
GAP_SECONDS = 1.0
RETRY_WAITS = (5, 15, 45)
REFUSED = (403, 429)
MAC_ROOT_CERTIFICATES = "/System/Library/Keychains/SystemRootCertificates.keychain"
CERTIFICATE_HELP = (
    "This computer's Python cannot check secure websites (missing certificates).\n"
    "On a Mac: open Finder > Applications > Python 3.x and double-click 'Install Certificates.command', then run again."
)
USER_AGENT = "Mozilla/5.0 (personal research; one request per second)"


def relative_path(day: date) -> str:
    return CURRENT_FO.path_for(day)


def load_manifest(path: Path) -> tuple[dict[str, str], set[str]]:
    """date -> expected SHA-256 for days NSE published a file, and the days it published none (weekends, holidays)."""
    if not path.is_file():
        return {}, set()
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    expected = {r["date"]: r["sha256"] for r in rows if r.get("status") == "200" and r.get("sha256")}
    return expected, {r["date"] for r in rows if r.get("status") == "404"}


def file_tag(dataset: Dataset, day: str) -> str:
    return f"{dataset.folder}|{day}"


def load_manifests(paths: dict[Dataset, Path]) -> tuple[dict[str, str], set[str]]:
    """file tag -> expected SHA-256, and the tags of files NSE never published, from each dataset's manifest."""
    expected, no_file = {}, set()
    for dataset, path in paths.items():
        fingerprints, missing = load_manifest(path)
        expected |= {file_tag(dataset, day): sha for day, sha in fingerprints.items()}
        no_file |= {file_tag(dataset, day) for day in missing}
    return expected, no_file


def secure_context() -> ssl.SSLContext:
    """Python's own certificates, or on a Mac without them the Mac's built-in ones. Checking is never switched off."""
    context = ssl.create_default_context()
    if context.cert_store_stats()["x509_ca"] or platform.system() != "Darwin":
        return context
    try:
        pem = subprocess.run(
            ["security", "find-certificate", "-a", "-p", MAC_ROOT_CERTIFICATES], capture_output=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return context
    with tempfile.NamedTemporaryFile("wb", suffix=".pem", delete=False) as bundle:
        bundle.write(pem)
    return ssl.create_default_context(cafile=bundle.name)


CONTEXT = secure_context()


class CertificateProblem(RuntimeError):
    """The computer cannot verify NSE's secure certificate; retrying will not help."""


def download(url: str) -> tuple[int, bytes]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    for wait in (*RETRY_WAITS, None):
        try:
            with urlopen(request, timeout=60, context=CONTEXT) as response:
                return response.status, response.read()
        except HTTPError as exc:
            return exc.code, b""
        except (URLError, OSError) as exc:
            if isinstance(getattr(exc, "reason", exc), ssl.SSLCertVerificationError):
                raise CertificateProblem(CERTIFICATE_HELP) from exc
            if wait is None:
                raise RuntimeError(f"network failure for {url}: {exc}") from exc
            print(f"  connection problem ({exc}); retrying in {wait} s")
            time.sleep(wait)
    raise AssertionError("unreachable")


def save(target: Path, data: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.part")
    temporary.write_bytes(data)
    temporary.replace(target)


def choose_folder(argv: list[str]) -> Path:
    """The folder named after the script, or asked for (Enter = the current folder)."""
    if argv:
        return Path(argv[0].strip().strip('"'))
    here = Path.cwd()
    answer = input(f"Which folder should the files go into?\nPress Enter for {here}\nor paste another folder: ")
    return Path(answer.strip().strip('"')) if answer.strip() else here


class Stop(RuntimeError):
    """NSE refused requests: stop now to avoid a block, and run again later."""


class Downloader:
    """Fetches one day's file of one dataset unless it is already there or known to have none."""

    def __init__(self, dest: Path, expected: dict[str, str], no_file: set[str]):
        self.dest, self.expected, self.no_file = dest, expected, no_file
        self.counts = {"saved": 0, "already there": 0, "no file that day": 0, "mismatch": 0, "failed": 0}
        self.log = dest / NO_FILE_LOG

    def get(self, dataset: Dataset, day: date) -> bool:
        """True when the file exists (saved now or before)."""
        target = self.dest / dataset.path_for(day)
        tag = file_tag(dataset, day.isoformat())
        want = self.expected.get(tag)
        if target.is_file():
            if want and hashlib.sha256(target.read_bytes()).hexdigest() != want:
                print(f"MISMATCH {day} {dataset.label}: existing file differs from the recorded fingerprint; untouched")
                self.counts["mismatch"] += 1
            else:
                self.counts["already there"] += 1
            return True
        if tag in self.no_file:
            return False
        status, data = download(dataset.url_for(day))
        time.sleep(GAP_SECONDS)
        if status in REFUSED:
            raise Stop(f"NSE refused the request (HTTP {status}). Stopped to avoid a block; run again later.")
        if status == 404:
            self.counts["no file that day"] += 1
            self.no_file.add(tag)
            with self.log.open("a") as f:
                f.write(tag + "\n")
            return False
        if status != 200:
            print(f"{day} {dataset.label}: unexpected HTTP {status}; skipped (run again later)")
            self.counts["failed"] += 1
            return False
        if want and hashlib.sha256(data).hexdigest() != want:
            print(f"MISMATCH {day} {dataset.label}: NSE's file differs from the recorded fingerprint; not saved")
            self.counts["mismatch"] += 1
            return False
        save(target, data)
        self.counts["saved"] += 1
        print(f"saved {day} {dataset.label}  ({len(data) / 1e6:.2f} MB)")
        return True


def run(
    dest: Path, start: date = FIRST_DAY, end: date | None = None, manifests: dict[Dataset, Path] | None = None
) -> int:
    end = end or date.today()
    expected, known_missing = load_manifests(
        manifests or {d: Path(__file__).with_name(n) for d, n in MANIFESTS.items()}
    )
    log = dest / NO_FILE_LOG
    no_file = (set(log.read_text().split()) if log.is_file() else set()) | known_missing
    dest.mkdir(parents=True, exist_ok=True)
    loader = Downloader(dest, expected, no_file)
    print(f"Saving into {dest / 'raw'}  (about 1.5 hours the first time; stop with Ctrl+C and run again any time)")
    day = start
    try:
        while day <= end:
            traded = [loader.get(d, day) for d in FO_DATASETS if d.covers(day)]
            if PARTICIPANT_OI.covers(day):  # every day, not only F&O-file days: its manifest lists the days without one
                traded.append(loader.get(PARTICIPANT_OI, day))
            if any(traded) and INDEX_CLOSE.covers(day):  # a trading day: NSE published any derivatives file for it
                loader.get(INDEX_CLOSE, day)  # (30 Mar 2021: no old-format F&O file, but index closes and OI exist)
            day += timedelta(days=1)
    except Stop as exc:
        print(exc)
    print("Done. " + "; ".join(f"{k}: {v}" for k, v in loader.counts.items()))
    return 1 if loader.counts["mismatch"] else 0


def main() -> int:
    dest = choose_folder(sys.argv[1:])
    try:
        code = run(dest)
    except (CertificateProblem, RuntimeError) as exc:
        print(f"\nStopped: {exc}")
        code = 2
    if not sys.argv[1:]:
        input("Press Enter to close.")
    return code


if __name__ == "__main__":
    sys.exit(main())
