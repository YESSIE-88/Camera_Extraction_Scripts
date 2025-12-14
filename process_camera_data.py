import os
import shutil
import subprocess
from datetime import datetime
from collections import defaultdict
import piexif
import shlex

# ==============================================
# Configuration
# ==============================================
PHOTO_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mpg', '.mpeg',
    '.m4v', '.3gp', '.3g2', '.ts', '.mts', '.m2ts', '.vob'
}

INPUT_DIR = '/home/jessiesellars/Pictures/Laurie_cam_dec'
OUTPUT_DIR = '/home/jessiesellars/Pictures/output'

# Mode options: "photo", "video", or "both"
MODE = "photo"

# Global dict to track counts per day for naming
date_counters = defaultdict(int)

# ==============================================
# Utility Functions
# ==============================================
def ensure_dir(path):
    """Ensures the output directory exists."""
    if not os.path.exists(path):
        os.makedirs(path)

def get_photo_datetime(path):
    """
    Attempts to get datetime from EXIF data. Falls back to file modification time.
    Uses specific error handling to prevent display issues.
    """
    # Default to file modification time (mtime)
    ts = os.path.getmtime(path)
    fallback_dt = datetime.fromtimestamp(ts)

    try:
        # Attempt to load EXIF data
        exif_dict = piexif.load(path)
        date_str = exif_dict["0th"].get(piexif.ImageIFD.DateTime)
        
        if date_str:
            # If EXIF is found, use it
            return datetime.strptime(date_str.decode(), "%Y:%m:%d %H:%M:%S")
    
    except piexif.Invalidbox as e:
        # Catch specific EXIF errors
        print(f"Warning: Invalid EXIF data in photo {path}. Falling back to mtime. Error: {e}")
    except Exception as e:
        # Catch other general errors (e.g., corrupted file that piexif can't handle)
        print(f"Warning: General error reading EXIF from photo {path}. Falling back to mtime. Error: {e}")

    # Fallback to modification time
    return fallback_dt

def get_video_datetime(path):
    """
    Attempts to get datetime from video metadata using ffprobe. Falls back to mtime.
    """
    # Default to file modification time (mtime)
    ts = os.path.getmtime(path)
    fallback_dt = datetime.fromtimestamp(ts)

    probe_cmd = (
        f"ffprobe -v error -select_streams v:0 -show_entries format_tags=creation_time "
        f"-of default=noprint_wrappers=1:nokey=1 {shlex.quote(path)}"
    )
    
    try:
        creation_time_str = subprocess.check_output(probe_cmd, shell=True).decode().strip()
        if creation_time_str:
            # Attempt to parse creation time (format can vary, ISO is common)
            # Example format: 2023-12-14T10:30:00.000000Z
            try:
                # Common ISO format parsing
                return datetime.fromisoformat(creation_time_str.replace('Z', '+00:00'))
            except ValueError:
                # If ISO parsing fails, fall back gracefully
                print(f"Warning: Could not parse video creation time '{creation_time_str}'. Using mtime.")
        
    except subprocess.CalledProcessError:
        # ffprobe failed or tag not present
        pass
    except Exception as e:
        print(f"Warning: Error during ffprobe for video {path}: {e}. Falling back to mtime.")
    
    return fallback_dt


def generate_name_with_counter(dt, ext):
    """Generates a date-based filename with a sequential counter."""
    date_str = dt.strftime("%Y_%m_%d")
    # Increment the counter for this date
    date_counters[date_str] += 1
    counter = date_counters[date_str]
    return f"{date_str}_{counter:03d}{ext}" # Added :03d for better sorting

# ==============================================
# Photo & Video Processing (Modified)
# ==============================================
def copy_photo(src, dst_dir):
    """
    Copies the photo using the date determined by get_photo_datetime().
    The copy operation is separate from the date extraction.
    """
    # Get the date/time (robustly handled in get_photo_datetime)
    dt = get_photo_datetime(src)
    ext = os.path.splitext(src)[1].lower()
    
    # Generate the destination path
    dst_name = generate_name_with_counter(dt, ext)
    dst_path = os.path.join(dst_dir, dst_name)
    
    # Perform the copy operation
    shutil.copy2(src, dst_path)
    print(f"-> Copied to: {dst_path}")
    
    return dst_path

def convert_video(src, dst_dir):
    """Converts the video to MP4 using FFmpeg and determines date robustly."""
    
    # Get the date/time (uses ffprobe metadata or mtime)
    dt = get_video_datetime(src)
    ext = ".mp4"
    
    # Generate the destination path
    dst_name = generate_name_with_counter(dt, ext)
    dst_path = os.path.join(dst_dir, dst_name)

    # Detect audio codec for smart conversion
    probe_cmd = f"ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 {shlex.quote(src)}"
    try:
        audio_codec = subprocess.check_output(probe_cmd, shell=True).decode().strip()
    except subprocess.CalledProcessError:
        audio_codec = "unknown"

    # Build ffmpeg command
    cmd = [
        "ffmpeg", "-i", src,
        "-map_metadata", "0",
        "-c:v", "copy",
        "-movflags", "+faststart",
    ]

    # Convert audio to AAC if not already AAC, otherwise copy
    if audio_codec != "aac":
        cmd += ["-c:a", "aac", "-b:a", "192k"]
    else:
        cmd += ["-c:a", "copy"]

    cmd.append(dst_path)

    subprocess.run(cmd, check=True)
    print(f"-> Converted to: {dst_path}")
    return dst_path

# ==============================================
# Processing Logic
# ==============================================
def process_file(path, output_dir):
    """Routes files to the appropriate processor based on extension and MODE."""
    ext = os.path.splitext(path)[1].lower()

    if ext in PHOTO_EXTENSIONS and MODE in ("photo", "both"):
        print(f"\nCopying photo: {path}")
        try:
            copy_photo(path, output_dir)
        except Exception as e:
            print(f"FATAL Error copying photo {path}: {e}")

    elif ext in VIDEO_EXTENSIONS and MODE in ("video", "both"):
        print(f"\nProcessing video: {path}")
        try:
            convert_video(path, output_dir)
        except subprocess.CalledProcessError as e:
            print(f"FATAL Error converting video {path} (FFmpeg failed): {e}")
        except Exception as e:
            print(f"FATAL Error converting video {path}: {e}")

def recurse_and_process(input_dir, output_dir):
    """Walks the input directory and processes each file."""
    ensure_dir(output_dir)
    print(f"Starting processing from {input_dir}...")
    for root, _, files in os.walk(input_dir):
        for file in files:
            full_path = os.path.join(root, file)
            process_file(full_path, output_dir)
    print("\nProcessing complete.")

# ==============================================
# Main Execution
# ==============================================
if __name__ == "__main__":
    recurse_and_process(INPUT_DIR, OUTPUT_DIR)