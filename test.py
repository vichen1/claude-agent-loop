from dotenv import load_dotenv
load_dotenv()
import anthropic

client = anthropic.Anthropic()
msg = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=100,
    messages=[{"role": "user", "content": "Say hi in five words"}],
)
print(msg.content[0].text)
