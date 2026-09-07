import os
import boto3
from dotenv import load_dotenv
from pathlib import Path
from insta_alert.utils.error_handler import report_error
from colorama import Fore, Back
cwd = Path(os.getcwd())
env_path = cwd / ".env"
load_dotenv(override=True) #this is wild btw
load_dotenv(env_path)

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL")

r2 = boto3.client(
    's3',
    endpoint_url = f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
    aws_access_key_id = R2_ACCESS_KEY_ID,
    aws_secret_access_key = R2_SECRET_ACCESS_KEY,
    region_name = 'auto',
)

def upload_image(image_path):
    image_path = Path(image_path)

    try:
        r2.upload_file(
            str(image_path),
            R2_BUCKET_NAME,
            image_path.name,
            ExtraArgs={
                'ContentType': 'image/jpeg'
            }
        )
    except Exception as e:
        print(Fore.RED + f'R2: Error while uploading file to Cloudflare R2!! Detail: {e}' + Fore.RESET)
        report_error(e, "An error occurred while attempting to upload to R2 site!")

    image_url = f'{R2_PUBLIC_URL}/{image_path.name}'
    print(Fore.GREEN + 'Posted to Cloudflare R2 Successfully!' + Fore.RESET)
    return image_url

if __name__ == '__main__':
    url = upload_image('graphics/live-test2/alert_FFWFGF_urnoid249018400e0831f89b6ee5c9ebc674a431b17ad0538a7c7a40011.jpg')
    print(url)