from django.contrib import admin
from django.conf import settings
from django.utils.html import format_html

from .forms import ProductForm
from .models import Category, Order, OrderItem, Product, Profile

admin.site.site_header = "Django E-Commerce Store Admin"
admin.site.site_title = "Store Admin"
admin.site.index_title = "Store management"


class StockFilter(admin.SimpleListFilter):
    title = "stock level"
    parameter_name = "stock"

    def lookups(self, request, model_admin):
        return [("out", "Out of stock"), ("low", "Low stock"), ("in", "In stock")]

    def queryset(self, request, queryset):
        limit = settings.LOW_STOCK_THRESHOLD
        if self.value() == "out":
            return queryset.filter(stock_quantity=0)
        if self.value() == "low":
            return queryset.filter(stock_quantity__gt=0, stock_quantity__lte=limit)
        if self.value() == "in":
            return queryset.filter(stock_quantity__gt=limit)
        return queryset


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "product_count")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Products")
    def product_count(self, obj):
        return obj.products.count()


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductForm
    list_display = ("thumbnail", "name", "category", "price", "discount_price", "stock_quantity", "is_featured", "created_at")
    list_display_links = ("thumbnail", "name")
    list_editable = ("stock_quantity", "is_featured")
    list_filter = ("category", "is_featured", StockFilter)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    list_select_related = ("category",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 25
    readonly_fields = ("created_at", "updated_at")
    actions = ["mark_featured", "unmark_featured"]

    @admin.display(description="Image")
    def thumbnail(self, obj):
        return format_html('<img src="{}" alt="" style="width:48px;height:48px;object-fit:cover;border-radius:6px">', obj.image_url)

    @admin.action(description="Mark selected products as featured")
    def mark_featured(self, request, queryset):
        self.message_user(request, f"{queryset.update(is_featured=True)} product(s) marked as featured.")

    @admin.action(description="Remove featured status from selected products")
    def unmark_featured(self, request, queryset):
        self.message_user(request, f"{queryset.update(is_featured=False)} product(s) updated.")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = ("product_name", "price", "quantity", "subtotal")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "customer_name", "total_price", "status", "created_at")
    list_editable = ("status",)
    list_filter = ("status", "created_at")
    search_fields = ("id", "customer_name", "email", "user__username")
    list_select_related = ("user",)
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]
    readonly_fields = ("user", "subtotal", "shipping_cost", "total_price", "payment_method", "created_at", "updated_at")
    actions = ["mark_processing", "mark_shipped", "mark_delivered", "mark_cancelled"]

    def get_search_results(self, request, queryset, search_term):
        # Allow searching by the displayed order number, e.g. "ORD-00012".
        term = search_term.strip()
        if term.upper().startswith("ORD-") and term[4:].isdigit():
            search_term = str(int(term[4:]))
        return super().get_search_results(request, queryset, search_term)

    def _set_status(self, request, queryset, status):
        self.message_user(request, f"{queryset.update(status=status)} order(s) updated.")

    @admin.action(description="Mark as Processing")
    def mark_processing(self, request, queryset):
        self._set_status(request, queryset, Order.Status.PROCESSING)

    @admin.action(description="Mark as Shipped")
    def mark_shipped(self, request, queryset):
        self._set_status(request, queryset, Order.Status.SHIPPED)

    @admin.action(description="Mark as Delivered")
    def mark_delivered(self, request, queryset):
        self._set_status(request, queryset, Order.Status.DELIVERED)

    @admin.action(description="Mark as Cancelled")
    def mark_cancelled(self, request, queryset):
        self._set_status(request, queryset, Order.Status.CANCELLED)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "city")
    search_fields = ("user__username", "user__email", "phone")
