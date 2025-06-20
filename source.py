#!/usr/bin/env python3

import os
import time  # <-- Add this import at the top
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox

def make_image_square(image_path, output_path):
    with Image.open(image_path) as im:
        width, height = im.size
        max_dim = max(width, height)
        new_im = Image.new("RGB", (max_dim, max_dim), (255, 255, 255))
        paste_x = (max_dim - width) // 2
        paste_y = (max_dim - height) // 2
        new_im.paste(im, (paste_x, paste_y))
        new_im.save(output_path, "JPEG")

# <-- Add this new function
def is_file_ready(file_path, max_attempts=5, delay=1):
    """Check if file exists and has content, with retries"""
    for attempt in range(max_attempts):
        try:
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                return True
            print(f"Waiting for {os.path.basename(file_path)}... (Attempt {attempt + 1}/{max_attempts})")
            time.sleep(delay)
        except Exception as e:
            print(f"Error checking file: {e}")
    return False

def main():
    # Hide the main Tkinter window
    root = tk.Tk()
    root.withdraw()

    # Ask the user to choose a folder
    current_dir = filedialog.askdirectory(title="Select folder with original images")
    if not current_dir:
        messagebox.showinfo("Cancelled", "No folder selected.")
        return

    folder_name = os.path.basename(current_dir)
    output_dir = os.path.join(current_dir, f"square_{folder_name}")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
    image_files = [f for f in os.listdir(current_dir) if f.lower().endswith(image_extensions)]

    if not image_files:
        messagebox.showinfo("No Images", "No image files found in the selected folder.")
        return

    processed = 0
    skipped = 0
    
    # <-- Modified processing loop starts here
    for filename in image_files:
        input_path = os.path.join(current_dir, filename)
        output_filename = os.path.splitext(filename)[0] + '.jpg'
        output_path = os.path.join(output_dir, output_filename)
        
        print(f"\nChecking {filename}...")
        
        if not is_file_ready(input_path):
            print(f"⚠️  Skipping {filename} - file not available")
            skipped += 1
            continue
            
        print(f"Processing {filename}...")
        try:
            make_image_square(input_path, output_path)
            processed += 1
        except Exception as e:
            print(f"❌ Failed to process {filename}: {e}")
            skipped += 1
    # <-- Modified processing loop ends here

    messagebox.showinfo(
        "Done", 
        f"Processing complete:\n\n"
        f"✅ Processed: {processed} files\n"
        f"⚠️  Skipped: {skipped} files\n\n"
        f"Output folder:\n{output_dir}"
    )

if __name__ == "__main__":
    main()
