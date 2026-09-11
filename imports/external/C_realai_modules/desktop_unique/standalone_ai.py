from realai import RealAIClient

client = RealAIClient(provider="local")
response = client.chat.create(
    messages=[{"role": "user", "content": "Explain quantum computing simply"}]
)
print(response['choices'][0]['message']['content'])