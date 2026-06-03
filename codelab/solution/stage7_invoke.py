"""Stage 7 solution — invoke saved agent + download files."""
import os
import tarfile
import tempfile

import requests
from google import genai
from config import DIGEST_PROMPT

AGENT_ID = "my-tech-digest"


def main():
    client = genai.Client()

    env_id = None
    stream = client.interactions.create(
        agent=AGENT_ID,
        input=DIGEST_PROMPT,
        environment="remote",
        stream=True,
    )

    for event in stream:
        print(event)
        if hasattr(event, "interaction") and event.interaction:
            if event.interaction.environment_id:
                env_id = event.interaction.environment_id

    if not env_id:
        print("No environment_id captured — cannot download files.")
        return

    print(f"\nDownloading sandbox snapshot for env: {env_id}")
    api_key = os.environ["GEMINI_API_KEY"]
    response = requests.get(
        f"https://generativelanguage.googleapis.com/v1beta/files/environment-{env_id}:download",
        params={"alt": "media"},
        headers={"x-goog-api-key": api_key},
        allow_redirects=True,
    )
    response.raise_for_status()

    os.makedirs("./output", exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tar_path = os.path.join(tmp, "snapshot.tar")
        with open(tar_path, "wb") as f:
            f.write(response.content)
        with tarfile.open(tar_path) as tar:
            tar.extractall(path="./output", filter="data")

    print("Files extracted to ./output/")
    pdf = "./output/workspace/digest.pdf"
    if os.path.exists(pdf):
        print(f"PDF ready: {pdf}  ({os.path.getsize(pdf):,} bytes)")
    else:
        print("digest.pdf not found in snapshot — agent may not have generated it.")


if __name__ == "__main__":
    main()
