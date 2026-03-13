import requests
import os

bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')

print("Sending test message...")
url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
payload = {
    'chat_id': chat_id,
    'text': '🔧 Test message from GitHub Actions',
    'parse_mode': 'HTML'
}

response = requests.post(url, json=payload)
print(response.json())
