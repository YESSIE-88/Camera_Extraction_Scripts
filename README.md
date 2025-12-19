# --- SYSTEM DEPENDENCIES (Run once) ---
sudo apt update
sudo apt install python3-venv libegl1-mesa-dev libgl1-mesa-dev libpulse0
sudo apt install gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav

# --- VIRTUAL ENVIRONMENT SETUP ---
python3 -m venv .venv
source .venv/bin/activate

# --- INSTALL PACKAGES ---
pip install PySide6 piexif

# --- TO RUN THE SCRIPTS ---
python add_video_metadata.py

python process_camera_data.py