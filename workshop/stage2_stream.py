from google import genai
from config import BASE_AGENT, DIGEST_PROMPT

client = genai.Client()

stream = client.interactions.create(
    agent=BASE_AGENT,
    input=DIGEST_PROMPT,
    environment="remote",
    stream=True,
)

for event in stream:
    print(event)
