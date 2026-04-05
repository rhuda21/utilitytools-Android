import requests
def delete(url):
    try:
        if not url.startswith("https://discord.com/api/webhooks/"):
            return {"success": False, "message": "Invalid Webhook URL format."}
        response = requests.delete(url, timeout=10)
        if response.status_code == 204:
            return {"success": True, "message": "Webhook successfully deleted!"}
        elif response.status_code == 404:
            return {"success": False, "message": "Webhook not found (already deleted)."}
        elif response.status_code == 429:
            return {"success": False, "message": "Rate limited! Try again in a few seconds."}
        else:
            return {"success": False, "message": f"Discord returned error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "message": f"Python Error: {str(e)}"}
