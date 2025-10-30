import traceback
from insta_alert.config_manager import config
import datetime
from discord_webhook import DiscordWebhook
from colorama import Fore
import requests
import json

def report_error(error: Exception, context: str):
    '''send discord message when process errors out'''
    try:
        tb_str = ''.join(traceback.format_exception(type(error), error, getattr(error, "__traceback__", None)))
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

        # Build mention strings
        mention_roles = getattr(config, "DISCORD_PINGS_ALL", [])

        mentions_text = ' '.join(
            [f"<@&{role}>" for role in mention_roles]
        )
        print(mentions_text)

        # Compose message
        message = (
            f"🚨 **CRITICAL ERROR in {context}** 🚨\n"
            f"**Time (UTC):** {timestamp}\n"
            f"**Error Type:** {type(error).__name__}\n"
            f"**Details:** ```{str(error)}```\n"
            f"**Traceback:** ```{tb_str[-1800:]}```"
            f"pings: {mentions_text}\n"
        )

        # Manually construct full payload (since discord_webhook doesn't expose payload editing)
        payload = {
            "content": message,
            "username": "error-bot"
        }
        
        headers = {
        "Content-Type": "application/json"
        }


        # Directly send the webhook POST
        response = requests.post(
            config.ERROR_WEBHOOK,
            data=json.dumps(payload),
            headers= headers
        )

        if response.status_code >= 300:
            print(Fore.RED + f"Discord webhook failed: {response.status_code} {response.text}" + Fore.RESET)
        else:
            print(Fore.GREEN + "Critical error reported to Discord successfully." + Fore.RESET)

    except Exception as discord_error:
        print(Fore.RED + f"Failed to send error to Discord: {discord_error}" + Fore.RESET)
        
if __name__ == '__main__':
    report_error(ConnectionResetError('test'), 'test')
