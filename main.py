import discord
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
import asyncio
import json

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_PATH")
PROCESSED_MESSAGES_FILE = os.getenv("PROCESSED_MESSAGES_PATH")
LAST_ROW_FILE = "last_row.txt"  
MESSAGE_DELAY_MINUTES = 1
VALIDATION_DELAY_MINUTES = 4
ROLE_NAME = "Test"

creds = Credentials.from_service_account_file(CREDENTIALS_FILE)
service = build('sheets', 'v4', credentials=creds)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  
client = discord.Client(intents=intents)



def read_processed_messages():
    """Reads processed messages from disk."""
    if os.path.exists(PROCESSED_MESSAGES_FILE):
        with open(PROCESSED_MESSAGES_FILE, "r") as file:
            return json.load(file)
    return []

processed_messages = read_processed_messages()

def write_processed_messages(processed_messages):
    """Writes processed messages to disk."""
    with open(PROCESSED_MESSAGES_FILE, "w") as file:
        json.dump(processed_messages, file)

def read_last_row():
    """Reads the last processed row number."""
    if os.path.exists(LAST_ROW_FILE):
        with open(LAST_ROW_FILE, "r") as file:
            return int(file.read().strip())
    return 0  

def write_last_row(row):
    """Writes the last processed row number."""
    with open(LAST_ROW_FILE, "w") as file:
        file.write(str(row))

last_row = read_last_row()

async def send_delayed_message(user_name, message_content):
    """Sends a delayed message to the user."""
    await asyncio.sleep(MESSAGE_DELAY_MINUTES*60)
    await send_message(user_name, message_content)

async def send_message(user_name, message_content):
    """Sends a direct message to a user."""
    try:
        member = discord.utils.get(guild.members, name=user_name)
        if member:
            await member.send(message_content)  
            print(f"Message sent to {user_name}.")
        else:
            print(f"User {user_name} not found.")
    except Exception as e:
        print(f"Error sending message to {user_name}: {e}")



async def check_new_responses():
    """Checks for new responses in the Google Sheets and sends them to Discord."""
    global last_row
    while True:
        try:
            sheet = service.spreadsheets()
            result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="A1:Z").execute()
            values = result.get('values', [])

            if not values:
                print("No responses found.")
            else:
                questions = values[0]

                if len(values) > last_row:
                    new_responses = values[last_row:]  
                    last_row = len(values)  
                    write_last_row(last_row)
                    for response in new_responses:
                        discord_username = None
                        embed = discord.Embed(
                            title="Réponse au formulaire",
                            color=discord.Color.blue(),
                        ) 
                        for question, answer in zip(questions, response):
                            embed.add_field(name=question, value=answer, inline=False)
                            if "tag discord" in question:
                                discord_username = answer
                                member = discord.utils.get(guild.members, name=discord_username)
                                if member:
                                    embed.set_thumbnail(url=member.avatar)
                            if "pseudo minecraft" in question:
                                embed.set_image(url=f"https://mc-heads.net/combo/{answer}")
                        embed.set_footer(text="Statut: En attente")
                        if member:
                            sent_message = await channel.send(embed=embed)
                            await sent_message.add_reaction("✅")
                            await sent_message.add_reaction("❌")
                            message_content = "Ta demande va être traitée."
                            asyncio.create_task(send_delayed_message(discord_username, message_content))

        except Exception as e:
            print(f"Error: {e}")

        await asyncio.sleep(10)

async def validate_reactions(message):
    """Validates reactions on a message by checking if at least 60% of members with a specific role reacted and if positive reactions (✅) outnumber negative ones (❌)."""
    try:
        # Get the role of members
        role = discord.utils.get(guild.roles, name=ROLE_NAME) 
        if not role:
            print(f"Role '{ROLE_NAME}' not found.")
            return False

        # Get members with this role
        members_with_role = [member for member in guild.members if role in member.roles]
        total_members_with_role = len(members_with_role)

        if total_members_with_role == 0:
            print(f"No members with the role '{ROLE_NAME}' have reacted.")
            return False

        # Get the reactions of the message
        reactions = message.reactions
        reacted_members = set()

        # Get the members who reacted to the message
        for reaction in reactions:
            async for user in reaction.users():
                if user in members_with_role:
                    reacted_members.add(user)

        # Calculate the percentage of members who reacted among those with the role
        reacted_percentage = (len(reacted_members) / total_members_with_role) * 100
        print(f"Percentage of members who reacted among those with the role: {reacted_percentage}% ")

        # Check if at least 60% of members with the role have reacted
        if reacted_percentage >= 60:
            # Count the positive (✅) and negative (❌) reactions
            positive_reactions_count = next((reaction.count for reaction in reactions if reaction.emoji == '✅'), 0) - 1
            negative_reactions_count = next((reaction.count for reaction in reactions if reaction.emoji == '❌'), 0) - 1
            embed = message.embeds[0]
            # Check if positive reactions are greater than negative reactions
            if positive_reactions_count > negative_reactions_count:
                embed.set_footer(text=f"Statut: Accepté - {positive_reactions_count}/{negative_reactions_count}")
                message_content = "Tu es accepté dans le serveur."
            else:
                embed.set_footer(text=f"Statut: Refusé - {positive_reactions_count}/{negative_reactions_count}")
                message_content = "Tu n'es pas accepté dans le serveur."

            # Send the validation message to the user
            for field in message.embeds[0].fields:
                if field.name == "tag discord":
                    user_name = field.value
                    break
            await message.edit(embed=embed)
            await send_message(user_name, message_content)
            return True
        else:
            return False

    except Exception as e:
        print(f"Error during reaction validation: {e}")
        return False

async def check_message_history():
    """Checks the message history for any unprocessed messages that have reactions."""
    async for message in channel.history(limit=100):  
        if message.author == client.user and message.id not in processed_messages:
            if any(str(reaction.emoji) in ["✅", "❌"] for reaction in message.reactions):
                result = await validate_reactions(message)
                if result:
                    processed_messages.append(message.id)
                    write_processed_messages(processed_messages)

@client.event
async def on_raw_reaction_add(payload):
    """Handles raw reactions added to messages."""
    if payload.message_id not in processed_messages:
        result = await validate_reactions(await channel.fetch_message(payload.message_id))
        if result:
            processed_messages.append(payload.message_id)
            write_processed_messages(processed_messages)

@client.event
async def on_ready():
    """Event handler when the bot is ready."""
    global channel, guild
    channel = client.get_channel(CHANNEL_ID)
    guild = client.get_channel(CHANNEL_ID).guild
    await client.change_presence(activity=discord.Game(name="toto"))
    await check_message_history()
    client.loop.create_task(check_new_responses())
    
client.run(DISCORD_TOKEN)
