from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.weigh_logs import WeighLog
from app.models.product import Product
from app.models.user import User
from app import db
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# CUSTOM DECORATOR
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# =====================================================
# ADMIN DASHBOARD
# =====================================================
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    pending_logs = WeighLog.query.filter_by(status='pending').order_by(WeighLog.created_at.desc()).all()
    products = Product.query.all() # Para sa Product Pricing table
    
    stats = {
        'pending_count': len(pending_logs),
        'total_users': User.query.count(),
        'total_products': len(products)
    }

    return render_template('dashboard/admin.html', 
                           pending_logs=pending_logs, 
                           products=products,
                           stats=stats)

# =====================================================
# APPROVE WEIGH LOG
# =====================================================
@admin_bp.route('/approve/<int:log_id>', methods=['POST'])
@login_required
@admin_required
def approve_log(log_id):
    log = WeighLog.query.get_or_404(log_id)
    try:
        log.status = 'approved'
        
        # Gagawa ng bagong product mula sa approved log
        new_product = Product(
            farmer_id=log.farmer_id,
            name=log.product,
            price=log.suggested_price or 0, # Tinitiyak na matching sa model mo
            stock_quantity=log.weight,
            location=f"{log.city}, {log.province}",
            status='approved',
            is_available=True
        )
        db.session.add(new_product)
        db.session.commit()
        flash(f"Approved: {log.product} is now live!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}", "danger")
    return redirect(url_for('admin.dashboard'))

# =====================================================
# REJECT WEIGH LOG
# =====================================================
@admin_bp.route('/reject/<int:log_id>', methods=['POST'])
@login_required
@admin_required
def reject_log(log_id):
    log = WeighLog.query.get_or_404(log_id)
    log.status = 'rejected'
    db.session.commit()
    flash(f"Record for {log.farmer_name} has been rejected.", "warning")
    return redirect(url_for('admin.dashboard'))

# =====================================================
# UPDATE PRODUCT PRICE (ITO ANG MISSING ROUTE!)
# =====================================================
@admin_bp.route('/update-price/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def update_price(product_id):
    product = Product.query.get_or_404(product_id)
    new_price = request.form.get('new_price')
    
    if new_price:
        try:
            product.price = float(new_price)
            db.session.commit()
            flash(f"Price for {product.name} updated to ₱{new_price}", "success")
        except ValueError:
            flash("Invalid price format.", "danger")
    
    return redirect(url_for('admin.dashboard'))