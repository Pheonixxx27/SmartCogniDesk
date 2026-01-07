from google import genai

client = genai.Client(
    api_key=""
)

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="Extract numeric IDs from this text: 140111000011644374 3216258445"
)

print(response.text)
