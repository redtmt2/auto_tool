import asyncio
import sys
import subprocess
import json
from pathlib import Path

# Set project root (adjust as needed)
ROOT_DIR = Path(__file__).resolve().parent.parent
DOWNLOAD_DIR = ROOT_DIR / "download"
DATA_DIR = ROOT_DIR / "data"
print(ROOT_DIR)

from tools.tuan_tool.edit_video import edit_video

# Dummy channel info
TEST_CHANNEL_ID = "UC4GukH9W5BZVfZ-GaOWQUSw"
TEST_CHANNEL_NAME = "Idol"

async def download_video_yt_dlp(yt_url, tiktok_id):
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    tiktok_dir = DOWNLOAD_DIR / tiktok_id
    tiktok_dir.mkdir(parents=True, exist_ok=True)

    output_path = tiktok_dir / "%(id)s.%(ext)s"
    cmd = ' '.join([
        "yt-dlp",
        "--cookies", str(ROOT_DIR / "www.youtube.com_cookies.txt"),
        "-f", "bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo+bestaudio",
        "--playlist-items", "1",
        "-o", f'"{str(output_path)}"',
        "--print", '"after_move:filepath"',
        yt_url,
    ])
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("yt-dlp failed:", result.stderr)
        return None
    # Lấy tên file từ dòng cuối cùng của stdout
    output_file = result.stdout.strip().splitlines()[-1]
    output_file_path = Path(output_file)
    print("output_file: ", output_file)
    if output_file_path.exists():
        return output_file_path
    print("No video file found after download.")
    return None

async def main(yt_url, tiktok_id):
    print(f"Downloading video from {yt_url} for TikTok ID {tiktok_id}...")
    video_file = await download_video_yt_dlp(yt_url, tiktok_id)
    if not video_file:
        print("Download failed!")
        return

    # Prepare dummy video/channel info for edit_video
    video_id = video_file.stem
    video_info = {
        "yt_videoid": video_id,
        "title": "Test Video",
        "link": yt_url,
        "published": "2025-01-01T00:00:00+00:00",
        "published_local": "2025-01-01T07:00:00+07:00",
        "url": yt_url,
    }
    channel_info = {
        "tiktokId": tiktok_id,
        "channelId": TEST_CHANNEL_ID,
        "channelName": TEST_CHANNEL_NAME,
    }
    youtube_data = {TEST_CHANNEL_ID: {}}
    tiktok_data = {tiktok_id: {}}

    print("Editing video...")
    try:
        result = await edit_video(channel_info, video_info, youtube_data, tiktok_data)
        print(f"Edit result: {result}")
        # Save info to data folder after successful edit
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        info_path = DATA_DIR / f"{tiktok_id}_{video_id}_info.json"
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump({
                "video_info": video_info,
                "channel_info": channel_info,
                "edit_result": result
            }, f, ensure_ascii=False, indent=2)
        print(f"Saved info to {info_path}")
    except Exception as e:
        print(f"Edit failed: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Standalone test: Download and edit YouTube Shorts")
    parser.add_argument("--yt_url", type=str, help="YouTube Shorts URL", default="https://www.youtube.com/@OreVsWorld/shorts")
    parser.add_argument("--tiktok_id", type=str, default="testuser2", help="TikTok ID for test folder")
    args = parser.parse_args()

    asyncio.run(main(args.yt_url, args.tiktok_id))