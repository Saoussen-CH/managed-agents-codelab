from google import genai

client = genai.Client()

first = client.interactions.create(
    agent="my-tech-digest",
    input="Today's digest. Sources: HN, Verge, TechCrunch.",
    environment="remote",
)
print("=== First turn ===")
print(first.output_text)
print(f"Environment ID: {first.environment_id}")

second = client.interactions.create(
    agent="my-tech-digest",
    input="Make the AI section twice as long. Add an 'Editor's Note' at the top.",
    environment=first.environment_id,
    previous_interaction_id=first.id,
)
print("\n=== Second turn (refined) ===")
print(second.output_text)
