#!/usr/bin/env python3

import os
import shutil
import time
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox

def get_desktop_path():
    """Get path to user's desktop"""
    return os.path.join(os.path.expanduser("~"), "Desktop")

def is_image_square(image_path):
    """Check if image is square with error handling"""
    try:
        with Image.open(image_path) as img:
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
                    os.path.join(original_dir, filename),
                    os.path.join(temp_input, filename)
                )
                all_images.append(filename)
            except Exception as e:
                print(f"❌ Failed to copy {filename}: {str(e)}")

    if not all_images:
        shutil.rmtree(temp_root, ignore_errors=True)
        return False, "No valid images found"

    # 2. Process non-square images (preserve original filenames and extensions)
    processed_count = 0
    for filename in all_images:
        input_path = os.path.join(temp_input, filename)
        output_filename = filename  # keep the original name
        output_path = os.path.join(temp_output, output_filename)

        # Skip if already in final output (from previous runs)
        if os.path.exists(os.path.join(final_output, output_filename)):
            continue

        try:
            if is_image_square(input_path):
                # Copy square images directly to final output with the same name
                shutil.copy2(input_path, os.path.join(final_output, filename))
                print(f"♢ Square image copied: {filename}")
            else:
                # Process non-square images
                with Image.open(input_path) as img:
                    width, height = img.size
                    max_dim = max(width, height)
                    new_img = Image.new("RGB", (max_dim, max_dim), (255, 255, 255))
                    new_img.paste(img, ((max_dim - width) // 2, (max_dim - height) // 2))

                    ext = os.path.splitext(filename)[1].lower()
                    if ext in [".jpg", ".jpeg"]:
                        new_img.save(output_path, "JPEG", quality=95)
                    else:
                        # Save in the original format when possible
                        # (Pillow infers format from extension; this avoids JPEG-only params)
                        new_img.save(output_path)
                processed_count += 1
                print(f"□ Processed: {filename}")
        except Exception as e:
            print(f"❌ Failed {filename}: {str(e)}")

    # 3. Final sweep to catch any missed square images
    square_count = 0
    for filename in os.listdir(original_dir):
        src = os.path.join(original_dir, filename)
        dst = os.path.join(final_output, filename)
        
        if (filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.jfif'))
            and not os.path.exists(dst)):
            try:
                if is_image_square(src):
                    shutil.copy2(src, dst)
                    square_count += 1
                    print(f"♢ Final sweep copied: {filename}")
            except Exception as e:
                print(f"❌ Final sweep failed on {filename}: {str(e)}")

    # 4. Move all processed images to final output
    moved_count = 0
    for filename in os.listdir(temp_output):
        try:
            shutil.move(
                os.path.join(temp_output, filename),
                os.path.join(final_output, filename)
            )
            moved_count += 1
        except Exception as e:
            print(f"❌ Failed to move {filename}: {str(e)}")

    # 5. Verify all square images made it
    verified_square = 0
    for filename in os.listdir(original_dir):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.jfif')):
            src = os.path.join(original_dir, filename)
            dst = os.path.join(final_output, filename)
            
            if is_image_square(src) and not os.path.exists(dst):
                try:
                    shutil.copy2(src, dst)
                    verified_square += 1
                    print(f"♢ Verification copied: {filename}")
                except Exception as e:
                    print(f"❌ Verification failed on {filename}: {str(e)}")

    # Cleanup
    shutil.rmtree(temp_root, ignore_errors=True)
    
    return True, (
        f"Final Results:\n"
        f"- Processed {processed_count} non-square images\n"
        f"- Copied {square_count + verified_square} square images\n"
        f"- Moved {moved_count} processed images\n"
        f"- Total in output: {len(os.listdir(final_output))} files\n"
        f"- Output folder: {final_output}"
    )

def main():
    root = tk.Tk()
    root.withdraw()
    
    try:
        source_dir = filedialog.askdirectory(title="Select folder with images")
        if not source_dir:
            return
            
        result, message = process_images_locally(source_dir)
        messagebox.showinfo("Processing Complete", message)
    except Exception as e:
        messagebox.showerror("Error", f"Operation failed:\n{str(e)}")
    finally:
        root.destroy()

if __name__ == "__main__":
    main()
