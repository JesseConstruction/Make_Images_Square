#!/usr/bin/env python3

import os
import shutil
import time
import hashlib
from typing import Tuple
from PIL import Image
import tkinter as tk
from tkinter import filedialog
import sys
from tkinter.scrolledtext import ScrolledText
from datetime import datetime

# ---------- Long-path + safe-name helpers ----------

# Conservative margins for Windows
_MAX_PATH = 240        # keep some headroom under 260
_MAX_COMPONENT = 200   # keep some headroom under 255

def as_winlong(path: str) -> str:
    """Return Windows extended-length absolute path (\\?\C:\...) when on Windows."""
    if os.name != "nt":
        return path
    ap = os.path.abspath(path)
    if ap.startswith("\\\\?\\"):
        return ap
    # UNC paths need \\?\UNC\server\share\...
    if ap.startswith("\\\\"):
        return "\\\\?\\UNC" + ap[1:]
    return "\\\\?\\" + ap

def safe_dest_path(base_dir: str, filename: str) -> Tuple[str, str, bool]:
    """
    Build a destination path for `filename` inside `base_dir`.
    If the filename or full path would be too long, shorten the filename by appending
    an 8-char hash. Returns (dest_path, new_filename, was_shortened).
    """
    base_dir = os.path.abspath(base_dir)
    name, ext = os.path.splitext(filename)
    candidate = os.path.join(base_dir, filename)

    if len(os.path.basename(filename)) <= _MAX_COMPONENT and len(candidate) <= _MAX_PATH:
        return candidate, filename, False

    h = hashlib.sha1(filename.encode("utf-8")).hexdigest()[:8]
    keep = max(1, _MAX_COMPONENT - len(ext) - 9)  # room for "-{hash}"
    new_name = f"{name[:keep]}-{h}{ext}"
    dest = os.path.join(base_dir, new_name)

    # final guard for entire path length
    if len(dest) > _MAX_PATH:
        extra = len(dest) - _MAX_PATH
        new_keep = max(1, keep - extra)
        new_name = f"{name[:new_keep]}-{h}{ext}"
        dest = os.path.join(base_dir, new_name)

    return dest, new_name, True

# ---------------------------------------------------

def get_desktop_path():
    """Get path to user's desktop"""
    return os.path.join(os.path.expanduser("~"), "Desktop")

def is_image_square(image_path):
    """Check if image is square with error handling"""
    try:
        with Image.open(as_winlong(image_path)) as img:
            return img.size[0] == img.size[1]
    except Exception as e:
        print(f"⚠️ Error checking {os.path.basename(image_path)}: {str(e)}")
        return False

def process_images_locally(original_dir):
    """Main processing workflow with guaranteed square image handling"""

    # Setup paths
    desktop = get_desktop_path()
    temp_root = os.path.join(desktop, f"img_processing_{int(time.time())}")
    temp_input = os.path.join(temp_root, "to_process")
    temp_output = os.path.join(temp_root, "processed")
    final_output = os.path.join(original_dir, "squared_results")

    os.makedirs(temp_input, exist_ok=True)
    os.makedirs(temp_output, exist_ok=True)
    os.makedirs(final_output, exist_ok=True)

    # 1. Copy ALL images to temp input for processing
    all_images = []
    for filename in os.listdir(original_dir):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.jfif')):
            try:
                shutil.copy2(
                    as_winlong(os.path.join(original_dir, filename)),
                    as_winlong(os.path.join(temp_input, filename))
                )
                all_images.append(filename)
            except Exception as e:
                print(f"❌ Failed to copy {filename}: {str(e)}")

    if not all_images:
        shutil.rmtree(temp_root, ignore_errors=True)
        return False, "No valid images found"

    # 2. Process non-square images (preserve original filenames and extensions)
    processed_count = 0
    square_copied = 0
    renamed_map = []   # (original_filename, new_filename)

    for filename in all_images:
        input_path = os.path.join(temp_input, filename)

        # Skip if already in final output (from previous runs)
        existing_path, _, _ = safe_dest_path(final_output, filename)
        if os.path.exists(existing_path):
            continue

        try:
            if is_image_square(input_path):
                # Copy square images directly to final output with the same (or safely shortened) name
                dest_path, new_name, shortened = safe_dest_path(final_output, filename)
                shutil.copy2(as_winlong(input_path), as_winlong(dest_path))
                if shortened:
                    renamed_map.append((filename, new_name))
                    print(f"✂ Renamed long filename → {new_name}")
                square_copied += 1
                print(f"♢ Square image copied: {new_name if shortened else filename}")
            else:
                # Process non-square images
                with Image.open(as_winlong(input_path)) as img:
                    width, height = img.size
                    max_dim = max(width, height)
                    new_img = Image.new("RGB", (max_dim, max_dim), (255, 255, 255))
                    new_img.paste(img, ((max_dim - width) // 2, (max_dim - height) // 2))

                    # Save to short temp first, then move to final safe path
                    temp_save = os.path.join(temp_output, filename)
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in [".jpg", ".jpeg"]:
                        new_img.save(as_winlong(temp_save), "JPEG", quality=95)
                    else:
                        new_img.save(as_winlong(temp_save))

                dest_path, new_name, shortened = safe_dest_path(final_output, filename)
                shutil.move(as_winlong(temp_save), as_winlong(dest_path))
                if shortened:
                    renamed_map.append((filename, new_name))
                    print(f"✂ Renamed long filename → {new_name}")
                processed_count += 1
                print(f"□ Processed: {new_name if shortened else filename}")
        except Exception as e:
            print(f"❌ Failed {filename}: {str(e)}")

    # 3. Final sweep to catch any missed square images
    for filename in os.listdir(original_dir):
        src = os.path.join(original_dir, filename)
        dest_path, new_name, shortened = safe_dest_path(final_output, filename)

        if (filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.jfif'))
                and not os.path.exists(dest_path)):
            try:
                if is_image_square(src):
                    shutil.copy2(as_winlong(src), as_winlong(dest_path))
                    if shortened:
                        renamed_map.append((filename, new_name))
                        print(f"✂ Renamed long filename → {new_name}")
                    square_copied += 1
                    print(f"♢ Final sweep copied: {new_name if shortened else filename}")
            except Exception as e:
                print(f"❌ Final sweep failed on {filename}: {str(e)}")

    # 4. Move any remaining processed images from temp_output to final_output
    moved_count = 0
    for filename in os.listdir(temp_output):
        try:
            src_tmp = os.path.join(temp_output, filename)
            dest_path, new_name, shortened = safe_dest_path(final_output, filename)
            shutil.move(as_winlong(src_tmp), as_winlong(dest_path))
            moved_count += 1
            if shortened:
                renamed_map.append((filename, new_name))
                print(f"✂ Renamed long filename → {new_name}")
        except Exception as e:
            print(f"❌ Failed to move {filename}: {str(e)}")

    # 5. Verify all square images made it
    verified_square = 0
    for filename in os.listdir(original_dir):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.jfif')):
            src = os.path.join(original_dir, filename)
            dest_path, new_name, shortened = safe_dest_path(final_output, filename)

            if is_image_square(src) and not os.path.exists(dest_path):
                try:
                    shutil.copy2(as_winlong(src), as_winlong(dest_path))
                    verified_square += 1
                    square_copied += 1
                    if shortened:
                        renamed_map.append((filename, new_name))
                        print(f"✂ Renamed long filename → {new_name}")
                    print(f"♢ Verification copied: {new_name if shortened else filename}")
                except Exception as e:
                    print(f"❌ Verification failed on {filename}: {str(e)}")

    # Write a rename mapping if any names were shortened
    if renamed_map:
        map_path = os.path.join(final_output, "filename_mapping.csv")
        try:
            with open(as_winlong(map_path), "w", encoding="utf-8") as fh:
                fh.write("original_filename,new_filename\n")
                for old, new in renamed_map:
                    fh.write(f"{old},{new}\n")
            print(f"↪ Wrote rename map: {map_path}")
        except Exception as e:
            print(f"⚠️ Failed to write rename map: {str(e)}")

    # Cleanup
    shutil.rmtree(temp_root, ignore_errors=True)

    return True, (
        "Final Results:\n"
        f"- Processed {processed_count} non-square images\n"
        f"- Copied {square_copied} square images\n"
        f"- Moved {moved_count} processed images\n"
        f"- Total in output: {len(os.listdir(final_output))} files\n"
        f"- Output folder: {final_output}"
    )

class TkConsoleTee:
    """Mirror stdout/stderr into a Tk ScrolledText and keep a memory buffer."""
    def __init__(self, text_widget, show_timestamps=False):
        self.text_widget = text_widget
        self.show_timestamps = show_timestamps
        self._orig_stdout = sys.__stdout__
        self._orig_stderr = sys.__stderr__
        self._buf = []  # in-memory log buffer

    def write(self, s):
        if not s:
            return
        line = s
        if self.show_timestamps and s.strip():
            ts = datetime.now().strftime("%H:%M:%S")
            line = f"[{ts}] {s}"
        # live window
        self.text_widget.insert("end", line)
        self.text_widget.see("end")
        self.text_widget.update_idletasks()
        # buffer
        self._buf.append(line)
        # optional: mirror back to real stdout (IDE/terminal)
        try:
            self._orig_stdout.write(s)
            self._orig_stdout.flush()
        except Exception:
            pass

    def flush(self):
        pass

    def get_value(self):
        return "".join(self._buf)

def main():
    root = tk.Tk()
    root.withdraw()

    # Live log window
    log_win = tk.Toplevel(root)
    log_win.title("Image Processing Log")
    log_win.geometry("800x400")

    tk.Label(log_win, text="Live Log", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=8, pady=(8, 0))
    log_text = ScrolledText(log_win, wrap="word", height=20)
    log_text.pack(fill="both", expand=True, padx=8, pady=8)

    # Redirect prints ONLY to the window (buffered in memory)
    tee = TkConsoleTee(log_text, show_timestamps=False)
    sys.stdout = tee
    sys.stderr = tee

    def on_close():
        log_win.destroy()
        root.destroy()

    log_win.protocol("WM_DELETE_WINDOW", on_close)

    logfile_path = None
    source_dir = None  # predeclare so it's available if an exception happens early

    try:
        print("Select the folder containing images…")
        source_dir = filedialog.askdirectory(title="Select folder with images")
        if not source_dir:
            print("No folder selected. Exiting.")
            on_close()
            return

        result, message = process_images_locally(source_dir)
        print("\n" + message)

        # Decide whether to persist a .log file
        text_dump = tee.get_value()
        printed_errors = ("❌" in text_dump) or ("⚠️" in text_dump) or ("Error" in text_dump)
        if (not result) or printed_errors:
            final_output = os.path.join(source_dir, "squared_results")
            os.makedirs(final_output, exist_ok=True)
            logfile_path = os.path.join(final_output, f"image_square_log_{int(time.time())}.log")
            with open(as_winlong(logfile_path), "w", encoding="utf-8") as fh:
                fh.write(text_dump)
            print(f"\nA log was saved to: {logfile_path}")

        print("\nProcessing Complete.")
        if logfile_path:
            print(f"\nA log was saved to:\n{logfile_path}")

    except Exception as e:
        print(f"Error: {str(e)}")
        # Safe error logging even if source_dir was never set
        text_dump = tee.get_value()
        base = source_dir if source_dir else get_desktop_path()
        final_output = os.path.join(base, "squared_results")
        os.makedirs(final_output, exist_ok=True)
        logfile_path = os.path.join(final_output, f"image_square_log_{int(time.time())}.log")
        with open(as_winlong(logfile_path), "w", encoding="utf-8") as fh:
            fh.write(text_dump)
        print(f"\nA log was saved to: {logfile_path}")

    finally:
        # Keep the window open so users can review output; they'll close it when done.
        pass

    # Bring the log window to front
    log_win.lift()
    log_win.attributes("-topmost", True)
    log_win.after(200, lambda: log_win.attributes("-topmost", False))
    root.deiconify()
    root.mainloop()

if __name__ == "__main__":
    main()
