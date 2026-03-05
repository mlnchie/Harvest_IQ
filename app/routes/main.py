from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
from sqlalchemy import func, or_, cast, String
from app.models.product import Product
from app.models.category import Category
from app.models.user import User
from app.models.search_log import SearchLog 
from app import db
from datetime import datetime, timezone
from flask_login import login_required, current_user
from openai import OpenAI 
import os

# 1. Blueprint Definition
main_bp = Blueprint('main', __name__)

# 🚨 OPENAI CLIENT INITIALIZATION
# 💡 PAALALA: I-paste dito ang iyong Secret Key (sk-...)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 🟢 ULTIMATE TRANSLATION MAP (Hybrid AI Fallback & Recipe Engine)
# Naglalaman ito ng komprehensibong listahan ng mga gulay, prutas, at seafood sa Pilipinas.
TRANSLATION_MAP = {
    # ─── RECIPES & DISHES ───
    "torta": ["talong", "eggplant", "itlog", "egg", "sibuyas", "onion", "bawang", "garlic", "mantika", "oil"],
    "tortang talong": ["talong", "eggplant", "itlog", "egg", "sibuyas", "onion", "bawang", "garlic", "mantika", "oil"],
    "sinigang": ["baboy", "pork", "kangkong", "water spinach", "tamarind", "sampaloc", "kamatis", "tomato", "gabi", "taro", "labanos", "radish"],
    "adobo": ["baboy", "pork", "manok", "chicken", "bawang", "garlic", "toyo", "soy sauce", "suka", "vinegar", "mantika", "oil", "paminta", "peppercorn"],
    "pinakbet": ["kalabasa", "squash", "sitaw", "yard-long bean", "talong", "eggplant", "ampalaya", "bitter melon", "okra", "bagoong"],
    
    # ─── THE BAHAY KUBO CLASSICS & VEGGIES ───
    "singkamas": ["singkamas", "jicama", "yam bean"], "jicama": ["singkamas", "jicama"],
    "sigarilyas": ["sigarilyas", "winged bean"], "winged bean": ["sigarilyas", "winged bean"],
    "mani": ["mani", "peanut"], "peanut": ["mani", "peanut"],
    "sitaw": ["sitaw", "yard-long bean", "snake bean"], "yard-long bean": ["sitaw", "yard-long bean"],
    "bataw": ["bataw", "hyacinth bean"],
    "patani": ["patani", "lima bean"], "lima bean": ["patani", "lima bean"],
    "kundol": ["kundol", "winter melon", "wax gourd"], "winter melon": ["kundol", "winter melon"],
    "patola": ["patola", "luffa", "sponge gourd"], "luffa": ["patola", "luffa"],
    "upo": ["upo", "bottle gourd"], "bottle gourd": ["upo", "bottle gourd"],
    "kalabasa": ["kalabasa", "squash", "pumpkin"], "squash": ["kalabasa", "squash", "pumpkin"],
    "labanos": ["labanos", "radish", "daikon"], "radish": ["labanos", "radish"],
    "mustasa": ["mustasa", "mustard greens"], "mustard greens": ["mustasa"],
    "sibuyas": ["sibuyas", "onion", "lasona", "shallots"], "onion": ["sibuyas", "onion"],
    "kamatis": ["kamatis", "tomato"], "tomato": ["kamatis", "tomato"],
    "bawang": ["bawang", "garlic"], "garlic": ["bawang", "garlic"],
    "luya": ["luya", "ginger"], "ginger": ["luya", "ginger"],
    "lingga": ["lingga", "sesame"], "sesame": ["lingga", "sesame"],
    "kangkong": ["kangkong", "water spinach", "swamp cabbage"], "water spinach": ["kangkong"],
    "malunggay": ["malunggay", "moringa"], "moringa": ["malunggay", "moringa"],
    "pechay": ["pechay", "native cabbage", "snow cabbage", "bok choy"], "bok choy": ["pechay", "bok choy"],
    "repolyo": ["repolyo", "cabbage"], "cabbage": ["repolyo", "cabbage"],
    "saluyot": ["saluyot", "jute mallow"],
    "alugbati": ["alugbati", "malabar spinach", "vine spinach"],
    "talong": ["talong", "eggplant"], "eggplant": ["talong", "eggplant"],
    "ampalaya": ["ampalaya", "bitter melon", "bitter gourd"], "bitter melon": ["ampalaya", "bitter melon"],
    "sayote": ["sayote", "chayote"], "chayote": ["sayote", "chayote"],
    "sili": ["sili", "chili", "siling haba", "siling labuyo", "bird's eye chili", "lara"],
    "lara": ["lara", "siling bell", "bell pepper", "sili"], "bell pepper": ["siling bell", "bell pepper", "lara"],
    "okra": ["okra", "lady's finger"],
    "kamansi": ["kamansi", "breadnut"],
    "rimas": ["rimas", "breadfruit"],
    "langka": ["langka", "jackfruit", "green jackfruit"], "jackfruit": ["langka", "jackfruit"],
    "papaya": ["papaya", "green papaya"],
    "kamote": ["kamote", "sweet potato"], "sweet potato": ["kamote", "sweet potato"],
    "gabi": ["gabi", "taro", "taro leaves", "dahon ng gabi"], "taro": ["gabi", "taro"],
    "ube": ["ube", "purple yam"], "purple yam": ["ube", "purple yam"],
    "kamoteng kahoy": ["kamoteng kahoy", "cassava", "manioc"], "cassava": ["kamoteng kahoy", "cassava"],
    "munggo": ["munggo", "mung bean", "toge", "mung bean sprouts"],
    "himbabao": ["himbabao", "birch flower", "alokon"],
    "kabute": ["kabute", "mushroom", "straw mushroom", "oyster mushroom"], "mushroom": ["kabute", "mushroom"],
    "mais": ["mais", "corn", "maize"], "corn": ["mais", "corn"],
    "brokuli": ["brokuli", "broccoli"], "broccoli": ["brokuli", "broccoli"],
    "kuliplor": ["kuliplor", "cauliflower"], "cauliflower": ["kuliplor", "cauliflower"],
    "karot": ["karot", "carrot"], "carrot": ["karot", "carrot"],

    # ─── FRUITS ───
    "mangga": ["mangga", "mango", "carabao", "pico", "indian"], "mango": ["mangga", "mango"],
    "saging": ["saging", "banana", "saba", "lakatan", "latundan", "saging a maiba"], "banana": ["saging", "banana"],
    "pinya": ["pinya", "pineapple"], "pineapple": ["pinya", "pineapple"],
    "pakwan": ["pakwan", "watermelon"], "watermelon": ["pakwan", "watermelon"],
    "melon": ["melon", "cantaloupe", "honeydew"],
    "buko": ["buko", "niyog", "coconut"], "coconut": ["buko", "niyog", "coconut"],
    "dalandan": ["dalandan", "philippine orange"], "orange": ["dalandan", "orange"],
    "suha": ["suha", "lukban", "pomelo"], "pomelo": ["suha", "pomelo"],
    "kalamansi": ["kalamansi", "philippine lime", "calamondin"],
    "lansones": ["lansones", "langsat"],
    "rambutan": ["rambutan"],
    "santol": ["santol", "cotton fruit"],
    "sampalok": ["sampalok", "tamarind"], "tamarind": ["sampalok", "tamarind"],
    "bayabas": ["bayabas", "guava"], "guava": ["bayabas", "guava"],
    "guyabano": ["guyabano", "soursop"], "soursop": ["guyabano", "soursop"],
    "durian": ["durian"],
    "mangostan": ["mangostan", "mangosteen"],
    "presa": ["presa", "strawberry"], "strawberry": ["presa", "strawberry"],
    "ubas": ["ubas", "grapes"], "grapes": ["ubas", "grapes"],

    # ─── SEAFOODS ───
    "bangus": ["bangus", "milkfish"], "milkfish": ["bangus", "milkfish"],
    "tilapia": ["tilapia"],
    "galunggong": ["galunggong", "round scad"],
    "tangigue": ["tangigue", "spanish mackerel"],
    "lapu-lapu": ["lapu-lapu", "grouper"], "grouper": ["lapu-lapu", "grouper"],
    "maya-maya": ["maya-maya", "red snapper"], "snapper": ["maya-maya", "red snapper"],
    "dilis": ["dilis", "anchovy"], "anchovy": ["dilis", "anchovy"],
    "sardinas": ["sardinas", "tamban", "sardine"], "sardine": ["sardinas", "tamban", "sardine"],
    "pating": ["pating", "shark"], "shark": ["pating", "shark"],
    "pagi": ["pagi", "ray", "stingray"],
    "halaan": ["halaan", "manila clams", "clams"], "clams": ["halaan", "tulya", "clams"],
    "kuhol": ["kuhol", "apple snail", "golden snail"],
    "tahong": ["tahong", "green mussel", "mussel"], "mussel": ["tahong", "mussel"],
    "talaba": ["talaba", "oyster"], "oyster": ["talaba", "oyster"],
    "sugpo": ["sugpo", "tiger prawn", "giant prawn", "shrimp", "hipon"],
    "hipon": ["hipon", "shrimp", "white shrimp", "suwahe", "sugpo"], "shrimp": ["hipon", "sugpo", "shrimp"],
    "alimasag": ["alimasag", "blue swimmer crab", "crab"],
    "alimango": ["alimango", "mud crab", "crab"], "crab": ["alimasag", "alimango", "talangka", "crab"],
    "pusit": ["pusit", "squid", "lumot"], "squid": ["pusit", "squid"],
    "pugita": ["pugita", "octopus", "kugita"], "octopus": ["pugita", "octopus"],
    "tuyo": ["tuyo", "dried salted fish", "dried fish"], "dried fish": ["tuyo", "daing"],
    "daing": ["daing", "sun-dried fish"],
    "tinapa": ["tinapa", "smoked fish"], "smoked fish": ["tinapa", "smoked fish"],
    "bagoong": ["bagoong", "alamang", "bagoong isda", "fermented shrimp paste"],
    "patis": ["patis", "fish sauce"],
    "burong isda": ["burong isda", "fermented fish with rice", "buro"],

    # ─── CONDIMENTS & SEASONINGS ───
    "mantika": ["mantika", "oil", "cooking oil"],
    "oil": ["mantika", "oil", "cooking oil"],
    "soya sauce": ["toyo", "soy sauce"],
    "toyo": ["toyo", "soy sauce"],
    "vinegar": ["suka", "vinegar"],
    "suka": ["suka", "vinegar"],
    "bagoong": ["bagoong", "alamang", "bagoong isda", "fermented shrimp paste"],
    "salt": ["asin", "salt"],
    "asin": ["asin", "salt"],
    "sesame oil": ["lingga", "sesame oil"], "lingga": ["lingga", "sesame oil"],
    "oyster sauce": ["siling bell", "bell pepper", "lara", "oyster sauce"],
    "paminta": ["paminta", "peppercorn", "black pepper"], 
    "peppercorn": ["paminta", "peppercorn"],
    "bay leaf": ["dahon ng laurel", "laurel", "bay leaf"], 
    "dahon ng laurel": ["dahon ng laurel", "bay leaf"],
    "rosemary": ["rosemary"],
    "thyme": ["thyme"],
    "cumin": ["cumin"],
    "paprika": ["paprika"],
    "chili powder": ["chili powder"],
    "knorr cubes": ["knorr cubes", "seasoning cubes"],
    "harina": ["harina", "flour"],
    "flour": ["harina", "flour"],
    "sugar": ["asukal", "sugar"],
    "asukal": ["asukal", "sugar"],
    "MSG": ["bitsin", "monosodium glutamate", "msg"],
    "bitsin": ["bitsin", "monosodium glutamate", "msg"]

}

# ─── Language Switcher ──────────────────────────────────────────────────────

@main_bp.route('/set-lang/<lang>')
def set_language(lang):
    if lang in ('en', 'tl'):
        session['lang'] = lang
    return redirect(request.referrer or url_for('main.index'))

# ─── Context Processor ────────────────────────────────────────────────────────

@main_bp.app_context_processor
def inject_globals():
    return {'now': datetime.now(timezone.utc)}

# ─── Main Routes ──────────────────────────────────────────────────────────────

@main_bp.route('/')
def index():
    products = Product.query.filter_by(is_available=True).order_by(Product.created_at.desc()).limit(8).all()
    categories = Category.query.all()
    top_farmers = User.query.filter_by(role='farmer', is_active=True).limit(6).all()
    return render_template('index.html', products=products, categories=categories, top_farmers=top_farmers)

# ─── 🔍 SMART SEARCH MAIN PAGE (Hybrid AI + Dictionary Engine) ────────────────

@main_bp.route('/search')
def search():
    raw_query = request.args.get('q', '').strip()
    
    if raw_query:
        new_log = SearchLog(keyword=raw_query, timestamp=datetime.now(timezone.utc))
        db.session.add(new_log)
        db.session.commit()

        clean_query = raw_query.lower().replace('kgs', '').replace('kg', '').replace('of', '').strip()
        search_keywords = [clean_query]

        # 🤖 STEP 1: AI INTENT & RECIPE ANALYZER
        try:
            if len(clean_query) >= 3:
                ai_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are the HarvestIQ Smart Search Engine. If the user inputs a Filipino dish, output a comma-separated list of ALL raw ingredients needed to cook it. If the dish is fried, you MUST include 'mantika, oil'. Example: 'torta' -> 'talong, eggplant, itlog, egg, bawang, mantika, oil'. If it's a single item, translate it. Output ONLY keywords."},
                        {"role": "user", "content": clean_query}
                    ],
                    max_tokens=80,
                    temperature=0.3,
                    timeout=4
                )
                
                ai_content = ai_response.choices[0].message.content
                translated_keys = [k.strip().lower() for k in ai_content.split(',')]
                search_keywords.extend(translated_keys)
                print(f"DEBUG RECIPE AI: '{clean_query}' -> extracted ingredients: {translated_keys}")
        except Exception as e:
            print(f"OpenAI Recipe Search Error: {e}")

        # 🟢 STEP 2: FORCED MANUAL DICTIONARY LOOKUP
        # Babasahin nito ang malaking listahan mo KAHIT nag-tagumpay ang AI.
        for key, ingredients in TRANSLATION_MAP.items():
            if clean_query in key or key in clean_query:
                search_keywords.extend(ingredients)

        # Remove duplicates
        search_keywords = list(set(search_keywords))

        # 🟢 MULTI-COLUMN FILTERING GAMIT ANG LAHAT NG SANGKAP
        conditions = []
        for k in search_keywords:
            conditions.append(Product.name.ilike(f'%{k}%'))
            conditions.append(Product.location.ilike(f'%{k}%'))
            conditions.append(Product.province.ilike(f'%{k}%'))
            conditions.append(cast(Product.stock_quantity, String).ilike(f'%{k}%'))

        products = Product.query.filter(or_(*conditions)).all()
    else:
        products = Product.query.all()

    return render_template('search/results.html', products=products, query=raw_query)

# ─── 🤖 AI-POWERED AUTO-SUGGEST API (Dropdown Suggestions) ──────────────────

@main_bp.route('/search-suggestions')
def search_suggestions():
    raw_query = request.args.get('q', '').strip().lower()
    if not raw_query or len(raw_query) < 2:
        return jsonify([])

    results = []
    search_keywords = [raw_query.replace('kgs', '').replace('kg', '').strip()]
    
    # 🤖 STEP 1: AI SUGGESTION ENGINE
    try:
        if len(raw_query) >= 3:
            ai_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are the HarvestIQ Smart Search Engine. If the user inputs a Filipino dish, output a comma-separated list of ALL raw ingredients needed to cook it. If the dish is fried, you MUST include 'mantika, oil'. Example: 'torta' -> 'talong, eggplant, itlog, egg, bawang, mantika, oil'. If it's a single item, translate it. Output ONLY keywords."},
                    {"role": "user", "content": raw_query}
                ],
                max_tokens=80,
                temperature=0.3,
                timeout=4
            )
            
            ai_content = ai_response.choices[0].message.content
            translated_keys = [k.strip().lower() for k in ai_content.split(',')]
            search_keywords.extend(translated_keys)
            print(f"DEBUG SUGGESTION AI: '{raw_query}' -> extracted ingredients: {translated_keys}")
            
    except Exception as e:
        print(f"OpenAI Suggestion Error: {e}")
        
    # 🟢 STEP 2: FORCED MANUAL DICTIONARY LOOKUP
    clean_q = raw_query.replace('kgs', '').replace('kg', '').strip()
    for key, ingredients in TRANSLATION_MAP.items():
        if clean_q in key or key in clean_q:
            search_keywords.extend(ingredients)

    # Remove duplicates
    search_keywords = list(set(search_keywords))

    conditions = []
    for k in search_keywords:
        conditions.append(Product.name.ilike(f'%{k}%'))
        conditions.append(Product.location.ilike(f'%{k}%'))
        conditions.append(Product.province.ilike(f'%{k}%'))
        conditions.append(cast(Product.stock_quantity, String).ilike(f'%{k}%'))

    standard_products = Product.query.filter(or_(*conditions)).limit(8).all()
    seen_locations = set()

    for p in standard_products:
        clean_query = raw_query.replace('kgs', '').replace('kg', '').strip()
        if p.location and p.location.lower() not in seen_locations and clean_query in p.location.lower():
            results.append({'type': 'location', 'text': p.location, 'icon': 'fa-map-marker-alt'})
            seen_locations.add(p.location.lower())
        
        results.append({
            'type': 'ai-suggestion', 
            'text': p.name, 
            'subtext': f"{p.stock_quantity}kg available in {p.location} • Match Found", 
            'icon': 'fa-utensils' if len(search_keywords) > 2 else 'fa-leaf'
        })
        
    return jsonify(results[:10])

# ─── Buyer Dashboard ──────────────────────────────────────────────────────────

@main_bp.route('/buyer/dashboard')
@login_required
def buyer_dashboard():
    trending_searches = db.session.query(SearchLog.keyword, func.count(SearchLog.id).label('total')).group_by(SearchLog.keyword).order_by(func.count(SearchLog.id).desc()).limit(8).all()
    total_region_supply = db.session.query(func.sum(Product.stock_quantity)).scalar() or 0

    from app.models.cart import CartItem
    cart_count = CartItem.query.filter_by(user_id=current_user.id).count()

    products = Product.query.filter_by(is_available=True).limit(8).all()
    
    from app.models.order import Order 
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()

    return render_template(
        'dashboard/buyer.html', 
        trending_searches=trending_searches,
        total_supply=total_region_supply,
        products=products,
        orders=orders,
        cart_count=cart_count
    )

# ─── Other Routes & Error Handlers ────────────────────────────────────────────

@main_bp.route('/about')
def about(): return render_template('about.html')

@main_bp.route('/contact')
def contact(): return render_template('contact.html')

@main_bp.app_errorhandler(404)
def not_found(e): return render_template('errors/404.html'), 404

@main_bp.app_errorhandler(500)
def server_error(e): return render_template('errors/500.html'), 500