from decimal import Decimal
from functools import wraps
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Case, Count, DecimalField, F, OuterRef, Subquery, Sum, When
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .cart import Cart
from .forms import CheckoutForm, LoginForm, ProductFilterForm, ProfileForm, RegisterForm, UserUpdateForm
from .models import Category, Order, OrderItem, Product, Profile
from .services import OrderError, create_order

User = get_user_model()

SORT_ORDERING = {
    "newest": ("-created_at", "-id"),
    "price_asc": ("effective_price", "id"),
    "price_desc": ("-effective_price", "id"),
    "name_asc": ("name", "id"),
    "name_desc": ("-name", "-id"),
}


def _next_url(request, fallback):
    """Redirect back to where the customer came from, but only to our own site."""
    target = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return target
    return fallback


def staff_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


# ------------------------------------------------------------------ catalogue
def home(request):
    cover = Product.objects.filter(category=OuterRef("pk")).order_by("-is_featured", "-created_at").values("image")[:1]
    categories = Category.objects.annotate(product_total=Count("products"), cover=Subquery(cover))
    featured = Product.objects.filter(is_featured=True).select_related("category")[:8]
    latest = Product.objects.select_related("category")[:8]
    return render(request, "store/home.html", {
        "categories": categories,
        "featured_products": featured,
        "latest_products": latest,
        "hero_products": [p for p in featured if p.image][:3],
    })


def product_list(request, slug=None):
    form = ProductFilterForm(request.GET or None)
    form.is_valid() if form.is_bound else None  # populates cleaned_data (valid fields only) even on partial errors
    cleaned = getattr(form, "cleaned_data", {}) if form.is_bound else {}

    category = None
    if slug:
        category = get_object_or_404(Category, slug=slug)
    elif cleaned.get("category"):
        category = Category.objects.filter(slug=cleaned["category"]).first()

    effective = Case(
        When(discount_price__isnull=False, then=F("discount_price")),
        default=F("price"),
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )
    products = Product.objects.select_related("category").annotate(effective_price=effective)

    query = (cleaned.get("q") or "").strip()
    if query:
        products = products.filter(name__icontains=query)
    if category:
        products = products.filter(category=category)
    if cleaned.get("min_price") is not None:
        products = products.filter(effective_price__gte=cleaned["min_price"])
    if cleaned.get("max_price") is not None:
        products = products.filter(effective_price__lte=cleaned["max_price"])

    sort = cleaned.get("sort") or "newest"
    products = products.order_by(*SORT_ORDERING.get(sort, SORT_ORDERING["newest"]))

    page = Paginator(products, settings.PRODUCTS_PER_PAGE).get_page(request.GET.get("page"))
    params = {k: v for k, v in request.GET.items() if k != "page" and v}
    return render(request, "store/product_list.html", {
        "form": form,
        "page_obj": page,
        "products": page.object_list,
        "categories": Category.objects.all(),
        "active_category": category,
        "query": query,
        "sort": sort,
        "sort_choices": ProductFilterForm.SORT_CHOICES,
        "querystring": urlencode(params),
        "min_price": request.GET.get("min_price", ""),
        "max_price": request.GET.get("max_price", ""),
    })


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related("category"), slug=slug)
    related = Product.objects.filter(category=product.category).exclude(pk=product.pk).select_related("category")[:4]
    return render(request, "store/product_detail.html", {
        "product": product,
        "related_products": related,
        "in_cart": Cart(request).quantity_of(product.pk),
    })


# ------------------------------------------------------------------ cart
def cart_detail(request):
    return render(request, "store/cart.html", {"cart": Cart(request)})


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    try:
        quantity = int(request.POST.get("quantity", "1"))
    except ValueError:
        quantity = 0
    if quantity < 1:
        messages.error(request, "Please enter a valid quantity.")
    else:
        error = Cart(request).add(product, quantity)
        if error:
            messages.error(request, error)
        else:
            messages.success(request, "Product added to cart.")
    return redirect(_next_url(request, reverse("cart_detail")))


@require_POST
def cart_update(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    cart = Cart(request)
    current = cart.quantity_of(product.pk)
    action = request.POST.get("action", "set")
    if action == "increase":
        new_qty = current + 1
    elif action == "decrease":
        new_qty = current - 1
    else:
        try:
            new_qty = int(request.POST.get("quantity", ""))
        except ValueError:
            messages.error(request, "Please enter a valid quantity.")
            return redirect("cart_detail")
    if new_qty < 1:
        cart.remove(product.pk)
        messages.success(request, "Product removed from cart.")
    else:
        error = cart.add(product, new_qty, override=True)
        messages.error(request, error) if error else messages.success(request, "Cart updated.")
    return redirect("cart_detail")


@require_POST
def cart_remove(request, product_id):
    Cart(request).remove(product_id)
    messages.success(request, "Product removed from cart.")
    return redirect("cart_detail")


# ------------------------------------------------------------------ checkout & orders
@login_required
def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.info(request, "Your cart is empty. Add something before checking out.")
        return redirect("cart_detail")
    problems = cart.stock_problems()
    if problems:
        for problem in problems:
            messages.error(request, problem)
        return redirect("cart_detail")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                order = create_order(request.user, cart, form.cleaned_data)
            except OrderError as exc:
                messages.error(request, str(exc))
                return redirect("cart_detail")
            cart.clear()
            messages.success(request, "Order placed successfully.")
            return redirect("order_confirmation", pk=order.pk)
        messages.error(request, "Please correct the highlighted fields.")
    else:
        user = request.user
        profile = Profile.objects.filter(user=user).first()
        form = CheckoutForm(initial={
            "customer_name": user.get_full_name() or user.username,
            "email": user.email,
            "phone": getattr(profile, "phone", ""),
            "address": getattr(profile, "address", ""),
            "city": getattr(profile, "city", ""),
            "postal_code": getattr(profile, "postal_code", ""),
        })
    return render(request, "store/checkout.html", {"form": form, "cart": cart, "payment_method": settings.CHECKOUT_PAYMENT_METHOD})


def _own_order(request, pk):
    # Filtering by user means another customer's order is simply "not found".
    return get_object_or_404(Order.objects.prefetch_related("items"), pk=pk, user=request.user)


@login_required
def order_confirmation(request, pk):
    return render(request, "store/order_confirmation.html", {"order": _own_order(request, pk)})


@login_required
def order_list(request):
    orders = (Order.objects.filter(user=request.user)
              .annotate(item_count=Sum("items__quantity")).order_by("-created_at", "-id"))
    page = Paginator(orders, 10).get_page(request.GET.get("page"))
    return render(request, "store/order_list.html", {"page_obj": page, "orders": page.object_list})


@login_required
def order_detail(request, pk):
    order = _own_order(request, pk)
    steps = [Order.Status.PENDING, Order.Status.PROCESSING, Order.Status.SHIPPED, Order.Status.DELIVERED]
    cancelled = order.status == Order.Status.CANCELLED
    reached = steps.index(order.status) if not cancelled else -1
    timeline = [{"label": s.label, "done": i <= reached, "current": i == reached} for i, s in enumerate(steps)]
    return render(request, "store/order_detail.html", {"order": order, "timeline": timeline, "cancelled": cancelled})


# ------------------------------------------------------------------ accounts
class StoreLoginView(LoginView):
    template_name = "store/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class StoreLogoutView(LogoutView):
    """POST-only logout (Django default) that returns to the home page."""


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="store.backends.EmailOrUsernameBackend")
        messages.success(request, f"Welcome, {user.username}! Your account has been created.")
        return redirect("home")
    return render(request, "store/register.html", {"form": form})


@login_required
def profile(request):
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)
    user_form = UserUpdateForm(request.POST or None, instance=request.user, prefix="user")
    profile_form = ProfileForm(request.POST or None, instance=profile_obj, prefix="profile")
    if request.method == "POST":
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("profile")
        messages.error(request, "Please correct the highlighted fields.")
    recent = Order.objects.filter(user=request.user)[:5]
    return render(request, "store/profile.html", {"user_form": user_form, "profile_form": profile_form, "recent_orders": recent})


# ------------------------------------------------------------------ management dashboard
@staff_required
def dashboard(request):
    active = Order.objects.exclude(status=Order.Status.CANCELLED)
    revenue = active.aggregate(total=Sum("total_price"))["total"] or Decimal("0.00")
    counts = dict(Order.objects.values_list("status").annotate(n=Count("id")))
    threshold = settings.LOW_STOCK_THRESHOLD
    return render(request, "store/dashboard.html", {
        "total_products": Product.objects.count(),
        "total_orders": Order.objects.count(),
        "total_customers": User.objects.filter(is_staff=False).count(),
        "total_revenue": revenue,
        "recent_orders": Order.objects.select_related("user")[:6],
        "low_stock": Product.objects.filter(stock_quantity__lte=threshold).select_related("category").order_by("stock_quantity", "name")[:10],
        "low_stock_threshold": threshold,
        "best_sellers": (
            OrderItem.objects.exclude(order__status=Order.Status.CANCELLED)
            .values("product_name").annotate(units=Sum("quantity")).order_by("-units", "product_name")[:5]
        ),
        "status_summary": [(s.label, counts.get(s.value, 0), s.value) for s in Order.Status],
    })
