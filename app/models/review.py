from app import db
from datetime import datetime

class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    
    # 🔗 Foreign Keys (Naka-link sa products at users table)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # ⭐ Review Details
    rating = db.Column(db.Integer, nullable=False)  # Tumatanggap ng 1 hanggang 5
    comment = db.Column(db.Text, nullable=True)     # Optional text review
    image = db.Column(db.String(255), nullable=True) # Optional image upload for proof
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 🤝 Relationships (Para madaling tawagin sa Jinja2 HTML)
    # Halimbawa sa HTML: {{ review.reviewer.username }} o {{ review.product.name }}
    reviewer = db.relationship('User', backref=db.backref('reviews_given', lazy=True))
    product = db.relationship('Product', backref=db.backref('product_reviews', lazy=True))

    def __repr__(self):
        return f'<Review {self.rating}★ on Product #{self.product_id} by User #{self.reviewer_id}>'