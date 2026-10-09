from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import F, Q
from django.templatetags.static import static
from django.urls import reverse
from django.utils.text import slugify

from .validators import validate_image_content, validate_image_size


def _unique_slug(model, base, instance_pk, max_length):
    base = (slugify(base) or "item")[: max_length - 8]
    slug, n = base, 2
    while model.objects.filter(slug=slug).exclude(pk=instance_pk).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Category, self.name, self.pk, 120)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("category_detail", kwargs={"slug": self.slug})


class Product(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Optional. Must be lower than the regular price.",
    )
    image = models.ImageField(
        upload_to="products/",
        blank=True,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
            validate_image_size,
            validate_image_content,
        ],
    )
    stock_quantity = models.PositiveIntegerField(default=0)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["-created_at"], name="product_created_idx"),
            models.Index(fields=["category", "price"], name="product_cat_price_idx"),
            models.Index(fields=["is_featured"], name="product_featured_idx"),
            models.Index(fields=["name"], name="product_name_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(discount_price__isnull=True) | Q(discount_price__lt=F("price")),
                name="product_discount_lt_price",
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.discount_price is not None and self.price is not None and self.discount_price >= self.price:
            raise ValidationError({"discount_price": "The discount price must be lower than the regular price."})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Product, self.name, self.pk, 170)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={"slug": self.slug})

    # ---- pricing
    @property
    def has_discount(self):
        return self.discount_price is not None and self.discount_price < self.price

    @property
    def current_price(self):
        return self.discount_price if self.has_discount else self.price

    @property
    def discount_percent(self):
        if not self.has_discount:
            return 0
        return int(((self.price - self.discount_price) / self.price * 100).quantize(Decimal("1")))

    @property
    def savings(self):
        return self.price - self.discount_price if self.has_discount else Decimal("0.00")

    # ---- stock
    @property
    def is_in_stock(self):
        return self.stock_quantity > 0

    @property
    def is_low_stock(self):
        return 0 < self.stock_quantity <= settings.LOW_STOCK_THRESHOLD

    @property
    def stock_status(self):
        if not self.is_in_stock:
            return "Out of Stock"
        return "Low Stock" if self.is_low_stock else "In Stock"

    @property
    def stock_css(self):
        return {"Out of Stock": "out", "Low Stock": "low", "In Stock": "in"}[self.stock_status]

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        return static("store/img/placeholder.svg")


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    customer_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(r"^\+?[0-9 ()\-]{7,20}$", "Enter a valid phone number.")],
    )
    address = models.TextField()
    city = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=15)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    shipping_cost = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    payment_method = models.CharField(max_length=60, default="Cash on Delivery (demo checkout)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["status"], name="order_status_idx"),
            models.Index(fields=["user", "-created_at"], name="order_user_created_idx"),
        ]

    def __str__(self):
        return self.order_number

    @property
    def order_number(self):
        return f"ORD-{self.pk:05d}" if self.pk else "ORD-?????"

    def get_absolute_url(self):
        return reverse("order_detail", kwargs={"pk": self.pk})


class OrderItem(models.Model):
    """A line of an order. Name and price are snapshots taken at purchase time."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items")
    product_name = models.CharField(max_length=150)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["id"]
        constraints = [models.CheckConstraint(condition=Q(quantity__gte=1), name="orderitem_quantity_gte_1")]

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"

    def save(self, *args, **kwargs):
        self.subtotal = self.price * self.quantity
        super().save(*args, **kwargs)


class Profile(models.Model):
    """Optional saved contact details used to pre-fill checkout."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=80, blank=True)
    postal_code = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return f"Profile of {self.user}"
