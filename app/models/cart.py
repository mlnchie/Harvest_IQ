from app import db
from datetime import datetime

class CartItem(db.Model):
    __tablename__ = "cart_items"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False) # I-assume natin may Product model ka
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Para makuha ang detalye ng produkto (pangalan, presyo, etc.)
    product = db.relationship('Product', backref='cart_entries')