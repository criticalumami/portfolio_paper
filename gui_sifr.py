import tkinter as tk
from tkinter import filedialog, messagebox
import os
import re
import subprocess

def srt_time_to_seconds(time_str):
    """Converts an SRT time string (HH:MM:SS,ms or HH:MM:SS.ms) to seconds."""
    parts = re.split('[:,.]', time_str)
    if len(parts) == 4:
        h, m, s, ms = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
        return h * 3600 + m * 60 + s + ms / 1000
    return 0

def search_srt_files(directory, search_term):
    """
    Searches for a term in SRT files within a directory and returns matching video info.
    """
    results = []
    if not os.path.isdir(directory):
        return results

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".srt"):
                srt_path = os.path.join(root, file)
                video_path = os.path.splitext(srt_path)[0] + ".mp4" # Assuming .mp4
                if not os.path.exists(video_path):
                    video_path = os.path.splitext(srt_path)[0] + ".mkv" # Also check for .mkv
                if not os.path.exists(video_path):
                    video_path = os.path.splitext(srt_path)[0] + ".mov" # Also check for .mov
                if not os.path.exists(video_path):
                    video_path = os.path.splitext(srt_path)[0] + ".avi" # Also check for .avi
                if not os.path.exists(video_path):
                    continue # Skip if no corresponding video found

                try:
                    with open(srt_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Regex to find timestamps and the following line of text
                        # It looks for a timestamp line, then captures the next line which is the subtitle text
                        # This is a simplified approach and might need refinement for complex SRT structures
                        pattern = re.compile(r'(\d{1,2}:\d{2}:\d{2}[,. ]\d{3})\s*-->\s*\d{1,2}:\d{2}:\d{2}[,. ]\d{3}\s*\n(.*?{}.*?)\n'.format(re.escape(search_term)), re.IGNORECASE | re.DOTALL)
                        
                        for match in pattern.finditer(content):
                            timestamp = match.group(1)
                            matched_line = match.group(2).strip()
                            results.append({
                                'video_path': video_path,
                                'timestamp': timestamp,
                                'matched_line': matched_line,
                                'srt_file': os.path.basename(srt_path)
                            })
                except Exception as e:
                    print(f"Error reading {srt_path}: {e}")
    return results

def play_video_at_time(video_path, start_time_seconds):
    """
    Plays a video at a specific time using VLC.
    """
    try:
        # Try to find VLC executable
        vlc_path = None
        if os.name == 'nt': # Windows
            vlc_path = os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), 'VideoLAN', 'VLC', 'vlc.exe')
            if not os.path.exists(vlc_path):
                vlc_path = os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), 'VideoLAN', 'VLC', 'vlc.exe')
        elif os.name == 'posix': # Linux/macOS
            vlc_path = 'vlc' # Assume it's in PATH
            
        if vlc_path and subprocess.run(['which', vlc_path], capture_output=True).returncode == 0: # Check if vlc is in PATH or found
            subprocess.Popen([vlc_path, '--start-time', str(int(start_time_seconds)), video_path])
        else:
            messagebox.showwarning("VLC Not Found", "VLC Media Player not found. Opening video without seeking to time. Please install VLC for full functionality.")
            subprocess.Popen(['xdg-open', video_path]) # Linux fallback
            subprocess.Popen(['open', video_path]) # macOS fallback
            subprocess.Popen([video_path], shell=True) # Windows fallback
    except Exception as e:
        messagebox.showerror("Error Playing Video", f"Could not play video: {e}")

class SifrGUI:
    def __init__(self, master):
        self.master = master
        master.title("Sifr Subtitle Search & Play")

        self.current_directory = tk.StringVar()
        self.current_directory.set(os.getcwd()) # Default to current working directory

        # Directory selection
        self.dir_frame = tk.Frame(master)
        self.dir_frame.pack(pady=10)

        tk.Label(self.dir_frame, text="Search Directory:").pack(side=tk.LEFT)
        self.dir_entry = tk.Entry(self.dir_frame, textvariable=self.current_directory, width=50)
        self.dir_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(self.dir_frame, text="Browse", command=self.browse_directory).pack(side=tk.LEFT)

        # Search input
        self.search_frame = tk.Frame(master)
        self.search_frame.pack(pady=5)

        tk.Label(self.search_frame, text="Search Term:").pack(side=tk.LEFT)
        self.search_term_entry = tk.Entry(self.search_frame, width=40)
        self.search_term_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(self.search_frame, text="Search", command=self.perform_search).pack(side=tk.LEFT)

        # Results display
        self.results_frame = tk.Frame(master)
        self.results_frame.pack(pady=10, fill=tk.BOTH, expand=True)

        self.results_listbox = tk.Listbox(self.results_frame, width=80, height=15)
        self.results_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.results_listbox.bind('<Double-Button-1>', self.play_selected_video)

        self.scrollbar = tk.Scrollbar(self.results_frame, orient="vertical", command=self.results_listbox.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill="y")
        self.results_listbox.config(yscrollcommand=self.scrollbar.set)

        # Play button
        self.play_button = tk.Button(master, text="Play Selected Video", command=self.play_selected_video)
        self.play_button.pack(pady=5)

        self.search_results = [] # To store the actual data of search results

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.current_directory.set(directory)

    def perform_search(self):
        search_term = self.search_term_entry.get().strip()
        directory = self.current_directory.get()

        if not search_term:
            messagebox.showwarning("Input Error", "Please enter a search term.")
            return
        if not directory or not os.path.isdir(directory):
            messagebox.showwarning("Input Error", "Please select a valid search directory.")
            return

        self.results_listbox.delete(0, tk.END) # Clear previous results
        self.search_results = search_srt_files(directory, search_term)

        if not self.search_results:
            self.results_listbox.insert(tk.END, "No results found.")
        else:
            for i, result in enumerate(self.search_results):
                display_text = f"[{result['srt_file']}] {result['timestamp']} - {result['matched_line']}"
                self.results_listbox.insert(tk.END, display_text)

    def play_selected_video(self, event=None):
        selected_indices = self.results_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Selection Error", "Please select a result from the list.")
            return

        selected_index = selected_indices[0]
        selected_result = self.search_results[selected_index]

        video_path = selected_result['video_path']
        timestamp_str = selected_result['timestamp']
        start_time_seconds = srt_time_to_seconds(timestamp_str)

        play_video_at_time(video_path, start_time_seconds)

if __name__ == "__main__":
    root = tk.Tk()
    app = SifrGUI(root)
    root.mainloop()
