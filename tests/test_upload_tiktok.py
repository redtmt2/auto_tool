from fake_useragent import UserAgent
from typing import Optional

from tiktok_uploader.upload import upload_videos
from tiktok_uploader.auth import AuthBackend

BROWSERS = {
    'chrome': "Chrome",
    'safari': "Safari",
    'edge': "Edge",
    'firefox': "Firefox"
}

def rotate_user_agent(os: Optional[str] = None):
    ua = UserAgent(browsers=BROWSERS[os])
    return ua.random

videos = [
    {
        'video': 'downloads/@auto5vnn/1_J0zOdXHW0.mp4',
        'description': ''
    }
]


auth = AuthBackend(cookies='tiktok_cookies.txt')
failed_videos = upload_videos(videos=videos, auth=auth, browser="firefox" ,user_agent=rotate_user_agent(os="firefox"), headless=False, skip_split_window=True)


for video in failed_videos:  # each input video object which failed
    print(f"{video['video']} with description {video['description']} failed")




