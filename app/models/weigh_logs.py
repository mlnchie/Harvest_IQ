from app import db
from datetime import datetime


class WeighLog(db.Model):
    __tablename__ = "weigh_logs"

    id = db.Column(db.Integer, primary_key=True)

    farmer_id = db.Column(db.Integer)
    farmer_name = db.Column(db.String(150))
    phone = db.Column(db.String(50))

    province = db.Column(db.String(100))
    city = db.Column(db.String(100))
    barangay = db.Column(db.String(100))
    full_address = db.Column(db.Text)

    product = db.Column(db.String(100))
    suggested_price = db.Column(db.Float)

    weight = db.Column(db.Float)

    status = db.Column(db.String(50), default="pending")

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

