import asyncio
from twikit import Client, TooManyRequests
from datetime import datetime
import json
import os
import discord
from discord.ext import commands
from configparser import ConfigParser

TRACKING_ACCOUNTS_FILE = "tracked_users.txt"
TWEETS_JSON_FILE = "tweets.json"

config = ConfigParser()
config.read("config.ini")
username = config["X"]["username"]
email = config["X"]["email"]
password = config["X"]["password"]
DISCORD_TOKEN = config["Discord"]["DISCORD_TOKEN"]
DISCORD_CHANNEL_ID = int(config["Discord"]["DISCORD_CHANNEL_ID"])

# * authenticate to X.com
client = Client(language="en-US")

if not os.path.exists("cookies.json"):
    client.login(auth_info_1=username, auth_info_2=email, password=password)
    client.save_cookies("cookies.json")
else:
    client.load_cookies("cookies.json")

# Discord client with commands
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
bot = commands.Bot(command_prefix="!", intents=intents)


# Load tracked accounts from file
def load_tracking_accounts():
    if os.path.exists(TRACKING_ACCOUNTS_FILE):
        with open(TRACKING_ACCOUNTS_FILE, "r") as file:
            return [line.strip() for line in file.readlines() if line.strip()]
    return []


# Load latest tweet IDs from JSON file
def load_latest_tweets():
    if os.path.exists(TWEETS_JSON_FILE):
        with open(TWEETS_JSON_FILE, "r") as file:
            return json.load(file)
    return {}


# Save latest tweet IDs to JSON file
def save_latest_tweets(latest_tweets):
    with open(TWEETS_JSON_FILE, "w") as file:
        json.dump(latest_tweets, file, indent=4)


# Fetch the latest tweet for a given username
async def get_latest_tweet(username):
    try:
        user = await client.get_user_by_screen_name(username)
        if user:
            tweets = await user.get_tweets(tweet_type="Tweets", count=1)
            if tweets:
                return tweets[0]
    except TooManyRequests as e:
        rate_limit_reset = datetime.fromtimestamp(e.rate_limit_reset)
        wait_time = max(0, (rate_limit_reset - datetime.now()).total_seconds())
        print(f"Rate limit reached. Waiting until {rate_limit_reset}")
        await asyncio.sleep(wait_time)
    except Exception as e:
        print(f"Error fetching tweet for @{username}: {e}")
    return None


# Background task to check for new tweets
import discord


# Background task to check for new tweets
async def track_tweets():
    await bot.wait_until_ready()
    channel = bot.get_channel(DISCORD_CHANNEL_ID)

    while not bot.is_closed():
        tracking_accounts = load_tracking_accounts()
        latest_tweets = load_latest_tweets()

        for username in tracking_accounts:
            tweet = await get_latest_tweet(username)
            if tweet:
                tweet_id = tweet.id  # Fetch the tweet ID
                if username not in latest_tweets or latest_tweets[username] != tweet_id:
                    # Update and save the latest tweet ID
                    latest_tweets[username] = tweet_id
                    save_latest_tweets(latest_tweets)

                    tweet_time = datetime.strptime(
                        str(tweet.created_at), "%a %b %d %H:%M:%S %z %Y"
                    )
                    formatted_time = tweet_time.strftime(
                        "%B %d, %Y at %I:%M %p"
                    )  # E.g., March 19, 2025 at 10:07 AM

                    # Create an embed message
                    embed = discord.Embed(
                        title=f"New Tweet from @{username} 💬",
                        description=tweet.text,
                        color=discord.Color.blue(),
                        timestamp=datetime.now(),
                    )
                    embed.set_author(
                        name=username,
                        url=f"https://twitter.com/{username}",
                        icon_url="https://abs.twimg.com/icons/apple-touch-icon-192x192.png",  # Twitter icon
                    )
                    embed.set_footer(
                        text="Twitter Tracker Bot",
                        icon_url="https://i.imgur.com/wSTFkRM.png",  # Discord icon
                    )
                    embed.add_field(
                        name="",
                        value=f"🔗 [View Tweet](https://twitter.com/{username}/status/{tweet_id})",
                        inline=False,
                    )
                    embed.add_field(
                        name="🗓️ Posted At", value=formatted_time, inline=True
                    )

                    # Check if the tweet contains media (images or videos)
                    if hasattr(tweet, "media") and tweet.media:
                        media_urls = []
                        for media in tweet.media:
                            if media.type == "photo":
                                embed.set_image(url=media.media_url)
                            elif media.type in ["video", "animated_gif"]:
                                # For video or animated GIF, add the media URL to the list
                                media_urls.append(
                                    media.video_info["variants"][0]["url"]
                                )

                        if media_urls:
                            embed.add_field(
                                name="📹 Media Attachments",
                                value="\n".join(media_urls),
                                inline=False,
                            )
                    await channel.send(embed=embed)

        await asyncio.sleep(60)  # Check every 60 seconds


# Command to add a Twitter user to the tracking list
@bot.command(name="track")
async def track(ctx, username: str):
    tracking_accounts = load_tracking_accounts()
    if username in tracking_accounts:
        await ctx.send(f"@{username} is already being tracked.")
    else:
        tracking_accounts.append(username)
        with open(TRACKING_ACCOUNTS_FILE, "w") as file:
            file.write("\n".join(tracking_accounts))
        await ctx.send(f"Now tracking @{username}.")


# Command to stop tracking a Twitter user
@bot.command(name="untrack")
async def untrack(ctx, username: str):
    tracking_accounts = load_tracking_accounts()
    if username in tracking_accounts:
        tracking_accounts.remove(username)
        with open(TRACKING_ACCOUNTS_FILE, "w") as file:
            file.write("\n".join(tracking_accounts))
        await ctx.send(f"Stopped tracking @{username}.")
    else:
        await ctx.send(f"@{username} is not being tracked.")


# Command to list tracked users
@bot.command(name="list")
async def list_tracked(ctx):
    tracking_accounts = load_tracking_accounts()
    if tracking_accounts:
        await ctx.send(
            "Currently tracking:\n"
            + "\n".join(f"- @{user}" for user in tracking_accounts)
        )
    else:
        await ctx.send("No users are being tracked.")


# Start the bot
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    bot.loop.create_task(track_tweets())


# Run the bot
bot.run(DISCORD_TOKEN)
