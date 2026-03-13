from flask import Blueprint, render_template, redirect, url_for, flash, session, request, jsonify
from flask_login import login_required, current_user
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.weigh_logs import WeighLog
from app import db
from datetime import datetime
from sqlalchemy.orm import joinedload

# 🛠️ HARDWARE SYNC (IoT Device Integration)
try:
    from app.models.device import Device
except Exception:
    Device = None

users_bp = Blueprint("users", __name__)

# ============================================================
# 🧭 DASHBOARD: ROLE-BASED VIEW LOGIC
# ============================================================
@users_bp.route("/dashboard")
@login_required
def dashboard():
    cart_count = len(session.get('cart', {}))
    
    # 🛒 Marketplace Preview: Approved at Available products lamang
    marketplace_products = Product.query.filter_by(
        status="approved", 
        is_available=True
    ).order_by(Product.created_at.desc()).all()

    # 1. ADMIN REDIRECT
    if current_user.role == "admin":
        return redirect(url_for("admin.dashboard"))

    # 2. FARMER DASHBOARD
    if current_user.role == "farmer":
        farmer_inventory = Product.query.filter_by(
            farmer_id=current_user.id
        ).order_by(Product.created_at.desc()).all()

        farmer_orders = Order.query.join(OrderItem).join(Product).filter(
            Product.farmer_id == current_user.id
        ).options(joinedload(Order.items)).order_by(Order.created_at.desc()).all()

        return render_template(
            "dashboard/farmer.html",
            orders=farmer_orders,
            products=marketplace_products, 
            farmer_products=farmer_inventory,
            cart_count=cart_count
        )

    # 3. BUYER DASHBOARD
    buyer_orders = Order.query.filter_by(buyer_id=current_user.id).all()
    return render_template(
        "dashboard/buyer.html", 
        orders=buyer_orders, 
        products=marketplace_products, 
        cart_count=cart_count
    )

# ============================================================
# 🛡️ ADMIN ACTIONS (Approvals & Pricing)
# ============================================================
@users_bp.route("/admin/approve-product/<int:product_id>", methods=["POST"])
@login_required
def admin_approve_product(product_id):
    if current_user.role != "admin":
        return redirect(url_for("main.index"))
    
    product = Product.query.get_or_404(product_id)
    product.status = "approved"
    
    try:
        db.session.commit()
        flash(f"'{product.name}' is now approved!", "success")
    except Exception:
        db.session.rollback()
        flash("Nagka-error sa pag-approve.", "danger")
            
    return redirect(url_for("admin.dashboard"))

@users_bp.route("/admin/edit-price/<int:product_id>", methods=["POST"])
@login_required
def admin_edit_price(product_id):
    if current_user.role != "admin":
        return redirect(url_for("main.index"))
    
    product = Product.query.get_or_404(product_id)
    new_price = request.form.get("price")
    if new_price:
        try:
            product.price = float(new_price)
            db.session.commit()
            flash(f"Price updated for {product.name}.", "success")
        except ValueError:
            flash("Maling format ng presyo.", "danger")
            
    return redirect(url_for("admin.dashboard"))

# ============================================================
# 👤 PROFILE UPDATE (The Reverting Address & Phone Fix)
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
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")
            flash("Nagkaroon ng error sa pag-save. Pakisubukang muli.", "danger")
            
    return render_template("dashboard/edit_profile.html")

# ============================================================
# ⚖️ IOT WEIGHING SYNC (ESP32 Integration)
# ============================================================
@users_bp.route("/start-weigh", methods=["POST"])
@login_required
def start_weigh():
    session["active_farmer_id"] = current_user.id
    if Device:
        device = Device.query.get(6)
        if device:
            device.weighing = True
            db.session.commit()
    flash("Weighing activated.", "success")
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
    flash("Weighing stopped.", "warning")
    return redirect(url_for("users.dashboard"))

# ============================================================
# ✅ ADDED: CONFIRM RECEIVED (Buyer Action Fix)
# ============================================================
@users_bp.route("/order/confirm-received/<int:order_id>", methods=["POST"])
@login_required
def confirm_received(order_id):
    """Pinapayagan ang Buyer na i-mark ang order bilang 'completed'."""
    order = Order.query.get_or_404(order_id)
    
    # 🛡️ Security Check: Dapat ang Buyer ang nag-click
    if order.buyer_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for("users.dashboard"))
    
    if order.status == 'shipped':
        order.status = 'completed'
        try:
            db.session.commit()
            flash("Order marked as received. Thank you!", "success")
        except Exception as e:
            db.session.rollback()
            flash("Error updating order.", "danger")
    return redirect(url_for("users.dashboard"))