# GuardianUnit_RPi/data_uploader.py
"""
Handles uploading event data and media files to the central server or cloud storage.
"""
import requests
import json
import configparser
import os

class DataUploader:
    def __init__(self, config_path='config_guardian.ini'):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        self.api_server_url = self.config.get('General', 'api_server_url')
        self.guardian_unit_id = self.config.get('General', 'guardian_unit_id')
        # TODO: Add cloud storage client initialization if uploading media directly
        print("Data Uploader Initialized.")

    def upload_event_data(self, event_data):
        """
        Uploads RFID event data (including video metadata) to the API server.
        event_data should be a dictionary.
        """
        endpoint = f"{self.api_server_url}/guardian_event" # Example endpoint
        payload = {
            "unit_id": self.guardian_unit_id,
            "event": event_data
        }
        try:
            response = requests.post(endpoint, json=payload, timeout=10)
            response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
            print(f"Event data uploaded successfully: {response.status_code}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error uploading event data: {e}")
            return False

    def upload_media_file(self, file_path, tag_id, timestamp_str):
        """
        Uploads a media file.
        Returns the public URL of the uploaded file, or None on failure.
        This is a placeholder. Implement based on your cloud storage choice.
        Alternatively, the API server can handle the file upload if the RPi POSTs it.
        """
        print(f"DataUploader: Pretending to upload {file_path}...")
        # TODO: Implement actual file upload to S3, GCS, Azure, or via API server
        # For now, return a mock URL based on filename
        filename = os.path.basename(file_path)
        mock_url = f"https://mock-storage.com/videos/{self.guardian_unit_id}/{filename}"
        print(f"DataUploader: Mock URL for {filename} is {mock_url}")
        return mock_url


if __name__ == '__main__':
    uploader = DataUploader()
    test_event = {
        "timestamp": "2023-01-01T12:00:00Z",
        "tag_id": "TEST_TAG_UPLOAD",
        "video_filename": "TEST_TAG_UPLOAD_20230101_120000.mp4",
        "video_url": "https://mock-storage.com/videos/GUARDIAN_001/TEST_TAG_UPLOAD_20230101_120000.mp4",
        "direction": "ingress" # Example
    }
    uploader.upload_event_data(test_event)
    # To test media upload, you'd need a dummy file
    # with open("dummy.mp4", "w") as f: f.write("dummy video")
    # uploader.upload_media_file("dummy.mp4", "TEST_TAG_UPLOAD", "20230101_120000")
    # os.remove("dummy.mp4")