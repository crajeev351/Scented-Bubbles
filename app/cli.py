import click
from decimal import Decimal
from flask.cli import with_appcontext
from app.extensions import db
from app.models.admins import Admin
from app.models.categories import Category
from app.models.products import Product
from app.models.product_variants import ProductVariant
from app.models.product_images import ProductImage
from app.models.combos import Combo
from app.models.combo_items import ComboItem
from app.models.banners import Banner
from app.models.settings import Setting
from app.models.pages import Page
from app.models.orders import Order
from app.models.order_items import OrderItem
from app.models.customers import Customer
from app.models.payments import Payment
from app.services.cache_service import cache


@click.command("create-admin")
@with_appcontext
def create_admin_command():
    """Create a new admin user interactively. No default passwords anywhere."""
    click.echo("\n--- Scented Bubbles: Create Admin User ---")
    username = click.prompt("Enter admin username", type=str).strip()
    email = click.prompt("Enter admin email", type=str).strip()

    if Admin.query.filter((Admin.username == username) | (Admin.email == email)).first():
        click.echo("Error: An admin with that username or email already exists.", err=True)
        return

    password = click.prompt("Enter secure password", hide_input=True, confirmation_prompt=True)
    if len(password) < 8:
        click.echo("Error: Password must be at least 8 characters long.", err=True)
        return

    admin = Admin(username=username, email=email, is_active=True)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    click.echo(f"Success: Admin account '{username}' created successfully!")


@click.command("seed-demo")
@with_appcontext
def seed_demo_command():
    """Seeds demo catalog: 2 categories, 6+ products with variants, 3 combos, 3 banners, settings, pages. NO admin."""
    click.echo("Seeding demo data for Scented Bubbles...")

    # 1. Store Settings (default company_name is 'Scented Bubbles')
    default_settings = {
        "company_name": ("Scented Bubbles", "Official registered brand name"),
        "tagline": ("Elegance in Every Mist & Breath", "Short store tagline"),
        "support_phone": ("919876543210", "Customer support phone number"),
        "support_whatsapp": ("919876543210", "WhatsApp contact number for click-to-chat"),
        "support_email": ("care@scentedbubbles.com", "Customer support email"),
        "store_address": ("Plot 42, Fragrance Avenue, Jubilee Hills, Hyderabad - 500033", "Physical store / fulfillment address"),
        "upi_id": ("scentedbubbles@okaxis", "Store UPI VPA for customer manual payments"),
        "upi_qr_url": ("/static/images/placeholder_upi_qr.png", "UPI QR code scan image"),
        "delivery_charge": ("50.00", "Standard delivery fee in INR"),
        "free_delivery_threshold": ("999.00", "Order total in INR for free shipping"),
        "cod_enabled": ("true", "Toggle Cash on Delivery (true/false)"),
        "gst_number": ("36AABCS1234F1Z5", "GSTIN identification"),
        "instagram_url": ("https://instagram.com/scentedbubbles", "Instagram handle"),
        "footer_text": ("Handcrafted fine fragrances and artisanal car diffusers designed to refresh your world.", "Footer summary"),
    }

    for key, (val, desc) in default_settings.items():
        Setting.set_value(key, val, desc)

    # 2. Policy & Informational Pages
    default_pages = {
        "about-us": (
            "About Scented Bubbles",
            "<p>At <strong>Scented Bubbles</strong>, we believe every space and moment deserves an aura of quiet luxury. Born from a devotion to artisanal perfumery, our creations balance French perfumery heritage with contemporary refinement.</p><p>From long-lasting Eau de Parfums to slow-evaporating wooden car diffusers, every batch of Scented Bubbles is hand-blended with IFRA-compliant fragrance oils, pure essential extracts, and cosmetic-grade carriers.</p>",
        ),
        "shipping-policy": (
            "Shipping Policy | Scented Bubbles",
            "<p>Orders placed at <strong>Scented Bubbles</strong> are dispatched within 24 to 48 business hours. We deliver across India with premium courier partners including Blue Dart, Delhivery, and DTDC.</p><p>Standard delivery takes 3 to 6 business days. Free shipping is automatically applied to all orders above ₹999.</p>",
        ),
        "refund-policy": (
            "Returns & Refunds | Scented Bubbles",
            "<p>Due to the personal nature of fine fragrances, <strong>Scented Bubbles</strong> cannot accept returns on opened perfume bottles or car diffusers. However, if your package arrives damaged, leaked, or incorrect, please reach out to care@scentedbubbles.com or message us on WhatsApp with an unboxing video within 48 hours for an instant replacement or refund.</p>",
        ),
        "terms-conditions": (
            "Terms & Conditions | Scented Bubbles",
            "<p>Welcome to <strong>Scented Bubbles</strong>. By accessing or shopping on our website, you agree to these terms. All products, imagery, and formulas are proprietary to Scented Bubbles. Prices and product availability are subject to change without prior notice.</p>",
        ),
        "privacy-policy": (
            "Privacy Policy | Scented Bubbles",
            "<p>Your privacy is paramount at <strong>Scented Bubbles</strong>. We collect customer name, phone number, and delivery address solely for fulfilling orders, tracking packages, and providing customer care. We never sell or lease your personal information to third parties.</p>",
        ),
    }

    for slug, (title, content) in default_pages.items():
        page = Page.query.filter_by(slug=slug).first()
        if not page:
            page = Page(slug=slug, title=title, content=content, is_active=True)
            db.session.add(page)
        else:
            page.title = title
            page.content = content

    # 3. Categories (2 main categories: Fine Fragrances & Luxury Car Diffusers)
    cat_fine = Category.query.filter_by(slug="fine-fragrances").first()
    if not cat_fine:
        cat_fine = Category(
            name="Fine Fragrances",
            slug="fine-fragrances",
            description="Exquisite Eau de Parfum blends crafted with rare botanicals and precious woods.",
            display_order=1,
            active=True,
        )
        db.session.add(cat_fine)

    cat_car = Category.query.filter_by(slug="car-perfumes").first()
    if not cat_car:
        cat_car = Category(
            name="Luxury Car Perfumes",
            slug="car-perfumes",
            description="Premium hanging diffusers and vent clips designed for enduring automotive elegance.",
            display_order=2,
            active=True,
        )
        db.session.add(cat_car)

    db.session.flush()

    # 4. Products, Variants & Curated Combos
    from app.seeds import seed_perfumes_catalog
    seed_perfumes_catalog(cat_fine, cat_car)

    # 5. Hero Banners (3 promotional banners)
    banners_data = [
        {
            "title": "Artisanal Fragrance & Automotive Elegance",
            "subtitle": "Discover slow-crafted perfumes and wooden car diffusers made with pure botanical essences.",
            "link_url": "/products",
            "image": "/static/images/banner_hero_1.webp",
            "display_order": 1,
        },
        {
            "title": "Curated Luxury Combos",
            "subtitle": "Pair your favorite Eau de Parfum with a matching car perfume and save up to 30%.",
            "link_url": "/combos",
            "image": "/static/images/banner_hero_2.webp",
            "display_order": 2,
        },
        {
            "title": "Complimentary Shipping",
            "subtitle": "Free express delivery across India on all orders above ₹999. Pay securely via UPI or COD.",
            "link_url": "/products",
            "image": "/static/images/banner_hero_3.webp",
            "display_order": 3,
        },
    ]

    for bdata in banners_data:
        banner = Banner.query.filter_by(title=bdata["title"]).first()
        if not banner:
            banner = Banner(
                title=bdata["title"],
                subtitle=bdata["subtitle"],
                link_url=bdata["link_url"],
                image_key=bdata["image"],
                display_order=bdata["display_order"],
                active=True,
            )
            db.session.add(banner)

    db.session.commit()
    cache.invalidate_all()
    click.echo("Success: Scented Bubbles demo data seeded cleanly! (NO admin user created; use 'flask create-admin').")


@click.command("reprocess-images")
@with_appcontext
def reprocess_images_command():
    """Reprocess all catalog images to ensure thumb, medium, and large WebP files exist."""
    from app.services.image_service import SIZE_SPECS, resize_and_compress, validate_image_content
    from app.services.storage import get_storage
    from PIL import Image
    from flask import current_app
    from pathlib import Path

    click.echo("--- Scented Bubbles: Reprocessing Catalog Images ---")
    storage = get_storage()
    base_dir = Path(current_app.root_path)
    count = 0

    # Collect all image keys across product images, combos, and banners
    keys_to_process = []
    for pi in ProductImage.query.all():
        keys_to_process.append((pi.image_key, f"Product {pi.product_id} Image"))
    for c in Combo.query.all():
        keys_to_process.append((c.image_key, f"Combo {c.name}"))
    for b in Banner.query.all():
        keys_to_process.append((b.image_key, f"Banner {b.title}"))

    click.echo(f"Found {len(keys_to_process)} image entries to check.")

    for raw_key, label in keys_to_process:
        if not raw_key or raw_key.startswith("http"):
            continue

        clean_path = raw_key.lstrip("/")
        # Find file in static/uploads or static/images
        candidate_paths = [
            base_dir / clean_path,
            base_dir / "static" / "uploads" / clean_path,
            base_dir / "static" / "images" / Path(clean_path).name,
        ]
        source_file = None
        for p in candidate_paths:
            if p.exists() and p.is_file():
                source_file = p
                break

        if not source_file:
            continue

        try:
            with open(source_file, "rb") as f:
                file_bytes = f.read()
            pil_img = validate_image_content(file_bytes)

            stem = source_file.stem
            # Strip existing size suffixes if re-running
            for s in ("_thumb", "_medium", "_large"):
                if stem.endswith(s):
                    stem = stem[:-len(s)]

            for size_name, spec in SIZE_SPECS.items():
                compressed = resize_and_compress(pil_img, max_dim=spec["max_dim"], quality=spec["quality"])
                variant_key = f"{stem}_{size_name}.webp"
                storage.save(compressed, variant_key, content_type="image/webp")

            count += 1
            click.echo(f"  [OK] Reprocessed: {label} ({stem}) -> thumb/medium/large generated")
        except Exception as e:
            click.echo(f"  [WARN] Failed to reprocess {label} ({raw_key}): {e}")

    cache.invalidate_all()
    click.echo(f"\nCompleted: Reprocessed {count} catalog images successfully!")


@click.command("seed-load-test")
@click.option("--products", "target_products", default=150, help="Target products count (default: 150)")
@click.option("--orders", "target_orders", default=1500, help="Target orders count (default: 1500)")
@with_appcontext
def seed_load_test_command(target_products, target_orders):
    """Seed catalog with 150+ products and 1,500+ realistic historical orders for performance load testing."""
    import random
    import time
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal

    start_time = time.time()
    click.echo(f"\n--- Scented Bubbles: Generating Load Test Dataset ({target_products} Products, {target_orders} Orders) ---")

    # 1. Ensure categories exist
    categories = Category.query.filter_by(is_deleted=False).all()
    if not categories:
        cat_names = ["Fine Fragrances", "Car Perfumes & Diffusers", "Artisanal Attars", "Home & Linen Mists"]
        for idx, cn in enumerate(cat_names):
            slug = cn.lower().replace(" ", "-").replace("&", "and")
            c = Category(name=cn, slug=slug, display_order=idx)
            db.session.add(c)
        db.session.commit()
        categories = Category.query.all()

    # 2. Generate Products & Variants to reach target_products
    existing_prod_count = Product.query.filter_by(is_deleted=False).count()
    needed_products = max(0, target_products - existing_prod_count)
    click.echo(f"Existing products: {existing_prod_count}. Generating {needed_products} new products...")

    fragrance_adjectives = ["Royal", "Velvet", "Smoky", "Celestial", "Golden", "Midnight", "Mystic", "Imperial", "Sublime", "Amber", "Pure", "Enchanted", "Silk", "Luminous", "Sacred"]
    fragrance_nouns = ["Oud", "Rose", "Bergamot", "Cedar", "Vanilla", "Musk", "Saffron", "Neroli", "Iris", "Leather", "Vetiver", "Cardamom", "Jasmine", "Sandalwood", "Ambergris"]

    all_variants = []
    if needed_products > 0:
        for i in range(needed_products):
            adj = fragrance_adjectives[i % len(fragrance_adjectives)]
            noun = fragrance_nouns[(i * 3 + 7) % len(fragrance_nouns)]
            num_suffix = f" {i + 1}" if i >= len(fragrance_adjectives) else ""
            pname = f"{adj} {noun}{num_suffix}"
            pslug = f"{adj.lower()}-{noun.lower()}-{i+1}"
            if Product.query.filter_by(slug=pslug).first():
                pslug = f"{pslug}-{random.randint(100, 9999)}"
            cat = categories[i % len(categories)]

            p = Product(
                category_id=cat.id,
                name=pname,
                slug=pslug,
                short_description=f"Sensory luxury formulation of {adj.lower()} accords with deep {noun.lower()} undertones.",
                full_description=f"Crafted exclusively for Scented Bubbles connoisseurs using IFRA certified botanical oils.",
                top_notes=f"{adj} Bergamot, Pink Pepper",
                heart_notes=f"Damask {noun}, Spiced Cardamom",
                base_notes=f"Smoky {noun}, Madagascar Vanilla, Golden Amber",
                fragrance_family=noun,
                active=True,
                featured=(i % 10 == 0),
                bestseller=(i % 8 == 0),
            )
            db.session.add(p)
            db.session.flush()

            # Attach 2 variants per product
            sizes = [("50ml EDP", "50ML", Decimal("1299.00"), Decimal("1149.00"), random.randint(15, 60)),
                     ("100ml EDP", "100ML", Decimal("2199.00"), Decimal("1899.00"), random.randint(10, 45))]
            for idx, (slabel, scode, pr, dpr, stk) in enumerate(sizes):
                sku = f"SKU-{p.id:04d}-{scode}"
                v = ProductVariant(
                    product_id=p.id,
                    size_label=slabel,
                    sku=sku,
                    price=pr,
                    discounted_price=dpr if (i % 2 == 0) else None,
                    stock=stk,
                    active=True,
                    display_order=idx,
                )
                db.session.add(v)
                all_variants.append(v)

            # Product image placeholder
            img_key = f"/static/images/{'car_amber_noir' if 'Car' in cat.name else 'perfume_velvet_oud'}.webp"
            p_img = ProductImage(product_id=p.id, image_key=img_key, is_primary=True)
            db.session.add(p_img)

            if i % 50 == 0:
                db.session.commit()
        db.session.commit()

    all_variants = ProductVariant.query.filter_by(is_deleted=False).all()
    click.echo(f"Total available variants: {len(all_variants)}")

    # 3. Generate Orders to reach target_orders
    existing_orders_count = Order.query.count()
    needed_orders = max(0, target_orders - existing_orders_count)
    click.echo(f"Existing orders: {existing_orders_count}. Generating {needed_orders} historical orders...")

    order_statuses = [
        Order.STATUS_DELIVERED,
        Order.STATUS_DELIVERED,
        Order.STATUS_DELIVERED,
        Order.STATUS_SHIPPED,
        Order.STATUS_PACKED,
        Order.STATUS_CONFIRMED,
        Order.STATUS_PENDING,
        Order.STATUS_CANCELLED,
    ]
    payment_statuses = [
        Order.PAYMENT_PAID,
        Order.PAYMENT_PAID,
        Order.PAYMENT_PAID,
        Order.PAYMENT_PAID,
        Order.PAYMENT_PENDING_VERIFICATION,
        Order.PAYMENT_FAILED,
    ]

    first_names = ["Aarav", "Ananya", "Rohan", "Priya", "Vikram", "Neha", "Aditya", "Sneha", "Kabir", "Meera", "Arjun", "Tanvi", "Karan", "Ishita", "Rahul"]
    cities = ["Mumbai", "Bengaluru", "Hyderabad", "Delhi", "Chennai", "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Chandigarh"]

    now = datetime.now(timezone.utc)
    batch_size = 250

    for i in range(needed_orders):
        # Distribute over past 180 days
        days_ago = random.randint(0, 180)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        order_date = now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
        date_str = order_date.strftime("%Y%m%d")
        order_id = f"PERF-{date_str}-{i+1:05d}"

        fname = random.choice(first_names)
        phone = f"98{random.randint(10000000, 99999999)}"
        city = random.choice(cities)

        # Match or create customer
        cust = Customer.query.filter_by(phone=phone).first()
        if not cust:
            cust = Customer(
                phone=phone,
                name=f"{fname} Sharma",
                email=f"{fname.lower()}{random.randint(10, 99)}@gmail.com",
            )
            db.session.add(cust)
            db.session.flush()

        # Pick 1-3 items
        num_items = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
        selected_vars = random.sample(all_variants, min(num_items, len(all_variants)))

        subtotal = Decimal("0.00")
        items_to_add = []
        for v in selected_vars:
            qty = random.randint(1, 2)
            uprice = v.effective_price
            tot = uprice * qty
            subtotal += tot
            items_to_add.append((v, qty, uprice, tot))

        delivery_charge = Decimal("0.00") if subtotal >= Decimal("999.00") else Decimal("50.00")
        total_amount = subtotal + delivery_charge

        ostatus = random.choice(order_statuses)
        pstatus = Order.PAYMENT_PAID if ostatus in (Order.STATUS_CONFIRMED, Order.STATUS_PACKED, Order.STATUS_SHIPPED, Order.STATUS_DELIVERED) else random.choice(payment_statuses)
        if ostatus == Order.STATUS_CANCELLED and pstatus == Order.PAYMENT_PAID:
            pstatus = Order.PAYMENT_REFUNDED
        pmethod = "MANUAL_UPI" if random.random() > 0.3 else "COD"

        ord_obj = Order(
            order_id=order_id,
            customer_id=cust.id,
            subtotal=subtotal,
            delivery_charge=delivery_charge,
            total_amount=total_amount,
            order_status=ostatus,
            payment_status=pstatus,
            payment_method=pmethod,
            shipping_name=f"{fname} Sharma",
            shipping_phone=phone,
            shipping_address_line1=f"Flat {random.randint(101, 804)}, Fragrance Heights",
            shipping_city=city,
            shipping_state="Maharashtra",
            shipping_pincode=f"{random.randint(400001, 400099)}",
            created_at=order_date,
            updated_at=order_date,
        )
        db.session.add(ord_obj)
        db.session.flush()

        for v, qty, uprice, tot in items_to_add:
            item = OrderItem(
                order_id=ord_obj.id,
                product_variant_id=v.id,
                product_name_snapshot=v.product.name,
                variant_label_snapshot=v.size_label,
                sku_snapshot=v.sku,
                unit_price_snapshot=uprice,
                quantity=qty,
                total_price=tot,
            )
            db.session.add(item)

        # Payment record
        pmethod = "MANUAL_UPI" if random.random() > 0.3 else "COD"
        utr_val = f"UTR{random.randint(100000000000, 999999999999)}" if pmethod == "MANUAL_UPI" else None
        pay = Payment(
            order_id=ord_obj.id,
            payment_method=pmethod,
            amount=total_amount,
            status=pstatus,
            utr=utr_val,
            created_at=order_date,
        )
        db.session.add(pay)

        if (i + 1) % batch_size == 0:
            db.session.commit()
            click.echo(f"  [Progress] Seeded {i + 1} / {needed_orders} orders...")

    db.session.commit()
    cache.invalidate_all()
    duration = time.time() - start_time
    click.echo(f"\nSuccess: Seeded load test data in {duration:.2f}s! ({Product.query.count()} total products, {Order.query.count()} total orders).")


@click.command("export-data")
def export_data_command():
    """Exports all SQLite records to data_backup.json and data_backup.sql for permanent safety."""
    from scripts.export_sqlite_data import export_data
    export_data()


@click.command("migrate-to-supabase")
@click.option("--target", default=None, help="Supabase PostgreSQL connection string (or uses DATABASE_URL env var)")
def migrate_to_supabase_command(target):
    """Migrates all SQLite records directly into Supabase PostgreSQL without data loss."""
    from scripts.migrate_to_supabase import run_migration
    import os
    target_url = target or os.environ.get("DATABASE_URL")
    if not target_url:
        click.echo("Error: Please provide --target or set DATABASE_URL environment variable.", err=True)
        return
    run_migration(target_url)



