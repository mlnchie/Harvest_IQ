from app import db

from datetime import datetime





# ─────────────────────────────────────────────

# ORDER MODEL

# ─────────────────────────────────────────────

class Order(db.Model):

    __tablename__ = "orders"



    # PRIMARY KEY

    id = db.Column(db.Integer, primary_key=True)



    # ─────────────────────────────

    # BUYER RELATION

    # ─────────────────────────────

    buyer_id = db.Column(

        db.Integer,

        db.ForeignKey("users.id"),

        nullable=False

    )



    # Relationship → allows current_user.orders

    buyer = db.relationship(

        "User",

        backref="orders",

        lazy=True

    )



    # ─────────────────────────────

    # ORDER INFO

    # ─────────────────────────────

    status = db.Column(

        db.String(30),

        default="pending"

    )

    # pending / confirmed / processing / shipped / delivered / cancelled / refunded



    total_amount = db.Column(

        db.Float,

        nullable=False

    )



    delivery_fee = db.Column(

        db.Float,

        default=0

    )



    shipping_address = db.Column(

        db.Text,

        nullable=False

    )



    payment_method = db.Column(

        db.String(50),

        default="cod"

    )

    # cod / gcash / maya / card



    payment_status = db.Column(

        db.String(30),

        default="unpaid"

    )

    # unpaid / paid / refunded



    payment_reference = db.Column(

        db.String(200)

    )



    notes = db.Column(

        db.Text

    )



    # ─────────────────────────────

    # TIMESTAMPS

    # ─────────────────────────────

    created_at = db.Column(

        db.DateTime,

        default=datetime.utcnow

    )



    updated_at = db.Column(

        db.DateTime,

        default=datetime.utcnow,

        onupdate=datetime.utcnow

    )



    # ─────────────────────────────

    # RELATIONSHIPS

    # ─────────────────────────────

    items = db.relationship(

        "OrderItem",

        backref="order",

        lazy=True,

        cascade="all, delete-orphan"

    )



    # ─────────────────────────────

    # COMPUTED

    # ─────────────────────────────

    @property

    def item_count(self):

        return sum(item.quantity for item in self.items)



    @property

    def grand_total(self):

        return self.total_amount + (self.delivery_fee or 0)



    def __repr__(self):

        return f"<Order #{self.id} - {self.status}>"







# ─────────────────────────────────────────────

# ORDER ITEMS

# ─────────────────────────────────────────────

class OrderItem(db.Model):

    __tablename__ = "order_items"



    id = db.Column(db.Integer, primary_key=True)



    order_id = db.Column(

        db.Integer,

        db.ForeignKey("orders.id"),

        nullable=False

    )



    product_id = db.Column(

        db.Integer,

        db.ForeignKey("products.id"),

        nullable=False

    )



    quantity = db.Column(

        db.Integer,

        nullable=False

    )



    unit_price = db.Column(

        db.Float,

        nullable=False

    )



    # ─────────────────────────────

    # RELATIONSHIP → Product

    # ─────────────────────────────

    product = db.relationship(

        "Product",

        backref="order_items",

        lazy=True

    )



    # ─────────────────────────────

    # COMPUTED

    # ─────────────────────────────

    @property

    def subtotal(self):

        return self.quantity * self.unit_price



    def __repr__(self):

        return f"<OrderItem Order:{self.order_id} Product:{self.product_id}>"