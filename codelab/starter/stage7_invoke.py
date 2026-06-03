"""
Stage 7 — Invoke the saved agent and download files.

Now that the agent is saved, call it by ID — no inline config needed.
Then download the full sandbox snapshot (a tar file containing all files
the agent created, including digest.pdf).

File download uses the Files API directly via HTTP — there is no SDK method yet.
Docs: https://ai.google.dev/gemini-api/docs/managed-agents-quickstart#download-files
"""
import os
import tarfile
import tempfile

import requests
from google import genai

from config import DIGEST_PROMPT

AGENT_ID = "my-tech-digest"   # must match what you used in Stage 6


def main():
    client = genai.Client()

    # TODO 10: Invoke the saved agent.
    # Use agent=AGENT_ID, input=DIGEST_PROMPT, environment="remote", stream=True.
    # Each invocation forks a fresh sandbox from base_environment.
    # Capture env_id from the interaction.completed event.
    #
    # env_id = None
    # stream = client.interactions.create(
    #     agent=AGENT_ID,
    #     input=DIGEST_PROMPT,
    #     environment="remote",
    #     stream=True,
    # )
    # for event in stream:
    #     print(event)
    #     if hasattr(event, "interaction") and event.interaction:
    #         if event.interaction.environment_id:
    #             env_id = event.interaction.environment_id

    # TODO 11: Download the environment snapshot using the Files API.
    # Endpoint: GET generativelanguage.googleapis.com/v1beta/files/environment-{env_id}:download
    # Auth: x-goog-api-key header with your GEMINI_API_KEY
    # Extract the tar and open ./output/workspace/digest.pdf
    #
    # if env_id:
    #     api_key = os.environ["GEMINI_API_KEY"]
    #     response = requests.get(
    #         f"https://generativelanguage.googleapis.com/v1beta/files/environment-{env_id}:download",
    #         params={"alt": "media"},
    #         headers={"x-goog-api-key": api_key},
    #         allow_redirects=True,
    #     )
    #     response.raise_for_status()
    #
    #     with tempfile.TemporaryDirectory() as tmp:
    #         tar_path = os.path.join(tmp, "snapshot.tar")
    #         with open(tar_path, "wb") as f:
    #             f.write(response.content)
    #         with tarfile.open(tar_path) as tar:
    #             tar.extractall(path="./output", filter="data")
    #
    #     print("Files extracted to ./output/")
    #     print("PDF: ./output/workspace/digest.pdf")
    pass


if __name__ == "__main__":
    main()
