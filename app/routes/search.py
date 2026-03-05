from flask import Blueprint, request, render_template
from flask_login import current_user
from app.models.product import Product
from app.models.search_log import SearchLog
from app.models.synonym import ProductMapping # IMPORT ITO
from app import db
from sqlalchemy import or_

search_bp = Blueprint("search", __name__)

@search_bp.route("/")
def search():
    query = request.args.get("q", "").strip().lower()

    if not query:
        return render_template("search/results.html", products=[], query=query)

    try:
        # 🧠 1. SYNONYM EXPANSION (The "Smart" Bridge)
        # Hahanapin kung may katumbas na salita ang query ni user
        mapping = ProductMapping.query.filter(
            or_(ProductMapping.word_a == query, ProductMapping.word_b == query)
        ).first()

        search_terms = [query]
        if mapping:
            # Kung nag-search ng "kamatis", idadagdag ang "tomato" sa search list
            equivalent = mapping.word_b if mapping.word_a == query else mapping.word_a
            search_terms.append(equivalent)

        # 🔎 2. DYNAMIC SEARCH LOGIC
        # Gagawa tayo ng listahan ng filters para sa bawat search term
        filters = []
        for term in search_terms:
            filters.append(Product.name.ilike(f"%{term}%"))
            filters.append(Product.description.ilike(f"%{term}%"))

        products = Product.query.filter(
            Product.status == "approved",
            Product.is_available == True,
            or_(*filters)
        ).all()

        # 📊 3. BIG DATA LOGGING (Region 3 Context)
        user_province = "Region 3"
        if current_user.is_authenticated and current_user.province:
            user_province = current_user.province

        new_log = SearchLog(
            keyword=query,
            location=user_province,
            results_count=len(products)
        )
        db.session.add(new_log)
        db.session.commit()
        print(f"📈 [SMART SEARCH] Terms: {search_terms} in {user_province}")

    except Exception as e:
        db.session.rollback()
        print(f"🔥 SEARCH ERROR: {e}")
        products = []

    return render_template("search/results.html", products=products, query=query)