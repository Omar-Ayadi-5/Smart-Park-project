from app import db


class SensorDevice(db.Model):
    """A Supabase Auth subject may update exactly one assigned parking spot."""
    __tablename__ = "sensor_device"
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(36), unique=True, nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey("parking_spot.id"), unique=True, nullable=False)
