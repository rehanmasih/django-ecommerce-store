from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Category, Order, Product, Profile

User = get_user_model()


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Email or username", widget=forms.TextInput(attrs={"autofocus": True}))


class CheckoutForm(forms.ModelForm):
    customer_name = forms.CharField(label="Full name", max_length=120)

    class Meta:
        model = Order
        fields = ["customer_name", "email", "phone", "address", "city", "postal_code"]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}

    def clean_customer_name(self):
        name = self.cleaned_data["customer_name"].strip()
        if len(name) < 2:
            raise forms.ValidationError("Please enter your full name.")
        return name


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if not email:
            raise forms.ValidationError("Email is required.")
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Another account already uses this email.")
        return email


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["phone", "address", "city", "postal_code"]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}


class ProductForm(forms.ModelForm):
    """Used by the admin. Image validation lives on the model field's validators."""

    class Meta:
        model = Product
        fields = "__all__"


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = "__all__"


class ProductFilterForm(forms.Form):
    SORT_CHOICES = [
        ("newest", "Newest"),
        ("price_asc", "Price: Low to High"),
        ("price_desc", "Price: High to Low"),
        ("name_asc", "Name: A-Z"),
        ("name_desc", "Name: Z-A"),
    ]
    q = forms.CharField(required=False, max_length=100)
    category = forms.CharField(required=False, max_length=120)
    min_price = forms.DecimalField(required=False, min_value=0, max_digits=10, decimal_places=2)
    max_price = forms.DecimalField(required=False, min_value=0, max_digits=10, decimal_places=2)
    sort = forms.ChoiceField(required=False, choices=SORT_CHOICES)

    def clean(self):
        data = super().clean()
        lo, hi = data.get("min_price"), data.get("max_price")
        if lo is not None and hi is not None and lo > hi:
            self.add_error("max_price", "Maximum price must be greater than the minimum price.")
            data["min_price"] = None  # inconsistent range: apply no price filter at all
        return data
