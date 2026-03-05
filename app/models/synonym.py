from app import db

class ProductMapping(db.Model):
    __tablename__ = 'product_mappings'
    
    id = db.Column(db.Integer, primary_key=True)
    # Ang keyword na tina-type (e.g., "kamatis")
    word_a = db.Column(db.String(100), nullable=False, index=True)
    # Ang katumbas na salita (e.g., "tomato")
    word_b = db.Column(db.String(100), nullable=False, index=True)

    def __repr__(self):
        return f'<Mapping {self.word_a} <=> {self.word_b}>'