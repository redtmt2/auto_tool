# Integrated YouTube to TikTok Automation Tool

This tool automatically monitors YouTube channels for new videos, downloads them, edits them to meet TikTok requirements, and uploads them to TikTok.

## Features

- **Continuous Monitoring**: Runs 24/7 to monitor specified YouTube channels for new videos
- **Multi-Account Support**: Handles multiple TikTok accounts simultaneously
- **Video Editing**: Automatically edits videos to ensure they are over 1 minute long
- **Cache System**: Maintains a cache to prevent duplicate downloads and uploads
- **Logging System**: Comprehensive logging for each TikTok account
- **Web Dashboard**: Simple web-based interface to manage the tool
- **Proxy Support**: Configurable proxy settings for each TikTok account

## Recent Updates

- **Single Input Configuration**: Now using a single `config/channels.json` file for all channel configurations
- **Automatic TikTok Login**: The system now checks for TikTok login cache and automatically initiates login if needed
- **Improved Error Handling**: Better logging and error recovery for TikTok login issues

## Installation

1. Clone this repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Install Playwright browsers:
   ```
   playwright install
   ```

## Configuration

### Channel Configuration

Edit the `config/channels.json` file to specify the YouTube channels to monitor:

```json
[
    {
        "tiktokId": "your_tiktok_username",
        "channelId": "YouTube_channel_ID",
        "channelName": "YouTube_channel_name",
        "url": "https://www.youtube.com/@channel_handle",
        "proxy": "http://username:password@host:port" // Optional
    }
]
```

Optional fields:
- `proxy`: Proxy configuration in format `http://username:password@host:port`
- `hashtags`: Array of hashtags to use for TikTok uploads

### Application Configuration

The application configuration is stored in `config/integrated_config.ini`:

```ini
[DEFAULT]
CheckInterval = 900  # Check interval in seconds (15 minutes)
MaxWorkers = 5
DeleteOldVideos = false
IgnoreFirstTime = true

[YOUTUBE]
ApiKey = YOUR_YOUTUBE_API_KEY
NotOlderThan = 48000  # in minutes

[EDIT]
VideoSpeed = 0.77
AudioSpeed = 1.299

[LOGGING]
LogLevel = INFO
```

### TikTok Login Cache

The system automatically checks for TikTok login cache files in the `accounts` folder. If no cache exists for a TikTok account:

1. The system will launch a browser for TikTok login
2. You need to log in manually in the browser window
3. After successful login, the cache will be saved as `accounts/TK_cookies_<tiktokId>.json`

## Usage

### Command Line

To start the application from the command line:

```
python integrated_app.py
```

### Web Dashboard

To start the web dashboard:

```
python dashboard.py
```

Then open your browser and navigate to `http://localhost:5000`

## Workflow

1. **TikTok Login Check**:
   - System checks if `tiktokId` has a cache file in the `accounts` folder
   - If no cache exists, it launches a login window
   - After login, the cache is saved for future use

2. **YouTube Monitoring**:
   - System checks YouTube channels for new videos
   - Downloads videos that meet the criteria

3. **Video Processing**:
   - Downloaded videos are edited for TikTok (aspect ratio, speed, etc.)

4. **TikTok Upload**:
   - Edited videos are uploaded to TikTok with appropriate descriptions and hashtags

## Troubleshooting

- **Login Issues**: Check the `login_errors.log` file for details
- **Processing Issues**: Check the account-specific log files in the `logs` directory
- **General Issues**: Check the `logs/integrated_app.log` file

## Dashboard Features

- Start/stop monitoring
- View logs for each TikTok account
- Add/remove YouTube channels
- Configure monitoring settings
- Clear cache
- View recent uploads

## File Structure

- `integrated_app.py`: Main application
- `dashboard.py`: Web dashboard
- `config/`: Configuration files
  - `integrated_config.ini`: Application configuration
  - `channels.json`: YouTube channels configuration
- `data/`: Data files
  - `cache.json`: Cache of processed videos
  - `youtube_channels.json`: YouTube channel data
  - `tiktok_channels.json`: TikTok channel data
- `logs/`: Log files
- `templates/`: HTML templates for the dashboard
- `tools/`: Original tools
  - `tuan_tool/`: YouTube monitoring and download tool
  - `TikTokAutoUploader/`: TikTok upload tool

## Logging

Logs are stored in the `logs/` directory:
- `integrated_app.log`: Main application log
- `dashboard.log`: Dashboard log
- `{tiktok_id}.log`: Log for each TikTok account

## Notes

- The tool uses the YouTube Data API to check for new videos, so you need a valid API key
- TikTok accounts must be configured in the `accounts/` directory
- The tool will automatically create necessary directories if they don't exist

## Requirements

- Python 3.8+
- FFmpeg (for video editing)
- Node.js (for TikTok upload)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
