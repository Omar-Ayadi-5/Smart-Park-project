from app.utils.time import utc_now
from app import db

class ParkingZone(db.Model):
    __tablename__ = "parking_zone"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationship
    # Une zone contient plusieurs places.
    spots = db.relationship("ParkingSpot", backref="zone", lazy=True)
