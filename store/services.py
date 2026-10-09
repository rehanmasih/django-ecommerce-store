"""Order creation. Everything happens in one database transaction."""
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F

from .cart import shipping_for
from .models import Order, OrderItem, Product


class OrderError(Exception):
    """Raised when an order can't be completed. The transaction is rolled back."""


@transaction.atomic
def create_order(user, cart, customer_data):
    items = list(cart)
    if not items:
        raise OrderError("Your cart is empty.")

    order = Order.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        payment_method=settings.CHECKOUT_PAYMENT_METHOD,
        **customer_data,
    )
    subtotal = Decimal("0.00")
    for item in items:
        product, qty = item["product"], item["quantity"]
        # Atomic conditional decrement: succeeds only if enough stock remains right now.
        updated = Product.objects.filter(pk=product.pk, stock_quantity__gte=qty).update(
            stock_quantity=F("stock_quantity") - qty
        )
        if not updated:
            available = Product.objects.filter(pk=product.pk).values_list("stock_quantity", flat=True).first() or 0
            raise OrderError(f"Sorry, only {available} of {product.name} are available. Your order was not placed.")
        line = OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,  # snapshot
            price=item["unit_price"],  # snapshot
            quantity=qty,
        )
        subtotal += line.subtotal

    order.subtotal = subtotal
    order.shipping_cost = shipping_for(subtotal)
    order.total_price = order.subtotal + order.shipping_cost
    order.save(update_fields=["subtotal", "shipping_cost", "total_price", "updated_at"])
    return order
