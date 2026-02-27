from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.weigh_logs import WeighLog
from app.models.product import Product
from app.models.order import Order
from app import db

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)

# ──────────────────────────────────────────────────────────
# 🛠 ADMIN DASHBOARD
# ──────────────────────────────────────────────────────────
@admin_bp.route("/dashboard")
@login_required
def dashboard():
    # Security check: Only allow users with the 'admin' role
    if current_user.role != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    # ⚖️ PENDING WEIGH LOGS (Top Section in your screenshot)
    # These are products farmers have weighed that need to be approved into the shop
    logs = WeighLog.query.filter_by(
        status="pending"
    ).order_by(
        WeighLog.created_at.desc()
    ).all()

    # 📋 PENDING ORDERS (Bottom Section in your screenshot)
    # We fetch 'pending_admin' (New), 'pending' (Accepted), and 'processing' (Farmer packing)
    # This keeps orders on the dashboard so you can monitor the status after approval
    pending_orders = Order.query.filter(
        Order.status.in_(["pending_admin", "pending", "processing", "shipped"])
    ).order_by(Order.created_at.desc()).all()

    return render_template(
        "dashboard/admin.html",
        logs=logs,
        pending_orders=pending_orders
    )


# ──────────────────────────────────────────────────────────
# ✅ APPROVE WEIGH LOG (Inventory Management)
# ──────────────────────────────────────────────────────────
@admin_bp.route("/approve/<int:log_id>")
@login_required
def approve_log(log_id):
    if current_user.role != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))

    log = WeighLog.query.get_or_404(log_id)

    # Prevent approving logs without a product name
    if not log.product:
        flash("No product name found in weigh log.", "danger")
        return redirect(url_for("admin.dashboard"))

    # Create the live Product from the Weigh Log data
    product = Product(
        name=log.product,
        farmer_id=log.farmer_id,
        stock_quantity=log.weight or 0,
        price=log.suggested_price or 0,
        unit="kg",
        status="approved",
        is_available=True,
        location=log.province or "Unknown",
        image="default_product.jpg"
    )

    db.session.add(product)
    
    # Update log status so it disappears from the 'Pending Weigh Logs' list
    log.status = "approved"

    try:
        db.session.commit()
        flash(f"Stock for {log.product} approved and added to marketplace!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error approving product stock.", "danger")

    return redirect(url_for("admin.dashboard"))