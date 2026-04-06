import os
import re
import time
import json
import base64
import requests
import tls_client
from concurrent.futures import ThreadPoolExecutor


def save_token(token):
    os.makedirs("data", exist_ok=True)
    with open("data/token.txt", "w") as f:
        f.write(token)

class ServerCloner:
    def __init__(self, token, source_guild_id, target_guild_id=None):
        self.token = token
        self.source_guild_id = source_guild_id
        self.target_guild_id = target_guild_id
        self.category_map = {}
        os.makedirs("backups", exist_ok=True)
        self.session = self._create_session()

    def _create_session(self):
        session = tls_client.Session(
            client_identifier="chrome_120",
            random_tls_extension_order=True
        )
        session.headers = self._get_headers()
        return session

    def _get_headers(self):
        props = {
            "os": "Windows",
            "browser": "Chrome",
            "device": "",
            "system_locale": "en-US",
            "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "browser_version": "120.0.0.0",
            "os_version": "10",
            "referrer": "https://discord.com/",
            "referring_domain": "discord.com",
            "referrer_current": "",
            "referring_domain_current": "",
            "release_channel": "stable",
            "client_build_number": 267860,
            "client_event_source": None,
            "design_id": 0,
            "native_build_number": None,
            "client_performance_cpu_cores": 8,
            "client_performance_memory": 16384,
            "accessibility_features": 0,
            "has_ever_used_accessibility_features": False,
            "has_client_mods": False
        }
        encoded = base64.b64encode(json.dumps(props, separators=(",", ":")).encode()).decode()
        return {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "authorization": self.token,
            "content-type": "application/json",
            "origin": "https://discord.com",
            "referer": f"https://discord.com/channels/{self.source_guild_id}/@home",
            "sec-ch-ua": '"Google Chrome";v="120", "Chromium";v="120", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "x-debug-options": "bugReporterEnabled",
            "x-discord-locale": "en-US",
            "x-discord-timezone": "America/New_York",
            "x-super-properties": encoded
        }

    def _get(self, path):
        try:
            r = self.session.get(f"https://discord.com/api/v9{path}", timeout=30)
            if r.status_code == 429:
                wait = r.json().get("retry_after", 1)
                time.sleep(wait)
                return self._get(path)
            return r
        except Exception:
            return None

    def _post(self, path, payload):
        try:
            r = self.session.post(f"https://discord.com/api/v9{path}", json=payload, timeout=30)
            if r.status_code == 429:
                wait = r.json().get("retry_after", 1)
                time.sleep(wait)
                return self._post(path, payload)
            return r
        except Exception:
            return None

    def _patch(self, path, payload):
        try:
            r = self.session.patch(f"https://discord.com/api/v9{path}", json=payload, timeout=30)
            if r.status_code == 429:
                wait = r.json().get("retry_after", 1)
                time.sleep(wait)
                return self._patch(path, payload)
            return r
        except Exception:
            return None

    def clone_server_details(self):
        if not self.target_guild_id:
            return {"success": False, "message": "Target Guild ID required"}
        
        r = self._get(f"/guilds/{self.source_guild_id}")
        if not r or r.status_code != 200:
            return {"success": False, "message": "Failed to fetch source guild"}
        
        guild = r.json()
        payload = {"name": guild.get("name", "Cloned Server")}
        
        if guild.get("icon"):
            try:
                data = requests.get(
                    f"https://cdn.discordapp.com/icons/{self.source_guild_id}/{guild['icon']}.png"
                ).content
                payload["icon"] = f"data:image/png;base64,{base64.b64encode(data).decode()}"
            except Exception:
                pass
        
        r = self._patch(f"/guilds/{self.target_guild_id}", payload)
        if r and r.status_code == 200:
            return {"success": True, "message": f"Server details cloned: {guild.get('name')}"}
        return {"success": False, "message": "Failed to update server details"}

    def clone_roles(self):
        if not self.target_guild_id:
            return {"success": False, "message": "Target Guild ID required"}
        
        r = self._get(f"/guilds/{self.source_guild_id}/roles")
        if not r or r.status_code != 200:
            return {"success": False, "message": "Failed to fetch source roles"}
        
        roles = [ro for ro in r.json() if ro["name"] != "@everyone"]
        created = []
        
        for role in roles:
            r = self._post(f"/guilds/{self.target_guild_id}/roles", {
                "name": role["name"],
                "permissions": role["permissions"],
                "color": role["color"],
                "hoist": role["hoist"],
                "mentionable": role["mentionable"]
            })
            if r and r.status_code in [200, 201]:
                created.append(r.json())
            time.sleep(0.25)
        
        if created:
            self._patch(f"/guilds/{self.target_guild_id}/roles",
                       [{"id": ro["id"], "position": ro["position"]} for ro in created])
        
        return {"success": True, "message": f"Cloned {len(created)} roles"}

    def clone_emojis(self):
        if not self.target_guild_id:
            return {"success": False, "message": "Target Guild ID required"}
        
        r = self._get(f"/guilds/{self.source_guild_id}/emojis")
        if not r or r.status_code != 200:
            return {"success": False, "message": "Failed to fetch source emojis"}
        
        cloned = 0
        for emoji in r.json():
            ext = "gif" if emoji["animated"] else "png"
            try:
                data = requests.get(f"https://cdn.discordapp.com/emojis/{emoji['id']}.{ext}").content
                b64 = f"data:image/{ext};base64,{base64.b64encode(data).decode()}"
                r2 = self._post(f"/guilds/{self.target_guild_id}/emojis", 
                               {"name": emoji["name"], "image": b64})
                if r2 and r2.status_code in [200, 201]:
                    cloned += 1
                elif r2 and r2.status_code == 400 and "maximum number" in r2.text.lower():
                    break
            except Exception:
                continue
            time.sleep(0.25)
        
        return {"success": True, "message": f"Cloned {cloned} emojis"}

    def clone_categories(self):
        if not self.target_guild_id:
            return {"success": False, "message": "Target Guild ID required"}
        
        r = self._get(f"/guilds/{self.source_guild_id}/channels")
        if not r or r.status_code != 200:
            return {"success": False, "message": "Failed to fetch channels"}
        
        categories = [c for c in r.json() if c["type"] == 4]
        cloned = 0
        
        for cat in categories:
            r = self._post(f"/guilds/{self.target_guild_id}/channels", {
                "name": cat["name"], "type": 4, "position": cat["position"]
            })
            if r and r.status_code == 201:
                self.category_map[cat["id"]] = r.json()["id"]
                cloned += 1
            time.sleep(0.10)
        
        return {"success": True, "message": f"Cloned {cloned} categories"}

    def clone_channels(self):
        if not self.target_guild_id:
            return {"success": False, "message": "Target Guild ID required"}
        
        r = self._get(f"/guilds/{self.source_guild_id}/channels")
        if not r or r.status_code != 200:
            return {"success": False, "message": "Failed to fetch channels"}
        
        channels = r.json()
        categories = [c for c in channels if c["type"] == 4]
        others = [c for c in channels if c["type"] != 4]
        
        for cat in categories:
            r2 = self._post(f"/guilds/{self.target_guild_id}/channels", {
                "name": cat["name"], "type": 4, "position": cat["position"]
            })
            if r2 and r2.status_code == 201:
                self.category_map[cat["id"]] = r2.json()["id"]
            time.sleep(0.10)
        
        cloned = 0
        for ch in others:
            payload = {
                "name": ch["name"],
                "type": ch["type"],
                "topic": ch.get("topic"),
                "nsfw": ch.get("nsfw", False),
                "bitrate": ch.get("bitrate"),
                "user_limit": ch.get("user_limit"),
                "rate_limit_per_user": ch.get("rate_limit_per_user", 0),
                "position": ch["position"]
            }
            if ch.get("parent_id") in self.category_map:
                payload["parent_id"] = self.category_map[ch["parent_id"]]
            
            r2 = self._post(f"/guilds/{self.target_guild_id}/channels", payload)
            if r2 and r2.status_code == 201:
                cloned += 1
            time.sleep(0.10)
        
        return {"success": True, "message": f"Cloned {cloned} channels"}

    def create_backup(self):
        backup = {}
        
        r = self._get(f"/guilds/{self.source_guild_id}")
        if not r or r.status_code != 200:
            return {"success": False, "message": "Failed to fetch guild"}
        
        guild = r.json()
        icon_b64 = None
        if guild.get("icon"):
            try:
                data = requests.get(
                    f"https://cdn.discordapp.com/icons/{self.source_guild_id}/{guild['icon']}.png"
                ).content
                icon_b64 = f"data:image/png;base64,{base64.b64encode(data).decode()}"
            except:
                pass
        
        backup["server_details"] = {"name": guild.get("name", "Server"), "icon": icon_b64}
        
        r = self._get(f"/guilds/{self.source_guild_id}/roles")
        backup["roles"] = [
            {k: ro[k] for k in ["name", "permissions", "color", "hoist", "mentionable", "position"]}
            for ro in (r.json() if r and r.status_code == 200 else [])
            if ro["name"] != "@everyone"
        ]
        
        r = self._get(f"/guilds/{self.source_guild_id}/channels")
        channels = r.json() if r and r.status_code == 200 else []
        backup["categories"] = [{"id": c["id"], "name": c["name"], "position": c["position"]} 
                               for c in channels if c["type"] == 4]
        backup["channels"] = [{
            "name": c["name"], "type": c["type"], "topic": c.get("topic"),
            "nsfw": c.get("nsfw", False), "bitrate": c.get("bitrate"),
            "user_limit": c.get("user_limit"), "rate_limit_per_user": c.get("rate_limit_per_user", 0),
            "position": c["position"], "parent_id": c.get("parent_id")
        } for c in channels if c["type"] != 4]
        
        r = self._get(f"/guilds/{self.source_guild_id}/emojis")
        emojis = []
        for e in (r.json() if r and r.status_code == 200 else []):
            try:
                ext = "gif" if e["animated"] else "png"
                data = requests.get(f"https://cdn.discordapp.com/emojis/{e['id']}.{ext}").content
                emojis.append({"name": e["name"], "image": f"data:image/{ext};base64,{base64.b64encode(data).decode()}"})
            except:
                pass
        backup["emojis"] = emojis
        
        path = f"backups/{self.source_guild_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(backup, f, indent=4)
        
        return {"success": True, "message": "Backup saved", "filename": path}

    def restore_from_backup(self, filename):
        if not self.target_guild_id:
            return {"success": False, "message": "Target Guild ID required"}
        
        path = os.path.join("backups", filename)
        if not os.path.isfile(path):
            return {"success": False, "message": f"Backup file not found: {filename}"}
        
        with open(path, "r", encoding="utf-8") as f:
            backup = json.load(f)
        
        payload = {"name": backup["server_details"]["name"]}
        if backup["server_details"].get("icon"):
            payload["icon"] = backup["server_details"]["icon"]
        self._patch(f"/guilds/{self.target_guild_id}", payload)
        
        for role in sorted(backup["roles"], key=lambda x: x["position"], reverse=True):
            self._post(f"/guilds/{self.target_guild_id}/roles", role)
            time.sleep(0.5)
        
        self.category_map = {}
        for cat in backup["categories"]:
            r = self._post(f"/guilds/{self.target_guild_id}/channels", 
                          {"name": cat["name"], "type": 4, "position": cat["position"]})
            if r and r.status_code == 201:
                self.category_map[cat["id"]] = r.json()["id"]
            time.sleep(0.5)
        
        for ch in backup["channels"]:
            payload = ch.copy()
            if ch.get("parent_id") in self.category_map:
                payload["parent_id"] = self.category_map[ch["parent_id"]]
            self._post(f"/guilds/{self.target_guild_id}/channels", payload)
            time.sleep(0.5)
        
        for emoji in backup["emojis"]:
            self._post(f"/guilds/{self.target_guild_id}/emojis", emoji)
            time.sleep(0.5)
        
        return {"success": True, "message": "Backup restored successfully"}

    def full_clone(self):
        if not self.target_guild_id:
            return {"success": False, "message": "Target Guild ID required"}
        
        results = []
        
        for func in [self.clone_server_details, self.clone_categories, self.clone_channels, 
                     self.clone_roles, self.clone_emojis, self.clone_stickers]:
            r = func()
            results.append(r.get("message", str(r)))
        
        return {"success": True, "message": "Full clone completed", "details": results}

    def clone_stickers(self):
        if not self.target_guild_id:
            return {"success": False, "message": "Target Guild ID required"}
        
        r = self._get(f"/guilds/{self.source_guild_id}/stickers")
        if not r or r.status_code != 200:
            return {"success": False, "message": "Failed to fetch source stickers"}
        
        cloned = 0
        for sticker in r.json():
            name = sticker.get("name", "sticker")
            try:
                data = requests.get(f"https://cdn.discordapp.com/stickers/{sticker['id']}.png").content
                b64 = f"data:image/png;base64,{base64.b64encode(data).decode()}"
                r2 = self._post(f"/guilds/{self.target_guild_id}/stickers", {
                    "name": name,
                    "description": sticker.get("description", ""),
                    "tags": sticker.get("tags", ""),
                    "file": b64
                })
                if r2 and r2.status_code == 201:
                    cloned += 1
            except Exception:
                continue
            time.sleep(1.0)
        
        return {"success": True, "message": f"Cloned {cloned} stickers"}

    def clone_webhooks(self):
        if not self.target_guild_id:
            return {"success": False, "message": "Target Guild ID required"}
        
        src = self._get(f"/guilds/{self.source_guild_id}/channels")
        tgt = self._get(f"/guilds/{self.target_guild_id}/channels")
        if not src or src.status_code != 200 or not tgt or tgt.status_code != 200:
            return {"success": False, "message": "Failed to fetch channels"}
        
        name_map = {ch["name"]: ch["id"] for ch in tgt.json()}
        cloned = 0
        
        for ch in src.json():
            wh_r = self._get(f"/channels/{ch['id']}/webhooks")
            if not wh_r or wh_r.status_code != 200:
                continue
            for wh in wh_r.json():
                tgt_id = name_map.get(ch["name"])
                if tgt_id:
                    r = self._post(f"/channels/{tgt_id}/webhooks", 
                                  {"name": wh["name"], "avatar": wh.get("avatar")})
                    if r and r.status_code == 200:
                        cloned += 1
                    time.sleep(1.5)
        
        return {"success": True, "message": f"Cloned {cloned} webhooks"}

    def clone_nsfw_flags(self):
        if not self.target_guild_id:
            return {"success": False, "message": "Target Guild ID required"}
        
        src = self._get(f"/guilds/{self.source_guild_id}/channels")
        tgt = self._get(f"/guilds/{self.target_guild_id}/channels")
        if not src or src.status_code != 200 or not tgt or tgt.status_code != 200:
            return {"success": False, "message": "Failed to fetch channels"}
        
        name_map = {ch["name"]: ch["id"] for ch in tgt.json()}
        cloned = 0
        
        for ch in src.json():
            tgt_id = name_map.get(ch["name"])
            if tgt_id and ch.get("nsfw") is not None:
                r = self._patch(f"/channels/{tgt_id}", {"nsfw": ch["nsfw"]})
                if r and r.status_code == 200:
                    cloned += 1
                time.sleep(1.5)
        
        return {"success": True, "message": f"Set NSFW flags for {cloned} channels"}


# ============ FUNCTIONS FOR run_tool ============

def validate_token(token=None, **kwargs):
    user = validate_token(token)
    if user:
        tag = user.get("username") or user.get("global_name") or "Unknown"
        discrim = user.get("discriminator", "0")
        username = f"{tag}#{discrim}" if discrim != "0" else tag
        return {"success": True, "username": username}
    return {"success": False, "message": "Invalid token"}

def execute(token=None, source_id=None, target_id=None, options=None, backup_file=None, **kwargs):
    if not token:
        return {"success": False, "message": "Token required"}
    if not source_id:
        return {"success": False, "message": "Source Guild ID required"}
    
    user = validate_token(token)
    if not user:
        return {"success": False, "message": "Invalid token"}
    
    save_token(token)
    results = []
    
    for opt in (options or []):
        if opt == "server":
            cloner = ServerCloner(token, source_id, target_id)
            r = cloner.clone_server_details()
            results.append(r.get("message", str(r)))
        
        elif opt == "roles":
            cloner = ServerCloner(token, source_id, target_id)
            r = cloner.clone_roles()
            results.append(r.get("message", str(r)))
        
        elif opt == "emojis":
            cloner = ServerCloner(token, source_id, target_id)
            r = cloner.clone_emojis()
            results.append(r.get("message", str(r)))
        
        elif opt == "categories":
            cloner = ServerCloner(token, source_id, target_id)
            r = cloner.clone_categories()
            results.append(r.get("message", str(r)))
        
        elif opt == "channels":
            cloner = ServerCloner(token, source_id, target_id)
            r = cloner.clone_channels()
            results.append(r.get("message", str(r)))
        
        elif opt == "backup":
            cloner = ServerCloner(token, source_id, None)
            r = cloner.create_backup()
            results.append(r.get("message", str(r)))
        
        elif opt == "nsfw":
            cloner = ServerCloner(token, source_id, target_id)
            r = cloner.clone_nsfw_flags()
            results.append(r.get("message", str(r)))
        
        elif opt == "stickers":
            cloner = ServerCloner(token, source_id, target_id)
            r = cloner.clone_stickers()
            results.append(r.get("message", str(r)))
        
        elif opt == "webhooks":
            cloner = ServerCloner(token, source_id, target_id)
            r = cloner.clone_webhooks()
            results.append(r.get("message", str(r)))
        
        elif opt == "full":
            cloner = ServerCloner(token, source_id, target_id)
            r = cloner.full_clone()
            if r.get("details"):
                results.extend(r["details"])
            else:
                results.append(r.get("message", "Full clone completed"))
        
        elif opt == "restore":
            if backup_file:
                cloner = ServerCloner(token, None, target_id)
                r = cloner.restore_from_backup(backup_file)
                results.append(r.get("message", str(r)))
            else:
                results.append("Restore: No backup file provided")
    
    return {"success": True, "message": "Operations completed", "details": results}

def backup(token=None, source_id=None, **kwargs):
    if not token:
        return {"success": False, "message": "Token required"}
    if not source_id:
        return {"success": False, "message": "Source Guild ID required"}
    
    user = validate_token(token)
    if not user:
        return {"success": False, "message": "Invalid token"}
    
    save_token(token)
    cloner = ServerCloner(token, source_id, None)
    return cloner.create_backup()