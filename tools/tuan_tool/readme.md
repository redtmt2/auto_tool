# TikTok Auto Reup

This project automates the process of downloading from Youtube shorts and re-uploading videos to TikTok.

## Features
- Download the latest Youtube shorts ☑
- Edit video with ffmpeg ✖
- Customizable captions and hashtags ✖
- Automatic upload video ✖

## Requirements

- [FFmpeg](https://ffmpeg.org/download.html)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- Python 3.12+
- Python packages:
    - `feedparser==6.0.11`
    - `aiohttp==3.7.4`
    - `isodate==0.6.0`

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/22minhhoang/tiktok_auto_reup.git
    ```
2. Navigate to the project directory:
    ```bash
    cd tiktok_auto_reup
    ```
3. Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. Configure your Youtube API KEY and others in `config.ini`.
2. Edit the `list.txt` file with the TikTok IDs and Youtube channel IDs you want to download from. Each line should be in the format `tiktok_id|youtube_channel_id`.
3. Run the script to update the list TikTok and Youtube IDs pair to DB:
    ```bash
    python update.py
    ```
4. Run the script everytime to check and download the latest Youtube shorts:
    ```bash
    python main.py
    ```
5. Downloaded videos will be saved in the `download` directory.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
