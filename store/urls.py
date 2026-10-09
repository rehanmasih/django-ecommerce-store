from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.product_list, name="product_list"),
    path("products/<slug:slug>/", views.product_detail, name="product_detail"),
    path("category/<slug:slug>/", views.product_list, name="category_detail"),
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:product_id>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("register/", views.register, name="register"),
    path("login/", views.StoreLoginView.as_view(), name="login"),
    path("logout/", views.StoreLogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/confirmation/", views.order_confirmation, name="order_confirmation"),
    path("dashboard/", views.dashboard, name="dashboard"),
]
