from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from app import db
from app.models.order import Order, OrderItem
from app.models.product import Product
from datetime import datetime

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')

# ============================================================
# 🛒 1. CHECKOUT ROUTE (Robust Auto-Fill Logic)
# ============================================================
@orders_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash("Your cart is empty.", "warning")
        return redirect(url_for('products.list_products'))

    total = 0
    checkout_items = []
    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            qty_float = float(quantity) # 🚨 INAYOS: Para sa decimal quantity
            total += product.price * qty_float
            checkout_items.append({'product': product, 'quantity': qty_float})

    if request.method == 'POST':
        # Sa cart.py 'shipping_address' ang hinahanap pero sa form mo sa cart.html 'address' ang name. 
        # Gagamitin natin ang dalawa para safe
        shipping_address = request.form.get('address') or request.form.get('shipping_address')
        payment_method = request.form.get('payment_method', 'cod')

        if not shipping_address:
            flash("Shipping address is required.", "danger")
            return redirect(url_for('cart.view_cart'))

        items_to_create = []
        for product_id, quantity in cart.items():
            p = Product.query.get(int(product_id))
            qty_float = float(quantity) # 🚨 INAYOS: Float casting
            if p and p.stock_quantity >= qty_float:
                items_to_create.append((p, qty_float))
            else:
                flash(f"Sorry, {p.name if p else 'item'} is out of stock.", "danger")
                return redirect(url_for('cart.view_cart'))

        new_order = Order(
            buyer_id=current_user.id,
            status="pending_admin", 
            total_amount=total,
            shipping_address=shipping_address,
            payment_method=payment_method,
            created_at=datetime.utcnow()
        )
        
        db.session.add(new_order)
        db.session.flush() 

        for product, quantity in items_to_create:
            item = OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=product.price
            )
            product.stock_quantity -= quantity
            db.session.add(item)

        db.session.commit()
        session.pop('cart', None) 
        flash("Order placed! Waiting for Admin verification.", "success")
        return redirect(url_for('orders.my_orders'))

    auto_address = ""
    if hasattr(current_user, 'full_address') and current_user.full_address:
        auto_address = current_user.full_address
    if not auto_address:
        parts = []
        for attr in ['barangay', 'city', 'province']:
            val = getattr(current_user, attr, None)
            if val: parts.append(val)
        auto_address = ", ".join(parts)

    return render_template('orders/checkout.html', total=total, items=checkout_items, auto_address=auto_address)

# ============================================================
# 🧭 2. MY ORDERS (Buyer view)
# ============================================================
@orders_bp.route('/')
@login_required
def my_orders():
    orders = Order.query.filter_by(buyer_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders/my_orders.html', orders=orders)

# ============================================================
# 📄 3. ORDER DETAIL (Tracking & Receipt View)
# ============================================================
@orders_bp.route('/<int:order_id>')
@login_required
def order_detail(order_id):
    """Pinapakita ang breakdown ng items at real-time status."""
    order = Order.query.get_or_404(order_id)
    
    # Security: Buyer, Admin, o ang Farmer lang ang makakakita
    is_owner = order.buyer_id == current_user.id
    is_admin = current_user.role == 'admin'
    
    if not (is_owner or is_admin):
        flash("Unauthorized access.", "danger")
        return redirect(url_for('users.dashboard'))

    return render_template('orders/order_status.html', order=order)

# ============================================================
# ❌ 4. CANCEL ORDER (Buyer Action)
# ============================================================
@orders_bp.route('/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.buyer_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('users.dashboard'))
        
    # Pwede lang mag-cancel kung hindi pa nabe-verify ni Admin
    if order.status == 'pending_admin':
        order.status = 'cancelled'
        # Ibalik ang stock quantity sa farmer
        for item in order.items:
            item.product.stock_quantity += item.quantity
        db.session.commit()
        flash('Order cancelled and stocks restored.', 'info')
    else:
        flash('Verified orders cannot be cancelled. Please contact Admin.', 'danger')
        
    return redirect(url_for('orders.order_detail', order_id=order_id))

# ============================================================
# 🚜 5. UPDATE STATUS (Logistics Action)
# ============================================================
@orders_bp.route('/update-status/<int:order_id>/<string:status>', methods=['POST'])
@login_required
def update_order_status(order_id, status):
    """Admin o Farmer ang nagpapatakbo nito (pending -> processing -> shipped -> completed)."""
    if current_user.role not in ['admin', 'farmer']:
        flash("Unauthorized.", "danger")
        return redirect(url_for('main.index'))

    order = Order.query.get_or_404(order_id)
    order.status = status
    db.session.commit()
    
    flash(f"Order #{order.id} status updated to {status.replace('_', ' ').title()}.", "success")
    return redirect(request.referrer or url_for('users.dashboard'))