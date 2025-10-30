from colorama import Fore, Back
from discord_webhook import DiscordWebhook, DiscordEmbed
from insta_alert.config_manager import config

def log_to_discord(message, img_path, webhooks):
    for hook in webhooks:
        webhook = DiscordWebhook(url= hook, content=message)
        with open(img_path, 'rb') as f:
            webhook.add_file(file=f.read(), filename='Alert.png')
        try:
            print(Fore.GREEN + f"Sent to Discord webhook {hook} successfully!" + Fore.RESET)
            response = webhook.execute()
        except Exception as e:
            print(Fore.RED + f"Error sending to webhook! {e}" + Fore.RESET)