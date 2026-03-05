import os
from werkzeug.utils import secure_filename
from flask import current_app
from app import db
from app.models.user import User
from app.models.category import Category

# ─────────────────────────────────────────────
# IMAGE UPLOAD HELPER
# ─────────────────────────────────────────────
def save_image(file):
    if not file:
        return None

    filename = secure_filename(file.filename)

    upload_path = os.path.join(
        current_app.root_path,
        'static/uploads/products',
        filename
    )

    os.makedirs(os.path.dirname(upload_path), exist_ok=True)
    file.save(upload_path)

    return f"uploads/products/{filename}"


# ─────────────────────────────────────────────
# SEED DEFAULT CATEGORIES
# ─────────────────────────────────────────────
def seed_categories():
    default_categories = [
        "Vegetables",
        "Fruits",
        "Rice",
        "Root Crops",
        "Livestock",
        "Seafood"
    ]

    for name in default_categories:
        existing = Category.query.filter_by(name=name).first()

        if not existing:
            category = Category(name=name)
            db.session.add(category)

    db.session.commit()
    print("✅ Default categories checked/created.")


# ─────────────────────────────────────────────
# SEED ADMIN USER
# ─────────────────────────────────────────────
def seed_admin():
    admin = User.query.filter_by(role="admin").first()

    if not admin:
        admin = User(
            username="admin",
            email="admin@harvestiq.com",
            role="admin",
            status="approved"
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print("Admin created successfully.")


# ─────────────────────────────────────────────
# 🤖 AUTOMATED SYNONYM MAPPING (Fixed Version)
# ─────────────────────────────────────────────
def auto_map_product(product_name):
    """Kusang gumagawa ng English-Tagalog bridge para sa search engine."""
    # 🛠️ LAZY IMPORT: Inilipat sa loob para iwas Circular Import Error
    from googletrans import Translator
    from app.models.synonym import ProductMapping

    translator = Translator()
    name_lower = product_name.lower().strip()

    try:
        # 1. I-check kung existing na ang mapping para hindi duplicate
        existing = ProductMapping.query.filter(
            (ProductMapping.word_a == name_lower) | 
            (ProductMapping.word_b == name_lower)
        ).first()
        
        if not existing:
            # 2. Detect language at i-translate sa kabila (en <-> tl)
            detection = translator.detect(name_lower)
            target_lang = 'en' if detection.lang == 'tl' else 'tl'
            
            translated = translator.translate(name_lower, dest=target_lang).text.lower()
            
            # 3. I-save ang bagong mapping
            new_map = ProductMapping(word_a=name_lower, word_b=translated)
            db.session.add(new_map)
            db.session.commit()
            print(f"🤖 [AUTO-MAP] Linked '{name_lower}' to '{translated}'")
            
    except Exception as e:
        # FAIL-SAFE: Print lang ang error pero hindi ititigil ang app flow
        print(f"⚠️ Auto-map background error: {e}")