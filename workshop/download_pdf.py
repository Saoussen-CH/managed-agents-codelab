import os
import sys
import tarfile

import requests


def download(env_id: str) -> None:
    api_key = os.environ["GEMINI_API_KEY"]

    r = requests.get(
        f"https://generativelanguage.googleapis.com/v1beta/files/environment-{env_id}:download",
        params={"alt": "media"},
        headers={"x-goog-api-key": api_key},
        allow_redirects=True,
    )
    r.raise_for_status()

    with open("snapshot.tar", "wb") as f:
        f.write(r.content)

    with tarfile.open("snapshot.tar") as tar:
        tar.extractall(path="./output", filter="data")

    print("PDF saved to ./output/workspace/digest.pdf")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python download_pdf.py <environment_id>")
        sys.exit(1)
    download(sys.argv[1])
