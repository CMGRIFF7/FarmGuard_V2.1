# GuardianUnit_RPi/camera_manager_picam.py
import time
import os
import configparser
from datetime import datetime
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput
import libcamera # For controls

class CameraManager:
    def __init__(self, config_path='config_guardian.ini'):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        self.media_path = self.config.get('General', 'media_save_path', fallback='./media_captures/')
        self.capture_duration = self.config.getint('Camera', 'capture_duration_seconds', fallback=10)
        
        if not os.path.exists(self.media_path):
            os.makedirs(self.media_path)
        
        self.picam2 = None
        try:
            self.picam2 = Picamera2()
            print("PiCamera2 Initialized.")
        except Exception as e:
            print(f"Error initializing PiCamera2: {e}. Camera functionality will be disabled.")
            self.picam2 = None # Ensure it's None if initialization failed

    def capture_video_for_tag(self, tag_id):
        if not self.picam2:
            print("Camera not available or failed to initialize.")
            return None

        try:
            # Configure for video recording
            # You can adjust resolution, framerate here if needed.
            # main_stream_size = {"size": (1280, 720)} # Example 720p
            main_stream_size = {"size": (1920, 1080)} # Example 1080p
            video_config = self.picam2.create_video_configuration(main=main_stream_size)
            # Apply autofocus settings
            video_config["controls"]["AfMode"] = libcamera.controls.AfModeEnum.Continuous # Continuous AutoFocus
            video_config["controls"]["AfSpeed"] = libcamera.controls.AfSpeedEnum.Fast 
            # video_config["controls"]["AfRange"] = libcamera.controls.AfRangeEnum.Full # Or Normal, Macro
            
            self.picam2.configure(video_config)
            
            encoder = H264Encoder(bitrate=8000000) # 8 Mbps, adjust as needed for quality/file size
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_tag_id = "".join(c if c.isalnum() else "_" for c in tag_id) # Sanitize tag_id
            
            # FfmpegOutput will handle the .mp4 extension
            filename_base = os.path.join(self.media_path, f"{safe_tag_id}_{timestamp_str}")
            output_filename = f"{filename_base}.mp4"
            output = FfmpegOutput(output_filename)

            self.picam2.start_encoder(encoder) # Start encoder separately
            self.picam2.start_recording(encoder, output) # Start recording
            print(f"Recording video to {output_filename} for {self.capture_duration} seconds...")
            
            # Wait for the capture duration
            # picamera2 records in a separate thread, so time.sleep() is fine.
            time.sleep(self.capture_duration)
            
            self.picam2.stop_recording()
            self.picam2.stop_encoder() # Stop encoder after recording
            
            print(f"Video saved: {output_filename}")
            return output_filename
        except Exception as e:
            print(f"Error during video capture: {e}")
            # Attempt to stop recording/encoder if an error occurs mid-way
            try:
                if self.picam2.started: # Check if picam2 object has 'started' attribute or similar check
                    if self.picam2.encoder and self.picam2.encoder.recording: # Check encoder state
                         self.picam2.stop_recording()
                    if self.picam2.encoder:
                        self.picam2.stop_encoder()
            except Exception as e_stop:
                print(f"Error trying to stop camera after capture error: {e_stop}")
            return None
        # finally:
            # It's generally better to keep the Picamera2 object alive if you plan to record again soon.
            # Closing and re-initializing it for every capture can be slow.
            # self.close_camera() # Only call this when the application is shutting down.

    def close_camera(self):
        if self.picam2:
            print("Closing PiCamera2.")
            try:
                # Ensure recording is stopped if it was somehow left running
                if self.picam2.started and self.picam2.encoder and self.picam2.encoder.recording:
                    self.picam2.stop_recording()
                if self.picam2.started and self.picam2.encoder:
                    self.picam2.stop_encoder()
                self.picam2.close()
            except Exception as e:
                print(f"Error closing camera: {e}")
            self.picam2 = None


# Standalone test
if __name__ == '__main__':
    import os
    config_file_path = 'config_guardian.ini'
    if not os.path.exists(config_file_path) and os.path.exists(os.path.join('..', config_file_path)):
        config_file_path = os.path.join('..', config_file_path)
    if not os.path.exists(config_file_path):
        config_file_path = os.path.join('GuardianUnit_RPi', 'config_guardian.ini')

    if not os.path.exists(config_file_path):
        print(f"Error: Config file '{config_file_path}' not found for standalone test.")
    else:
        cam_manager = CameraManager(config_path=config_file_path)
        if cam_manager.picam2: # Check if camera initialized successfully
            test_tag = "TEST_CAM_001"
            print(f"Testing camera capture for tag: {test_tag}")
            video_file = cam_manager.capture_video_for_tag(test_tag)
            if video_file:
                print(f"Test video saved to: {video_file}")
            else:
                print("Test video capture failed.")
            cam_manager.close_camera() # Close camera after standalone test
        else:
            print("Camera manager could not initialize the camera.")