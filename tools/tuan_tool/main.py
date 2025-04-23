"""
This script downloads the latest video from the given YouTube channel.
"""
import os
import asyncio
import json
import shutil
import configparser
from datetime import datetime, timedelta, timezone
import argparse
import requests
import aiohttp
import isodate

try:
    from utils import logger, CURRENT_DIR, ROOT_DIR
    from edit_video import edit_video
except ImportError:
    from .utils import logger, CURRENT_DIR, ROOT_DIR
    from .edit_video import edit_video

# Read config
config = configparser.ConfigParser()
config.read(CURRENT_DIR / "config.ini")
# Use the centralized channels.json file
CHANNELS_CONFIG = ROOT_DIR / "config" / "channels.json"
WORKERS_NUM = int(config["DEFAULT"]["WORKERS_NUM"])
DELETE_OLD_VIDEOS = config["DEFAULT"].getboolean("DELETE_OLD_VIDEOS")
IGNORE_FIRST_TIME = config["DEFAULT"].getboolean("IGNORE_FIRST_TIME")
WAIT_TIME = int(config["DEFAULT"]["WAIT_TIME"])

API_KEY = config["YOUTUBE"]["YOUTUBE_API_KEY_2"]
MAX_NEW_UPLOADS = int(config["YOUTUBE"]["MAX_NEW_UPLOADS"])
NOT_ODLER_THAN = int(config["YOUTUBE"]["NOT_ODLER_THAN"])


lock = asyncio.Lock()


def load_channels():
    """Load channels from the centralized config file"""
    if not CHANNELS_CONFIG.exists():
        logger.error(f"Channels config file not found: {CHANNELS_CONFIG}")
        # Create empty channels file if it doesn't exist
        CHANNELS_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        with open(CHANNELS_CONFIG, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return []
        
    try:
        with open(CHANNELS_CONFIG, 'r', encoding='utf-8') as f:
            channels = json.load(f)
        logger.info(f"Loaded {len(channels)} channels from centralized config")
        return channels
    except Exception as e:
        logger.error(f"Error loading channels config: {e}")
        # Return empty list if file is invalid
        return []

def load_uploaded_status(status_path):
    if os.path.exists(status_path):
        with open(status_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_uploaded_status(status_path, status):
    with open(status_path, 'w', encoding='utf-8') as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

def mark_edited(tiktok_id, video_id, edited=True, video_metadata=None):
    status_path = str(ROOT_DIR / "data" / "uploaded_status.json")
    uploaded_db = load_uploaded_status(status_path)
    if tiktok_id not in uploaded_db:
        uploaded_db[tiktok_id] = {}
    if video_id not in uploaded_db[tiktok_id]:
        uploaded_db[tiktok_id][video_id] = {}
    uploaded_db[tiktok_id][video_id]["edited"] = edited
    uploaded_db[tiktok_id][video_id]["edit_time"] = datetime.now().isoformat(timespec="seconds")
    if video_metadata:
        uploaded_db[tiktok_id][video_id]["publish_time"] = video_metadata.get("published")
        uploaded_db[tiktok_id][video_id]["title"] = video_metadata.get("title")
        uploaded_db[tiktok_id][video_id]["url"] = video_metadata.get("url")
    save_uploaded_status(status_path, uploaded_db)

def mark_uploaded(tiktok_id, video_id, uploaded=True):
    status_path = str(ROOT_DIR / "data" / "uploaded_status.json")
    uploaded_db = load_uploaded_status(status_path)
    if tiktok_id not in uploaded_db:
        uploaded_db[tiktok_id] = {}
    if video_id not in uploaded_db[tiktok_id]:
        uploaded_db[tiktok_id][video_id] = {}
    uploaded_db[tiktok_id][video_id]["uploaded"] = uploaded
    uploaded_db[tiktok_id][video_id]["upload_time"] = datetime.now().isoformat(timespec="seconds")
    save_uploaded_status(status_path, uploaded_db)

def is_short(vid):
    url = 'https://www.youtube.com/shorts/' + vid
    ret = requests.head(url)
    # whether 303 or other values, it's not short
    return ret.status_code == 200

async def get_published_videos(channel_info, user_agent=None) -> list:
    status_path = str(ROOT_DIR / "data" / "uploaded_status.json")
    channel_id = channel_info["channelId"]
    tiktok_id = channel_info["tiktokId"]
    uploaded_db = load_uploaded_status(status_path)
    if tiktok_id not in uploaded_db:
        uploaded_db[tiktok_id] = {}

    api_url = "https://www.googleapis.com/youtube/v3/activities"
    headers = {"User-Agent": user_agent} if user_agent else {}
    params = {
        "key": API_KEY,
        "channelId": channel_id,
        "part": "contentDetails,snippet",
        "maxResults": 6,
    }

    published_videos = []
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, params=params, headers=headers) as response:
            if response.status != 200:
                logger.error(f"Tiktok ID: {tiktok_id} | Failed to get activities | Status: {response.status}")
                return []
            data = await response.json()

            video_ids = []
            video_id_to_snippet = {}
            for item in data.get("items", []):
                content_details = item.get("contentDetails", {})
                video_id = content_details.get("upload", {}).get("videoId")
                if not video_id:
                    continue  # Not an upload activity
                if not is_short(video_id):
                    continue  # Not a YouTube Shorts
                video_ids.append(video_id)
                video_id_to_snippet[video_id] = item["snippet"]
                if len(video_ids) >= MAX_NEW_UPLOADS:
                    break

        if not video_ids:
            return []

        newest_video_id = video_ids[0]
        download_folder = ROOT_DIR / "download" / tiktok_id
        if (download_folder / f"{newest_video_id}.mp4").exists() or (download_folder / f"{newest_video_id}_final.mp4").exists():
            logger.info(f"Tiktok ID: {tiktok_id} | Video {newest_video_id} đã tồn tại. Bỏ qua.")
            return []

        details_url = "https://www.googleapis.com/youtube/v3/videos"
        details_params = {
            "key": API_KEY,
            "id": ','.join(video_ids),
            "part": "contentDetails,snippet",
        }

        async with session.get(details_url, params=details_params) as details_response:
            if details_response.status != 200:
                logger.error(f"Tiktok ID: {tiktok_id} | Failed to get video details | Status: {details_response.status}")
                return []
            details_data = await details_response.json()

            for item in details_data.get("items", []):
                video_id = item["id"]
                snippet = video_id_to_snippet.get(video_id, item.get("snippet", {}))
                duration_str = item["contentDetails"].get("duration")
                try:
                    duration = isodate.parse_duration(duration_str).total_seconds()
                except Exception as e:
                    logger.warning(f"Tiktok ID: {tiktok_id} | Failed to parse duration for video {video_id}: {e}")
                    continue

                if duration < 30 or duration > 300:
                    continue

                video = {
                    "yt_videoid": video_id,
                    "title": snippet.get("title", video_id),
                    "link": f"https://www.youtube.com/shorts/{video_id}",
                    "published": snippet.get("publishedAt", ""),
                    "duration": duration,
                }
                uploaded_db[tiktok_id][video_id] = {"uploaded": False, "edited": False}
                published_videos.append(video)

    save_uploaded_status(status_path, uploaded_db)
    return published_videos


async def get_latest_video(published_videos, channel_info):
    """
    Get the latest video from the given YouTube channel
    Update data only abnormal case
    """
    # Initialize  for this channel if it doesn't exist
    # No longer need to initialize any dict here since youtube_data/tiktok_data is removed.
    
    # Initialize latestVideoId in channel_info if it doesn't exist
    latest_video = None
    for video in published_videos:
        latest_video = video
        break
    return latest_video


async def verify_video(video):
    """
    Additional verification for video (if needed). Assumes duration is already checked.
    """
    # If you want to add more checks, do it here. Otherwise, just return the video dict.
    # For now, just set published_local for compatibility.
    try:
        published_utc = datetime.strptime(
            video["published"], "%Y-%m-%dT%H:%M:%S%z"
        )
        published_localtime = published_utc.astimezone(
            timezone(timedelta(hours=7))
        ).isoformat(timespec="seconds")
        video["published_local"] = published_localtime
    except Exception:
        video["published_local"] = video.get("published", "")
    return {"yt_videoid": video["yt_videoid"], "title": video["title"], "link": video["link"], "published": video["published"], "published_local": video["published_local"], "url": video["link"]}


async def download_video(video_url, tiktok_id):
    """
    Download video from the given URL
    """
    try:

        download_folder = ROOT_DIR / "download" / tiktok_id
        if not download_folder.exists():
            download_folder.mkdir(parents=True)

        cmd = " ".join(
            [
                "yt-dlp",
                "--cookies",
                f"{ROOT_DIR}/www.youtube.com_cookies.txt",
                "-f",
                f'"{args.format}"',  # Wrapped in quotes
                "--merge-output-format",
                "mp4",
                "-P",
                str(download_folder),
                "-o",
                f'"{args.output}"',
                video_url,
            ]
        )

        # Add timeout handling
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)  # 5 min timeout

            if stdout:
                logger.warning(f"Tiktok ID: {tiktok_id} [stdout]\n{stdout.decode()}")
            if stderr:
                logger.error(f"Tiktok ID: {tiktok_id} [stderr]\n{stderr.decode()}")
            if proc.returncode != 0:
                logger.error(f"Tiktok ID: {tiktok_id} | Download failed with code {proc.returncode}")

            return proc.returncode

        except asyncio.TimeoutError:
            logger.error(f"Tiktok ID: {tiktok_id} | Download timed out after 5 minutes")
            return 1

    except Exception as e:
        logger.error(f"Tiktok ID: {tiktok_id} | Download failed with error: {str(e)}")
        return 1


async def worker(channel_info_queue):
    """
    Get the latest video from the given YouTube channel
    """
    while not channel_info_queue.empty():
        channel_info = await channel_info_queue.get()
        try:
            published_videos = []  # Should be loaded from somewhere
            latest_video = await get_latest_video(published_videos, channel_info)
            await edit_video(channel_info, latest_video)
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            continue
        finally:
            channel_info_queue.task_done()


async def run_task(tasks):
    """
    Spawn workers to get channel info
    """
    background_tasks = set()
    async with asyncio.TaskGroup() as tg:
        # Create workers
        for i in range(args.workers):
            task = tg.create_task(worker(tasks))
            background_tasks.add(task)
            if i + 1 >= tasks.qsize():
                break
        await asyncio.gather(*background_tasks)


async def main():
    """
    Main function
    """
    print("Start Run!!")
    download_folder = ROOT_DIR / "download"
    if DELETE_OLD_VIDEOS and download_folder.exists():
        for child_folder in download_folder.iterdir():
            if child_folder.is_dir():
                shutil.rmtree(child_folder)

    # Read input list from file
    channels = load_channels()
    tasks = asyncio.Queue()
    for channel in channels:
        channel_id = channel["channelId"]
        tiktok_id = channel["tiktokId"]
        channel_name = channel["channelName"]
        channel_info = {
            "tiktokId": tiktok_id,
            "channelId": channel_id,
            "channelName": channel_name
        }
        await tasks.put(channel_info)

    await run_task(tasks)


if __name__ == "__main__":
    # For testing
    import argparse
    parser = argparse.ArgumentParser(description='Download latest videos from YouTube channels.')
    parser.add_argument('--cookies', type=str, default=str(ROOT_DIR / 'www.youtube.com_cookies.txt'), help='Path to the cookies file.')
    parser.add_argument('--format', type=str, default='bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio', help='Video format for download.')
    parser.add_argument('--output', type=str, default='%(id)s.%(ext)s', help='Output filename template.')
    parser.add_argument('--workers', type=int, default=1, help='Number of workers to run concurrently.')
    args = parser.parse_args()
    asyncio.run(main())