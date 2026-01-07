from google import genai

client = genai.Client(api_key="AIzaSyCa_GIhY-NQNq8KgGHjbmkogtSz_un0h0s")

models = client.models.list()

for m in models:
    print(m.name)
