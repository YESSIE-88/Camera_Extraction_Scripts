import sys
import os
import glob
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox
)
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl, QDateTime
from datetime import datetime
import shutil

class VideoDateTagger(QWidget):
    def __init__(self, directory):
        super().__init__()
        self.setWindowTitle("Video Date Tagger")
        self.resize(800, 600)

        self.directory = directory
        self.video_files = sorted(glob.glob(os.path.join(directory, "*.mp4")))
        self.index = 0
        self.counter = 0

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        self.video_widget = QVideoWidget()
        self.player.setVideoOutput(self.video_widget)

        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText("Enter date: YYYY-MM-DD")

        self.save_button = QPushButton("Save Date and Rename")
        self.save_button.clicked.connect(self.save_date_and_rename)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Current video:"))
        layout.addWidget(self.video_widget)
        layout.addWidget(self.date_input)
        layout.addWidget(self.save_button)
        self.setLayout(layout)

        self.load_next_video()

    def load_next_video(self):
        if self.index >= len(self.video_files):
            QMessageBox.information(self, "Done", "All videos processed.")
            self.close()
            return

        self.current_file = self.video_files[self.index]
        self.player.setSource(QUrl.fromLocalFile(self.current_file))
        self.player.play()

    def save_date_and_rename(self):
        date_str = self.date_input.text()
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid date format. Use YYYY-MM-DD.")
            return

        # New filename and full path
        new_filename = f"{date_str.replace('-', '_')}_{self.counter}.mp4"
        new_path = os.path.join(self.directory, new_filename)

        try:
            os.rename(self.current_file, new_path)

            # Set access and modification time
            timestamp = date_obj.timestamp()
            os.utime(new_path, (timestamp, timestamp))

            self.counter += 1
            self.index += 1
            self.date_input.clear()
            self.load_next_video()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to rename or update time: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)

    dir_dialog = QFileDialog()
    dir_dialog.setFileMode(QFileDialog.Directory)
    dir_dialog.setOption(QFileDialog.ShowDirsOnly, True)

    if dir_dialog.exec():
        selected_dir = dir_dialog.selectedFiles()[0]
        window = VideoDateTagger(selected_dir)
        window.show()
        sys.exit(app.exec())
