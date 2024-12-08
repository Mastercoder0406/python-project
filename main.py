import os
import asyncio
import requests
import instaloader
import subprocess
import time
from aiohttp import ClientSession
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from tqdm import tqdm

# Global Configuration
FLIC_TOKEN = "flic_8c650a449fb287e5b6f162dbf956a532498f313bad0603bc7f88a6344681f41e"
VIDEO_DIR = "videos"
CATEGORY_ID =25  # Replace with the appropriate category_id

# 1. Download Videos ------------------------------------------------------

def download_instagram_video(url):
    """Download video from Instagram."""
    loader = instaloader.Instaloader()
    try:
        post_code = url.split("/")[-2]
        post = instaloader.Post.from_shortcode(loader.context, post_code)
        loader.download_post(post, target=VIDEO_DIR)
        print(f"Instagram video downloaded: {post_code}")
    except Exception as e:
        print(f"Error downloading Instagram video: {e}")

def download_tiktok_video(url):
    """Download video from TikTok using yt-dlp."""
    try:
        subprocess.run(["yt-dlp", "-o", f"{VIDEO_DIR}/%(title)s.%(ext)s", url], check=True)
        print("TikTok video downloaded successfully.")
    except Exception as e:
        print(f"Error downloading TikTok video: {e}")

def download_video(platform, url):
    """Download video based on platform."""
    if platform == "instagram":
        download_instagram_video(url)
    elif platform == "tiktok":
        download_tiktok_video(url)
    else:
        print("Unsupported platform. Please choose 'instagram' or 'tiktok'.")

# 2. API Integration ------------------------------------------------------

def get_upload_url():
    """Generate upload URL using GET request."""
    headers = {"Flic-Token": FLIC_TOKEN, "Content-Type": "application/json"}
    response = requests.get("https://api.socialverseapp.com/posts/generate-upload-url", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print("Upload URL obtained successfully.")
        return data['upload_url'], data['hash']
    else:
        print("Error fetching upload URL:", response.text)
        return None, None

async def upload_video_async(session, upload_url, file_path):
    """Upload video file asynchronously using PUT."""
    try:
        with open(file_path, 'rb') as video:
            async with session.put(upload_url, data=video) as response:
                if response.status == 200:
                    print(f"Uploaded: {file_path}")
                else:
                    print(f"Upload failed for {file_path}: {response.status}")
    except Exception as e:
        print(f"Error during upload: {e}")

def create_post(video_hash, title):
    """Create post after video upload."""
    headers = {"Flic-Token": FLIC_TOKEN, "Content-Type": "application/json"}
    payload = {
        "title": title,
        "hash": video_hash,
        "is_available_in_public_feed": False,
        "category_id": CATEGORY_ID
    }
    response = requests.post("https://api.socialverseapp.com/posts", json=payload, headers=headers)
    if response.status_code == 200:
        print(f"Post created successfully: {title}")
    else:
        print("Failed to create post:", response.text)

async def process_video(file_path, title):
    """Generate upload URL, upload video, and create post."""
    print(f"Processing file: {file_path}")
    upload_url, video_hash = get_upload_url()
    if upload_url and video_hash:
        async with ClientSession() as session:
            await upload_video_async(session, upload_url, file_path)
        create_post(video_hash, title)
        os.remove(file_path)  # Auto-delete after upload
        print(f"File deleted: {file_path}")
    else:
        print("Skipping file due to upload URL error.")

# 3. Directory Monitoring -------------------------------------------------

class VideoHandler(FileSystemEventHandler):
    """Monitor directory for new .mp4 files."""
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".mp4"):
            print(f"New video detected: {event.src_path}")
            asyncio.run(process_video(event.src_path, title=os.path.basename(event.src_path)))

def monitor_directory(directory):
    """Monitor specified directory for video files."""
    if not os.path.exists(directory):
        os.makedirs(directory)
    event_handler = VideoHandler()
    observer = Observer()
    observer.schedule(event_handler, directory, recursive=False)
    observer.start()
    print(f"Monitoring directory: {directory}")
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# 4. Main Function --------------------------------------------------------

async def main():
    print("Video Bot Started!")
    print("1. Download videos from Instagram/TikTok")
    print("2. Monitor directory for .mp4 files and upload them")

    # User input for downloading videos
    while True:
        platform = input("Enter platform (instagram/tiktok or 'q' to quit): ").lower()
        if platform == 'q':
            break
        url = input("Enter video URL: ").strip()
        download_video(platform, url)

    # Start monitoring directory
    print("\nStarting directory monitoring...")
    monitor_directory(VIDEO_DIR)

if __name__ == "__main__":
    asyncio.run(main())
