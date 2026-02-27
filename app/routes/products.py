from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.product import Product
from app.models.category import Category
from app.utils.helpers import save_image

products_bp = Blueprint(
    "products",
    __name__,
    url_prefix="/products"
)

# ─────────────────────────────
# LIST PRODUCTS
# ─────────────────────────────
@products_bp.route("/")
def list_products():
    """
    Displays the marketplace. Uses pagination to support the 
    'products.pages' logic in the HTML template.
    """
    # Get current page from URL parameters (?page=1)
    page = request.args.get('page', 1, type=int)
    per_page = 9  # Adjust this number to show more/less per page

    # FIXED: Replaced .all() with .paginate()
    products_pagination = Product.query.filter_by(
        status="approved",
        is_available=True
    ).order_by(Product.created_at.desc()).paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )

    categories = Category.query.all()

    return render_template(
        "products/list.html",
        products=products_pagination,  # This object now has the .pages attribute
        categories=categories
    )


# ─────────────────────────────
# PRODUCT DETAIL
# ─────────────────────────────
@products_bp.route("/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("products/detail.html", product=product)


# ─────────────────────────────
# ADD PRODUCT
# ─────────────────────────────
@products_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_product():
    if current_user.role != "farmer":
        flash("Only farmers can add products.", "danger")
        return redirect(url_for("users.dashboard"))

    categories = Category.query.all()

    if request.method == "POST":
        image_file = request.files.get("image")
        image_path = save_image(image_file) if image_file else "default_product.jpg"

        product = Product(
            farmer_id=current_user.id,
            category_id=request.form.get("category_id"),
            name=request.form.get("name"),
            description=request.form.get("description"),
            price=float(request.form.get("price", 0)),
            unit="kg",
            stock_quantity=float(request.form.get("stock_quantity", 0)),
            status="approved",
            is_available=True,
            location=current_user.province,
            image=image_path
        )

        db.session.add(product)
        db.session.commit()

        flash("Product added successfully!", "success")
        return redirect(url_for("users.dashboard"))

    return render_template(
        "products/add.html",
        categories=categories
    )


# ─────────────────────────────
# EDIT PRODUCT
# ─────────────────────────────
@products_bp.route("/edit/<int:product_id>", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if product.farmer_id != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for("users.dashboard"))

    categories = Category.query.all()

    if request.method == "POST":
        product.name = request.form.get("name")
        product.description = request.form.get("description")
        product.price = float(request.form.get("price", 0))
        product.stock_quantity = float(request.form.get("stock_quantity", 0))
        product.category_id = request.form.get("category_id")

        db.session.commit()

        flash("Product updated!", "success")
        return redirect(url_for("users.dashboard"))

    return render_template(
        "products/edit.html",
        product=product,
        categories=categories
    )


# ─────────────────────────────
# DELETE PRODUCT
# ─────────────────────────────
@products_bp.route("/delete/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    if product.farmer_id != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for("users.dashboard"))

    db.session.delete(product)
    db.session.commit()

    flash("Product deleted.", "success")
    return redirect(url_for("users.dashboard"))