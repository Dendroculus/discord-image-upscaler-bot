# Discord Image Upscaler Bot

A Discord bot that upscales images using high-quality Lanczos resampling. Users can upload images and get them upscaled automatically.

## Features

- 🖼️ Upscale images with configurable scale factor (default: 2x)
- 🎨 Support for multiple image formats (PNG, JPG, JPEG, WEBP, GIF)
- ⚡ Fast processing using PIL/Pillow
- 🔒 File size validation and format checking
- 📊 Information command to display bot capabilities

## Prerequisites

- Python 3.8 or higher
- A Discord Bot Token (from [Discord Developer Portal](https://discord.com/developers/applications))

## Installation

1. Clone this repository:
```bash
git clone https://github.com/Dendroculus/discord-image-upscaler-bot.git
cd discord-image-upscaler-bot
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

4. Edit `.env` and add your Discord bot token:
```
DISCORD_TOKEN=your_actual_discord_bot_token_here
UPSCALE_FACTOR=2
MAX_FILE_SIZE_MB=8
```

## Configuration

Edit the `.env` file to customize bot behavior:

- `DISCORD_TOKEN`: Your Discord bot token (required)
- `UPSCALE_FACTOR`: Image upscaling multiplier (default: 2)
- `MAX_FILE_SIZE_MB`: Maximum allowed file size in MB (default: 8)

## Usage

1. Start the bot:
```bash
python bot.py
```

2. Invite the bot to your Discord server using the OAuth2 URL from Discord Developer Portal with the following permissions:
   - Send Messages
   - Attach Files
   - Read Message History
   - Use Slash Commands

3. In Discord, use the following commands:

### Commands

- `!upscale` - Attach an image to your message and use this command to upscale it
- `!info` - Display bot information and capabilities

### Example Usage

1. Upload an image in a Discord channel
2. Type `!upscale` in the message with the attachment
3. Wait for the bot to process
4. Receive your upscaled image!

## How It Works

The bot uses the Pillow (PIL) library with Lanczos resampling algorithm, which provides high-quality image upscaling by:
1. Downloading the attached image
2. Loading it into memory
3. Applying Lanczos interpolation to resize the image
4. Returning the upscaled result

## Limitations

- Maximum file size: 8MB (configurable)
- Supported formats: PNG, JPG, JPEG, WEBP, GIF
- Discord's file upload limit may apply to output images

## Development

### Project Structure

```
discord-image-upscaler-bot/
├── bot.py              # Main bot implementation
├── config.py           # Configuration management
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
├── .env               # Your local configuration (not committed)
├── README.md          # This file
└── LICENSE            # MIT License
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Troubleshooting

### Bot doesn't respond
- Ensure the bot token is correct in `.env`
- Verify the bot has proper permissions in your Discord server
- Check that message content intent is enabled in Discord Developer Portal

### Image processing fails
- Ensure the image format is supported
- Check that the file size is within limits
- Verify Pillow is installed correctly

## Support

For issues and questions, please open an issue on GitHub.