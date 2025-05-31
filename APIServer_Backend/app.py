# APIServer_Backend/app.py
from flask import Flask, request, jsonify, render_template, abort
import os
import configparser
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timezone # Added timezone for UTC consistency

# --- Initialize Flask App ---
app = Flask(__name__)

# --- Configuration ---
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(__file__), 'config_server.ini')
if not os.path.exists(config_path):
    # This helps if running flask commands from project root vs. APIServer_Backend dir
    alt_config_path = os.path.join(os.path.dirname(__file__), '..', 'config_server.ini') # Check one level up for testing
    if os.path.exists(alt_config_path):
        config_path = alt_config_path
    else:
        raise FileNotFoundError(f"Configuration file not found at {config_path} or {alt_config_path}")
config.read(config_path)

db_user = config.get('Database', 'db_user')
db_password = config.get('Database', 'db_password')
db_host = config.get('Database', 'db_host')
db_port = config.get('Database', 'db_port')
db_name = config.get('Database', 'db_name')

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Initialize Database and Migrations ---
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- Import Models (AFTER db is initialized) ---
from .models import Asset, GuardianEvent, SubUnitEvent # Import all your models

print("Flask App Initializing with SQLAlchemy and Migrate...")

# --- Helper for parsing boolean query parameters ---
def str_to_bool(s):
    if s is None:
        return False
    return s.lower() in ['true', '1', 't', 'y', 'yes']

# --- Routes ---
@app.route('/')
def index_page():
    return render_template('index.html', message="FarmGuard V2 Backend Ready!")

@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({"status": "ok", "message": "FarmGuard API is running with DB!"}), 200

# --- Asset API Endpoints ---
@app.route('/api/assets', methods=['POST'])
def create_asset():
    data = request.json
    if not data or not data.get('asset_name'):
        return jsonify({"status": "error", "message": "Missing asset_name"}), 400

    if data.get('rfid_tag_assigned'):
        existing_asset_rfid = Asset.query.filter_by(rfid_tag_assigned=data.get('rfid_tag_assigned')).first()
        if existing_asset_rfid:
            return jsonify({"status": "error", "message": f"RFID tag {data.get('rfid_tag_assigned')} is already assigned."}), 409
    
    if data.get('serial_number'):
        existing_asset_serial = Asset.query.filter_by(serial_number=data.get('serial_number')).first()
        if existing_asset_serial:
            return jsonify({"status": "error", "message": f"Serial number {data.get('serial_number')} already exists."}), 409

    new_asset = Asset(
        asset_name=data.get('asset_name'),
        description=data.get('description'),
        rfid_tag_assigned=data.get('rfid_tag_assigned'),
        asset_type=data.get('asset_type'),
        serial_number=data.get('serial_number'),
        current_status=data.get('current_status', 'unknown'),
        is_active=data.get('is_active', True) # Default to active
    )
    if data.get('purchase_date'):
        try:
            new_asset.purchase_date = datetime.strptime(data.get('purchase_date'), '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid purchase_date format. Use YYYY-MM-DD."}), 400
            
    try:
        db.session.add(new_asset)
        db.session.commit()
        return jsonify({"status": "success", "message": "Asset created", "asset": new_asset.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error creating asset: {e}")
        return jsonify({"status": "error", "message": f"Could not create asset: {str(e)}"}), 500

@app.route('/api/assets', methods=['GET'])
def get_assets():
    try:
        include_deleted = str_to_bool(request.args.get('include_deleted', 'false'))
        query = Asset.query
        if not include_deleted:
            query = query.filter_by(is_active=True)
        
        assets_query = query.order_by(Asset.asset_name).all() # Add pagination later
        assets_list = [asset.to_dict() for asset in assets_query]
        return jsonify(assets_list), 200
    except Exception as e:
        print(f"Error fetching assets: {e}")
        return jsonify({"status": "error", "message": "Could not fetch assets"}), 500

@app.route('/api/assets/<int:asset_id>', methods=['GET'])
def get_asset(asset_id):
    try:
        include_deleted = str_to_bool(request.args.get('include_deleted', 'false'))
        query = Asset.query
        if not include_deleted:
            query = query.filter_by(is_active=True)
        
        asset = query.filter_by(id=asset_id).first()
        if not asset:
            return jsonify({"status": "error", "message": "Asset not found or not active"}), 404
        return jsonify(asset.to_dict()), 200
    except Exception as e:
        print(f"Error fetching asset {asset_id}: {e}")
        return jsonify({"status": "error", "message": "Could not fetch asset"}), 500


@app.route('/api/assets/<int:asset_id>', methods=['PUT'])
def update_asset(asset_id):
    asset = Asset.query.filter_by(id=asset_id).first() # Get asset regardless of active status for update
    if not asset:
        return jsonify({"status": "error", "message": "Asset not found"}), 404
        
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    if 'rfid_tag_assigned' in data and data['rfid_tag_assigned'] != asset.rfid_tag_assigned:
        existing_asset_rfid = Asset.query.filter(Asset.id != asset_id, Asset.rfid_tag_assigned == data['rfid_tag_assigned']).first()
        if existing_asset_rfid:
            return jsonify({"status": "error", "message": f"RFID tag {data['rfid_tag_assigned']} is already assigned to another asset."}), 409
    
    if 'serial_number' in data and data['serial_number'] != asset.serial_number:
        existing_asset_serial = Asset.query.filter(Asset.id != asset_id, Asset.serial_number == data['serial_number']).first()
        if existing_asset_serial:
            return jsonify({"status": "error", "message": f"Serial number {data['serial_number']} already exists for another asset."}), 409

    asset.asset_name = data.get('asset_name', asset.asset_name)
    asset.description = data.get('description', asset.description)
    asset.rfid_tag_assigned = data.get('rfid_tag_assigned', asset.rfid_tag_assigned)
    asset.asset_type = data.get('asset_type', asset.asset_type)
    asset.serial_number = data.get('serial_number', asset.serial_number)
    asset.current_status = data.get('current_status', asset.current_status)
    asset.is_active = data.get('is_active', asset.is_active) # Allow updating active status

    if data.get('purchase_date'):
        try:
            asset.purchase_date = datetime.strptime(data.get('purchase_date'), '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid purchase_date format. Use YYYY-MM-DD."}), 400
    
    try:
        db.session.commit()
        return jsonify({"status": "success", "message": "Asset updated", "asset": asset.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error updating asset {asset_id}: {e}")
        return jsonify({"status": "error", "message": f"Could not update asset: {str(e)}"}), 500


@app.route('/api/assets/<int:asset_id>', methods=['DELETE'])
def delete_asset(asset_id): # This is now a SOFT DELETE
    asset = Asset.query.filter_by(id=asset_id).first() # Get asset regardless of active status
    if not asset:
        return jsonify({"status": "error", "message": "Asset not found"}), 404
    
    if not asset.is_active: # Already soft-deleted
        return jsonify({"status": "info", "message": "Asset was already marked as deleted"}), 200

    try:
        asset.is_active = False
        asset.deleted_at = datetime.now(timezone.utc) # Use timezone aware datetime
        db.session.commit()
        return jsonify({"status": "success", "message": "Asset marked as deleted (soft delete)"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error soft deleting asset {asset_id}: {e}")
        return jsonify({"status": "error", "message": f"Could not soft delete asset: {str(e)}"}), 500

# --- Guardian Event API Endpoints ---
@app.route('/api/guardian_event', methods=['POST'])
def handle_guardian_event():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400
    
    print(f"Received Guardian Event: {data}")

    unit_id = data.get('unit_id')
    event_data = data.get('event', {})
    timestamp_iso = event_data.get('timestamp_iso')
    tag_id = event_data.get('tag_id')
    video_url_remote = event_data.get('video_url_remote')
    direction = event_data.get('direction')
    raw_payload_to_store = event_data

    if not all([unit_id, timestamp_iso, tag_id]):
        return jsonify({"status": "error", 
                        "message": "Missing required fields: unit_id, event.timestamp_iso, event.tag_id"}), 400

    linked_asset_id = None
    # Only link to active assets
    associated_asset = Asset.query.filter_by(rfid_tag_assigned=tag_id, is_active=True).first() 
    if associated_asset:
        linked_asset_id = associated_asset.id
        # Example: update asset status when an event occurs
        # associated_asset.current_status = f"Seen by {unit_id} at {direction} on {timestamp_iso}"
        # associated_asset.updated_at = datetime.now(timezone.utc) # Will be handled by onupdate if field exists
        print(f"Event for tag {tag_id} linked to active asset ID {linked_asset_id} ({associated_asset.asset_name})")
    else:
        print(f"No active asset found with RFID tag {tag_id}. Event will be unlinked or linked to an inactive asset if one exists with this tag.")
        # You could also check if an inactive asset has this tag:
        # inactive_asset_with_tag = Asset.query.filter_by(rfid_tag_assigned=tag_id, is_active=False).first()
        # if inactive_asset_with_tag:
        #     linked_asset_id = inactive_asset_with_tag.id # Link to inactive asset
        #     print(f"Event for tag {tag_id} linked to INACTIVE asset ID {linked_asset_id}")


    try:
        new_event = GuardianEvent(
            unit_id=unit_id,
            timestamp_iso=timestamp_iso,
            tag_id=tag_id,
            asset_id=linked_asset_id,
            video_url_remote=video_url_remote,
            direction=direction,
            raw_event_payload=raw_payload_to_store
        )
        db.session.add(new_event)
        # if associated_asset: # No direct changes to asset here unless explicitly needed
            # db.session.add(associated_asset) 
        db.session.commit()
        return jsonify({"status": "success", 
                        "message": "Guardian event received and stored", 
                        "event_id": new_event.id,
                        "linked_asset_id": linked_asset_id}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error storing guardian event: {e}")
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500

@app.route('/api/events', methods=['GET'])
def get_all_events():
    try:
        # Add query parameter to filter by asset_id, unit_id etc. later
        events_query = GuardianEvent.query.order_by(GuardianEvent.received_at.desc()).limit(100).all()
        event_list = [event.to_dict() for event in events_query]
        return jsonify(event_list), 200
    except Exception as e:
        print(f"Error fetching events: {e}")
        return jsonify({"status": "error", "message": "Could not fetch events"}), 500

# TODO: Add SubUnitEvent ingestion endpoint /api/lorawan_uplink

# --- Main Block ---
if __name__ == '__main__':
    server_host = config.get('Server', 'host', fallback='0.0.0.0')
    server_port = config.getint('Server', 'port', fallback=5000)
    server_debug = config.getboolean('Server', 'debug', fallback=True)
    
    app.run(host=server_host, port=server_port, debug=server_debug)