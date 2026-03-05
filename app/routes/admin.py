from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.weigh_logs import WeighLog
from app.models.product import Product
from app.models.order import Order
from app.models.user import User
from app import db
from sqlalchemy import func 
from functools import wraps

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)

# ──────────────────────────────────────────────────────────
# 🔒 SECURITY DECORATOR
# ──────────────────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            flash("Access denied.", "danger")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)
    return decorated_function

# ──────────────────────────────────────────────────────────
# 🛠 ADMIN DASHBOARD (Big Data Enhanced)
# ──────────────────────────────────────────────────────────
@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    logs = WeighLog.query.filter_by(status="pending").order_by(WeighLog.created_at.desc()).all()
    
    # Listahan ng mga orders para sa Logistics Control
    pending_orders = Order.query.filter(
        Order.status.in_(["pending_admin", "pending", "processing", "shipped"])
    ).order_by(Order.created_at.desc()).all()
    
    products = Product.query.order_by(Product.created_at.desc()).all()

    # 📊 BIG DATA ANALYTICS: Aggregated from IoT hardware sensors
    stats = {
        'total_volume_kg': db.session.query(func.sum(Product.stock_quantity)).scalar() or 0,
        'active_farmers': User.query.filter_by(role='farmer').count(),
        'total_listings': len(products),
        # Supply by location para sa inyong Region 3 mapping
        'supply_by_location': db.session.query(
            Product.location, 
            func.sum(Product.stock_quantity)
        ).group_by(Product.location).all()
    }

    return render_template(
        "dashboard/admin.html",
        logs=logs,
        pending_orders=pending_orders,
        products=products,
        stats=stats 
    )

# ──────────────────────────────────────────────────────────
# 🟢 THE FIX: UPDATE ORDER STATUS (Mawawala na ang BuildError)
# ──────────────────────────────────────────────────────────
@admin_bp.route("/update-order-status/<int:order_id>/<string:status>", methods=['POST'])
@login_required
@admin_required
def update_order_status(order_id, status):
    order = Order.query.get_or_404(order_id)
    try:
        # Binabago ang status (shipped, completed, etc.)
        order.status = status
        db.session.commit()
        flash(f"Order #{order_id} status updated to {status}!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error updating status.", "danger")
    
    return redirect(url_for('admin.dashboard'))

# ──────────────────────────────────────────────────────────
# ✅ APPROVE WEIGH LOG
# ──────────────────────────────────────────────────────────
@admin_bp.route("/approve/<int:log_id>")
@login_required
@admin_required
def approve_log(log_id):
    log = WeighLog.query.get_or_404(log_id)

    if not log.product:
        flash("No product name found in weigh log.", "danger")
        return redirect(url_for("admin.dashboard"))

    product = Product(
        name=log.product,
        farmer_id=log.farmer_id,
        stock_quantity=log.weight or 0,
        price=log.suggested_price or 0,
        unit="kg",
        status="approved",
        is_available=True,
        location=log.province or "Angeles, Pampanga", 
        image="default_product.jpg"
    )

    db.session.add(product)
    log.status = "approved"

    try:
        db.session.commit()
        flash(f"Stock for {log.product} approved and added to marketplace!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error approving product stock.", "danger")

    return redirect(url_for("admin.dashboard"))

# ──────────────────────────────────────────────────────────
# 📦 ADMIN ACCEPT ORDER
# ──────────────────────────────────────────────────────────
@admin_bp.route("/accept-order/<int:order_id>", methods=['POST'])
@login_required
@admin_required
def accept_order(order_id):
    order = Order.query.get_or_404(order_id)
    try:
        order.status = 'pending' 
        db.session.commit()
        flash(f"Order #{order_id} verified and synced for delivery.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error verifying order.", "danger")
    
    return redirect(url_for('admin.dashboard'))

# ──────────────────────────────────────────────────────────
# 🏷️ UPDATE PRODUCT PRICE
# ──────────────────────────────────────────────────────────
@admin_bp.route("/update-price/<int:product_id>", methods=['POST'])
@login_required
@admin_required
def update_price(product_id):
    product = Product.query.get_or_404(product_id)
    new_price = request.form.get('price') 
    
    if new_price:
        try:
            product.price = float(new_price)
            db.session.commit()
            flash(f"Price for {product.name} updated to ₱{new_price}", "success")
        except ValueError:
            flash("Invalid price format.", "danger")
    
    return redirect(url_for("admin.dashboard"))