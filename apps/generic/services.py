# generic/services.py
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Securely fetch secrets from the environment
discord_bot_token = os.getenv("discord_bot_token")
indexer_channel_id = os.getenv("INDEXER_DISCORD_CHANNEL_ID")

def send_discord_message(msg, channel_id):
    """Generic function to send a message to any Discord channel."""
    if not discord_bot_token:
        print("ERROR: discord_bot_token is not configured. Cannot send message.")
        return
    
    url = f"https://discordapp.com/api/channels/{channel_id}/messages"
    headers = { "Authorization": "Bot " + discord_bot_token }
    body = { "content": msg }
    
    try:
        response = requests.post(url, headers=headers, data=body)
        response.raise_for_status() # Raises an exception for bad status codes (4xx or 5xx)
        print(f"Successfully sent Discord message to channel {channel_id}.")
        return {"data": f"Status code {response.status_code}"}
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to send Discord message: {e}")
        return {"error": str(e)}

def send_indexer_alert(msg: str, network: str = "N/A", app: str = "N/A"):
    """
    Sends a pre-formatted, critical alert to the dedicated indexer channel.
    """
    if not indexer_channel_id:
        print("WARNING: INDEXER_DISCORD_CHANNEL_ID not set. Cannot send alert.")
        return

    # Build the string line-by-line, now including network and app context.
    lines = [
        "🚨 **CRITICAL INDEXER ERROR** 🚨",
        "---",
        f"**Network:** `{network.upper()}`",
        f"**App:** `{app.upper()}`",
        "---",
        "**Disruption Detected:**",
        "```",
        msg,
        "```",
        "---",
        "Please investigate the indexer service immediately."
    ]
    formatted_msg = "\n".join(lines)
    
    return send_discord_message(formatted_msg, indexer_channel_id)
# generic/services.py