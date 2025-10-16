from dotenv import load_dotenv
from colorama import Fore, Back
import requests
import json
import os
load_dotenv()

FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")

def post_to_facebook(message, img_path): #message is string & img is https url reference to .jpg or .png
    if not img_path:
        print('no image path provided')
        return
    photo_upload_url = f"https://graph.facebook.com/{FACEBOOK_PAGE_ID}/photos"
    photo_payload = {
        "published": "false",
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
    }

    try:
        with open(img_path, 'rb') as image_file:
            files = {'source': image_file}
            photo_response = requests.post(photo_upload_url, data = photo_payload, files = files)

        photo_response.raise_for_status()
        photo_id = photo_response.json()['id']
        print(Fore.GREEN + "FB: Uploaded Image successfully" + Fore.RESET)

    except requests.RequestException as e:
        print(Fore.RED + f"FB: Error uploading image: {e}" + Fore.RESET)
        print(Fore.RED + f"FB: Response: {e.response.text}" + Fore.RESET) # More detailed error
        return
    except FileNotFoundError:
        print(Fore.RED + f"FB: Error: Could not find image file at {img_path}" + Fore.RESET)
        return

        # create the post using the uploaded photo ID
    post_url = f"https://graph.facebook.com/{FACEBOOK_PAGE_ID}/feed"
    post_payload = {
        "message": message,
        "attached_media[0]": json.dumps({"media_fbid": photo_id}),
        "access_token": FACEBOOK_PAGE_ACCESS_TOKEN,
    }

    try:
        post_response = requests.post(post_url, data=post_payload)
        post_response.raise_for_status()
        print(Fore.GREEN + "FB: Posted to Facebook successfully" + Fore.RESET)
    except requests.RequestException as e:
        print(Fore.RED + f"Error creating post: {e}" + Fore.RESET)
        print(Fore.RED + f"Response: {e.response.text}" + Fore.RESET)