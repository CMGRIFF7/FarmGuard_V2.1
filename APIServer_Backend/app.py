# APIServer_Backend/app.py
from flask import Flask, request, jsonify, render_template, abort
import os
import configparser
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timezone, timedelta
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager, verify_jwt_in_request

# --- Initialize Flask App ---
app = Flask(__name__)

# --- Configuration ---
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(__file__), 'config_server.ini')
if not os.path.exists(config_path):
    alt_config_path = os.path.join(os.path.dirname(__file__), '..', 'config_server.ini') 
    if os.path.exists(alt_config_path):
        config_path = alt_config_path
    else: # Fallback to current dir if still not found (e.g. when running flask commands from APIServer_Backend)
        alt_config_path_local = 'config_server.ini'
        if os.path.exists(alt_config_path_local):
            config_path = alt_config_path_local
        else:
             raise FileNotFoundError(f"Configuration file not found at primary: {os.path.join(os.path.dirname(__file__), 'config_server.ini')}, alt: {alt_config_path}, or local: {alt_config_path_local}")
config.read(config_path)


db_user = config.get('Database', 'db_user', fallback='your_db_user')
db_password = config.get('Database', 'db_password', fallback='your_db_password')
db_host = config.get('Database', 'db_host', fallback='localhost')
db_port = config.get('Database', 'db_port', fallback='5432')
db_name = config.get('Database', 'db_name', fallback='farmguard_v2_db')

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config["JWT_SECRET_KEY"] = config.get('Server', 'jwt_secret_key', fallback="change-this-super-secret-key-in-config")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=config.getint('Server', 'jwt_expiry_hours', fallback=24))

# --- Initialize Extensions ---
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# --- Import Models (AFTER db and bcrypt are initialized) ---
from .models import User, Asset, GuardianEvent, SubUnitEvent

print("Flask App Initializing with SQLAlchemy, Migrate, Bcrypt, and JWTManager...")

# --- Helper for parsing boolean query parameters ---
def str_to_bool(s):
    if s is None: return False
    return s.lower() in ['true', '1', 't', 'y', 'yes']

# --- Routes ---
@app.route('/')
def index_page():
    return render_template('index.html', message="FarmGuard V2 Backend Ready with Auth!")

@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({"status": "ok", "message": "FarmGuard API is running with DB!"}), 200

# --- Authentication API Endpoints ---
@app.route('/api/auth/register', methods=['POST'])
def register_user():
    data = request.json
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({"status": "error", "message": "Missing username, email, or password"}), 400

    username = data.get('username').strip()
    email = data.get('email').strip().lower()
    
    if User.query.filter_by(username=username).first():
        return jsonify({"status": "error", "message": "Username already exists"}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"status": "error", "message": "Email already exists"}), 409

    try:
        new_user = User(
            username=username,
            email=email,
            password=data.get('password'),
            role=data.get('role', 'viewer')
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"status": "success", "message": "User registered successfully", "user": new_user.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error registering user: {e}")
        return jsonify({"status": "error", "message": f"Could not register user: {str(e)}"}), 500

@app.route('/api/auth/login', methods=['POST'])
def login_user():
    data = request.json
    if not data or not data.get('email_or_username') or not data.get('password'):
        return jsonify({"status": "error", "message": "Missing email/username or password"}), 400

    email_or_username = data.get('email_or_username').strip()
    password = data.get('password')

    user = User.query.filter((User.email == email_or_username.lower()) | (User.username == email_or_username)).first()

    if user and user.check_password(password):
        if not user.is_active:
            return jsonify({"status": "error", "message": "User account is inactive."}), 403
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token, user=user.to_dict()), 200
    else:
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401

@app.route('/api/users/me', methods=['GET'])
@jwt_required()
def get_current_user_profile(): # Renamed for clarity
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user or not user.is_active: # Also check if user is active
        return jsonify({"status": "error", "message": "User not found or inactive"}), 404
    return jsonify(user.to_dict()), 200

# --- Asset API Endpoints ---
@app.route('/api/assets', methods=['POST'])
@jwt_required()
def create_asset():
    data = request.json
    if not data or not data.get('asset_name'): return jsonify({"status": "error", "message": "Missing asset_name"}), 400
    
    rfid_tag = data.get('rfid_tag_assigned')
    if rfid_tag:
        if Asset.query.filter_by(rfid_tag_assigned=rfid_tag).first():
            return jsonify({"status": "error", "message": f"RFID tag {rfid_tag} is already assigned."}), 409
    
    serial_num = data.get('serial_number')
    if serial_num:
        if Asset.query.filter_by(serial_number=serial_num).first():
            return jsonify({"status": "error", "message": f"Serial number {serial_num} already exists."}), 409
            
    new_asset = Asset(
        asset_name=data.get('asset_name'),
        description=data.get('description'),
        rfid_tag_assigned=rfid_tag,
        asset_type=data.get('asset_type'),
        serial_number=serial_num,
        current_status=data.get('current_status', 'unknown'),
        is_active=data.get('is_active', True)
    )
    if data.get('purchase_date'):
        try: new_asset.purchase_date = datetime.strptime(data.get('purchase_date'), '%Y-%m-%d').date()
        except ValueError: return jsonify({"status": "error", "message": "Invalid purchase_date format. Use YYYY-MM-DD."}), 400
    
    try:
        db.session.add(new_asset); db.session.commit()
        return jsonify({"status": "success", "message": "Asset created", "asset": new_asset.to_dict()}), 201
    except Exception as e:
        db.session.rollback(); print(f"Error creating asset: {e}")
        return jsonify({"status": "error", "message": f"Could not create asset: {str(e)}"}), 500

@app.route('/api/assets', methods=['GET'])
@jwt_required(optional=True) # Allow anonymous access but identify user if token present
def get_assets():
    try:
        include_deleted = str_to_bool(request.args.get('include_deleted', 'false'))
        query = Asset.query
        if not include_deleted:
            query = query.filter_by(is_active=True)
        
        # Optional: Implement role-based filtering if needed later
        # current_user_id = get_jwt_identity()
        # if current_user_id: # If user is logged in
        #     user = User.query.get(current_user_id)
        #     if user and user.role != 'admin' and not include_deleted: # Example: non-admins only see active
        #         query = query.filter_by(is_active=True)
        # else: # Anonymous user
        #     if not include_deleted:
        #          query = query.filter_by(is_active=True)


        assets_query = query.order_by(Asset.asset_name).all() # Add pagination later
        assets_list = [asset.to_dict() for asset in assets_query]
        return jsonify(assets_list), 200
    except Exception as e:
        print(f"Error fetching assets: {e}")
        return jsonify({"status": "error", "message": "Could not fetch assets"}), 500

@app.route('/api/assets/<int:asset_id>', methods=['GET'])
@jwt_required(optional=True)
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
@jwt_required()
def update_asset(asset_id):
    asset = Asset.query.filter_by(id=asset_id).first() # Get asset regardless of active status for update
    if not asset:
        return jsonify({"status": "error", "message": "Asset not found"}), 404
        
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    if 'rfid_tag_assigned' in data and data['rfid_tag_assigned'] != asset.rfid_tag_assigned:
        existing_rfid = Asset.query.filter(Asset.id != asset_id, Asset.rfid_tag_assigned == data['rfid_tag_assigned']).first()
        if existing_rfid:
            return jsonify({"status": "error", "message": f"RFID tag {data['rfid_tag_assigned']} is already assigned."}), 409
    
    if 'serial_number' in data and data['serial_number'] != asset.serial_number:
        existing_serial = Asset.query.filter(Asset.id != asset_id, Asset.serial_number == data['serial_number']).first()
        if existing_serial:
            return jsonify({"status": "error", "message": f"Serial number {data['serial_number']} already exists."}), 409

    asset.asset_name = data.get('asset_name', asset.asset_name)
    asset.description = data.get('description', asset.description)
    asset.rfid_tag_assigned = data.get('rfid_tag_assigned', asset.rfid_tag_assigned)
    asset.asset_type = data.get('asset_type', asset.asset_type)
    asset.serial_number = data.get('serial_number', asset.serial_number)
    asset.current_status = data.get('current_status', asset.current_status)
    
    if 'is_active' in data: # Explicitly allow reactivating or deactivating
        asset.is_active = data.get('is_active')
        if not asset.is_active and not asset.deleted_at: # If deactivating now
            asset.deleted_at = datetime.now(timezone.utc)
        elif asset.is_active: # If reactivating
            asset.deleted_at = None


    if data.get('purchase_date'):
        try: asset.purchase_date = datetime.strptime(data.get('purchase_date'), '%Y-%m-%d').date()
        except ValueError: return jsonify({"status": "error", "message": "Invalid purchase_date format. Use YYYY-MM-DD."}), 400
    
    try:
        db.session.commit()
        return jsonify({"status": "success", "message": "Asset updated", "asset": asset.to_dict()}), 200
    except Exception as e:
        db.session.rollback(); print(f"Error updating asset {asset_id}: {e}")
        return jsonify({"status": "error", "message": f"Could not update asset: {str(e)}"}), 500

@app.route('/api/assets/<int:asset_id>', methods=['DELETE'])
@jwt_required() 
def delete_asset(asset_id): # Soft delete
    asset = Asset.query.filter_by(id=asset_id).first()
    if not asset:
        return jsonify({"status": "error", "message": "Asset not found"}), 404
    
    if not asset.is_active:
        return jsonify({"status": "info", "message": "Asset was already marked as deleted"}), 200

    try:
        asset.is_active = False
        asset.deleted_at = datetime.now(timezone.utc)
        db.session.commit()
        return jsonify({"status": "success", "message": "Asset marked as deleted (soft delete)"}), 200
    except Exception as e:
        db.session.rollback(); print(f"Error soft deleting asset {asset_id}: {e}")
        return jsonify({"status": "error", "message": f"Could not soft delete asset: {str(e)}"}), 500

# --- Guardian Event API Endpoints ---
@app.route('/api/guardian_event', methods=['POST'])
@jwt_required(optional=True) # Allow unauthenticated devices to post, but can identify if token is sent
def handle_guardian_event():
    data = request.json
    if not data: return jsonify({"status": "error", "message": "No data provided"}), 400
    
    print(f"Received Guardian Event: {data}")
    unit_id = data.get('unit_id')
    event_data = data.get('event', {})
    timestamp_iso = event_data.get('timestamp_iso')
    tag_id = event_data.get('tag_id')
    video_url_remote = event_data.get('video_url_remote')
    direction = event_data.get('direction')
    raw_payload_to_store = event_data

    if not all([unit_id, timestamp_iso, tag_id]):
        return jsonify({"status": "error", "message": "Missing required fields: unit_id, event.timestamp_iso, event.tag_id"}), 400

    linked_asset_id = None
    associated_asset = Asset.query.filter_by(rfid_tag_assigned=tag_id, is_active=True).first() 
    if associated_asset:
        linked_asset_id = associated_asset.id
        print(f"Event for tag {tag_id} linked to active asset ID {linked_asset_id} ({associated_asset.asset_name})")
    else:
        # Optional: Check if an inactive asset has this tag and link if desired, or log differently
        inactive_asset_with_tag = Asset.query.filter_by(rfid_tag_assigned=tag_id, is_active=False).first()
        if inactive_asset_with_tag:
            linked_asset_id = inactive_asset_with_tag.id # Link to inactive asset
            print(f"Event for tag {tag_id} linked to INACTIVE asset ID {linked_asset_id} ({inactive_asset_with_tag.asset_name})")
        else:
            print(f"No asset (active or inactive) found with RFID tag {tag_id}. Event will be unlinked.")
            # TODO: Trigger "Unknown Tag" alert here via AlertService

    try:
        new_event = GuardianEvent(
            unit_id=unit_id, timestamp_iso=timestamp_iso, tag_id=tag_id, asset_id=linked_asset_id,
            video_url_remote=video_url_remote, direction=direction, raw_event_payload=raw_payload_to_store
        )
        db.session.add(new_event)
        db.session.commit()
        return jsonify({"status": "success", "message": "Guardian event received and stored", 
                        "event_id": new_event.id, "linked_asset_id": linked_asset_id}), 201
    except Exception as e:
        db.session.rollback(); print(f"Error storing guardian event: {e}")
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500

@app.route('/api/events', methods=['GET'])
@jwt_required(optional=True)
def get_all_events():
    try:
        # TODO: Add filters for asset_id, unit_id, date range, etc.
        events_query = GuardianEvent.query.order_by(GuardianEvent.received_at.desc()).limit(100).all()
        event_list = [event.to_dict() for event in events_query]
        return jsonify(event_list), 200
    except Exception as e:
        print(f"Error fetching events: {e}")
        return jsonify({"status": "error", "message": "Could not fetch events"}), 500

# TODO: Add SubUnitEvent ingestion endpoint /api/lorawan_uplink
# TODO: Add Alert endpoints
# TODO: Add FSMA related endpoints

# --- Main Block ---
if __name__ == '__main__':
    server_host = config.get('Server', 'host', fallback='0.0.0.0')
    server_port = config.getint('Server', 'port', fallback=5000)
    server_debug = config.getboolean('Server', 'debug', fallback=True)
    
    app.run(host=server_host, port=server_port, debug=server_debug)
