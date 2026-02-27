from flask import Blueprint, request, jsonify
from app import db
from app.models.weigh_logs import WeighLog
from app.models.user import User
from app.models.device import Device
from app.models.weigh_session import WeighSession
from app.models.product import Product # ✅ FIX: Idinagdag ang Product model para sa search
from sqlalchemy import or_ # ✅ FIX: Idinagdag para sa multi-column search
import traceback

api_bp = Blueprint(
    "api",
    __name__,
    url_prefix="/api"
)

# =====================================================
# DEVICE CONFIG (Dapat tumugma sa ID 6 sa iyong Arduino)
# =====================================================
DEVICE_ID = 6


# =====================================================
# START WEIGHING (Triggered mula sa Dashboard)
# =====================================================
@api_bp.route("/start-weighing", methods=["POST"])
def start_weighing():
    data = request.get_json() or {}

    farmer_id = data.get("farmer_id")
    product_name = data.get("product_name")
    price_value = data.get("price")

    if not farmer_id:
        return jsonify({"error": "Missing farmer_id"}), 400

    farmer = User.query.get(farmer_id)
    if not farmer:
        return jsonify({"error": "Farmer not found"}), 404

    # I-reset ang lahat ng dating active sessions para sa farmer na ito
    WeighSession.query.filter_by(
        farmer_id=farmer_id,
        is_active=True
    ).update({"is_active": False})

    # Gumawa ng bagong active session sa database
    new_session = WeighSession(
        farmer_id=farmer_id,
        product_name=product_name,
        price=price_value,
        is_active=True
    )
    db.session.add(new_session)

    # I-ON ang Weighing Status ng Device
    device = Device.query.get(DEVICE_ID)
    if device:
        device.weighing = True
    else:
        device = Device(
            id=DEVICE_ID,
            name="Main Scale",
            weighing=True
        )
        db.session.add(device)

    db.session.commit()
    print(f"[API] 🟢 Weighing session started for Farmer: {farmer.username}")
    return jsonify({"status": "started"})


# =====================================================
# STOP WEIGHING (Manual Reset)
# =====================================================
@api_bp.route("/stop-weighing", methods=["POST"])
def stop_weighing():
    device = Device.query.get(DEVICE_ID)
    if device:
        device.weighing = False

    # I-deactivate ang lahat ng sessions
    WeighSession.query.filter_by(is_active=True).update({"is_active": False})
    
    db.session.commit()
    print("[API] 🛑 Weighing session stopped manually.")
    return jsonify({"status": "stopped"})


# =====================================================
# ESP CHECK COMMAND (Polling endpoint para sa ESP32)
# =====================================================
@api_bp.route("/check-weighing/<int:device_id>")
def check_weighing(device_id):
    device = Device.query.get(device_id)

    # Chine-check kung ang device ay naka-ON at may active session sa DB
    if device and device.weighing:
        active_session = WeighSession.query.filter_by(is_active=True).first()
        if active_session:
            return jsonify({
                "weighing": True, 
                "farmer_id": active_session.farmer_id
            })

    return jsonify({"weighing": False})


# =====================================================
# SUBMIT FINAL WEIGHT (Hardware Data Entry)
# =====================================================
@api_bp.route("/submit-weight", methods=["POST"])
def submit_weight():
    data = request.get_json() or {}
    weight = data.get("weight")

    print(f"[API] 📥 Incoming weight attempt: {data}")

    # Hanapin ang active session sa DB (hindi gumagamit ng global variable)
    weigh_session = WeighSession.query.filter_by(is_active=True).first()

    if not weigh_session:
        print("[API ERROR] Weight received but NO active WeighSession found.")
        return jsonify({"error": "No active session"}), 400

    farmer = User.query.get(weigh_session.farmer_id)
    if not farmer:
        return jsonify({"error": "Farmer not found"}), 404

    # I-validate ang format ng timbang
    try:
        weight_value = float(weight)
        if weight_value <= 0:
             return jsonify({"error": "Weight must be > 0"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid weight format"}), 400

    # I-save sa WeighLog (Safe approach gamit ang getattr para iwas crash)
    try:
        log = WeighLog(
            farmer_id=farmer.id,
            farmer_name=farmer.username,
            phone=getattr(farmer, 'phone', 'N/A'),
            province=getattr(farmer, 'province', 'N/A'),
            city=getattr(farmer, 'city', 'N/A'),
            barangay=getattr(farmer, 'barangay', 'N/A'),
            full_address=getattr(farmer, 'full_address', 'N/A'),
            product=weigh_session.product_name or "Unknown Product",
            suggested_price=weigh_session.price or 0,
            weight=weight_value,
            status="pending"
        )
        db.session.add(log)

        # I-reset ang device status at session pagkatapos ng matagumpay na pag-save
        device = Device.query.get(DEVICE_ID)
        if device:
            device.weighing = False
        
        weigh_session.is_active = False

        db.session.commit()
        print(f"[API SUCCESS] ✅ Saved: {weight_value}kg for Farmer {farmer.username}")
        return jsonify({"message": "Weight submitted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print("[DATABASE ERROR] Failed to save record!")
        print(traceback.format_exc())
        return jsonify({"error": "Database error", "details": str(e)}), 500


# =====================================================
# PRODUCT SEARCH (AJAX para sa Marketplace AI Search)
# =====================================================
@api_bp.route("/search-products")
def search_products():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    try:
        # ✅ FIX: Ginamit ang Product model imbes na WeighLog
        results = Product.query.filter(
            Product.status == "approved",
            Product.is_available == True,
            or_(
                Product.name.ilike(f"%{query}%"),
                Product.description.ilike(f"%{query}%"),
                Product.location.ilike(f"%{query}%")
            )
        ).all()

        data = []
        for r in results:
            data.append({
                "id": r.id,
                "name": r.name,
                "farmer": r.farmer.username if r.farmer else "HarvestIQ Farmer",
                "location": r.location or "Philippines",
                "stock": r.stock_quantity,
                "price": float(r.price or 0),
                "image": r.image or "default_product.jpg"
            })

        return jsonify(data)
    except Exception as e:
        print(f"🔥 SEARCH API ERROR: {e}")
        return jsonify([]), 500