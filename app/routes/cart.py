from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from app import db
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.utils.constants import DELIVERY_FEE, FREE_DELIVERY_THRESHOLD, PAYMENT_METHODS

cart_bp = Blueprint('cart', __name__, url_prefix='/cart')

def get_cart():
    return session.get('cart', {})

def save_cart(cart):
    session['cart'] = cart
    session.modified = True

@cart_bp.route('/')
def view_cart():
    cart = get_cart()
    items = []
    subtotal = 0
    for p_id, qty in cart.items():
        product = Product.query.get(int(p_id))
        if product and product.is_available:
            item_subtotal = product.price * qty
            subtotal += item_subtotal
            items.append({'product': product, 'quantity': qty, 'subtotal': item_subtotal})
    
    delivery_fee = 0 if subtotal >= FREE_DELIVERY_THRESHOLD or subtotal == 0 else DELIVERY_FEE
    grand_total = subtotal + delivery_fee
    
    return render_template('cart/cart.html', 
                           items=items, total=subtotal, 
                           delivery_fee=delivery_fee, grand_total=grand_total, 
                           payment_methods=PAYMENT_METHODS, threshold=FREE_DELIVERY_THRESHOLD)

# ✅ DAGDAG: CHECKOUT ROUTE (Para ma-fix ang BuildError)
@cart_bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    cart = get_cart()
    if not cart:
        flash("Walang laman ang iyong cart.", "warning")
        return redirect(url_for('cart.view_cart'))

    shipping_address = request.form.get('shipping_address', '').strip()
    payment_method = request.form.get('payment_method', 'cod')

    if not shipping_address:
        flash("Pakilagay ang iyong address.", "danger")
        return redirect(url_for('cart.view_cart'))

    subtotal = 0
    items_to_save = []
    for p_id, qty in cart.items():
        product = Product.query.get(int(p_id))
        if not product or product.stock_quantity < qty:
            flash(f"Stock error sa {product.name if product else 'item'}.", "danger")
            return redirect(url_for('cart.view_cart'))
        subtotal += product.price * qty
        items_to_save.append({'product': product, 'qty': qty})

    delivery_fee = 0 if subtotal >= FREE_DELIVERY_THRESHOLD else DELIVERY_FEE
    
    try:
        new_order = Order(
            buyer_id=current_user.id,
            total_amount=subtotal + delivery_fee,
            delivery_fee=delivery_fee,
            shipping_address=shipping_address,
            payment_method=payment_method,
            status='pending'
        )
        db.session.add(new_order)
        db.session.flush()

        for item in items_to_save:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item['product'].id,
                quantity=item['qty'],
                unit_price=item['product'].price
            )
            item['product'].stock_quantity -= item['qty']
            db.session.add(order_item)

        db.session.commit()
        session.pop('cart', None) # Clear cart after success
        flash(f"Salamat! Order #{new_order.id} placed.", "success")
        return redirect(url_for('users.dashboard'))
    except Exception as e:
        db.session.rollback()
        flash("Error sa checkout.", "danger")
        return redirect(url_for('cart.view_cart'))

@cart_bp.route('/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    qty = int(request.form.get('quantity', 1))
    cart = get_cart()
    key = str(product_id)
    cart[key] = cart.get(key, 0) + qty
    if cart[key] > product.stock_quantity: cart[key] = product.stock_quantity
    save_cart(cart)
    flash(f"Added {product.name} to cart!", "success")
    return redirect(url_for('cart.view_cart'))

@cart_bp.route('/update', methods=['POST'])
def update_cart():
    cart = get_cart()
    for key, value in request.form.items():
        if key.startswith('qty_'):
            p_id = key.replace('qty_', '')
            try:
                new_qty = int(value)
                product = Product.query.get(int(p_id))
                if product and new_qty > 0: cart[p_id] = min(new_qty, product.stock_quantity)
                elif new_qty <= 0: cart.pop(p_id, None)
            except ValueError: pass
    save_cart(cart)
    return redirect(url_for('cart.view_cart'))

@cart_bp.route('/remove/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart = get_cart()
    cart.pop(str(product_id), None)
    save_cart(cart)
    return redirect(url_for('cart.view_cart'))