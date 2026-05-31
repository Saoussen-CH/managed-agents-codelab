from google import genai
from config import BASE_AGENT, DIGEST_PROMPT, EDITORIAL_VOICE

client = genai.Client()

interaction = client.interactions.create(
    agent=BASE_AGENT,
    input=DIGEST_PROMPT,
    system_instruction=EDITORIAL_VOICE,
    environment="remote",
)

print(interaction.output_text)
