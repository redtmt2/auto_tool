# -*- coding: utf-8 -*-
"""
Integrated YouTube to TikTok Automation Tool

This application monitors YouTube channels for new videos, downloads them,
edits them to meet TikTok requirements, and uploads them to TikTok.
"""

import os
import json
import time
import asyncio
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import traceback
from concurrent.futures import ThreadPoolExecutor

# Import YouTube monitoring and download functions
from tools.tuan_tool.main import (
    get_published_videos,
    load_uploaded_status, mark_edited, mark_uploaded,
    edit_video, 
    WAIT_TIME
)

from TikTokAutoUploader.tiktokautouploader import upload_tiktok
from fake_useragent import UserAgent
from typing import Optional


BROWSERS = {
    'chrome': "Chrome",
    'safari': "Safari",
    'edge': "Edge",
    'firefox': "Firefox"
}

# Setup paths
CURRENT_DIR = Path(__file__).resolve().parent
ACCOUNT_FOLDER = CURRENT_DIR / "accounts"
CACHE_FILE = CURRENT_DIR / "data" / "cache.json"
LOG_DIR = CURRENT_DIR / "logs"

# Ensure directories exist
os.makedirs(CURRENT_DIR / "config", exist_ok=True)
os.makedirs(CURRENT_DIR / "data", exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(ACCOUNT_FOLDER, exist_ok=True)

# Setup logging tổng thể
error_handler = logging.FileHandler(LOG_DIR / "integrated_app.error.log", encoding="utf-8")
error_handler.setLevel(logging.ERROR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "integrated_app.log", encoding="utf-8"),
        logging.StreamHandler(),
        error_handler  # Thêm handler này
    ],
    encoding="utf-8"
)
logger = logging.getLogger("integrated_app")

def rotate_user_agent(browser_name: Optional[str] = "firefox"):
    ua = UserAgent(browsers=BROWSERS[browser_name])
    return ua.random

class TikTokUploader:
    def __init__(self):
        pass  # No global cookies file

    def _update_status(self, tiktok_id, status, result, video_path=None):
        DATA_DIR = Path(__file__).resolve().parent / "data"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        info = {
            "tiktok_id": tiktok_id,
            "status": status,
            "result": result,
            "video_path": str(video_path) if video_path else None
        }
        info_path = DATA_DIR / f"{tiktok_id}_upload_status.json"
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

    async def upload_to_channel(self, channel, video_path) -> bool:
        try:
            tiktok_id = channel.get('tiktokId')
            # cookies_file = f'accounts/TK_cookies_{tiktok_id}.json'
            # Choose browser (default to firefox)
            browser = channel.get('browser', 'firefox')
            user_agent = rotate_user_agent(browser)
            # Truyền proxy nếu có trong channel config, xử lý cả dạng dict và str
            proxy = channel.get('proxy')
            if isinstance(proxy, str):
                # Dạng: host:port hoặc host:port:user:pass
                parts = proxy.split(':')
                if len(parts) == 2:
                    proxy = {"server": f"{parts[0]}:{parts[1]}"}
                elif len(parts) == 4:
                    proxy = {
                        "server": f"{parts[0]}:{parts[1]}",
                        "username": parts[2],
                        "password": parts[3]
                    }
                else:
                    logger.warning(f"Invalid proxy format: {proxy}. Skipping proxy.")
                    proxy = None

            success = await upload_tiktok(
                video=str(video_path),
                description='',
                accountname=tiktok_id,
                suppressprint=True,
                headless=True,
                stealth=True,
                proxy=proxy,
                user_agent=user_agent,
                logger=logger
            )
            if success:
                self._update_status(tiktok_id, 'success', 'Uploaded', video_path)
                return True
            else:
                self._update_status(tiktok_id, 'failed', 'Failed to upload', video_path)
                return False
        except Exception as e:
            self._update_status(tiktok_id, 'failed', str(e), video_path)
            return False

    def _update_status(self, channel_id, status, details, video_path=None):
        status_file = "data/status.json"
        status_obj = {
            'tiktok_id': channel_id,
            'timestamp': datetime.now().isoformat(),
            'status': status,
            'details': details,
            'video_path': str(video_path) if video_path else None
        }
        # Try to read the existing status file
        try:
            if os.path.exists(status_file):
                with open(status_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # If the file is a list (legacy), convert to dict by grouping by tiktok_id
                if isinstance(data, list):
                    new_data = {}
                    for entry in data:
                        tid = entry.get('tiktok_id', 'unknown')
                        if tid not in new_data:
                            new_data[tid] = []
                        new_data[tid].append(entry)
                    data = new_data
            else:
                data = {}
        except Exception:
            data = {}

        # Append the new status_obj to the correct tiktok_id
        if channel_id not in data or not isinstance(data[channel_id], list):
            data[channel_id] = []
        data[channel_id].append(status_obj)

        # Save back as dict-of-lists
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# Account-specific loggers
account_loggers = {}

def setup_account_logger(account_id):
    """Setup a logger for a specific TikTok account"""
    if account_id in account_loggers:
        return account_loggers[account_id]
    
    log_file = LOG_DIR / f"{account_id}.log"
    
    # Tạo handler cho file với encoding utf-8
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    
    # Tạo handler cho console (tùy chọn)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    
    # Tạo logger cho account
    account_logger = logging.getLogger(f"account_{account_id}")
    account_logger.setLevel(logging.INFO)
    account_logger.addHandler(file_handler)
    account_logger.addHandler(console_handler)  # Thêm để log ra console
    
    account_loggers[account_id] = account_logger
    return account_logger


def load_cache():
    """Load the cache of processed videos"""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"youtube_videos": {}, "tiktok_uploads": {}}

def save_cache(cache):
    """Save the cache of processed videos"""
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=4)

def load_channels():
    """Load channels from the unified config file"""
    channels_file = CURRENT_DIR / "config" / "channels.json"
    
    # Ensure config directory exists
    os.makedirs(CURRENT_DIR / "config", exist_ok=True)
    
    if not channels_file.exists():
        logger.info(f"Creating new channels config file at: {channels_file}")
        with open(channels_file, 'w', encoding="utf-8") as f:
            json.dump([], f, indent=4)
        return []
    
    try:
        with open(channels_file, 'r', encoding="utf-8") as f:
            channels = json.load(f)
        logger.info(f"Loaded {len(channels)} channels from config")
        return channels
    except Exception as e:
        logger.error(f"Error loading channels config: {e}")
        # Return empty list if file is invalid
        return []

async def process_channel_concurrently(channel):
    tiktok_id = channel.get('tiktokId')
    channel_id = channel.get('channelId')
    channel_name = channel.get('channelName')
    logger.info(f"=== START processing channel: {channel_name} (TikTok: {tiktok_id}) ===")
    
    if not all([tiktok_id, channel_id, channel_name]):
        logger.error(f"Missing required information for channel: {channel}")
        return
    
    # Check if TikTok account has valid login cache
    cookie_path = os.path.join(ACCOUNT_FOLDER, f"TK_cookies_{tiktok_id}.txt")

    # Only check for existence; manual creation is required
    if not os.path.exists(cookie_path):
        logger.error(f"No TikTok login cache found for account {tiktok_id}. Please create accounts/TK_cookies_{tiktok_id}.txt manually.")
        return False
    
    logger.info(f"Processing channel: {channel_name} (ID: {channel_id}) for TikTok account: {tiktok_id}")
    
    try:
        # Get published videos
        published_videos = await get_published_videos(channel, rotate_user_agent("chrome"))
        if not published_videos:
            logger.warning(f"No published videos found for channel: {channel_name}")
            return
        
        status_path = "data/uploaded_status.json"
        uploaded_db = load_uploaded_status(status_path)

        for video in published_videos:
            video_id = video.get('yt_videoid') or video.get('id')
            video_url = video.get('url') or video.get('link')
            duration = video.get('duration')
            if not video_id or not video_url:
                logger.warning(f"No suitable videos found for channel: {channel_name}")
                continue
            status = uploaded_db.get(tiktok_id, {}).get(video_id, {})
            if status.get("edited") and status.get("uploaded"):
                logger.info(f"Video {video_id} already edited and uploaded. Skipping.")
                logger.info(f"Status: edited={status.get('edited')}, uploaded={status.get('uploaded')}, edit_time={status.get('edit_time')}, upload_time={status.get('upload_time')}")
                continue
            elif status.get("edited"):
                logger.info(f"Video {video_id} already edited but not uploaded yet.")
                logger.info(f"Status: edited={status.get('edited')}, edit_time={status.get('edit_time')}")
            elif status.get("uploaded"):
                logger.info(f"Video {video_id} already uploaded but not edited.")
                logger.info(f"Status: uploaded={status.get('uploaded')}, upload_time={status.get('upload_time')}")
            download_folder = CURRENT_DIR / "download" / tiktok_id
            if not download_folder.exists():
                download_folder.mkdir(parents=True)
            # Nếu chưa edit, thì edit
            video_title = None
            if not status.get("edited"):
                # Download video
                logger.info(f"Downloading video: {video_id} from channel: {channel_name}")
                cmd = " ".join([
                    "yt-dlp",
                    "--cookies",
                    str(CURRENT_DIR / "www.youtube.com_cookies.txt"),
                    "-f",
                    '"bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4"',
                    "--merge-output-format",
                    "mp4",
                    "-P",
                    str(download_folder),
                    "--playlist-items", "1",
                    "-o",
                    '"%(id)s.%(ext)s"',
                    "--print", '"after_move:filepath"',
                    video_url,
                ])
                proc = await asyncio.create_subprocess_shell(
                    cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode != 0:
                    logger.error(f"Failed to download video: {video_id} from channel: {channel_name}")
                    logger.error(stderr.decode())
                    continue
                # Parse the output file path from yt-dlp stdout
                output_lines = stdout.decode().strip().splitlines()
                if not output_lines:
                    logger.error(f"No output from yt-dlp for video: {video_id}")
                    continue
                
                output_file = output_lines[-1].strip().strip('"')
                output_file_path = Path(output_file)
                logger.info(f"yt-dlp output file: {output_file_path}")
                
                if not output_file_path.exists():
                    logger.error(f"Downloaded file does not exist: {output_file_path}")
                    continue

                logger.info(f"Video duration: {duration:.2f} seconds")

                # Edit video for TikTok
                video_title = await edit_video(channel, video)
                edited_path = download_folder / f"{video_title}.mp4"
                if not video_title or not os.path.exists(edited_path):
                    logger.error(f"Failed to edit video: {edited_path}")
                    continue
                logger.info(f"Video edited: {video_title}")
                mark_edited(tiktok_id, video_id, edited=True, video_metadata=video)

            else:
                # Nếu đã edit, lấy lại tên file edit
                video_title = video_id + "_final"
                edited_path = str(download_folder / f"{video_title}.mp4")
                if not os.path.exists(edited_path):
                    logger.error(f"Edited file does not exist: {edited_path}")
                    continue
            # Nếu đã upload rồi thì bỏ qua
            if status.get("uploaded"):
                logger.info(f"Video {video_id} already uploaded. Skipping upload.")
                continue
            # Upload video
            uploader = TikTokUploader()
            upload_result = await uploader.upload_to_channel(channel, edited_path)
            if upload_result:
                mark_uploaded(tiktok_id, video_id, uploaded=True)
                logger.info(f"Video {video_id} uploaded and marked as uploaded.")
            else:
                logger.warning(f"Failed to upload video {video_id}")

    except Exception as e:
        logger.error(f"Error processing channel {channel_name}: {e}")
    finally:
        logger.info(f"=== END processing channel: {channel_name} (TikTok: {tiktok_id}) ===")

async def run_monitoring_cycle():
    """Run a complete monitoring cycle for all accounts and channels"""
    logger.info("Starting monitoring cycle")

    # Load channels configuration
    channels = load_channels()
    
    # Group channels by TikTok account
    tiktok_accounts = set(channel["tiktokId"] for channel in channels)
    
    # Process each TikTok account
    tasks = []
    for tiktok_id in tiktok_accounts:
        account_channels = [channel for channel in channels if channel["tiktokId"] == tiktok_id]
        for channel in account_channels:
            task = asyncio.create_task(process_channel_concurrently(channel))
            tasks.append(task)
    
    # Wait for all tasks to complete
    await asyncio.gather(*tasks)
    
    logger.info("Monitoring cycle completed")

def monitoring_loop():
    """Main monitoring loop that runs continuously"""
    logger.info(f"Starting monitoring loop with interval: {WAIT_TIME} seconds")
    
    while True:
        try:
            # Run the monitoring cycle
            asyncio.run(run_monitoring_cycle())
            
            # Wait for the next cycle
            logger.info(f"Waiting {WAIT_TIME} seconds until next check")
            time.sleep(WAIT_TIME)
            
        except Exception as e:
            logger.error(f"Error in monitoring loop: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Wait a bit before retrying
            time.sleep(60)

def start_monitoring():
    """Start the monitoring in a separate thread"""
    monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
    monitoring_thread.start()
    return monitoring_thread

if __name__ == "__main__":
    logger.info("Starting Integrated YouTube to TikTok Automation Tool")
    
    # Start the monitoring loop
    monitoring_thread = start_monitoring()
    
    try:
        # Keep the main thread alive
        while monitoring_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        logger.error(traceback.format_exc())
