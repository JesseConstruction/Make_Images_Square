#!/usr/bin/env python3

import os
import time
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

def make_image_square(image_path, output_path):
    with Image.open(image_path) as im:
        width, height = im.size
        max_dim = max(width, height)
        new_im = Image.new("RGB", (max_dim, max_dim), (255, 255, 255))
        paste_x = (max_dim - width) // 2
        paste_y = (max_dim - height) // 2
        new_im.paste(im, (paste_x, paste_y))
        new_im.save(output_path, "JPEG")

def wait_for_file(file_path, filename):
    """Three-stage waiting process with user interaction"""
    # Stage 1: Quick initial check (3 seconds)
    for _ in range(3):
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return True
        time.sleep(1)
    
    # Stage 2: Longer wait with progress (20 seconds)
    root = tk.Tk()
    root.withdraw()
    for i in range(20):
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return True
        
        # Show progress every 5 seconds
        if i % 5 == 0:
            remaining = 20 - i
            if not messagebox.askyesno(
                "File Loading",
                f"Waiting for '{filename}' to load...\n\n"
                f"{remaining} seconds remaining.\n"
                "Continue waiting?",
                icon='question'
            ):
                return False
        time.sleep(1)
    
    # Stage 3: Final check with option to skip or retry
    return messagebox.askyesno(
        "File Not Ready",
        f"'{filename}' still not available after 23 seconds.\n\n"
        "Do you want to try waiting longer? (Cancel will skip this file)",
        icon='warning'
    )

def main():
    root = tk.Tk()
    root.withdraw()

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
    
    for filename in image_files:
        input_path = os.path.join(current_dir, filename)
        output_filename = os.path.splitext(filename)[0] + '.jpg'
        output_path = os.path.join(output_dir, output_filename)
        
        print(f"\nChecking {filename}...")
        
        if not wait_for_file(input_path, filename):
            print(f"⚠️  Skipping {filename} - file not available after waiting period")
            skipped += 1
            continue
            
        print(f"Processing {filename}...")
        try:
            make_image_square(input_path, output_path)
            processed += 1
        except Exception as e:
            print(f"❌ Failed to process {filename}: {e}")
            if messagebox.askyesno(
                "Processing Error",
                f"Failed to process {filename}:\n{e}\n\n"
                "Do you want to retry this file?",
                icon='error'
            ):
                try:
                    make_image_square(input_path, output_path)
                    processed += 1
                except Exception as e2:
                    print(f"❌ Failed again on {filename}: {e2}")
                    skipped += 1
            else:
                skipped += 1

    messagebox.showinfo(
        "Processing Complete", 
        f"Finished processing folder:\n\n"
        f"✅ Successfully processed: {processed} files\n"
        f"⚠️  Skipped: {skipped} files\n\n"
        f"Output saved to:\n{output_dir}"
    )

if __name__ == "__main__":
    main()
