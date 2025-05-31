# APIServer_Backend/models.py
from .app import db, bcrypt # Import db and bcrypt instance from app.py
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='viewer') # e.g., 'admin', 'manager', 'viewer'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Example: Relationship for who acknowledged alerts (add if you have Alert model later)
    # acknowledged_alerts = db.relationship('Alert', backref='acknowledged_by_user', lazy='dynamic')

    def __init__(self, username, email, password, role='viewer', is_active=True):
        self.username = username
        self.email = email
        self.set_password(password) # Use the method to hash password
        self.role = role
        self.is_active = is_active

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Asset(db.Model):
    __tablename__ = 'assets'
    id = db.Column(db.Integer, primary_key=True)
    asset_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    rfid_tag_assigned = db.Column(db.String(100), unique=True, nullable=True, index=True)
    asset_type = db.Column(db.String(100), nullable=True) 
    serial_number = db.Column(db.String(100), nullable=True, unique=True)
    purchase_date = db.Column(db.Date, nullable=True)
    current_status = db.Column(db.String(50), nullable=True, default='unknown')
    
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True) # Soft delete
    deleted_at = db.Column(db.DateTime, nullable=True) # Soft delete timestamp
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (relying on ondelete='SET NULL' on the FK side)
    guardian_events = db.relationship('GuardianEvent', backref='asset', lazy='dynamic')
    subunit_events = db.relationship('SubUnitEvent', backref='asset', lazy='dynamic')

    def __repr__(self):
        return f"<Asset {self.id}: {self.asset_name} {'(Deleted)' if not self.is_active else ''}>"

    def to_dict(self):
        return {
            'id': self.id,
            'asset_name': self.asset_name,
            'description': self.description,
            'rfid_tag_assigned': self.rfid_tag_assigned,
            'asset_type': self.asset_type,
            'serial_number': self.serial_number,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'current_status': self.current_status,
            'is_active': self.is_active,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class GuardianEvent(db.Model):
    __tablename__ = 'guardian_events'
    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.String(50), nullable=False)
    timestamp_iso = db.Column(db.String(50), nullable=False)
    tag_id = db.Column(db.String(100), nullable=False, index=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id', ondelete='SET NULL'), nullable=True, index=True)
    video_url_remote = db.Column(db.String(512), nullable=True)
    direction = db.Column(db.String(20), nullable=True)
    raw_event_payload = db.Column(db.JSONB, nullable=True)
    received_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<GuardianEvent {self.id} - Unit {self.unit_id} - Tag {self.tag_id}>"
    
    def to_dict(self):
        asset_info = None
        if self.asset: # Check if asset relationship is loaded (due to backref) and not None (due to SET NULL)
            asset_info = { 
                "id": self.asset.id, 
                "name": self.asset.asset_name,
                "is_active": self.asset.is_active 
            }
        return {
            'id': self.id,
            'unit_id': self.unit_id,
            'timestamp_iso': self.timestamp_iso,
            'tag_id': self.tag_id,
            'asset_id': self.asset_id,
            'asset_info': asset_info,
            'video_url_remote': self.video_url_remote,
            'direction': self.direction,
            'raw_event_payload': self.raw_event_payload,
            'received_at': self.received_at.isoformat() if self.received_at else None
        }

class SubUnitEvent(db.Model):
    __tablename__ = 'subunit_events'
    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.String(50), nullable=False) 
    tag_id = db.Column(db.String(100), nullable=True, index=True) 
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id', ondelete='SET NULL'), nullable=True, index=True)
    location_description = db.Column(db.String(255), nullable=True) 
    battery_level_mv = db.Column(db.Integer, nullable=True) 
    rssi = db.Column(db.Integer, nullable=True)
    snr = db.Column(db.Float, nullable=True)
    raw_lorawan_payload = db.Column(db.Text, nullable=True) 
    reported_at_device = db.Column(db.DateTime, nullable=True) 
    received_at_server = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<SubUnitEvent {self.id} - Unit {self.unit_id}>"

    def to_dict(self):
        asset_info = None
        if self.asset: # Check if asset relationship is loaded and not None
            asset_info = { 
                "id": self.asset.id, 
                "name": self.asset.asset_name,
                "is_active": self.asset.is_active
            }
        return {
            'id': self.id,
            'unit_id': self.unit_id,
            'tag_id': self.tag_id,
            'asset_id': self.asset_id,
            'asset_info': asset_info,
            'location_description': self.location_description,
            'battery_level_mv': self.battery_level_mv,
            'rssi': self.rssi,
            'snr': self.snr,
            'raw_lorawan_payload': self.raw_lorawan_payload,
            'reported_at_device': self.reported_at_device.isoformat() if self.reported_at_device else None,
            'received_at_server': self.received_at_server.isoformat() if self.received_at_server else None
        }

print("models.py loaded with User, Asset, GuardianEvent, SubUnitEvent models.")
