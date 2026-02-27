from flask import Blueprint, render_template, redirect, url_for, flash, session, request, jsonify
from flask_login import login_required, current_user
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.weigh_logs import WeighLog
from app import db
from datetime import datetime
from sqlalchemy.orm import joinedload

# try import device model safely
try:
    from app.models.device import Device
except Exception:
    Device = None

users_bp = Blueprint("users", __name__)

# ============================================================
# 🧭 USER DASHBOARD (Role-Based Redirects)
# ============================================================
@users_bp.route("/dashboard")
@login_required
def dashboard():
    cart_count = len(session.get('cart', {}))
    
    # Marketplace preview (Top 6 latest products)
    products = Product.query.filter_by(
        status="approved",
        is_available=True
    ).order_by(Product.created_at.desc()).limit(6).all()

    # 1. ADMIN REDIRECT
    if current_user.role == "admin":
        return redirect(url_for("admin.dashboard"))

    # 2. 👨‍🌾 FARMER LOGIC
    if current_user.role == "farmer":
        farmer_orders = Order.query.join(OrderItem).join(Product).filter(
            Product.farmer_id == current_user.id,
            Order.status.in_(["pending", "processing", "shipped", "completed"])
        ).options(joinedload(Order.items)).order_by(Order.created_at.desc()).distinct().all()

        farmer_products = Product.query.filter_by(farmer_id=current_user.id).all()
        weigh_logs = WeighLog.query.filter_by(farmer_id=current_user.id).order_by(WeighLog.created_at.desc()).all()
        total_revenue = sum((p.stock_quantity or 0) * (p.price or 0) for p in farmer_products)

        return render_template(
            "dashboard/farmer.html",
            orders=farmer_orders,
            products=products,
            farmer_products=farmer_products,
            weigh_logs=weigh_logs,
            total_revenue=total_revenue,
            cart_count=cart_count
        )

    # 3. 🛒 BUYER LOGIC
    orders = Order.query.filter_by(buyer_id=current_user.id).order_by(Order.created_at.desc()).all()
    
    return render_template(
        "dashboard/buyer.html",
        orders=orders,
        products=products,
        cart_count=cart_count
    )

# ============================================================
# 👤 PROFILE MANAGEMENT
# ============================================================
@users_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        current_user.full_name = request.form.get("full_name")
        current_user.phone = request.form.get("phone")
        current_user.province = request.form.get("province")
        current_user.city = request.form.get("city")
        current_user.barangay = request.form.get("barangay")
        current_user.full_address = request.form.get("full_address")

        try:
            db.session.commit()
            flash("Profile updated successfully!", "success")
            return redirect(url_for("users.dashboard"))
        except Exception:
            db.session.rollback()
            flash("Nagkaroon ng error sa pag-update ng profile.", "danger")

    return render_template("dashboard/edit_profile.html")

# ============================================================
# 🛡️ ADMIN ACTIONS (VERIFICATION & PRICING)
# ============================================================
@users_bp.route("/admin/accept-order/<int:order_id>", methods=["POST"])
@login_required
def admin_accept_order(order_id):
    if current_user.role != "admin":
        flash("Unauthorized.", "danger")
        return redirect(url_for("main.index"))
    
    order = Order.query.get_or_404(order_id)
    order.status = "pending" 
    order.admin_approved_at = datetime.utcnow()
    
    db.session.commit()
    flash(f"Order #{order.id} verified and sent to Farmer for preparation.", "success")
    return redirect(url_for("admin.dashboard"))

@users_bp.route("/admin/edit-price/<int:product_id>", methods=["POST"])
@login_required
def admin_edit_price(product_id):
    """Pinapayagan ang admin na i-override ang presyo ng produkto."""
    if current_user.role != "admin":
        flash("Unauthorized access.", "danger")
        return redirect(url_for("main.index"))
    
    product = Product.query.get_or_404(product_id)
    new_price = request.form.get("price")
    
    if new_price:
        try:
            product.price = float(new_price)
            db.session.commit()
            flash(f"Price for {product.name} updated to ₱{new_price}.", "success")
        except ValueError:
            flash("Maling format ng presyo.", "danger")
            
    return redirect(url_for("admin.dashboard"))

# ============================================================
# 🚚 LOGISTICS: SHARED STATUS UPDATES (Admin & Buyer)
# ============================================================
@users_bp.route("/update-order-status/<int:order_id>/<string:status>", methods=["POST"])
@login_required
def update_order_status(order_id, status):
    """
    Admin: Updates to 'shipped' or 'completed'.
    Buyer: Updates to 'completed' (Confirm receipt).
    """
    order = Order.query.get_or_404(order_id)

    # 1. ADMIN ACTIONS
    if current_user.role == "admin":
        if status == "shipped":
            order.status = "shipped"
            order.shipped_at = datetime.utcnow()
            flash(f"Order #{order.id} is now IN TRANSIT.", "success")
        elif status == "completed":
            order.status = "completed"
            order.delivered_at = datetime.utcnow()
            order.payment_status = "paid"
            flash(f"Order #{order.id} marked as COMPLETED by Admin.", "success")
        
        db.session.commit()
        return redirect(url_for("admin.dashboard"))

    # 2. BUYER ACTIONS
    if current_user.role == "buyer":
        if order.buyer_id != current_user.id:
            flash("Access denied.", "danger")
            return redirect(url_for("users.dashboard"))
        
        # Buyer can only complete if the order is already shipped
        if status == "completed" and order.status == "shipped":
            order.status = "completed"
            order.delivered_at = datetime.utcnow()
            order.payment_status = "paid"
            db.session.commit()
            flash("Salamat sa pagtanggap ng iyong order!", "success")
        else:
            flash("Hindi pa pwedeng i-confirm ang order na hindi pa na-ship.", "warning")
            
        return redirect(url_for("users.dashboard"))

    return redirect(url_for("main.index"))

# ============================================================
# 👨‍🌾 FARMER ACTIONS
# ============================================================
@users_bp.route("/farmer/prepare-order/<int:order_id>", methods=["POST"])
@login_required
def farmer_prepare_order(order_id):
    if current_user.role != "farmer":
        flash("Access denied.", "danger")
        return redirect(url_for("users.dashboard"))

    order = Order.query.get_or_404(order_id)
    order.status = "processing"
    order.processed_at = datetime.utcnow()
    
    db.session.commit()
    flash(f"Order #{order.id} is being packed and prepared.", "success")
    return redirect(url_for("users.dashboard"))

# ============================================================
# 🔍 AI KEYWORD SEARCH API
# ============================================================
@users_bp.route("/api/search")
@login_required
def search_products():
    """Keyword search for products safely avoiding missing columns."""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify([])

    try:
        # SAFE SEARCH: Name at Location lang ang hahanapin para iwas DB crash
        search_results = Product.query.filter(
            (Product.name.ilike(f'%{query}%')) |
            (Product.location.ilike(f'%{query}%'))
        ).filter_by(status='approved', is_available=True).all()

        output = []
        for p in search_results:
            output.append({
                'id': p.id,
                'name': p.name,
                'price': float(p.price or 0), # FIXED: Safe float conversion
                'location': p.location or 'Philippines',
                'image': p.image or 'default_product.jpg',
                'farmer': p.farmer.username if p.farmer else 'HarvestIQ Seller'
            })
        
        return jsonify(output)
    except Exception as e:
        print(f"Search API Error: {e}")
        return jsonify([]), 500

# ============================================================
# 🚀 HARDWARE SYNC (ESP32 Weighing)
# ============================================================
@users_bp.route("/start-weigh", methods=["POST"])
@login_required
def start_weigh():
    if current_user.role != "farmer":
        flash("Unauthorized.", "danger")
        return redirect(url_for("users.dashboard"))

    session["active_farmer_id"] = current_user.id
    
    if Device:
        device = Device.query.get(6) # Sync to Device ID 6
        if device:
            device.weighing = True
            db.session.commit()
    
    flash("Weighing hardware activated.", "success")
    return redirect(url_for("users.dashboard"))

@users_bp.route("/stop-weigh", methods=["POST"])
@login_required
def stop_weigh():
    session.pop("active_farmer_id", None)
    
    if Device:
        device = Device.query.get(6)
        if device:
            device.weighing = False
            db.session.commit()
            
    flash("Weighing hardware stopped.", "warning")
    return redirect(url_for("users.dashboard"))