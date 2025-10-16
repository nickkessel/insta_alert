from instagrapi import Client
from dotenv import load_dotenv
import os
from colorama import Fore, Back, Style
from PIL import Image, ImageOps
import config
import json
load_dotenv()

SESSION_FILE = "session.json"

def instagram_login(username, password):
    """
    Logs into Instagram reliably by creating, verifying, and reusing a session file.
    This session includes device settings to appear more legitimate to Instagram.

    Args:
        username (str): The Instagram username.
        password (str): The Instagram password.

    Returns:
        Client: An authenticated instagrapi Client object, or None if login fails.
    """
    cl = Client()

    try:
        if os.path.exists(SESSION_FILE):
            # Session file exists, let's load it and verify the user.
            with open(SESSION_FILE, 'r') as f:
                session_data = json.load(f)
            
            stored_user = session_data.get('username')
            
            if stored_user == username:
                print(f"✅ Session file verified for user: {stored_user}")
                cl.load_settings(SESSION_FILE)
                # The login is session-based, which is less suspicious
                #print(f"id: {session_data.get("authorization_data", {}).get("sessionid")}")
                cl.login_by_sessionid(session_data.get("authorization_data", {}).get("sessionid"))
                cl.get_timeline_feed() # Verify login works
                print(Back.GREEN + f"Successfully logged in as @{username} using existing session." + Back.RESET)
                return cl
            else:
                print(f"⚠️ Session file is for a different user ('{stored_user}'). Logging in new user '{username}'.")
                # Fall through to the new login logic below
        
        # --- This block runs if session file doesn't exist OR is for a different user ---
        print(f"Performing a new login for @{username}...")
        cl.login(username, password)
        
        # This is the most important step: dump_settings saves device info, cookies, etc.
        # This makes future logins look like they're from the same "phone".
        cl.dump_settings(SESSION_FILE)
        print(f"Created a new session file: {SESSION_FILE}")

        # Now, add our custom username tag to the file
        with open(SESSION_FILE, 'r+') as f:
            session_data = json.load(f)
            session_data['username'] = username
            f.seek(0) # Rewind file to the beginning
            json.dump(session_data, f, indent=4)
            f.truncate() # Remove any trailing data if the new content is smaller

        print(Back.GREEN + f"Successfully logged in and created session for @{username}." + Back.RESET)
        return cl

    except Exception as e:
        print(Back.RED + f"Error during Instagram login for @{username}: {e}" + Back.RESET)
        return None

def make_instagram_post(caption, file_path, type, client):
    '''
    Args:
        caption (str): Caption for the post, including any tags
        file_path (str): Path to the alert graphic, must be in .jpg format
        type (str): grid or story
        client (Client): authenticated Instagrapi Client object
    '''
    try:
        if type == 'grid':
            client.photo_upload(path = file_path, caption = caption)
            
        if type == 'story':
            resize_for_instagram_story(file_path, 'graphics/tempresize.jpg') #TODO: make this a unique path for each graphic so if the process fails for whatever reason it doesnt post again the last thing to be put at the tempresize.jpg address.
            client.photo_upload_to_story(path = 'graphics/tempresize.jpg', caption= caption)
            
        print(Back.GREEN + f'IG {type} post success.' + Back.RESET)
    except Exception as e: 
        print(Back.RED + f"Some error occuring while posting to IG {type}. Skipping the post. More: {e}" + Back.RESET)
        
def resize_for_instagram_story(image_path, output_path):
    """
    Resizes an image to fit within a 9x16 aspect ratio (1080x1920 pixels)
    for Instagram Stories, adding black bars as padding without cropping.

    Args:
        image_path (str): The path to the input image file.
        output_path (str): The path where the resized image will be saved.
    """
    # Define Instagram Story resolution (9:16 aspect ratio)
    IG_STORY_WIDTH = 1080
    IG_STORY_HEIGHT = 1920
    IG_STORY_ASPECT_RATIO = IG_STORY_WIDTH / IG_STORY_HEIGHT

    try:
        with Image.open(image_path) as img:
            original_width, original_height = img.size
            original_aspect_ratio = original_width / original_height
            print('img open')

            # Determine scaling factor
            if original_aspect_ratio > IG_STORY_ASPECT_RATIO:
                new_width = IG_STORY_WIDTH
                new_height = int(new_width / original_aspect_ratio)
            else:
                new_height = IG_STORY_HEIGHT
                new_width = int(new_height * original_aspect_ratio)

            # Resize the image while maintaining its aspect ratio
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Create a new blank image with the target Instagram Story dimensions (black background)
            new_img = Image.new("RGB", (IG_STORY_WIDTH, IG_STORY_HEIGHT), (0, 0, 0)) # Black background

            # Calculate paste position to center the resized image
            paste_x = (IG_STORY_WIDTH - new_width) // 2
            paste_y = (IG_STORY_HEIGHT - new_height) // 2
            new_img.paste(img, (paste_x, paste_y))

            # Save the result
            new_img.save(output_path)
            print(f"Image resized and saved to {output_path}")

    except FileNotFoundError:
        print(f"Error: Image not found at {image_path}")
    except Exception as e:
        print(f"An error occurred: {e}")
            
if __name__ == '__main__':
    cl1 = instagram_login('-', '-') #returns a client object #TODO: rare but should handle case for if password is changed/session.json file is for the right username but login fails. 
    
    feed = cl1.get_timeline_feed()

    #make_instagram_post('test??', 'graphics/alert_SPSUNR_urnoid2490184009e01364a406b776d7043786c21d5df92e5b570e20011.jpg', 'story')