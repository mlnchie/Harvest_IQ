from flask import Blueprint, request, render_template
from app.models.product import Product
from sqlalchemy import or_

# TANGGALIN NATIN ANG url_prefix DITO dahil naka-set na ito sa __init__.py.
# Pipigilan nito ang "/search/search/" URL bug na nagdudulot ng 404 error.
search_bp = Blueprint("search", __name__)

@search_bp.route("/")
def search():
    # Kunin ang keyword na tinype ng user sa search bar
    query = request.args.get("q", "").strip()

    # Kung walang tinype at pinindot lang ang search button
    if not query:
        return render_template(
            "search/results.html",
            products=[],
            query=query
        )

    try:
        # 🔎 SIMPLE AI-LIKE KEYWORD MATCHING
        # Hahanapin ang keyword sa Name, Description, o Location
        products = Product.query.filter(
            Product.status == "approved",
            Product.is_available == True,
            or_(
                Product.name.ilike(f"%{query}%"),
                Product.description.ilike(f"%{query}%"),
                Product.location.ilike(f"%{query}%")
            )
        ).all()

    except Exception as e:
        print(f"🔥 SEARCH ROUTE ERROR: {e}")
        products = []

    return render_template(
        "search/results.html",
        products=products,
        query=query
    )