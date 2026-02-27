from flask import Blueprint, render_template, redirect, url_for, flash, session, request
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
# 🧭 USER DASHBOARD (Role-Based)
# ============================================================
@users_bp.route("/dashboard")
@login_required
def dashboard():
    cart_count = len(session.get('cart', {}))
    
    # APPROVED PRODUCTS (Marketplace Preview for Buyers)
    products = Product.query.filter_by(
        status="approved",
        is_available=True
    ).order_by(Product.created_at.desc()).limit(6).all()

    # 1. ADMIN REDIRECT
    if current_user.role == "admin":
        return redirect(url_for("admin.dashboard"))

    # 2. 👨‍🌾 FARMER LOGIC
    if current_user.role == "farmer":
        # JOIN Bridge: Order -> OrderItem -> Product
        # This filters for orders containing items owned by this specific farmer
        # Orders only appear once the Admin moves status to 'pending'
        farmer_orders = Order.query.join(OrderItem).join(Product).filter(
            Product.farmer_id == current_user.id,
            Order.status.in_(["pending", "processing", "shipped", "completed"])
        ).options(joinedload(Order.items)).order_by(Order.created_at.desc()).distinct().all()

        # Farmer's own Inventory and Weighing History
        farmer_products = Product.query.filter_by(farmer_id=current_user.id).all()
        weigh_logs = WeighLog.query.filter_by(farmer_id=current_user.id).order_by(WeighLog.created_at.desc()).all()

        # Compute Total Revenue (Current Stock Value)
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
    # Buyers see all their orders regardless of internal status
    orders = Order.query.filter_by(buyer_id=current_user.id).order_by(Order.created_at.desc()).all()
    
    return render_template(
        "dashboard/buyer.html",
        orders=orders,
        products=products,
        cart_count=cart_count
    )

# ============================================================
# 🛡️ ADMIN ACTION: VERIFY & ACCEPT ORDER
# ============================================================
@users_bp.route("/admin/accept-order/<int:order_id>", methods=["POST"])
@login_required
def admin_accept_order(order_id):
    """Admin verifies order; changes status to 'pending' to make it visible to Farmer"""
    if current_user.role != "admin":
        flash("Unauthorized.", "danger")
        return redirect(url_for("main.index"))
    
    order = Order.query.get_or_404(order_id)
    order.status = "pending" 
    order.admin_approved_at = datetime.utcnow()
    
    db.session.commit()
    flash(f"Order #{order.id} verified and sent to Farmer.", "success")
    return redirect(url_for("admin.dashboard"))

# ============================================================
# 👨‍🌾 FARMER ACTION: PREPARE ORDER (PACKING)
# ============================================================
@users_bp.route("/farmer/prepare-order/<int:order_id>", methods=["POST"])
@login_required
def farmer_prepare_order(order_id):
    if current_user.role != "farmer":
        flash("Unauthorized.", "danger")
        return redirect(url_for("users.dashboard"))

    order = Order.query.get_or_404(order_id)
    
    # Status moves to processing while Farmer packs the items
    order.status = "processing"
    order.processed_at = datetime.utcnow()
    
    db.session.commit()
    flash(f"Order #{order.id} is now being prepared.", "success")
    return redirect(url_for("users.dashboard"))

# ============================================================
# 🚚 UPDATE STATUS: SHIPPED / COMPLETED (DELIVERY CYCLE)
# ============================================================
@users_bp.route("/update-order-status/<int:order_id>/<string:status>", methods=["POST"])
@login_required
def update_order_status(order_id, status):
    order = Order.query.get_or_404(order_id)
    
    if status == "shipped":
        order.status = "shipped"
        order.shipped_at = datetime.utcnow()
    elif status == "completed":
        order.status = "completed"
        order.delivered_at = datetime.utcnow()
        order.payment_status = "paid"

    db.session.commit()
    flash(f"Order #{order.id} updated to {status}.", "success")
    return redirect(url_for("users.dashboard"))

# ============================================================
# 🚀 HARDWARE CONTROLS (WEIGHING) - RETAINED & SYNCED
# ============================================================
@users_bp.route("/start-weigh", methods=["POST"])
@login_required
def start_weigh():
    if current_user.role != "farmer":
        flash("Unauthorized.", "danger")
        return redirect(url_for("users.dashboard"))

    # Track which farmer is currently using the physical hardware
    session["active_farmer_id"] = current_user.id
    
    if Device:
        device = Device.query.get(3)
        if device:
            device.weighing = True
            db.session.commit()
    
    flash("Start command sent to weighing hardware.", "success")
    return redirect(url_for("users.dashboard"))

@users_bp.route("/stop-weigh", methods=["POST"])
@login_required
def stop_weigh():
    session.pop("active_farmer_id", None)
    
    if Device:
        device = Device.query.get(3)
        if device:
            device.weighing = False
            db.session.commit()
            
    flash("Weighing stopped.", "warning")
    return redirect(url_for("users.dashboard"))