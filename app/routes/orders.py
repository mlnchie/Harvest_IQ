from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_required, current_user
from app import db
from app.models.order import Order, OrderItem
from app.models.product import Product
from datetime import datetime

orders_bp = Blueprint('orders', __name__)

# ============================================================
# 🛒 NEW: CHECKOUT ROUTE (The missing piece)
# ============================================================
@orders_bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash("Your cart is empty.", "warning")
        return redirect(url_for('main.index'))

    shipping_address = request.form.get('address')
    payment_method = request.form.get('payment_method', 'cod')

    if not shipping_address:
        flash("Shipping address is required.", "danger")
        return redirect(url_for('cart.view_cart'))

    # Calculate Total
    total = 0
    items_to_create = []
    for product_id, quantity in cart.items():
        product = Product.query.get(int(product_id))
        if product and product.stock_quantity >= quantity:
            total += product.price * quantity
            items_to_create.append((product, quantity))
        else:
            flash(f"Sorry, {product.name if product else 'item'} is out of stock.", "danger")
            return redirect(url_for('cart.view_cart'))

    # ✅ THE FIX: Create order with 'pending_admin'
    new_order = Order(
        buyer_id=current_user.id,
        status="pending_admin", # This makes it show up on ADMIN dashboard
        total_amount=total,
        shipping_address=shipping_address,
        payment_method=payment_method,
        created_at=datetime.utcnow()
    )
    
    db.session.add(new_order)
    db.session.flush() # Get the ID before committing

    for product, quantity in items_to_create:
        item = OrderItem(
            order_id=new_order.id,
            product_id=product.id,
            quantity=quantity,
            unit_price=product.price
        )
        db.session.add(item)

    db.session.commit()
    session.pop('cart', None) # Clear cart
    
    flash("Order placed! Waiting for Admin verification.", "success")
    return redirect(url_for('orders.my_orders'))


# ============================================================
# 🧭 MY ORDERS (Buyer view)
# ============================================================
@orders_bp.route('/')
@login_required
def my_orders():
    # Fetch orders for the logged-in buyer
    orders = Order.query.filter_by(buyer_id=current_user.id)\
                        .order_by(Order.created_at.desc()).all()
    return render_template('orders/my_orders.html', orders=orders)


# ============================================================
# 📄 ORDER DETAIL (Tracking View)
# ============================================================
@orders_bp.route('/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    # Allow buyer, admin, or the farmer who owns the product to see it
    return render_template('orders/order_status.html', order=order)


# ============================================================
# ❌ CANCEL ORDER
# ============================================================
@orders_bp.route('/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.buyer_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('main.index'))
        
    # Only allow cancellation if admin hasn't verified yet
    if order.status == 'pending_admin':
        order.status = 'cancelled'
        db.session.commit()
        flash('Order cancelled.', 'info')
    else:
        flash('Verified orders cannot be cancelled manually. Please contact Admin.', 'danger')
        
    return redirect(url_for('orders.order_detail', order_id=order_id))