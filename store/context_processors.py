from django.conf import settings

from .cart import Cart
from .models import Category


def store_context(request):
    return {
        "STORE_NAME": settings.STORE_NAME,
        "CURRENCY": settings.CURRENCY_SYMBOL,
        "SHIPPING_FLAT_RATE": settings.SHIPPING_FLAT_RATE,
        "FREE_SHIPPING_THRESHOLD": settings.FREE_SHIPPING_THRESHOLD,
        "nav_categories": Category.objects.all(),
        "cart_count": len(Cart(request)),
    }
