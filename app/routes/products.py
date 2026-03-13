from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.models.product import Product
from app.models.category import Category
from app.models.review import Review 
from app.utils.helpers import save_image, auto_map_product 

products_bp = Blueprint(
    "products",
    "__name__",
    url_prefix="/products"
)

# 🛒 MARKETPLACE: Buyer Listing (Approved Only)
@products_bp.route("/")
def list_products():
    page = request.args.get('page', 1, type=int)
    per_page = 9 

    products_pagination = Product.query.filter_by(
        status="approved", 
        is_available=True
    ).order_by(Product.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    categories = Category.query.all()
    return render_template("products/list.html", products=products_pagination, categories=categories)


# 🔍 PRODUCT DETAIL
@products_bp.route("/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("products/detail.html", product=product)


# 👨‍🌾 ADD HARVEST (Starts as pending)
@products_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_product():
    if current_user.role != "farmer":
        flash("Only farmers can add products.", "danger")
        return redirect(url_for("users.dashboard"))

    categories = Category.query.all()

    if request.method == "POST":
        try:
            image_file = request.files.get("image")
            image_path = save_image(image_file) if image_file else "default_product.jpg"
            product_name = request.form.get("name")

            raw_category = request.form.get("category_id")
            safe_category_id = int(raw_category) if raw_category and raw_category.isdigit() else None
            user_province = getattr(current_user, 'province', 'Pampanga')
            input_location = request.form.get("location") or user_province

            new_product = Product(
                farmer_id=current_user.id,
                category_id=safe_category_id,
                name=product_name,
                description=request.form.get("description"),
                price=float(request.form.get("price", 0) or 0),
                unit=request.form.get("unit", "kg"),
                stock_quantity=float(request.form.get("stock_quantity", 0) or 0),
                min_order_quantity=float(request.form.get("min_order_quantity", 1) or 1),
                status="pending", 
                is_available=True,
                is_organic='is_organic' in request.form,
                location=input_location,
                province="Pampanga",
                image=image_path
            )

            db.session.add(new_product)
            db.session.commit()
            
            try:
                auto_map_product(product_name)
            except Exception as e:
                print(f"⚠️ Auto-map warning: {e}")

            flash(f"Success! '{product_name}' is waiting for admin approval.", "info")
            return redirect(url_for("users.dashboard"))
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ DB ADD PRODUCT ERROR: {str(e)}")
            flash(f"Nagka-error sa pag-save: {str(e)[:50]}...", "danger")

    return render_template("products/add.html", categories=categories)


# ✏️ EDIT & DELETE
@products_bp.route("/edit/<int:product_id>", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.farmer_id != current_user.id:
        return redirect(url_for("users.dashboard"))

    if request.method == "POST":
        product.name = request.form.get("name")
        raw_category = request.form.get("category_id")
        product.category_id = int(raw_category) if raw_category and raw_category.isdigit() else product.category_id
        
        product.unit = request.form.get("unit")
        product.price = float(request.form.get("price", 0) or 0)
        product.stock_quantity = float(request.form.get("stock_quantity", 0) or 0)
        product.min_order_quantity = float(request.form.get("min_order_quantity", 1) or 1)
        product.location = request.form.get("location") or product.location
        product.description = request.form.get("description")
        product.is_organic = 'is_organic' in request.form
        product.is_available = 'is_available' in request.form

        image_file = request.files.get("image")
        if image_file and image_file.filename != '':
            product.image = save_image(image_file)

        db.session.commit()
        flash("Product updated successfully!", "success")
        return redirect(url_for("users.dashboard"))

    return render_template("products/edit.html", product=product, categories=Category.query.all())


@products_bp.route("/delete/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.farmer_id == current_user.id or current_user.role == 'admin':
        db.session.delete(product)
        db.session.commit()
        flash("Product deleted.", "success")
    return redirect(url_for("users.dashboard"))


# ⭐ RATE & REVIEW PRODUCT (Manual Rating Logic Kept)
@products_bp.route("/<int:product_id>/rate", methods=["POST"])
@login_required
def rate_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    existing_review = Review.query.filter_by(product_id=product.id, reviewer_id=current_user.id).first()
    if existing_review:
        flash("Nakapag-review ka na sa produktong ito.", "warning")
        return redirect(request.referrer)

    try:
        rating_value = int(request.form.get("rating", 5))
        comment_text = request.form.get("comment", "")
        
        image_file = request.files.get("image")
        image_path = None
        if image_file and image_file.filename != '':
            image_path = save_image(image_file)

        # 1. Save Review
        new_review = Review(
            product_id=product.id,
            reviewer_id=current_user.id,
            rating=rating_value,
            comment=comment_text,
            image=image_path
        )
        db.session.add(new_review)

        # 2. Manual Product Rating Calculation
        # Formula: $$Total\_Score / (Count + 1)$$
        if product.review_count == 0:
            product.average_rating = float(rating_value)
        else:
            total_score = (product.average_rating * product.review_count) + rating_value
            product.average_rating = total_score / (product.review_count + 1)
            
        product.review_count += 1
        
        # 3. Manual Farmer Rating Update
        farmer = product.farmer
        all_farmer_products = Product.query.filter_by(farmer_id=farmer.id).all()
        
        total_farmer_stars = 0
        total_farmer_reviews = 0
        
        for p in all_farmer_products:
            if p.review_count > 0:
                total_farmer_stars += (p.average_rating * p.review_count)
                total_farmer_reviews += p.review_count
                
        if total_farmer_reviews > 0:
            farmer.average_rating = total_farmer_stars / total_farmer_reviews
            
        db.session.commit()
        flash("Salamat! Na-publish na ang iyong review.", "success")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error sa pag-save ng review: {e}")
        flash(f"Nagka-error: {str(e)}", "danger")

    return redirect(request.referrer)