# GuardianUnit_RPi/rfid_reader_ufr.py
import time
import configparser
import mercurial # For ThingMagic readers

class RFIDReader:
    def __init__(self, config_path='config_guardian.ini'):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        self.reader_type = self.config.get('RFID', 'reader_type', fallback='MOCK').upper()
        self.reader_uri = self.config.get('RFID', 'reader_uri', fallback='tmr:///dev/ttyUSB0')
        self.reader = None
        self.connected = False

        if self.reader_type != 'THINGMAGIC':
            print(f"Warning: Configured reader_type is '{self.reader_type}', but this script is optimized for THINGMAGIC. Attempting to proceed.")
        
        print(f"Initializing THINGMAGIC RFID Reader at {self.reader_uri}...")
        try:
            self.reader = mercurial.Reader(self.reader_uri)
            self.reader.connect()
            self.connected = True
            print("ThingMagic RFID Reader connected successfully.")

            # Configure reader parameters (optional, but good practice)
            if self.config.has_option('RFID', 'region'):
                region = self.config.get('RFID', 'region')
                self.reader.set_region(region)
                print(f"Set RFID region to: {region}")

            if self.config.has_option('RFID', 'read_power'):
                power = self.config.getint('RFID', 'read_power')
                # For ThingMagic USB Pro, antenna port is typically 1.
                # Some readers might have multiple physical antennas mapped to logical ports.
                # The set_read_plan is more versatile if you have complex antenna setups.
                # For a single antenna on USB Pro, setting power on antenna 1 is common.
                # self.reader.set_read_powers([1], [power]) # Older method
                self.reader.set_read_plan([1], "GEN2", read_power=power) # Antenna 1, GEN2, specific power
                print(f"Set RFID read power to: {power} cBdm on antenna 1")
            else:
                # Default sensible plan if not specified
                self.reader.set_read_plan([1], "GEN2")
                print("Set RFID to default read plan (Antenna 1, GEN2, default power)")
            
            # Example: Setting GEN2 session (helps with reading tags in motion or dense tag populations)
            # Consult ThingMagic Gen2 documentation for optimal settings for your use case.
            # self.reader.param_set("/reader/gen2/session", "S1") # S0, S1, S2, S3
            # print("Set GEN2 session to S1")


        except Exception as e:
            print(f"Error initializing ThingMagic RFID reader: {e}")
            self.reader = None
            self.connected = False

    def read_tag(self):
        """Reads tags. Returns the EPC of the first tag found as a hex string, or None."""
        if not self.connected or not self.reader:
            # print("RFID Reader not connected.") # Can be noisy
            return None
        
        try:
            # Read for a short duration to capture tags quickly.
            # Timeout in milliseconds. Adjust as needed for moving vehicles.
            # 200-500ms is a common starting point.
            tags = self.reader.read(timeout=300) 
            if tags:
                # Log all tags found for debugging, but return the first one for simplicity in Phase 1
                # for i, tag in enumerate(tags):
                #     print(f"  Tag {i+1}: EPC={tag.epc.hex()}, RSSI={tag.rssi}, Antenna={tag.antenna}, ReadCount={tag.read_count}")
                
                # Return the EPC of the first tag. 
                # In a more advanced setup, you might select based on RSSI or other criteria.
                return tags[0].epc.hex()
            return None
        except Exception as e:
            print(f"Error during RFID read: {e}")
            # Potentially attempt to reconnect or handle specific errors
            # For now, just return None
            return None

    def close(self):
        if self.reader and self.connected:
            print("Closing ThingMagic RFID Reader connection.")
            try:
                self.reader.disconnect() # Use disconnect for mercurial.Reader
                self.connected = False
            except Exception as e:
                print(f"Error disconnecting RFID reader: {e}")

# Standalone test
if __name__ == '__main__':
    import os
    # This allows running the script directly from its directory or project root for testing
    config_file_path = 'config_guardian.ini'
    if not os.path.exists(config_file_path) and os.path.exists(os.path.join('..', config_file_path)):
        config_file_path = os.path.join('..', config_file_path)
    
    if not os.path.exists(config_file_path):
         # Try if running from root of FarmGuard_V2
        config_file_path = os.path.join('GuardianUnit_RPi', 'config_guardian.ini')

    if not os.path.exists(config_file_path):
        print(f"Error: Config file '{config_file_path}' not found for standalone test.")
    else:
        reader = RFIDReader(config_path=config_file_path)
        if reader.connected:
            print("Testing RFID Reader (Ctrl+C to stop)...")
            try:
                while True:
                    tag_epc = reader.read_tag()
                    if tag_epc:
                        print(f"Tag Detected: EPC = {tag_epc}")
                    time.sleep(0.1) # Brief pause between read attempts
            except KeyboardInterrupt:
                print("Stopping test.")
            finally:
                reader.close()
        else:
            print("Could not connect to RFID reader for test.")