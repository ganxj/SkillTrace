from __future__ import annotations

import pathlib
import sys
import zipfile

import requests
import urllib3


ENGINE_VERSION = "42d3d75a56efe1a2e9902f52dc8006099c45d937"
URL = (
    "https://storage.flutter-io.cn/flutter_infra_release/flutter/"
    f"{ENGINE_VERSION}/dart-sdk-windows-x64.zip"
)
ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / ".tools" / "flutter" / "bin" / "cache"
ZIP_PATH = CACHE / "dart-sdk-windows-x64.zip"


def main() -> int:
    urllib3.disable_warnings()
    CACHE.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {URL}")
    with requests.get(URL, stream=True, verify=False, timeout=60) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length") or 0)
        done = 0
        with ZIP_PATH.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                file.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r{done / total:.1%}", end="", flush=True)
    print(f"\nDownloaded {ZIP_PATH}")

    print("Expanding Dart SDK...")
    with zipfile.ZipFile(ZIP_PATH) as archive:
        archive.extractall(CACHE)
    ZIP_PATH.unlink()
    (CACHE / "engine-dart-sdk.stamp").write_text(ENGINE_VERSION, encoding="ascii")
    print("Dart SDK cache is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

