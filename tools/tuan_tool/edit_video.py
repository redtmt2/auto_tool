"""
This script edit video with ffmpeg.
"""
import os
import asyncio
import json
import shutil
import configparser
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiohttp
import feedparser
import isodate

try:
    from utils import logger, CURRENT_DIR, ROOT_DIR
except ImportError:
    from .utils import logger, CURRENT_DIR, ROOT_DIR

# Read config
config = configparser.ConfigParser()
config.read(CURRENT_DIR / "config.ini")

os.environ["IMAGEIO_FFMPEG_EXE"] = "D:/yt_download/tools/tuan_tool/ffmpeg.exe"

# GPU_SUPPORT: "CUDA", "MPS", "CPU"
GPU_SUPPORT = "MPS"  # Thay thành "CUDA" hoặc "MPS" nếu muốn dùng GPU

def get_ffmpeg_video_codec():
    if GPU_SUPPORT == "CUDA":
        return "h264_nvenc"
    elif GPU_SUPPORT == "MPS":
        return "h264_videotoolbox"
    else:
        return "libx264"

CODEC = get_ffmpeg_video_codec()

async def change_video_speed(source, output, original_duration, target_duration):
    """
    Change video speed so that final duration is exactly target_duration (in seconds).
    """
    speed_factor = original_duration / target_duration
    video_filter = f'setpts={1/speed_factor}*PTS'
    # atempo only supports 0.5-2.0 per filter, so chain if needed
    atempo_filters = []
    remain = speed_factor
    while remain < 0.5 or remain > 2.0:
        if remain < 0.5:
            atempo_filters.append('atempo=0.5')
            remain /= 0.5
        else:
            atempo_filters.append('atempo=2.0')
            remain /= 2.0
    atempo_filters.append(f'atempo={remain:.5f}')
    audio_filter = ','.join(atempo_filters)
    cmd = f'ffmpeg -y -i "{source}" -filter:v "{video_filter}" -filter:a "{audio_filter}" "{output}"'
    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, _ = await proc.communicate()
    return proc.returncode


async def concate_video(source, ending, output):
    """
    Slow down the video
    """
    # .\ffmpeg.exe -i .\download\59s.mp4 -i .\download\ending.mp4 -filter_complex "[0:v] [0:a] [1:v] [1:a] concat=n=2:v=1:a=1 [v] [a]" -map "[v]" -map "[a]" .\download\output-video-join.mp4
    cmd = " ".join(
        [
            "ffmpeg",
            "-y",
            "-i",
            f'"{source}"',
            "-i",
            f'"{ending}"',
            "-r",
            "30",
            "-filter_complex",
            '"[0:v] [0:a] [1:v] [1:a] concat=n=2:v=1:a=1 [v] [a]"',
            "-map",
            '"[v]"',
            "-map",
            '"[a]"',
            "-c:v", CODEC,
            f'"{output}"',
        ]
    )
    logger.debug(cmd)

    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    # stdout, stderr = await proc.communicate()
    _, _ = await proc.communicate()

    # logger.info(f"[{cmd!r} exited with {proc.returncode}]")
    # if stdout:
    #     logger.info(f"[stdout]\n{stdout.decode()}")
    # if stderr:
    #     logger.error(f"Tiktok ID: {tiktok_id} [stderr]\n{stderr.decode()}")

    return proc.returncode


# Helper: Slow down video to arbitrary speed
async def slow_down_video(source, output, speed_factor):
    """
    Slow down or speed up the video by speed_factor (e.g., 0.9 for slower, 1.1 for faster)
    """
    # Check if input has audio
    cmd_probe = f'ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "{source}"'
    proc_probe = await asyncio.create_subprocess_shell(cmd_probe, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, _ = await proc_probe.communicate()
    has_audio = bool(stdout.decode().strip())

    video_filter = f'setpts={1/speed_factor}*PTS'
    if has_audio:
        atempo_filters = []
        remain = speed_factor
        while remain < 0.5 or remain > 2.0:
            if remain < 0.5:
                atempo_filters.append('atempo=0.5')
                remain /= 0.5
            else:
                atempo_filters.append('atempo=2.0')
                remain /= 2.0
        atempo_filters.append(f'atempo={remain:.3f}')
        audio_filter = ','.join(atempo_filters)
        cmd = f'ffmpeg -y -i "{source}" -filter:v "{video_filter}" -c:v {CODEC} -filter:a "{audio_filter}" "{output}"'
    else:
        cmd = f'ffmpeg -y -i "{source}" -filter:v "{video_filter}" -c:v {CODEC} -an "{output}"'

    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        print("FFMPEG ERROR:", stderr.decode())
    return proc.returncode

# Helper: Trim video segment
async def trim_video(source, output, start_time, duration):
    """
    Trim a segment from the video (start_time in seconds, duration in seconds)
    """
    cmd = f'ffmpeg -y -ss {start_time} -i "{source}" -t {duration} -c copy "{output}"'
    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, _ = await proc.communicate()
    return proc.returncode


def get_current_time() -> str:
    current_time = datetime.now()
    # Get dd:mm:HH:MM
    converted_time = current_time.strftime("%d%m_%H%M")
    return converted_time


async def edit_video(channel_info, latest_video):
    """
    Edit video
    Return video title
    """
    source = None
    output_temp = None
    output = None
    try:
        video_duration = latest_video['duration']
        logger.info(f"Tiktok ID: {channel_info['tiktokId']} | Video duration: {video_duration} | Editing...")
        video_title = latest_video['yt_videoid'] + '_final'
        source = (
            ROOT_DIR
            / "download"
            / channel_info['tiktokId']
            / f"{latest_video['yt_videoid']}.mp4"
        )
        output = (
            ROOT_DIR
            / "download"
            / channel_info['tiktokId']
            / f"{video_title}.mp4"
        )
        # Validate source file exists
        if not source.exists() or source.stat().st_size == 0:
            raise FileNotFoundError(f"Source video file missing or empty: {source}")

        # 1. If duration >= 61s: download as-is, no edit
        if video_duration >= 61:
            shutil.copy(str(source), str(output))
            logger.info(f"Tiktok ID: {channel_info['tiktokId']} | No edit needed (>=61s)")

        # 2. If duration < 30s: skip
        elif video_duration < 30:
            logger.info(f"Tiktok ID: {channel_info['tiktokId']} | Video too short (<30s), skipping.")
            return None

        # 3. If 51 <= duration < 61: slow down to exactly 61s
        elif 51 <= video_duration < 61:
            output_temp = (
                ROOT_DIR / "download" / channel_info['tiktokId'] / f"{latest_video['yt_videoid']}_slowdown.mp4"
            )
            res = await change_video_speed(source, output_temp, video_duration, 61)
            if res != 0:
                raise RuntimeError("Failed to slow down video to 61s")
            shutil.move(str(output_temp), str(output))
            logger.info(f"Tiktok ID: {channel_info['tiktokId']} | Slowed down to 61s.")

        # 4. If 31 <= duration < 51: slow to 0.9x, then append ending to reach 61s
        elif 31 <= video_duration < 51:
            slowed_temp = (
                ROOT_DIR / "download" / channel_info['tiktokId'] / f"{latest_video['yt_videoid']}_slow09.mp4"
            )
            res = await slow_down_video(source, slowed_temp, 0.9)
            if res != 0:
                raise RuntimeError("Failed to slow down video to 0.9x")
            # Get new duration after slow down
            cmd = f'ffprobe -v quiet -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{slowed_temp}"'
            proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, _ = await proc.communicate()
            slowed_duration = float(stdout.decode()) if stdout else video_duration / 0.9
            # If slowed_duration >= 61, trim to 61s
            if slowed_duration >= 61:
                res = await trim_video(slowed_temp, output, 0, 61)
                if res != 0:
                    raise RuntimeError("Failed to trim slowed video to 61s")
            else:
                # Need to append from original video
                append_needed = 61 - slowed_duration
                # Default: take last N seconds from original video
                start_clip = max(0, video_duration - append_needed)
                clip_temp = (
                    ROOT_DIR / "download" / channel_info['tiktokId'] / f"{latest_video['yt_videoid']}_clip.mp4"
                )
                res = await trim_video(source, clip_temp, start_clip, append_needed)
                if res != 0:
                    raise RuntimeError("Failed to trim ending segment for append")
                # Concatenate slowed + clip
                concat_temp = (
                    ROOT_DIR / "download" / channel_info['tiktokId'] / f"{latest_video['yt_videoid']}_concat.mp4"
                )
                cmd = (
                    f'ffmpeg -y -i "{slowed_temp}" -i "{clip_temp}" '
                    f'-filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1 [v][a]" '
                    f'-map "[v]" -map "[a]" "{concat_temp}"'
                )
                proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                _, _ = await proc.communicate()
                # Final trim to 61s (in case concat is slightly longer)
                res = await trim_video(concat_temp, output, 0, 61)
                if res != 0:
                    raise RuntimeError("Failed to trim final video to 61s")
                # Cleanup
                if clip_temp.exists():
                    clip_temp.unlink()
                if concat_temp.exists():
                    concat_temp.unlink()
            # Cleanup
            if slowed_temp.exists():
                slowed_temp.unlink()
            logger.info(f"Tiktok ID: {channel_info['tiktokId']} | Slowed to 0.9x and appended ending to reach 61s.")

        else:
            # Fallback: just copy source (should not hit)
            shutil.copy(str(source), str(output))
            logger.warning(f"Tiktok ID: {channel_info['tiktokId']} | Unexpected duration, copied as-is.")

        # Validate output file
        if not output.exists() or output.stat().st_size == 0:
            raise RuntimeError("Output file missing or empty after processing")
    
        # Clean up source file after successful processing
        if source.exists():
            source.unlink()
        if output_temp and output_temp.exists():
            output_temp.unlink()
        return video_title
    
    except Exception as e:
        logger.error(f"Tiktok ID: {channel_info['tiktokId']} | Video processing failed: {str(e)}")
        try:
            if output_temp and output_temp.exists():
                output_temp.unlink()
            if output and output.exists():
                output.unlink()
        except Exception as cleanup_error:
            logger.error(f"Tiktok ID: {channel_info['tiktokId']} | Cleanup failed: {str(cleanup_error)}")
        raise
