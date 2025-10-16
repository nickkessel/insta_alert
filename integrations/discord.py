from colorama import Fore, Back
from discord_webhook import DiscordWebhook, DiscordEmbed
import config


def log_to_discord(message, img_path):
    webhook = DiscordWebhook(url=config.WEBHOOKS[0], content=message)
    with open(img_path, 'rb') as f:
        webhook.add_file(file=f.read(), filename='Alert.png')
    try:
        print(Fore.GREEN + "Sent to Discord webhook successfully!" + Fore.RESET)
        response = webhook.execute()
    except Exception as e:
        print(Fore.RED + f"Error sending to webhook! {e}" + Fore.RESET)