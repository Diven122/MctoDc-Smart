import os

import discord
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM_PROMPT = "You are a helpful, friendly assistant in a Discord server. Keep answers concise."

# Discord needs the "message content" intent to read messages
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

gemini = genai.Client(api_key=GEMINI_API_KEY)

# One chat session per channel, so the bot remembers the conversation
chats = {}


def get_chat(channel_id):
    if channel_id not in chats:
        chats[channel_id] = gemini.aio.chats.create(
            model=MODEL,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=800,
            ),
        )
    return chats[channel_id]


def split_message(text, limit=2000):
    """Discord messages max out at 2000 characters."""
    return [text[i : i + limit] for i in range(0, len(text), limit)]


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (model: {MODEL})")


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    is_dm = message.guild is None
    is_mentioned = bot.user in message.mentions
    if not (is_dm or is_mentioned):
        return

    # Remove the @mention from the text
    prompt = message.content
    for mention in (f"<@{bot.user.id}>", f"<@!{bot.user.id}>"):
        prompt = prompt.replace(mention, "")
    prompt = prompt.strip()

    if not prompt:
        await message.reply("Say something and I'll reply!")
        return

    # Reset the conversation memory for this channel
    if prompt.lower() == "!reset":
        chats.pop(message.channel.id, None)
        await message.reply("Conversation reset.")
        return

    async with message.channel.typing():
        try:
            chat = get_chat(message.channel.id)
            response = await chat.send_message(prompt)
            reply = response.text or "I couldn't generate a response to that."
        except Exception as e:
            print(f"Gemini error: {e}")
            reply = "Sorry, something went wrong talking to Gemini."

    for chunk in split_message(reply):
        await message.reply(chunk)


if __name__ == "__main__":
    if not DISCORD_TOKEN or not GEMINI_API_KEY:
        raise SystemExit("Set DISCORD_TOKEN and GEMINI_API_KEY in your .env file.")
    bot.run(DISCORD_TOKEN)