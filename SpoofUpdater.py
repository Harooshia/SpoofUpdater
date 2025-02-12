import requests
import os
import sys
import time
import threading
import re
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import psutil
import ctypes
GITHUB_API_URL = "https://api.github.com/repos/Harooshia/SpoofReader/releases/latest"
EXECUTABLE_BASENAME = "SpoofReader"
COMMON_DIRECTORIES = [
    os.getcwd(),
    os.path.join(os.path.expanduser("~"), "Desktop"),
    os.path.join(os.path.expanduser("~"), "Downloads"),
    os.path.join(os.path.expanduser("~"), "Documents"),
    "C:\\Program Files\\SpoofReader",
    "C:\\Program Files (x86)\\SpoofReader"
]
def find_installed_version():
    pattern = re.compile(rf"{EXECUTABLE_BASENAME}(\d+\.\d+)\.exe")
    for directory in COMMON_DIRECTORIES:
        if os.path.exists(directory):
            for file in os.listdir(directory):
                match = pattern.match(file)
                if match:
                    version = match.group(1)
                    exe_path = os.path.join(directory, file)
                    return version, exe_path

    return None, None
def get_latest_release():
    try:
        response = requests.get(GITHUB_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        latest_version = data["tag_name"]
        assets = data.get("assets", [])
        exe_url = None
        for asset in assets:
            if asset["name"].endswith(".exe"):
                exe_url = asset["browser_download_url"]
                break
        return latest_version, exe_url
    except requests.exceptions.RequestException as e:
        print(f"Error fetching latest release: {e}")
        return None, None
def close_old_process(exe_name):
    """Check if the old process is running and terminate it."""
    for process in psutil.process_iter(["pid", "name"]):
        try:
            if exe_name.lower() in process.info["name"].lower():
                print(f"Closing running process: {exe_name}")
                process.terminate()
                time.sleep(2)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
class DownloadWindow:
    def __init__(self, root, url, filename, old_exe):
        self.root = root
        self.url = url
        self.filename = filename
        self.old_exe = old_exe
        self.root.title("Downloading Update")
        self.root.geometry("400x200")
        self.root.resizable(False, False)
        self.label = tk.Label(root, text="Downloading update...", font=("Arial", 12))
        self.label.pack(pady=10)
        self.progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=10)
        self.status_label = tk.Label(root, text="Initializing...", font=("Arial", 10))
        self.status_label.pack()
        self.speed_label = tk.Label(root, text="Speed: 0 KB/s | Time Left: --", font=("Arial", 10))
        self.speed_label.pack()
        self.start_download()
    def start_download(self):
        threading.Thread(target=self.download_file, daemon=True).start()
    def download_file(self):
        try:
            response = requests.get(self.url, stream=True, timeout=20)
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            downloaded_size = 0
            start_time = time.time()
            with open(self.filename, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        break
                    file.write(chunk)
                    downloaded_size += len(chunk)
                    percent = (downloaded_size / total_size) * 100
                    self.progress["value"] = percent
                    self.root.update_idletasks()
                    elapsed_time = time.time() - start_time
                    speed = (downloaded_size / 1024) / elapsed_time
                    time_left = (total_size - downloaded_size) / (speed * 1024) if speed > 0 else 0
                    self.status_label.config(text=f"{downloaded_size // 1024} KB / {total_size // 1024} KB")
                    self.speed_label.config(text=f"Speed: {speed:.2f} KB/s | Time Left: {time_left:.2f} s")
            self.label.config(text="Download Complete!")
            self.progress["value"] = 100
            time.sleep(1)
            if self.old_exe and os.path.exists(self.old_exe):
                try:
                    close_old_process(os.path.basename(self.old_exe))
                    os.remove(self.old_exe)
                    print(f"Deleted old version: {self.old_exe}")
                except Exception as e:
                    print(f"Failed to delete old executable: {e}")
            messagebox.showinfo("Download Complete", f"Downloaded to:\n{self.filename}")
            self.launch_new_version()
        except requests.exceptions.RequestException as e:
            self.label.config(text="Download Failed")
            self.status_label.config(text=str(e))
    def launch_new_version(self):
        """Launch the new version with admin rights automatically."""
        try:
            print(f"Launching new version as Admin: {self.filename}")
            ctypes.windll.shell32.ShellExecuteW(None, "runas", self.filename, None, None, 1)
            sys.exit(0)
        except Exception as e:
            print(f"Error launching new executable: {e}")
            messagebox.showerror("Error", f"Failed to launch: {self.filename}")
if __name__ == "__main__":
    current_version, exe_path = find_installed_version()
    if not current_version or not exe_path:
        print("No existing installation found. Proceeding with fresh install...")
    else:
        print(f"Detected installed version: {current_version} at {exe_path}")
    latest_version, exe_url = get_latest_release()
    if latest_version and exe_url:
        if current_version is None or latest_version != current_version:
            print(f"New version found: {latest_version}. Downloading update...")

            # Ensure the downloaded file goes to the user's desktop
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            new_exe = os.path.join(desktop_path, f"SpoofReader{latest_version}.exe")

            root = tk.Tk()
            DownloadWindow(root, exe_url, new_exe, exe_path)
            root.mainloop()
        else:
            print("You're already on the latest version.")
    else:
        print("Failed to check for updates.")
