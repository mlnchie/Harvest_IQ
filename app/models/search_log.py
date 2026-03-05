from datetime import datetime
from app import db

class SearchLog(db.Model):
    __tablename__ = 'search_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(255), nullable=False, index=True)
    # Dito papasok ang probinsya (e.g., Bulacan, Tarlac, Aurora)
    location = db.Column(db.String(100), index=True) 
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    results_count = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<SearchLog {self.keyword} from {self.location}>'