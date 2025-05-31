# GuardianUnit_RPi/main_guardian_local.py
import time
import csv
import os
from datetime import datetime
import configparser

from rfid_reader_ufr import RFIDReader # Stays the same
from camera_manager_picam import CameraManager # <<<< CHANGED HERE

# data_uploader import is for later phases
# from data_uploader import DataUploader 

def log_local_event(log_file_path, tag_id, timestamp_dt, video_filename):
    # (Content of this function remains the same)
    file_exists = os.path.isfile(log_file_path)
    timestamp_str = timestamp_dt.strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file_path, 'a', newline='') as csvfile:
        fieldnames = ['timestamp', 'tag_id', 'video_filename']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({'timestamp': timestamp_str, 'tag_id': tag_id, 'video_filename': video_filename})
    print(f"Local event logged: {timestamp_str}, {tag_id}, {video_filename}")


def main():
    # Construct path to config file relative to this script's location
    # This makes it more robust if run from different working directories.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_dir, 'config_guardian.ini')
    
    config_parser = configparser.ConfigParser()
    if not os.path.exists(config_file):
        print(f"FATAL ERROR: Configuration file not found at {config_file}")
        return
    config_parser.read(config_file)
    
    log_file = config_parser.get('General', 'log_file_path', fallback='./local_event_log.csv')
    # If log_file_path is relative, make it relative to the script's dir too, or GuardianUnit_RPi
    if not os.path.isabs(log_file):
        log_file = os.path.join(script_dir, log_file)

    guardian_id = config_parser.get('General', 'guardian_unit_id', fallback='GUARDIAN_DEFAULT')

    # Initialize components
    rfid = RFIDReader(config_path=config_file)
    camera = CameraManager(config_path=config_file) # Using the new camera manager
    # uploader = DataUploader(config_path=config_file) # For later

    if not rfid.connected:
        print("Failed to connect to RFID reader. Check configuration and connections. Exiting.")
        camera.close_camera() # Ensure camera is closed if RFID fails early
        return
    if not camera.picam2: # Check if camera was initialized
        print("Failed to initialize camera. Video capture will be disabled. Continuing RFID only...")
        # Decide if you want to exit or continue without camera
        # return # Or just let it run for RFID

    print(f"Guardian Unit '{guardian_id}' Started. Scanning for RFID tags...")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            tag_id = rfid.read_tag()
            if tag_id:
                current_time_dt = datetime.now()
                current_timestamp_iso = current_time_dt.isoformat() # For potential future API use
                print(f"--- Tag Detected: {tag_id} at {current_time_dt.strftime('%Y-%m-%d %H:%M:%S')} ---")
                
                video_filename_local = None
                if camera.picam2: # Only try to capture if camera is available
                    video_filename_local = camera.capture_video_for_tag(tag_id)
                
                if video_filename_local:
                    log_local_event(log_file, tag_id, current_time_dt, os.path.basename(video_filename_local))
                elif not camera.picam2:
                     print(f"Camera not available. Event logged without video for tag {tag_id}.")
                     log_local_event(log_file, tag_id, current_time_dt, "NO_VIDEO_CAM_INIT_FAIL")
                else:
                    print(f"Failed to capture video for tag {tag_id}. Event logged without video.")
                    log_local_event(log_file, tag_id, current_time_dt, "NO_VIDEO_CAPTURE_FAIL")
                
                # --- Placeholder for Phase 2+ data upload ---
                # if video_filename_local:
                #     video_url_remote = uploader.upload_media_file(video_filename_local, tag_id, current_time_dt.strftime("%Y%m%d_%H%M%S"))
                # else:
                #     video_url_remote = None
                # event_payload = {
                #     "timestamp_iso": current_timestamp_iso,
                #     "tag_id": tag_id,
                #     "video_filename_local": os.path.basename(video_filename_local) if video_filename_local else None,
                #     "video_url_remote": video_url_remote,
                #     "direction": "unknown" 
                # }
                # print(f"Prepared event payload for upload: {event_payload}")
                # uploader.upload_event_data(event_payload)
                # --- End Placeholder ---

                print("----------------------------------------------------")
                # Brief pause after processing a tag. Might need adjustment based on vehicle speed
                # and how quickly you want to be able to detect the *next* distinct tag.
                time.sleep(1) 
            else:
                # How often to attempt a read when no tag is present.
                # Shorter makes it more responsive but uses slightly more CPU.
                time.sleep(0.05) # 50ms

    except KeyboardInterrupt:
        print("\nStopping Guardian Unit...")
    finally:
        if 'rfid' in locals() and rfid: # Check if rfid object exists
            rfid.close()
        if 'camera' in locals() and camera: # Check if camera object exists
            camera.close_camera()
        print("Guardian Unit stopped.")

if __name__ == "__main__":
    main()