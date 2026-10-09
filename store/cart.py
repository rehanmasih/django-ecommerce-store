"""Session-based shopping cart.

The cart lives in the Django session as {product_id: quantity}. Prices are never stored
in the session; they are read from the database every time so totals are always current.
"""
from decimal import Decimal

from django.conf import settings

from .models import Product

CART_SESSION_KEY = "cart"


def shipping_for(subtotal):
    """Flat-rate shipping, waived above FREE_SHIPPING_THRESHOLD (if > 0). Empty carts pay nothing."""
    if subtotal <= 0:
        return Decimal("0.00")
    threshold = settings.FREE_SHIPPING_THRESHOLD
    if threshold and subtotal >= threshold:
        return Decimal("0.00")
    return settings.SHIPPING_FLAT_RATE


class Cart:
    def __init__(self, request):
        self.session = request.session
        self.cart = self.session.get(CART_SESSION_KEY, {})
        self._items = None

    # ---- persistence
    def _save(self):
        self.session[CART_SESSION_KEY] = self.cart
        self.session.modified = True
        self._items = None

    # ---- mutation
    def quantity_of(self, product_id):
        return self.cart.get(str(product_id), 0)

    def add(self, product, quantity=1, override=False):
        """Add/set a quantity. Returns an error message, or None on success."""
        if not product.is_in_stock:
            return f"{product.name} is out of stock."
        new_qty = quantity if override else self.quantity_of(product.pk) + quantity
        if new_qty < 1:
            return "Please enter a valid quantity."
        if new_qty > product.stock_quantity:
            n = product.stock_quantity
            return f"Only {n} item{'s are' if n != 1 else ' is'} available."
        self.cart[str(product.pk)] = new_qty
        self._save()
        return None

    def remove(self, product_id):
        if self.cart.pop(str(product_id), None) is not None:
            self._save()

    def clear(self):
        self.cart = {}
        self.session.pop(CART_SESSION_KEY, None)
        self.session.modified = True
        self._items = None

    # ---- reading
    def _load(self):
        if self._items is None:
            ids = [int(pk) for pk in self.cart]
            products = Product.objects.select_related("category").in_bulk(ids)
            items, dirty = [], False
            for pk_str, qty in list(self.cart.items()):
                product = products.get(int(pk_str))
                if product is None:  # product was deleted
                    del self.cart[pk_str]
                    dirty = True
                    continue
                price = product.current_price
                items.append({"product": product, "quantity": qty, "unit_price": price, "total_price": price * qty})
            if dirty:
                self._save()
            self._items = items
        return self._items

    def __iter__(self):
        return iter(self._load())

    def __len__(self):
        return sum(self.cart.values())

    @property
    def subtotal(self):
        return sum((i["total_price"] for i in self._load()), Decimal("0.00"))

    @property
    def shipping(self):
        return shipping_for(self.subtotal)

    @property
    def total(self):
        return self.subtotal + self.shipping

    def stock_problems(self):
        """List of human-readable problems (item no longer available in that quantity)."""
        problems = []
        for item in self._load():
            p, q = item["product"], item["quantity"]
            if not p.is_in_stock:
                problems.append(f"{p.name} is now out of stock. Please remove it from your cart.")
            elif q > p.stock_quantity:
                problems.append(f"Only {p.stock_quantity} of {p.name} are available. Please update your cart.")
        return problems
