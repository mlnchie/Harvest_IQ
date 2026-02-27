from app import db, bcrypt
from flask_login import UserMixin
from datetime import datetime


class User(db.Model, UserMixin):
    __tablename__ = "users"

    # ─────────────────────────────────────────────
    # PRIMARY KEY
    # ─────────────────────────────────────────────
    id = db.Column(db.Integer, primary_key=True)

    # ─────────────────────────────────────────────
    # LOGIN INFO
    # ─────────────────────────────────────────────
    username = db.Column(
        db.String(100),
        unique=True,
        nullable=True
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=True
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    # ─────────────────────────────────────────────
    # ROLE & STATUS
    # ─────────────────────────────────────────────
    role = db.Column(
        db.String(50),
        default="buyer"
    )
    # buyer / farmer / admin

    status = db.Column(
        db.String(50),
        default="approved"
    )
    # pending / approved / rejected

    # Flask-Login ACTIVE FLAG
    is_active = db.Column(
        db.Boolean,
        default=True
    )

    # ─────────────────────────────────────────────
    # PROFILE INFO
    # ─────────────────────────────────────────────
    full_name = db.Column(db.String(150))
    phone = db.Column(db.String(50))

    province = db.Column(db.String(100))
    city = db.Column(db.String(100))
    barangay = db.Column(db.String(100))
    full_address = db.Column(db.Text)
    
    # Optional: Region field for display consistency
    region = db.Column(db.String(100), default="Philippines")

    # ─────────────────────────────────────────────
    # RATINGS INFO (FIXES THE CRASH)
    # ─────────────────────────────────────────────
    average_rating = db.Column(db.Float, default=0.0) #

    # ─────────────────────────────────────────────
    # FARMER PRODUCT INFO
    # ─────────────────────────────────────────────
    main_product = db.Column(db.String(100))

    price_per_kg = db.Column(
        db.Float,
        default=0
    )

    # ─────────────────────────────────────────────
    # LIVE WEIGHING FLAG (ESP32 SYNC)
    # ─────────────────────────────────────────────
    is_weighing = db.Column(
        db.Boolean,
        default=False
    )

    # ─────────────────────────────────────────────
    # TIMESTAMP
    # ─────────────────────────────────────────────
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # ─────────────────────────────────────────────
    # PASSWORD METHODS
    # ─────────────────────────────────────────────
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(
            self.password_hash,
            password
        )

    # Flask-Login required
    def get_id(self):
        return str(self.id)

    # ─────────────────────────────────────────────
    # OPTIONAL HELPERS
    # ─────────────────────────────────────────────
    def is_farmer(self):
        return self.role == "farmer"

    def is_admin(self):
        return self.role == "admin"

    def is_buyer(self):
        return self.role == "buyer"

    def is_approved(self):
        return self.status == "approved"