import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import threading
import subprocess

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FFmpeg Sequential Encoder")
        self.geometry("1000x600")
        self.resizable(False, False)

        self.file_queue = {}  # Dictionary to store {filename: full_path}
        self.encoding_thread = None
        self.stop_event = threading.Event()
        self.ffmpeg_process = None

        # Main layout frames
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        left_frame = ctk.CTkFrame(self)
        left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        left_frame.grid_rowconfigure(0, weight=1)
        left_frame.grid_rowconfigure(1, weight=1)

        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        # Left side: Queue and Options
        self.queue_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        self.queue_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.queue_frame.grid_columnconfigure(0, weight=1)
        self.queue_frame.grid_rowconfigure(1, weight=1)

        self.options_frame = ctk.CTkFrame(left_frame)
        self.options_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # -- File Queue Widgets --
        queue_label = ctk.CTkLabel(self.queue_frame, text="File Queue")
        queue_label.grid(row=0, column=0, columnspan=2, pady=(0, 5), sticky="w")

        self.file_listbox = tk.Listbox(self.queue_frame, selectmode=tk.EXTENDED)
        self.file_listbox.grid(row=1, column=0, columnspan=2, sticky="nsew")

        self.add_files_button = ctk.CTkButton(self.queue_frame, text="Add Files", command=self.add_files)
        self.add_files_button.grid(row=2, column=0, pady=5, padx=(0,5), sticky="ew")

        self.remove_selected_button = ctk.CTkButton(self.queue_frame, text="Remove Selected", command=self.remove_selected)
        self.remove_selected_button.grid(row=3, column=0, pady=5, padx=(0,5), sticky="ew")

        self.clear_queue_button = ctk.CTkButton(self.queue_frame, text="Clear Queue", command=self.clear_queue)
        self.clear_queue_button.grid(row=4, column=0, pady=5, padx=(0,5), sticky="ew")

        # -- Encoding Options Widgets --
        options_label = ctk.CTkLabel(self.options_frame, text="Encoding Options")
        options_label.pack(anchor="w", padx=10, pady=5)

        # Video Codec
        codec_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        codec_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(codec_frame, text="Video Codec:").pack(side="left")
        self.video_codec_var = ctk.StringVar(value="AV1 (NVENC)")
        codec_menu = ctk.CTkOptionMenu(codec_frame, variable=self.video_codec_var, values=["AV1 (NVENC)", "H.265 (NVENC)", "H.264 (NVENC)"])
        codec_menu.pack(side="right")

        # Video Bitrate
        bitrate_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        bitrate_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(bitrate_frame, text="Bitrate (kbps):").pack(side="left")
        self.bitrate_var = ctk.StringVar(value="2000")
        bitrate_entry = ctk.CTkEntry(bitrate_frame, textvariable=self.bitrate_var)
        bitrate_entry.pack(side="right")

        # FPS
        fps_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        fps_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(fps_frame, text="FPS:").pack(side="left")
        self.fps_var = ctk.StringVar(value="Keep Original")
        fps_menu = ctk.CTkOptionMenu(fps_frame, variable=self.fps_var, values=["Keep Original", "30"])
        fps_menu.pack(side="right")

        # Audio Options
        audio_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        audio_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(audio_frame, text="Audio:").pack(side="left")
        self.audio_var = ctk.StringVar(value="Copy Audio")
        audio_menu = ctk.CTkOptionMenu(audio_frame, variable=self.audio_var, values=["Copy Audio", "Re-encode to AAC (192kbps)"])
        audio_menu.pack(side="right")

        # Output Folder
        output_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        output_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(output_frame, text="Output Folder:").pack(side="left")
        browse_button = ctk.CTkButton(output_frame, text="Browse...", command=self.browse_output_folder)
        browse_button.pack(side="right")
        self.output_path_var = ctk.StringVar()
        output_entry = ctk.CTkEntry(output_frame, textvariable=self.output_path_var, state="readonly")
        output_entry.pack(side="left", fill="x", expand=True, padx=(5,5))


        # Right side: Log and Progress
        log_label = ctk.CTkLabel(right_frame, text="FFmpeg Log")
        log_label.grid(row=0, column=0, pady=(0, 5), sticky="w", padx=10)
        self.log_textbox = ctk.CTkTextbox(right_frame, state="disabled", activate_scrollbars=True)
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=10)

        # Bottom Controls and Status
        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")
        bottom_frame.grid_columnconfigure(2, weight=1)

        self.start_button = ctk.CTkButton(bottom_frame, text="Start Encoding", command=self.start_encoding)
        self.start_button.grid(row=0, column=0, padx=5, pady=5)

        self.stop_button = ctk.CTkButton(bottom_frame, text="Stop Encoding", state="disabled", command=self.stop_encoding)
        self.stop_button.grid(row=0, column=1, padx=5, pady=5)

        self.status_label = ctk.CTkLabel(bottom_frame, text="Idle")
        self.status_label.grid(row=0, column=2, padx=10, sticky="w")

        self.progress_bar = ctk.CTkProgressBar(bottom_frame)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=3, padx=10, sticky="ew")


    def add_files(self):
        files = filedialog.askopenfilenames(
            title="Select video files",
            filetypes=(("Video files", "*.mp4 *.mkv *.mov *.avi"), ("All files", "*.*"))
        )
        for file_path in files:
            filename = os.path.basename(file_path)
            if filename not in self.file_queue:
                self.file_queue[filename] = file_path
                self.file_listbox.insert(tk.END, filename)

    def remove_selected(self):
        selected_indices = self.file_listbox.curselection()
        for i in reversed(selected_indices):
            filename = self.file_listbox.get(i)
            del self.file_queue[filename]
            self.file_listbox.delete(i)

    def clear_queue(self):
        self.file_queue.clear()
        self.file_listbox.delete(0, tk.END)

    def browse_output_folder(self):
        folder_path = filedialog.askdirectory(title="Select Output Folder")
        if folder_path:
            self.output_path_var.set(folder_path)

    def start_encoding(self):
        if not self.file_queue:
            messagebox.showerror("Error", "The file queue is empty.")
            return
        if not self.output_path_var.get():
            messagebox.showerror("Error", "Please select an output folder.")
            return

        self._set_ui_state("encoding")
        self.stop_event.clear()
        self.encoding_thread = threading.Thread(target=self._run_encoding)
        self.encoding_thread.start()

    def stop_encoding(self):
        self.status_label.configure(text="Stopping...")
        self.stop_event.set()
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()

    def _run_encoding(self):
        queue_list = list(self.file_queue.items())
        total_files = len(queue_list)
        is_stopped = False

        for i, (filename, input_path) in enumerate(queue_list):
            if self.stop_event.is_set():
                is_stopped = True
                break

            self.after(0, self._update_status, f"Encoding file {i+1} of {total_files}: {filename}")
            self.after(0, self.progress_bar.start)

            output_path = self._get_output_path(filename)
            command = self._generate_ffmpeg_command(input_path, output_path)

            try:
                self.ffmpeg_process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )

                for line in iter(self.ffmpeg_process.stdout.readline, ''):
                    self.after(0, self._append_to_log, line)
                    if self.stop_event.is_set():
                        break

                self.ffmpeg_process.stdout.close()
                return_code = self.ffmpeg_process.wait()

                if self.stop_event.is_set(): # Check again after process finished
                    is_stopped = True
                    break

                if return_code != 0:
                    self.after(0, self._append_to_log, f"\nERROR: FFmpeg returned exit code {return_code}\n")
                    messagebox.showerror("Encoding Error", f"An error occurred while encoding {filename}. Check the log for details.")
                    is_stopped = True # Stop the queue on error
                    break

            except FileNotFoundError:
                messagebox.showerror("Error", "ffmpeg.exe not found. Make sure it's in the application's directory or in your system's PATH.")
                is_stopped = True
                break
            except Exception as e:
                messagebox.showerror("Error", f"An unexpected error occurred: {e}")
                is_stopped = True
                break

        final_status = "Queue stopped by user." if is_stopped else "Queue finished."
        self.after(0, self._finalize_encoding, final_status)

    def _get_output_path(self, original_filename):
        base, ext = os.path.splitext(original_filename)
        output_filename = f"{base}_encoded{ext}"
        return os.path.join(self.output_path_var.get(), output_filename)

    def _append_to_log(self, text):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert(tk.END, text)
        self.log_textbox.see(tk.END)
        self.log_textbox.configure(state="disabled")

    def _update_status(self, text):
        self.status_label.configure(text=text)

    def _set_ui_state(self, state):
        if state == "encoding":
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            for child in self.options_frame.winfo_children():
                self._disable_widgets(child)
            for child in self.queue_frame.winfo_children():
                if isinstance(child, ctk.CTkButton):
                    child.configure(state="disabled")
            self.log_textbox.configure(state="normal")
            self.log_textbox.delete("1.0", tk.END)
            self.log_textbox.configure(state="disabled")
        elif state == "idle":
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            for child in self.options_frame.winfo_children():
                self._enable_widgets(child)
            for child in self.queue_frame.winfo_children():
                 if isinstance(child, ctk.CTkButton):
                    child.configure(state="normal")

    def _disable_widgets(self, parent):
        for widget in parent.winfo_children():
            try:
                widget.configure(state="disabled")
            except:
                pass # Some widgets dont have state
            self._disable_widgets(widget)

    def _enable_widgets(self, parent):
        for widget in parent.winfo_children():
            try:
                if isinstance(widget, ctk.CTkEntry) and widget.cget("textvariable") == self.output_path_var:
                     widget.configure(state="readonly")
                else:
                    widget.configure(state="normal")
            except:
                pass # Some widgets dont have state
            self._enable_widgets(widget)

    def _finalize_encoding(self, final_status):
        self._set_ui_state("idle")
        self.status_label.configure(text=final_status)
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.ffmpeg_process = None
        self.stop_event.clear()

    def _generate_ffmpeg_command(self, input_path, output_path):
        command = ["ffmpeg", "-i", input_path]

        # Video Codec
        codec_map = {
            "AV1 (NVENC)": "av1_nvenc",
            "H.265 (NVENC)": "hevc_nvenc",
            "H.264 (NVENC)": "h264_nvenc",
        }
        command.extend(["-c:v", codec_map[self.video_codec_var.get()]])

        # Video Bitrate
        bitrate = self.bitrate_var.get()
        if bitrate.isdigit():
            command.extend(["-b:v", f"{bitrate}k"])

        # FPS
        if self.fps_var.get() == "30":
            command.extend(["-r", "30"])

        # Audio Options
        if self.audio_var.get() == "Copy Audio":
            command.extend(["-c:a", "copy"])
        else: # Re-encode to AAC
            command.extend(["-c:a", "aac", "-b:a", "192k"])

        command.append(output_path)
        return command


if __name__ == "__main__":
    app = App()
    app.mainloop()