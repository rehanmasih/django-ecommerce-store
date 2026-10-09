"""Create demo categories, products and product images.

Usage:
    python manage.py seed_store           # safe to re-run (updates existing demo items)
    python manage.py seed_store --reset   # delete all products/categories first
"""
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from store.demo_images import render_product_image
from store.models import Category, Product

CATEGORIES = [
    ("Electronics", "electronics", "Phones, laptops, audio and everyday tech."),
    ("Clothing", "clothing", "Comfortable everyday wear for every season."),
    ("Shoes", "shoes", "Running shoes, sneakers, boots and formal pairs."),
    ("Accessories", "accessories", "Bags, watches, eyewear and finishing touches."),
    ("Home & Kitchen", "home-kitchen", "Appliances, cookware and pieces that make a house a home."),
]

# (category, name, art, (colour, accent), art options, price, discount, stock, featured, description)
D = Decimal
PRODUCTS = [
    # ------------------------------------------------------------ Electronics
    ("Electronics", "Nova X Smartphone", "smartphone", ("#3b5bdb", "#ffd166"), {}, "699.00", "629.00", 18, True,
     "6.5-inch OLED display, 128 GB storage and a dual-camera system that handles low light with ease. "
     "All-day battery with fast charging, plus 5G connectivity."),
    ("Electronics", "ProBook 15 Laptop", "laptop", ("#243b6b", "#4dabf7"), {}, "1199.00", "1049.00", 9, True,
     "15.6-inch Full HD display, 16 GB RAM and a 512 GB SSD in a slim aluminium body. Built for work, "
     "study and light creative projects, with up to 10 hours of battery life."),
    ("Electronics", "Wireless Bluetooth Headphones", "headphones", ("#2f3542", "#ff6b6b"), {}, "99.99", "79.99", 24, True,
     "Over-ear headphones with active noise cancellation, plush memory-foam cushions and 30 hours of playback "
     "on a single charge. Folds flat for travel."),
    ("Electronics", "Pulse Smart Watch", "smartwatch", ("#20c997", "#3d4a5c"), {}, "199.00", "169.00", 14, True,
     "Track heart rate, sleep and workouts on a bright always-on display. Water resistant to 50 metres, "
     "with notifications from your phone and a 5-day battery."),
    ("Electronics", "AirBeat Wireless Earbuds", "earbuds", ("#e9ecef", "#4dabf7"), {}, "79.00", None, 30, False,
     "True wireless earbuds with a secure in-ear fit, clear calls and 6 hours of listening per charge. "
     "The pocket-sized case adds 24 more hours."),
    ("Electronics", "Boom Mini Bluetooth Speaker", "speaker", ("#364152", "#ff922b"), {}, "59.99", "49.99", 3, False,
     "Portable speaker with punchy 360-degree sound, an IPX6 splash-proof shell and 12 hours of battery. "
     "Pair two for stereo."),
    ("Electronics", "TactiPro Mechanical Keyboard", "keyboard", ("#2b303b", "#ff6b6b"), {}, "89.00", None, 12, False,
     "Compact mechanical keyboard with tactile switches, PBT keycaps and a detachable USB-C cable. "
     "Satisfying to type on all day."),
    ("Electronics", "Glide Wireless Mouse", "mouse", ("#3a4150", "#4dabf7"), {}, "29.99", "24.99", 4, False,
     "Quiet-click ergonomic mouse with adjustable DPI and a 12-month battery life from a single AA cell. "
     "Connects through a tiny USB receiver or Bluetooth."),
    # ------------------------------------------------------------ Clothing
    ("Clothing", "Classic Cotton T-Shirt", "tshirt", ("#f1f3f5", "#3b5bdb"), {}, "19.99", None, 60, False,
     "A wardrobe staple in soft, breathable 100% cotton with a relaxed crew neck. Pre-washed so it keeps its shape."),
    ("Clothing", "Harbor Crew Tee", "tshirt", ("#2f4b7c", "#ffd166"), {"mark": True}, "24.99", "19.99", 45, False,
     "Mid-weight navy tee with a small chest emblem. Ring-spun cotton that gets softer with every wash."),
    ("Clothing", "Premium Fleece Hoodie", "hoodie", ("#495057", "#f1f3f5"), {}, "64.99", "49.99", 22, True,
     "Heavyweight brushed-fleece hoodie with a roomy kangaroo pocket, adjustable drawcord hood and ribbed cuffs."),
    ("Clothing", "Denim Jacket", "jacket", ("#3f6ea3", "#f0c060"), {}, "89.00", "74.00", 11, True,
     "Timeless button-front jacket in rigid mid-blue denim with chest pockets and contrast stitching."),
    ("Clothing", "Slim Fit Jeans", "pants", ("#2f5d8c", "#f0c060"), {}, "59.99", None, 35, False,
     "Slim through the leg with a touch of stretch for all-day comfort. Five-pocket styling in dark indigo wash."),
    ("Clothing", "Casual Oxford Shirt", "shirt", ("#9ec5e8", "#ffffff"), {}, "44.99", "36.99", 27, False,
     "Button-down oxford weave in light blue, with a chest pocket and a collar that sits neatly with or without a tie."),
    ("Clothing", "Court Performance Polo", "shirt", ("#2f9e77", "#f1f3f5"), {"polo": True}, "34.99", None, 0, False,
     "Moisture-wicking piqué polo with contrast sleeve bands. Currently sold out - check back soon."),
    ("Clothing", "Cotton Joggers", "pants", ("#6c757d", "#dee2e6"), {"jogger": True}, "39.99", "32.99", 40, False,
     "Tapered joggers in soft French terry with an elastic drawstring waist and ribbed ankle cuffs."),
    # ------------------------------------------------------------ Shoes
    ("Shoes", "Urban Running Shoes", "sneaker", ("#ff7a45", "#212529"), {"running": True}, "89.99", "74.99", 20, True,
     "Lightweight running shoes with a breathable mesh upper and responsive cushioning for daily road miles."),
    ("Shoes", "Classic Sneakers", "sneaker", ("#f1f3f5", "#3b5bdb"), {}, "64.99", None, 33, True,
     "Clean white low-top sneakers in smooth leather-look uppers. Goes with almost everything in your wardrobe."),
    ("Shoes", "Leather Formal Shoes", "formal", ("#7b4a2a", "#c9a27a"), {}, "119.00", "99.00", 12, False,
     "Hand-finished leather oxfords with a cushioned insole and a durable stitched sole for the office or special occasions."),
    ("Shoes", "Sports Training Shoes", "sneaker", ("#212529", "#e03131"), {"sole": "#e9ecef"}, "79.99", None, 2, False,
     "Stable, grippy trainers built for gym sessions and court sports, with reinforced sidewalls for lateral support."),
    ("Shoes", "Trail Hiking Boots", "boot", ("#a67c52", "#3a3a3a"), {}, "129.00", "109.00", 8, False,
     "Waterproof hiking boots with padded ankle support and a deep-lugged outsole that grips wet rock and loose trail."),
    ("Shoes", "Suede Chelsea Boots", "boot", ("#8a5a3b", "#ffd166"), {"chelsea": True}, "109.00", None, 15, False,
     "Soft suede pull-on boots with elastic side panels and a low stacked heel. Easy to dress up or down."),
    # ------------------------------------------------------------ Accessories
    ("Accessories", "Urban Backpack", "backpack", ("#2f4858", "#f2b134"), {}, "49.99", "39.99", 40, True,
     "Water-resistant 24-litre backpack with a padded 15-inch laptop sleeve, quick-access front pocket and breathable straps."),
    ("Accessories", "Leather Wallet", "wallet", ("#7a4a2b", "#3b5bdb"), {}, "34.99", None, 25, False,
     "Slim genuine-leather bifold with six card slots and a full-length note compartment. Ages beautifully."),
    ("Accessories", "Classic Sunglasses", "sunglasses", ("#1f2933", "#3c4a5a"), {}, "39.00", "29.00", 18, False,
     "Round-frame sunglasses with polarised UV400 lenses and spring hinges for a comfortable, secure fit."),
    ("Accessories", "Leather Belt", "belt", ("#6b3f22", "#c8ccd4"), {}, "27.99", None, 30, False,
     "Full-grain leather belt with a brushed-metal buckle and five adjustment holes."),
    ("Accessories", "Premium Baseball Cap", "cap", ("#2f5d8c", "#f2b134"), {}, "21.99", "17.99", 50, False,
     "Six-panel cotton twill cap with a curved brim and an adjustable strap at the back."),
    ("Accessories", "Classic Analog Watch", "watch", ("#1f3a5f", "#7a4a2b"), {}, "129.00", "99.00", 10, True,
     "Minimal navy-dial quartz watch with a genuine leather strap, sapphire-coated glass and 5 ATM water resistance."),
    # ------------------------------------------------------------ Home & Kitchen
    ("Home & Kitchen", "Digital Coffee Maker", "coffee", ("#2b2f38", "#4dd0b8"), {}, "79.99", "64.99", 15, True,
     "12-cup programmable drip coffee maker with a glass carafe, keep-warm plate and reusable filter."),
    ("Home & Kitchen", "Kitchen Blender", "blender", ("#c92a2a", "#8ce99a"), {}, "59.99", None, 19, False,
     "700-watt blender with a 1.5-litre jar and stainless-steel blades. Handles smoothies, soups and crushed ice."),
    ("Home & Kitchen", "Non-Stick Cookware Set", "cookware", ("#868e96", "#ff8787"), {}, "149.00", "119.00", 7, True,
     "Seven-piece set with a stockpot, saucepan, frying pan and lids. Even heating, non-stick interior, oven safe to 200 C."),
    ("Home & Kitchen", "Modern Table Lamp", "lamp", ("#d9954f", "#2b2f38"), {}, "44.99", None, 21, False,
     "Warm-glow table lamp with a fabric shade and a weighted base. Takes any E27 bulb."),
    ("Home & Kitchen", "Kitchen Utensil Organizer", "organizer", ("#c9a06a", "#4dabf7"), {}, "24.99", "19.99", 33, False,
     "Bamboo drawer tray with four compartments and non-slip feet, sized to hold spatulas, spoons and cutlery."),
    ("Home & Kitchen", "Insulated Water Bottle", "bottle", ("#2a9d8f", "#ffd166"), {}, "24.99", None, 70, False,
     "750 ml double-wall stainless-steel bottle. Keeps drinks cold for 24 hours or hot for 12, with a leak-proof lid."),
    ("Home & Kitchen", "Porcelain Dinner Set", "dinnerset", ("#3b5bdb", "#3b5bdb"), {}, "89.00", "72.00", 9, False,
     "Twelve-piece porcelain set with dinner plates, bowls and mugs. Dishwasher and microwave safe."),
    ("Home & Kitchen", "Electric Kettle", "kettle", ("#adb5bd", "#4dabf7"), {}, "39.99", "32.99", 4, False,
     "1.7-litre stainless-steel kettle with a water-level window, auto shut-off and boil-dry protection."),
]


class Command(BaseCommand):
    help = "Create demo categories, products and locally generated product images."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete all existing products and categories first.")

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["reset"]:
            Product.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write("Existing products and categories removed.")

        cats = {}
        for name, slug, description in CATEGORIES:
            cats[name], _ = Category.objects.update_or_create(slug=slug, defaults={"name": name, "description": description})

        media_dir = settings.MEDIA_ROOT / "products"
        media_dir.mkdir(parents=True, exist_ok=True)
        made = updated = generated = 0
        for cat, name, art, colours, options, price, discount, stock, featured, description in PRODUCTS:
            slug = slugify(name)
            filename = f"{slug}.jpg"
            if not (media_dir / filename).exists():
                render_product_image(art, media_dir / filename, cats[cat].slug, colours, **options)
                generated += 1
            _, created = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name, "category": cats[cat], "description": description,
                    "price": D(price), "discount_price": D(discount) if discount else None,
                    "stock_quantity": stock, "is_featured": featured, "image": f"products/{filename}",
                },
            )
            made, updated = (made + 1, updated) if created else (made, updated + 1)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(cats)} categories and {made + updated} products "
            f"({made} created, {updated} updated, {generated} images generated)."
        ))
