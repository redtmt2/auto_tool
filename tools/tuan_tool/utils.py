"""
This module contains utility functions for the project.
"""
import base64
import json
import logging
from pathlib import Path
import configparser
import re
import os


ROOT_DIR = Path(os.getcwd())
print("ROOT_DIR:", ROOT_DIR)
CURRENT_DIR = Path(__file__).resolve().parent

# Read config
config = configparser.ConfigParser()
config.read(CURRENT_DIR / "config.ini")

if config["LOGGING"]["LOG_LEVEL"] == "DEBUG":
    LOG_LEVEL = logging.DEBUG
else:
    LOG_LEVEL = logging.INFO
LOG_FILE = config["LOGGING"]["LOG_FILE"]
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def convert_base64_to_json(base64_sample: str) -> dict:
    """
    Convert a base64 encoded string to a JSON object
    Args:
        base64_sample (str): A base64 encoded string
    Returns:
        dict: A JSON object
    """
    # base64_sample = "eyJGb2xkZXJPdXRwdXQiOm51bGwsIklucHV0VmlkZW8iOm51bGwsIklucHV0VGh1bWJuYWlsIjpudWxsLCJPdXRwdXRWaWRlbyI6bnVsbCwiT3V0cHV0VGh1bWJuYWlsIjpudWxsLCJSZW5kZXJUeXBlIjpudWxsLCJSZW5kZXJDb25maWciOm51bGwsIlByb2dyZXNzQ29uZmlnX1NlbGVjdEluZGV4IjowLCJjb3VudFRocmVhZFN0YXJ0IjowLCJpc1J1bm5pbmciOmZhbHNlLCJpc1N1Y2Nlc3MiOmZhbHNlLCJSb3ciOiI0IiwiSXR5cGUiOiJGaWxlIiwiVXJsIjoiQzpcXFdvcmtcXHNyY1xcTmV3IGZvbGRlclxc5LiW55WM44Gu44Ki44OL44Oh44Gu5qeY44Gq5rCX6LGhM+mBuCAjdHJlbmRpbmcgI+efpeitmCAj6ZuR5a2mLm1wNCIsIkNhcHRpb24iOiLkuJbnlYzjga7jgqLjg4vjg6Hjga7mp5jjgarmsJfosaEz6YG4ICN0cmVuZGluZyAj55+l6K2YICPpm5HlraYiLCJDYXB0aW9uT3JpZ2luYWwiOm51bGwsIlByaXZhY3kiOiJTY2hlZHVsZWQiLCJTY2hlZHVsZSI6IjEzLzA5LzIwMjQgMDk6MjciLCJDdXRWaWRlbyI6bnVsbCwiRHVyYXRpb24iOiIwMDowMTowMyIsIlRvdGFsRHVyYXRpb24iOiIwMDowMTowMyIsIkFjY291bnQiOnsiVHlwZSI6IkZpcmVmb3ggUG9ydGFibGUiLCJJRCI6bnVsbCwiTmFtZSI6IjFfc2NhcmluZ193ZWF0aGVyIiwiSURBY2NvdW50IjoiMSJ9LCJDYXJ0IjpudWxsLCJNdXNpYyI6bnVsbCwiQ2FydEFjY291bnRzIjp7IklEUHJvZHVjdCI6bnVsbCwiTmFtZVByb2R1Y3QiOiJOb25lIn0sIk11c2ljQWNjb3VudHMiOm51bGwsIkFjY291bnREZXRhaWxzIjpudWxsLCJTdGF0dXMiOiJOb3Qgc3RhcnQiLCJEb3dubG9hZCI6MCwiUmVuZGVyIjowLCJVcGxvYWQiOjAsIlNvdXJjZSI6bnVsbCwiTG9nRXJyb3IiOltdLCJVUkkiOm51bGx9"
    data_input = json.loads(base64.b64decode(base64_sample).decode("utf-8"))
    return data_input


def remove_hashtags(text: str) -> str:
    """
    Remove hashtags from a text
    Args:
        text (str): A text
    Returns:
        str: A text without hashtags
    """
    pattern = r"#\s*shorts?"
    r = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return r
