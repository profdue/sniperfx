import requests
import os

bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')

print(f"Token starts with: {bot_token[:10] if bot_token else 'None'}")
print(f"Token ends with: {bot_token[-5:] if bot_token else 'None'}")
print(f"Chat ID: {chat_id}")

# Test with explicit string
url = "https://api.telegram.org/bot8723449566:AAGx0Y4p5uOpa3ibc30UpNFPQjVPDqsqiFA/sendMessage"
payload = {
    'chat_id': '876675468',
    'text': 'Test with hardcoded values',
    'parse_mode': 'HTML'
}

response = requests.post(url, json=payload)
print(response.json())
