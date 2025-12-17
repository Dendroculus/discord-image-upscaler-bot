"""Discord Image Upscaler Bot - Main bot implementation."""
import io
import discord
from discord.ext import commands
from PIL import Image
import aiohttp
from config import (
    DISCORD_TOKEN,
    UPSCALE_FACTOR,
    MAX_FILE_SIZE_BYTES,
    SUPPORTED_FORMATS
)

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


async def download_image(url: str) -> bytes:
    """Download image from URL."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.read()
            else:
                raise Exception(f"Failed to download image: HTTP {response.status}")


def _upscale_image_sync(image_data: bytes, factor: int) -> io.BytesIO:
    """Synchronous image upscaling (run in executor)."""
    try:
        # Open image from bytes
        image = Image.open(io.BytesIO(image_data))
    except Exception as e:
        raise ValueError(f"Invalid or corrupted image data: {str(e)}")
    
    # Calculate new dimensions
    new_width = image.width * factor
    new_height = image.height * factor
    
    # Upscale using high-quality Lanczos resampling
    upscaled = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Save to BytesIO
    output = io.BytesIO()
    image_format = image.format or 'PNG'
    upscaled.save(output, format=image_format)
    output.seek(0)
    
    return output


async def upscale_image(image_data: bytes, factor: int = UPSCALE_FACTOR) -> io.BytesIO:
    """Upscale image using Lanczos resampling in an executor."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _upscale_image_sync, image_data, factor)


@bot.event
async def on_ready():
    """Event handler for when bot is ready."""
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is ready to upscale images with factor: {UPSCALE_FACTOR}x')


@bot.command(name='upscale', help='Upscale an attached image')
async def upscale(ctx):
    """Command to upscale an image attached to the message."""
    # Check if message has attachments
    if not ctx.message.attachments:
        await ctx.send("❌ Please attach an image to upscale!")
        return
    
    attachment = ctx.message.attachments[0]
    
    # Check file size
    if attachment.size > MAX_FILE_SIZE_BYTES:
        await ctx.send(f"❌ File too large! Maximum size: {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB")
        return
    
    # Check file format
    dot_index = attachment.filename.rfind('.')
    if dot_index == -1:
        await ctx.send("❌ File has no extension! Supported formats: " + ", ".join(SUPPORTED_FORMATS))
        return
    file_ext = attachment.filename.lower()[dot_index:]
    if file_ext not in SUPPORTED_FORMATS:
        await ctx.send(f"❌ Unsupported format! Supported formats: {', '.join(SUPPORTED_FORMATS)}")
        return
    
    # Send processing message
    processing_msg = await ctx.send("🔄 Processing your image...")
    
    try:
        # Download image
        image_data = await download_image(attachment.url)
        
        # Upscale image
        upscaled_image = await upscale_image(image_data, UPSCALE_FACTOR)
        
        # Create Discord file
        filename = f"upscaled_{attachment.filename}"
        discord_file = discord.File(upscaled_image, filename=filename)
        
        # Send upscaled image
        await ctx.send(
            f"✅ Image upscaled by {UPSCALE_FACTOR}x!",
            file=discord_file
        )
        
        # Delete processing message
        await processing_msg.delete()
        
    except Exception as e:
        await processing_msg.edit(content=f"❌ Error processing image: {str(e)}")
        print(f"Error: {e}")


@bot.command(name='info', help='Get bot information')
async def info(ctx):
    """Command to display bot information."""
    embed = discord.Embed(
        title="Discord Image Upscaler Bot",
        description="A bot to upscale your images!",
        color=discord.Color.blue()
    )
    embed.add_field(name="Upscale Factor", value=f"{UPSCALE_FACTOR}x", inline=True)
    embed.add_field(
        name="Max File Size",
        value=f"{MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB",
        inline=True
    )
    embed.add_field(
        name="Supported Formats",
        value=", ".join(SUPPORTED_FORMATS),
        inline=False
    )
    embed.add_field(
        name="Usage",
        value="Attach an image and use `!upscale` command",
        inline=False
    )
    
    await ctx.send(embed=embed)


def main():
    """Main entry point for the bot."""
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN not set in environment variables!")
        print("Please create a .env file based on .env.example")
        return
    
    bot.run(DISCORD_TOKEN)


if __name__ == '__main__':
    main()
