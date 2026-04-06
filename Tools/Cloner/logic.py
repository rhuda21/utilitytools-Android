import os
import re
import time
import json
import base64
import requests
import tls_client
from concurrent.futures import ThreadPoolExecutor

def validate_token(token):
    try:
        r = requests.get(
            "https://discord.com/api/v9/users/@me",
            headers={"Authorization": token},
            timeout=8
        )
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None

def load_token():
    os.makedirs("data", exist_ok=True)
    token_path = "data/token.txt"
    if os.path.isfile(token_path):
        with open(token_path, "r") as f:
            token = f.read().strip()
        if token and validate_token(token):
            return token
    return None

def save_token(token):
    os.makedirs("data", exist_ok=True)
    with open("data/token.txt", "w") as f:
        f.write(token)

def safe_request(fn, *args, retries=3, **kwargs):
    for _ in range(retries):
        try:
            r = fn(*args, **kwargs)
            if r.status_code == 429:
                wait = r.json().get("retry_after", 1) + 0.5
                time.sleep(wait)
                continue
            return r
        except Exception:
            time.sleep(1.5)
    return None

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
            "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "browser_version": "120.0.0.0",
            "os_version": "10",
            "release_channel": "stable",
            "client_build_number": 267860
        }
        encoded = base64.b64encode(json.dumps(props, separators=(",", ":")).encode()).decode()
        return {
            "accept": "*/*",
            "authorization": self.token,
            "content-type": "application/json",
            "origin": "https://discord.com",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "x-super-properties": encoded
        }

    def _get(self, path):
        return safe_request(self.session.get, f"https://discord.com/api/v9{path}")

    def _post(self, path, payload):
        return safe_request(self.session.post, f"https://discord.com/api/v9{path}", json=payload)

    def _patch(self, path, payload):
        return safe_request(self.session.patch, f"https://discord.com/api/v9{path}", json=payload)

    def fetch_source_channels(self):
        r = self._get(f"/guilds/{self.source_guild_id}/channels")
        if r and r.status_code == 200:
            return r.json()
        return []

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
        
        channels = self.fetch_source_channels()
        categories = [c for c in channels if c["type"] == 4]
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
        
        channels = self.fetch_source_channels()
        categories = [c for c in channels if c["type"] == 4]
        others = [c for c in channels if c["type"] != 4]
        
        for cat in categories:
            self._post(f"/guilds/{self.target_guild_id}/channels", {
                "name": cat["name"], "type": 4, "position": cat["position"]
            })
            time.sleep(0.10)
        
        cloned = 0
        for ch in others:
            r = self._post(f"/guilds/{self.target_guild_id}/channels", {
                "name": ch["name"],
                "type": ch["type"],
                "topic": ch.get("topic"),
                "nsfw": ch.get("nsfw", False),
                "bitrate": ch.get("bitrate"),
                "user_limit": ch.get("user_limit"),
                "rate_limit_per_user": ch.get("rate_limit_per_user", 0),
                "position": ch["position"]
            })
            if r and r.status_code == 201:
                cloned += 1
            time.sleep(0.10)
        
        return {"success": True, "message": f"Cloned {cloned} channels"}

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
                elif r2 and r2.json().get("code") == 30039:
                    break
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
        
        return {"success": True, "message": f"Backup saved", "filename": path}

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
        
        r = self.clone_server_details()
        results.append(r)
        
        r = self.clone_categories()
        results.append(r)
        
        r = self.clone_channels()
        results.append(r)
        
        r = self.clone_roles()
        results.append(r)
        
        r = self.clone_emojis()
        results.append(r)
        
        r = self.clone_stickers()
        results.append(r)
        
        r = self.clone_nsfw_flags()
        results.append(r)
        
        r = self.clone_webhooks()
        results.append(r)
        
        return {"success": True, "message": "Full clone completed", "details": results}