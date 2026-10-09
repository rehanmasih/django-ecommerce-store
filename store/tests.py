import io
import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .cart import Cart
from .models import Category, Order, OrderItem, Product
from .services import OrderError, create_order

User = get_user_model()

CHECKOUT_DATA = {
    "customer_name": "Ada Lovelace", "email": "ada@example.com", "phone": "+1 555 123 4567",
    "address": "12 Analytical St", "city": "London", "postal_code": "N1 9GU",
}


def make_product(name="Wireless Headphones", price="100.00", discount=None, stock=10, category=None, **kw):
    category = category or Category.objects.get_or_create(name="Electronics")[0]
    return Product.objects.create(
        name=name, description="A test product.", price=Decimal(price),
        discount_price=Decimal(discount) if discount else None, stock_quantity=stock, category=category, **kw)


def png_bytes(fmt="PNG"):
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), "red").save(buf, fmt)
    return buf.getvalue()


class ProductModelTests(TestCase):
    def test_slug_generated_and_unique(self):
        a, b = make_product("Same Name"), make_product("Same Name")
        self.assertEqual(a.slug, "same-name")
        self.assertEqual(b.slug, "same-name-2")

    def test_str_and_absolute_url(self):
        p = make_product("Nice Lamp")
        self.assertEqual(str(p), "Nice Lamp")
        self.assertEqual(p.get_absolute_url(), "/products/nice-lamp/")

    def test_discount_percentage_is_calculated(self):
        p = make_product(price="100", discount="80")
        self.assertTrue(p.has_discount)
        self.assertEqual(p.discount_percent, 20)
        self.assertEqual(p.current_price, Decimal("80"))
        self.assertEqual(p.savings, Decimal("20"))

    def test_no_discount(self):
        p = make_product(price="100")
        self.assertFalse(p.has_discount)
        self.assertEqual(p.discount_percent, 0)
        self.assertEqual(p.current_price, Decimal("100"))

    def test_discount_must_be_lower_than_price(self):
        p = Product(name="Bad", description="x", price=Decimal("50"), discount_price=Decimal("60"),
                    category=Category.objects.create(name="C"))
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_database_constraint_blocks_bad_discount(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_product(price="50", discount="60")

    def test_stock_status(self):
        self.assertEqual(make_product("A", stock=50).stock_status, "In Stock")
        self.assertEqual(make_product("B", stock=3).stock_status, "Low Stock")
        self.assertEqual(make_product("C", stock=0).stock_status, "Out of Stock")

    def test_image_url_falls_back_to_placeholder(self):
        self.assertIn("placeholder.svg", make_product().image_url)

    def test_invalid_image_rejected(self):
        p = make_product()
        p.image = SimpleUploadedFile("evil.jpg", b"not really an image", content_type="image/jpeg")
        with self.assertRaises(ValidationError) as ctx:
            p.full_clean()
        self.assertIn("image", ctx.exception.message_dict)

    def test_wrong_extension_rejected(self):
        p = make_product()
        p.image = SimpleUploadedFile("shell.php", png_bytes(), content_type="image/png")
        with self.assertRaises(ValidationError):
            p.full_clean()

    @override_settings(MAX_IMAGE_UPLOAD_MB=0)
    def test_oversized_image_rejected(self):
        p = make_product()
        p.image = SimpleUploadedFile("big.png", png_bytes(), content_type="image/png")
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_valid_image_accepted(self):
        p = make_product()
        p.image = SimpleUploadedFile("ok.png", png_bytes(), content_type="image/png")
        p.full_clean()  # no error


class CategoryTests(TestCase):
    def test_slug_and_str(self):
        c = Category.objects.create(name="Home & Kitchen")
        self.assertEqual(c.slug, "home-kitchen")
        self.assertEqual(str(c), "Home & Kitchen")

    def test_category_page_filters_products(self):
        e, c = Category.objects.create(name="Electronics"), Category.objects.create(name="Clothing")
        make_product("Laptop", category=e)
        make_product("Hoodie", category=c)
        r = self.client.get(reverse("category_detail", args=["clothing"]))
        self.assertContains(r, "Hoodie")
        self.assertNotContains(r, "Laptop")

    def test_unknown_category_404(self):
        self.assertEqual(self.client.get(reverse("category_detail", args=["nope"])).status_code, 404)

    def test_category_query_param_filter(self):
        e, c = Category.objects.create(name="Electronics"), Category.objects.create(name="Clothing")
        make_product("Laptop", category=e)
        make_product("Hoodie", category=c)
        r = self.client.get(reverse("product_list"), {"category": "electronics"})
        self.assertContains(r, "Laptop")
        self.assertNotContains(r, "Hoodie")


class CatalogueTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.phone = make_product("Smartphone", price="500", discount="400")
        make_product("Phone Case", price="15")
        make_product("Wireless Phone Charger", price="30")
        make_product("Blender", price="60")

    def test_home_page(self):
        make_product("Star Item", is_featured=True)
        r = self.client.get(reverse("home"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Featured Products")
        self.assertContains(r, "Latest Products")
        self.assertContains(r, "Star Item")

    def test_partial_search(self):
        r = self.client.get(reverse("product_list"), {"q": "phone"})
        names = {p.name for p in r.context["products"]}
        self.assertEqual(names, {"Smartphone", "Phone Case", "Wireless Phone Charger"})

    def test_search_no_results(self):
        r = self.client.get(reverse("product_list"), {"q": "zzzz"})
        self.assertContains(r, "No Products Found")

    def test_search_is_safe_with_odd_input(self):
        r = self.client.get(reverse("product_list"), {"q": "'; DROP TABLE store_product; --"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Product.objects.count(), 4)

    def test_price_filter_uses_discounted_price(self):
        r = self.client.get(reverse("product_list"), {"min_price": "350", "max_price": "450"})
        self.assertEqual([p.name for p in r.context["products"]], ["Smartphone"])

    def test_price_filter_invalid_values_do_not_break(self):
        r = self.client.get(reverse("product_list"), {"min_price": "abc", "max_price": ""})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["products"]), 4)

    def test_price_filter_min_greater_than_max_is_ignored(self):
        r = self.client.get(reverse("product_list"), {"min_price": "100", "max_price": "10"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["products"]), 4)
        self.assertContains(r, "Maximum price must be greater")

    def test_sorting(self):
        def names(sort):
            return [p.name for p in self.client.get(reverse("product_list"), {"sort": sort}).context["products"]]
        self.assertEqual(names("price_asc")[0], "Phone Case")
        self.assertEqual(names("price_desc"), ["Smartphone", "Blender", "Wireless Phone Charger", "Phone Case"])
        self.assertEqual(names("name_asc")[0], "Blender")
        self.assertEqual(names("name_desc")[0], "Wireless Phone Charger")
        self.assertEqual(names("newest")[0], "Blender")

    def test_pagination(self):
        for i in range(15):
            make_product(f"Bulk {i}")
        r = self.client.get(reverse("product_list"))
        self.assertEqual(len(r.context["products"]), 12)
        self.assertTrue(r.context["page_obj"].has_next())
        r2 = self.client.get(reverse("product_list"), {"page": 2})
        self.assertEqual(len(r2.context["products"]), 7)

    def test_pagination_keeps_filters(self):
        for i in range(15):
            make_product(f"Bulk {i}")
        r = self.client.get(reverse("product_list"), {"q": "Bulk"})
        self.assertContains(r, "q=Bulk&amp;page=2")

    def test_product_detail(self):
        r = self.client.get(self.phone.get_absolute_url())
        self.assertContains(r, "Smartphone")
        self.assertContains(r, "20% OFF")
        self.assertContains(r, "Add to Cart")

    def test_related_products_same_category_only(self):
        other = Category.objects.create(name="Other")
        make_product("Unrelated", category=other)
        r = self.client.get(self.phone.get_absolute_url())
        related = {p.name for p in r.context["related_products"]}
        self.assertNotIn("Smartphone", related)
        self.assertNotIn("Unrelated", related)
        self.assertIn("Blender", related)

    def test_out_of_stock_disables_add_to_cart(self):
        p = make_product("Gone", stock=0)
        r = self.client.get(p.get_absolute_url())
        self.assertContains(r, "Out of Stock")
        self.assertNotContains(r, reverse("cart_add", args=[p.id]))

    def test_missing_product_404(self):
        self.assertEqual(self.client.get(reverse("product_detail", args=["nope"])).status_code, 404)


class CartTests(TestCase):
    def setUp(self):
        self.p1 = make_product("Headphones", price="100", discount="80", stock=5)
        self.p2 = make_product("Backpack", price="50", stock=3)

    def add(self, product, qty=1):
        return self.client.post(reverse("cart_add", args=[product.id]), {"quantity": qty}, follow=True)

    def cart(self):
        return Cart(self.client.get(reverse("cart_detail")).wsgi_request)

    def test_add_product(self):
        r = self.add(self.p1, 2)
        self.assertContains(r, "Product added to cart.")
        self.assertEqual(len(self.cart()), 2)

    def test_add_same_product_accumulates(self):
        self.add(self.p1, 1)
        self.add(self.p1, 2)
        self.assertEqual(len(self.cart()), 3)

    def test_add_requires_post(self):
        self.assertEqual(self.client.get(reverse("cart_add", args=[self.p1.id])).status_code, 405)

    def test_stock_validation_on_add(self):
        r = self.add(self.p2, 10)
        self.assertContains(r, "Only 3 items are available.")
        self.assertEqual(len(self.cart()), 0)

    def test_stock_validation_when_accumulating(self):
        self.add(self.p2, 2)
        r = self.add(self.p2, 2)
        self.assertContains(r, "Only 3 items are available.")
        self.assertEqual(len(self.cart()), 2)

    def test_out_of_stock_cannot_be_added(self):
        p = make_product("Gone", stock=0)
        r = self.add(p)
        self.assertContains(r, "out of stock")
        self.assertEqual(len(self.cart()), 0)

    def test_invalid_quantities(self):
        for bad in ("0", "-2", "abc", ""):
            r = self.add(self.p1, bad)
            self.assertContains(r, "valid quantity")
        self.assertEqual(len(self.cart()), 0)

    def test_increase_and_decrease(self):
        self.add(self.p1, 2)
        self.client.post(reverse("cart_update", args=[self.p1.id]), {"action": "increase"})
        self.assertEqual(len(self.cart()), 3)
        self.client.post(reverse("cart_update", args=[self.p1.id]), {"action": "decrease"})
        self.assertEqual(len(self.cart()), 2)

    def test_decrease_to_zero_removes(self):
        self.add(self.p1, 1)
        self.client.post(reverse("cart_update", args=[self.p1.id]), {"action": "decrease"})
        self.assertEqual(len(self.cart()), 0)

    def test_increase_beyond_stock_rejected(self):
        self.add(self.p2, 3)
        r = self.client.post(reverse("cart_update", args=[self.p2.id]), {"action": "increase"}, follow=True)
        self.assertContains(r, "Only 3 items are available.")
        self.assertEqual(len(self.cart()), 3)

    def test_set_quantity(self):
        self.add(self.p1, 1)
        r = self.client.post(reverse("cart_update", args=[self.p1.id]), {"action": "set", "quantity": "4"}, follow=True)
        self.assertContains(r, "Cart updated.")
        self.assertEqual(len(self.cart()), 4)

    def test_remove(self):
        self.add(self.p1, 2)
        r = self.client.post(reverse("cart_remove", args=[self.p1.id]), follow=True)
        self.assertContains(r, "Product removed from cart.")
        self.assertContains(r, "Your Cart is Empty")

    def test_totals_and_shipping(self):
        self.add(self.p1, 2)  # 2 x 80 = 160
        self.add(self.p2, 1)  # 50
        cart = self.cart()
        self.assertEqual(cart.subtotal, Decimal("210.00"))
        self.assertEqual(cart.shipping, Decimal("10.00"))
        self.assertEqual(cart.total, Decimal("220.00"))
        self.assertEqual([i["total_price"] for i in cart], [Decimal("160.00"), Decimal("50.00")])

    @override_settings(FREE_SHIPPING_THRESHOLD=Decimal("150"))
    def test_free_shipping_over_threshold(self):
        self.add(self.p1, 2)
        self.assertEqual(self.cart().shipping, Decimal("0.00"))

    def test_empty_cart_has_no_shipping(self):
        self.assertEqual(self.cart().total, Decimal("0.00"))

    def test_price_change_reflected_in_cart(self):
        self.add(self.p2, 1)
        Product.objects.filter(pk=self.p2.pk).update(price=Decimal("70"))
        self.assertEqual(self.cart().subtotal, Decimal("70.00"))

    def test_deleted_product_dropped_from_cart(self):
        self.add(self.p2, 1)
        self.p2.delete()
        self.assertEqual(self.cart().subtotal, Decimal("0.00"))

    def test_cart_count_in_header(self):
        self.add(self.p1, 3)
        self.assertContains(self.client.get(reverse("home")), 'class="cart-badge">3<')

    def test_empty_cart_page(self):
        r = self.client.get(reverse("cart_detail"))
        self.assertContains(r, "Your Cart is Empty")

    def test_cart_page_lists_items(self):
        self.add(self.p1, 2)
        r = self.client.get(reverse("cart_detail"))
        self.assertContains(r, "Headphones")
        self.assertContains(r, "$160.00")
        self.assertContains(r, "$170.00")  # 160 + 10 shipping

    def test_redirect_after_add_is_same_site_only(self):
        r = self.client.post(reverse("cart_add", args=[self.p1.id]), {"quantity": 1, "next": "https://evil.example/"})
        self.assertEqual(r.url, reverse("cart_detail"))


class AuthTests(TestCase):
    def test_register(self):
        r = self.client.post(reverse("register"), {
            "username": "newbie", "email": "n@example.com", "password1": "S3cure-pass-99", "password2": "S3cure-pass-99"})
        self.assertRedirects(r, reverse("home"))
        self.assertTrue(User.objects.filter(username="newbie").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_register_validation(self):
        User.objects.create_user("taken", "t@example.com", "pw")
        base = {"username": "x1", "email": "x@example.com", "password1": "S3cure-pass-99", "password2": "S3cure-pass-99"}
        for override, text in (
            ({"username": "taken"}, "already exists"),
            ({"email": "not-an-email"}, "valid email"),
            ({"email": "T@example.com"}, "email already exists"),
            ({"password2": "different-pass-1"}, "didn’t match"),
            ({"password1": "123", "password2": "123"}, "too short"),
        ):
            r = self.client.post(reverse("register"), {**base, **override})
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, text)

    def test_login_with_username_and_email(self):
        User.objects.create_user("shopper", "shopper@example.com", "pw-12345-x")
        for ident in ("shopper", "SHOPPER@example.com"):
            self.client.logout()
            r = self.client.post(reverse("login"), {"username": ident, "password": "pw-12345-x"})
            self.assertRedirects(r, reverse("home"), fetch_redirect_response=False)
            self.assertIn("_auth_user_id", self.client.session)

    def test_login_wrong_password(self):
        User.objects.create_user("shopper", "s@example.com", "pw-12345-x")
        r = self.client.post(reverse("login"), {"username": "shopper", "password": "nope"})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_is_post_only_and_redirects_home(self):
        User.objects.create_user("shopper", "s@example.com", "pw-12345-x")
        self.client.login(username="shopper", password="pw-12345-x")
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        r = self.client.post(reverse("logout"))
        self.assertRedirects(r, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_requires_login(self):
        r = self.client.get(reverse("profile"))
        self.assertRedirects(r, f"{reverse('login')}?next={reverse('profile')}")

    def test_profile_update(self):
        u = User.objects.create_user("shopper", "s@example.com", "pw-12345-x")
        self.client.force_login(u)
        r = self.client.post(reverse("profile"), {
            "user-first_name": "Sam", "user-last_name": "Shop", "user-email": "new@example.com",
            "profile-phone": "+1 555 000 1111", "profile-address": "1 Main St", "profile-city": "Town", "profile-postal_code": "12345"},
            follow=True)
        self.assertContains(r, "Profile updated successfully.")
        u.refresh_from_db()
        self.assertEqual((u.first_name, u.email, u.profile.city), ("Sam", "new@example.com", "Town"))

    def test_profile_rejects_duplicate_email(self):
        User.objects.create_user("other", "taken@example.com", "pw")
        u = User.objects.create_user("shopper", "s@example.com", "pw-12345-x")
        self.client.force_login(u)
        r = self.client.post(reverse("profile"), {"user-email": "taken@example.com"})
        self.assertContains(r, "Another account already uses this email.")

    def test_profile_shows_orders_empty_state(self):
        self.client.force_login(User.objects.create_user("shopper", "s@example.com", "pw"))
        self.assertContains(self.client.get(reverse("profile")), "No Orders Yet")


class OrderTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("buyer", "buyer@example.com", "pw-12345-x")
        self.other = User.objects.create_user("other", "other@example.com", "pw-12345-x")
        self.p1 = make_product("Headphones", price="100", discount="80", stock=5)
        self.p2 = make_product("Backpack", price="50", stock=3)

    def fill_cart(self):
        self.client.post(reverse("cart_add", args=[self.p1.id]), {"quantity": 2})
        self.client.post(reverse("cart_add", args=[self.p2.id]), {"quantity": 1})

    def place(self, data=None):
        return self.client.post(reverse("checkout"), data or CHECKOUT_DATA)

    def test_checkout_requires_login(self):
        r = self.client.get(reverse("checkout"))
        self.assertRedirects(r, f"{reverse('login')}?next={reverse('checkout')}")

    def test_checkout_with_empty_cart_redirects(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse("checkout"), follow=True)
        self.assertRedirects(r, reverse("cart_detail"))
        self.assertContains(r, "Your Cart is Empty")

    def test_checkout_page_shows_summary(self):
        self.client.force_login(self.user)
        self.fill_cart()
        r = self.client.get(reverse("checkout"))
        self.assertContains(r, "Place Order")
        self.assertContains(r, "$220.00")
        self.assertContains(r, "Cash on Delivery")

    def test_place_order_creates_everything(self):
        self.client.force_login(self.user)
        self.fill_cart()
        r = self.place()
        order = Order.objects.get()
        self.assertRedirects(r, reverse("order_confirmation", args=[order.pk]))
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.subtotal, Decimal("210.00"))
        self.assertEqual(order.shipping_cost, Decimal("10.00"))
        self.assertEqual(order.total_price, Decimal("220.00"))
        self.assertEqual(order.order_number, f"ORD-{order.pk:05d}")
        items = {i.product_name: i for i in order.items.all()}
        self.assertEqual(items["Headphones"].quantity, 2)
        self.assertEqual(items["Headphones"].price, Decimal("80.00"))
        self.assertEqual(items["Headphones"].subtotal, Decimal("160.00"))
        self.assertEqual(items["Backpack"].subtotal, Decimal("50.00"))

    def test_stock_reduced_and_cart_cleared(self):
        self.client.force_login(self.user)
        self.fill_cart()
        self.place()
        self.p1.refresh_from_db(); self.p2.refresh_from_db()
        self.assertEqual((self.p1.stock_quantity, self.p2.stock_quantity), (3, 2))
        self.assertEqual(len(Cart(self.client.get(reverse("cart_detail")).wsgi_request)), 0)

    def test_confirmation_page(self):
        self.client.force_login(self.user)
        self.fill_cart()
        r = self.client.post(reverse("checkout"), CHECKOUT_DATA, follow=True)
        self.assertContains(r, "Order Placed Successfully!")
        self.assertContains(r, "$220.00")
        self.assertContains(r, "ORD-")

    def test_checkout_validation(self):
        self.client.force_login(self.user)
        self.fill_cart()
        for field, bad in (("customer_name", ""), ("email", "nope"), ("phone", "abc"), ("address", ""), ("city", ""), ("postal_code", "")):
            r = self.place({**CHECKOUT_DATA, field: bad})
            self.assertEqual(r.status_code, 200, field)
        self.assertEqual(Order.objects.count(), 0)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock_quantity, 5)

    def test_stock_changed_after_carting_blocks_checkout(self):
        self.client.force_login(self.user)
        self.fill_cart()
        Product.objects.filter(pk=self.p1.pk).update(stock_quantity=1)
        r = self.client.get(reverse("checkout"), follow=True)
        self.assertContains(r, "Only 1 of Headphones are available")
        self.assertEqual(Order.objects.count(), 0)

    def test_transaction_rolls_back_on_stock_failure(self):
        self.client.force_login(self.user)
        self.fill_cart()
        cart = Cart(self.client.get(reverse("cart_detail")).wsgi_request)
        list(cart)  # load items
        Product.objects.filter(pk=self.p2.pk).update(stock_quantity=0)  # race: stock vanishes mid-checkout
        with self.assertRaises(OrderError):
            create_order(self.user, cart, CHECKOUT_DATA)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock_quantity, 5)  # first line's decrement was rolled back too

    def test_cannot_buy_more_than_stock_via_service(self):
        cart = Cart(type("R", (), {"session": self.client.session})())
        cart.cart = {str(self.p2.pk): 99}
        with self.assertRaises(OrderError):
            create_order(self.user, cart, CHECKOUT_DATA)
        self.assertEqual(Order.objects.count(), 0)

    def test_order_snapshot_survives_product_changes(self):
        self.client.force_login(self.user)
        self.fill_cart()
        self.place()
        Product.objects.filter(pk=self.p1.pk).update(name="Renamed", price=Decimal("999"), discount_price=None)
        self.p2.delete()
        order = Order.objects.get()
        names = {i.product_name: i.price for i in order.items.all()}
        self.assertEqual(names, {"Headphones": Decimal("80.00"), "Backpack": Decimal("50.00")})
        r = self.client.get(reverse("order_detail", args=[order.pk]))
        self.assertContains(r, "Headphones")
        self.assertContains(r, "$220.00")
        self.assertEqual(order.items.get(product_name="Backpack").product, None)

    def make_order(self, user):
        o = Order.objects.create(user=user, total_price=Decimal("10"), **CHECKOUT_DATA)
        OrderItem.objects.create(order=o, product=self.p1, product_name="Headphones", price=Decimal("10"), quantity=1)
        return o

    def test_order_list_and_detail_for_owner(self):
        o = self.make_order(self.user)
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse("order_list")), o.order_number)
        r = self.client.get(reverse("order_detail", args=[o.pk]))
        self.assertContains(r, "Ada Lovelace")
        self.assertContains(r, "12 Analytical St")

    def test_order_list_empty_state(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse("order_list")), "No Orders Yet")

    def test_user_cannot_see_another_users_order(self):
        o = self.make_order(self.other)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("order_detail", args=[o.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("order_confirmation", args=[o.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("order_list")), o.order_number)

    def test_anonymous_cannot_see_orders(self):
        o = self.make_order(self.other)
        for url in (reverse("order_list"), reverse("order_detail", args=[o.pk])):
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_status_timeline(self):
        o = self.make_order(self.user)
        Order.objects.filter(pk=o.pk).update(status=Order.Status.SHIPPED)
        self.client.force_login(self.user)
        r = self.client.get(reverse("order_detail", args=[o.pk]))
        self.assertEqual([s["done"] for s in r.context["timeline"]], [True, True, True, False])
        Order.objects.filter(pk=o.pk).update(status=Order.Status.CANCELLED)
        self.assertContains(self.client.get(reverse("order_detail", args=[o.pk])), "This order was cancelled.")


class DashboardAndAdminTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_superuser("boss", "boss@example.com", "pw-12345-x")
        self.customer = User.objects.create_user("cust", "cust@example.com", "pw-12345-x")
        self.p = make_product("Scarce Thing", stock=2)
        make_product("Plentiful Thing", stock=100)
        o = Order.objects.create(user=self.customer, total_price=Decimal("30"), **CHECKOUT_DATA)
        OrderItem.objects.create(order=o, product=self.p, product_name="Scarce Thing", price=Decimal("10"), quantity=3)

    def test_dashboard_requires_staff(self):
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 302)
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 403)

    def test_dashboard_statistics_come_from_database(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse("dashboard"))
        self.assertEqual(r.context["total_products"], 2)
        self.assertEqual(r.context["total_orders"], 1)
        self.assertEqual(r.context["total_customers"], 1)
        self.assertEqual(r.context["total_revenue"], Decimal("30"))
        self.assertEqual([p.name for p in r.context["low_stock"]], ["Scarce Thing"])
        self.assertEqual(list(r.context["best_sellers"]), [{"product_name": "Scarce Thing", "units": 3}])
        self.assertIn(("Pending", 1, "pending"), r.context["status_summary"])

    def test_dashboard_excludes_cancelled_from_revenue(self):
        Order.objects.update(status=Order.Status.CANCELLED)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("dashboard")).context["total_revenue"], Decimal("0.00"))

    def test_admin_pages_load(self):
        self.client.force_login(self.staff)
        order = Order.objects.get()
        urls = [reverse("admin:index")]
        for model in ("product", "category", "order"):
            urls.append(reverse(f"admin:store_{model}_changelist"))
        urls += [reverse("admin:auth_user_changelist"), reverse("admin:store_product_add"), reverse("admin:store_category_add"),
                 reverse("admin:store_product_change", args=[self.p.pk]), reverse("admin:store_order_change", args=[order.pk])]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_admin_filters_and_search(self):
        self.client.force_login(self.staff)
        url = reverse("admin:store_product_changelist")
        self.assertContains(self.client.get(url, {"stock": "low"}), "Scarce Thing")
        self.assertNotContains(self.client.get(url, {"stock": "low"}), "Plentiful Thing")
        self.assertContains(self.client.get(url, {"q": "Plentiful"}), "Plentiful Thing")
        order = Order.objects.get()
        r = self.client.get(reverse("admin:store_order_changelist"), {"q": order.order_number})
        self.assertContains(r, order.order_number)

    def test_admin_can_update_order_status(self):
        self.client.force_login(self.staff)
        order = Order.objects.get()
        self.client.post(reverse("admin:store_order_changelist"), {
            "action": "mark_shipped", "_selected_action": [order.pk]})
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.SHIPPED)

    def test_non_staff_cannot_use_admin(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 302)


class SeedCommandTests(TestCase):
    def test_seed_store_creates_products_with_images(self):
        from django.core.management import call_command
        tmp = tempfile.mkdtemp()
        try:
            with override_settings(MEDIA_ROOT=__import__("pathlib").Path(tmp)):
                call_command("seed_store", stdout=io.StringIO())
                call_command("seed_store", stdout=io.StringIO())  # idempotent
                self.assertEqual(Category.objects.count(), 5)
                self.assertGreaterEqual(Product.objects.count(), 25)
                self.assertEqual(len({p.image.name for p in Product.objects.all()}), Product.objects.count())
                for p in Product.objects.all():
                    self.assertTrue(p.image.storage.exists(p.image.name), p.name)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
