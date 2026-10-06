"""
Catalog seeding definitions for Scented Bubbles.
Contains genuine Original Manufacturer oil made only fine fragrances,
pre-launch 30ml offer, 50ml collections, CR7 special sizing (50/100ml only),
and luxury car perfumes using the uploaded demo images.
"""
from decimal import Decimal
from app.extensions import db
from app.models.categories import Category
from app.models.products import Product
from app.models.product_variants import ProductVariant
from app.models.product_images import ProductImage
from app.models.combos import Combo
from app.models.combo_items import ComboItem

PERFUME_IMG = "/static/images/perfume_sample.webp"
CAR_IMG = "/static/images/car_sample.webp"

# 10 perfumes with 30ml Pre-launch Offer (flat ₹380)
PERFUMES_WITH_30ML_OFFER = {
    "Tam Dao (SRK)",
    "Burberry Weekend",
    "Azzaro Most Wanted",
    "YSL Libre",
    "Armani Tobacco",
    "Dior Homme",
    "Imperial Valley",
    "Gucci Guilty",
    "CK One",
    "Hugo Boss Bottled",
}

PERFUMES_CATALOG = [
    {
        "name": "Tam Dao (SRK)",
        "slug": "tam-dao-srk",
        "short_description": "Original Manufacturer oil made only perfume inspired by Tam Dao (signature scent of Shah Rukh Khan).",
        "full_description": "Original Manufacturer oil made only perfume inspired by Tam Dao, famously worn by Shah Rukh Khan. A masterclass in warmth and understated majesty, balancing sacred Goa sandalwood, crisp Italian cypress, and creamy white amber.",
        "fragrance_family": "Woody Sandalwood",
        "top_notes": "Italian Cypress, Myrtle, Delicate Rose",
        "heart_notes": "Goa Sandalwood, Atlas Cedarwood",
        "base_notes": "Golden Amber, White Musk, Brazilian Rosewood",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "Burberry Weekend",
        "slug": "burberry-weekend",
        "short_description": "Original Manufacturer oil made only perfume inspired by Burberry Weekend.",
        "full_description": "Original Manufacturer oil made only perfume inspired by Burberry Weekend. Relaxing, luminous, and uplifting with sparkling mandarin, sweet nectarine, wild rose, and soft cedarwood.",
        "fragrance_family": "Fresh Citrus Floral",
        "top_notes": "Mandarin Orange, Sage, Reseda",
        "heart_notes": "Blue Hyacinth, Iris, Nectarine, Peach Blossom",
        "base_notes": "Cedarwood, Sandalwood, Sheer Musk",
        "featured": True,
        "bestseller": False,
    },
    {
        "name": "Azzaro Most Wanted",
        "slug": "azzaro-most-wanted",
        "short_description": "Original Manufacturer oil made only perfume inspired by Azzaro The Most Wanted.",
        "full_description": "Original Manufacturer oil made only perfume inspired by Azzaro The Most Wanted. An ultra-addictive, magnetic oriental fragrance featuring fiery cardamom, decadent toffee caramel, and smoky bourbon vanilla.",
        "fragrance_family": "Amber Woody Gourmand",
        "top_notes": "Guatemalan Cardamom, Mandarin",
        "heart_notes": "Toffee Caramel, Provence Lavender",
        "base_notes": "Bourbon Vanilla, Amberwood",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "YSL Libre",
        "slug": "ysl-libre",
        "short_description": "Original Manufacturer oil made only perfume inspired by YSL Libre.",
        "full_description": "Original Manufacturer oil made only perfume inspired by YSL Libre. A bold declaration of freedom uniting burning Moroccan orange blossom, crisp French lavender, and glowing Madagascar vanilla.",
        "fragrance_family": "Floral Lavender",
        "top_notes": "French Diva Lavender, Mandarin, Blackcurrant",
        "heart_notes": "Moroccan Orange Blossom, Jasmine Sambac",
        "base_notes": "Madagascar Vanilla, Cedarwood, Ambergris",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "Armani Tobacco",
        "slug": "armani-tobacco",
        "short_description": "Original Manufacturer oil made only perfume inspired by Armani Privé Tobacco.",
        "full_description": "Original Manufacturer oil made only perfume inspired by Armani Privé Tobacco. An aristocratic, intoxicating blend of rich aromatic pipe tobacco, sweet dried fruits, honey, and warm oriental resins.",
        "fragrance_family": "Oriental Tobacco",
        "top_notes": "Spicy Ginger, Blonde Tobacco Leaf, Osmanthus",
        "heart_notes": "Golden Honey, Dried Fruits, Clove",
        "base_notes": "Tonka Bean, Bourbon Vanilla, Benzoin Resins",
        "featured": False,
        "bestseller": True,
    },
    {
        "name": "Dior Homme",
        "slug": "dior-homme",
        "short_description": "Original Manufacturer oil made only perfume inspired by Dior Homme.",
        "full_description": "Original Manufacturer oil made only perfume inspired by Dior Homme. Sophisticated masculine elegance defined by noble Tuscan iris, warm cocoa, pink pepper, and Virginia cedarwood.",
        "fragrance_family": "Woody Floral Musk",
        "top_notes": "Bergamot, Pink Pepper, Elemi",
        "heart_notes": "Tuscan Iris, Cashmere Wood, Atlas Cedar",
        "base_notes": "Haitian Vetiver, White Musk, Iso E Super",
        "featured": True,
        "bestseller": False,
    },
    {
        "name": "Imperial Valley",
        "slug": "imperial-valley",
        "short_description": "Original Manufacturer oil made only perfume inspired by Gissah Imperial Valley.",
        "full_description": "Original Manufacturer oil made only perfume inspired by Gissah Imperial Valley. Regal and commanding, blending rare Davana herbs, Italian bergamot, pink pepper, rosemary, and Cambodian agarwood.",
        "fragrance_family": "Oriental Aromatic",
        "top_notes": "Davana, Italian Bergamot, Pink Pepper",
        "heart_notes": "Rosemary, White Amber, Smoky Agarwood",
        "base_notes": "Leather Accord, Vetiver, Musk",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "Gucci Guilty",
        "slug": "gucci-guilty",
        "short_description": "Original Manufacturer oil made only perfume inspired by Gucci Guilty.",
        "full_description": "Original Manufacturer oil made only perfume inspired by Gucci Guilty. An alluring, fearless fragrance of sparkling pink pepper, lilac petals, patchouli, and sensual golden amber.",
        "fragrance_family": "Amber Floral",
        "top_notes": "Pink Pepper, Mandarin Orange, Bergamot",
        "heart_notes": "Lilac, Peach, Geranium, Jasmine",
        "base_notes": "Patchouli, Amber, White Musk, Vanilla",
        "featured": False,
        "bestseller": True,
    },
    {
        "name": "CK One",
        "slug": "ck-one",
        "short_description": "Original Manufacturer oil made only perfume inspired by CK One.",
        "full_description": "Original Manufacturer oil made only perfume inspired by CK One. The quintessential clean, universal scent featuring green tea, papaya, bergamot, and sheer skin musk.",
        "fragrance_family": "Citrus Aromatic",
        "top_notes": "Lemon, Green Notes, Bergamot, Pineapple, Papaya",
        "heart_notes": "Lily-of-the-Valley, Jasmine, Violet, Nutmeg",
        "base_notes": "Green Tea, Musk, Cedar, Sandalwood, Oakmoss",
        "featured": False,
        "bestseller": False,
    },
    {
        "name": "Hugo Boss Bottled",
        "slug": "hugo-boss-bottled",
        "short_description": "Original Manufacturer oil made only perfume inspired by Hugo Boss Bottled.",
        "full_description": "Original Manufacturer oil made only perfume inspired by Hugo Boss Bottled. Crisp red apple, warm cinnamon spice, geranium, and rich sandalwood crafted for the driven modern man.",
        "fragrance_family": "Woody Spicy",
        "top_notes": "Crisp Apple, Plum, Bergamot, Lemon",
        "heart_notes": "Cinnamon, Mahogany Wood, Carnation, Geranium",
        "base_notes": "Vanilla, Sandalwood, Cedar, Vetiver",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "CR7 (Cristiano Ronaldo)",
        "slug": "cr7-cristiano-ronaldo",
        "short_description": "Original Manufacturer oil made only perfume inspired by CR7 (Cristiano Ronaldo). Made in 50ml & 100ml.",
        "full_description": "Original Manufacturer oil made only perfume inspired by CR7 (Cristiano Ronaldo). An energetic, charismatic fragrance with bold cardamom, fresh lavender, warm cinnamon, and smoky cedarwood.",
        "fragrance_family": "Aromatic Fougere",
        "top_notes": "Bergamot, Artemisia, Cardamom, Lavender",
        "heart_notes": "Cinnamon, Cedarwood, Iris, Tobacco",
        "base_notes": "Sandalwood, Amber, Vanilla, Musk",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "Montblanc Legend",
        "slug": "montblanc-legend",
        "short_description": "Original Manufacturer oil made only perfume inspired by Montblanc Legend.",
        "full_description": "Original Manufacturer oil made only perfume inspired by Montblanc Legend. Classic charisma blending fresh bergamot, French lavender, pineapple leaf, and exotic sandalwood.",
        "fragrance_family": "Aromatic Fougere",
        "top_notes": "Lavender, Pineapple, Bergamot, Lemon Verbena",
        "heart_notes": "Red Apple, Dried Fruits, Oakmoss, Geranium",
        "base_notes": "Tonka Bean, Sandalwood",
        "featured": False,
        "bestseller": True,
    },
    {
        "name": "Imagination",
        "slug": "imagination",
        "short_description": "Original Manufacturer oil made only perfume inspired by Louis Vuitton Imagination.",
        "full_description": "Original Manufacturer oil made only perfume inspired by Louis Vuitton Imagination. An exhilarating trail of rare Chinese black tea, Sicilian citrus, and radiant ambroxan.",
        "fragrance_family": "Citrus Aromatic",
        "top_notes": "Calabrian Bergamot, Sicilian Orange, Citron",
        "heart_notes": "Ceylon Black Tea, Tunisian Neroli, Nigerian Ginger",
        "base_notes": "Ambroxan, Olibanum, Guaiac Wood",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "Khamrah Qahwa",
        "slug": "khamrah-qahwa",
        "short_description": "Original Manufacturer oil made only perfume inspired by Lattafa Khamrah Qahwa.",
        "full_description": "Original Manufacturer oil made only perfume inspired by Khamrah Qahwa. Warm roasted Arabic coffee, candied ginger, sweet praline, and creamy bourbon vanilla.",
        "fragrance_family": "Gourmand Oriental",
        "top_notes": "Cinnamon, Cardamom, Ginger",
        "heart_notes": "Roasted Coffee (Qahwa), Praline, Candied Fruits, White Flowers",
        "base_notes": "Coffee Beans, Vanilla, Tonka Bean, Benzoin, Musk",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "Astral (FIFA)",
        "slug": "astral-fifa",
        "short_description": "Original Manufacturer oil made only perfume inspired by Astral FIFA Edition.",
        "full_description": "Original Manufacturer oil made only perfume inspired by Astral FIFA Edition. Dynamic energizing citrus, invigorating ocean spray, and sporty woody amber.",
        "fragrance_family": "Fresh Sporty Aquatic",
        "top_notes": "Grapefruit, Marine Ozone, Mandarin",
        "heart_notes": "Bay Leaf, Jasmine, Lavender",
        "base_notes": "Guaiac Wood, Oakmoss, Patchouli, Ambergris",
        "featured": False,
        "bestseller": True,
    },
    {
        "name": "Aggressive",
        "slug": "aggressive",
        "short_description": "Original Manufacturer oil made only perfume with dark woods, spice, and smoky leather.",
        "full_description": "Original Manufacturer oil made only perfume. A commanding, intensely masculine fragrance crafted with dark woods, cracked black pepper, smoky leather, and deep amber.",
        "fragrance_family": "Intense Woody Leather",
        "top_notes": "Black Pepper, Bergamot, Pink Peppercorn",
        "heart_notes": "Smoky Leather, Cedarwood, Vetiver",
        "base_notes": "Agarwood (Oud), Dark Amber, Patchouli",
        "featured": True,
        "bestseller": False,
    },
    {
        "name": "Tom Ford Vanilla",
        "slug": "tom-ford-vanilla",
        "short_description": "Original Manufacturer oil made only perfume inspired by Tom Ford Tobacco Vanille.",
        "full_description": "Original Manufacturer oil made only perfume inspired by Tom Ford Tobacco Vanille. Rich creamy Madagascar vanilla, aromatic spices, cocoa, and warm tonka bean.",
        "fragrance_family": "Oriental Gourmand",
        "top_notes": "Tobacco Leaf, Spicy Aromatics",
        "heart_notes": "Bourbon Vanilla, Cacao, Tonka Bean, Tobacco Blossom",
        "base_notes": "Dried Fruits, Woody Resins",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "Davidoff Cool Water (Akshay Kumar)",
        "slug": "davidoff-cool-water-akshay-kumar",
        "short_description": "Original Manufacturer oil made only perfume inspired by Davidoff Cool Water (as worn by Akshay Kumar).",
        "full_description": "Original Manufacturer oil made only perfume inspired by Davidoff Cool Water, signature fragrance of Akshay Kumar. Crisp ocean breeze, peppermint, lavender, and warm amber.",
        "fragrance_family": "Aromatic Aquatic",
        "top_notes": "Sea Water, Mint, Green Notes, Lavender, Rosemary",
        "heart_notes": "Sandalwood, Jasmine, Neroli, Geranium",
        "base_notes": "Musk, Oakmoss, Cedar, Amber, Tobacco",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "Club de Nuit Armaf",
        "slug": "club-de-nuit-armaf",
        "short_description": "Original Manufacturer oil made only perfume inspired by Club De Nuit Intense Armaf.",
        "full_description": "Original Manufacturer oil made only perfume inspired by Club De Nuit Intense Man Armaf. Zesty lemon, smoky birch, crisp apple, blackcurrant, and ambergris.",
        "fragrance_family": "Woody Spicy",
        "top_notes": "Lemon, Pineapple, Blackcurrant, Apple, Bergamot",
        "heart_notes": "Birch, Jasmine, Rose",
        "base_notes": "Musk, Ambergris, Patchouli, Vanilla",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "Carolina Herrera - Good Girl",
        "slug": "carolina-herrera-good-girl",
        "short_description": "Original Manufacturer oil made only perfume inspired by Carolina Herrera Good Girl.",
        "full_description": "Original Manufacturer oil made only perfume inspired by Carolina Herrera Good Girl. Sensual tuberose, roasted tonka bean, white sambac jasmine, and dark cocoa.",
        "fragrance_family": "Oriental Floral",
        "top_notes": "Almond, Coffee, Bergamot, Lemon",
        "heart_notes": "Tuberose, Jasmine Sambac, Orange Blossom, Orris",
        "base_notes": "Tonka Bean, Cacao, Vanilla, Praline, Sandalwood",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "Dubai Gold",
        "slug": "dubai-gold",
        "short_description": "Original Manufacturer oil made only perfume inspired by luxury Arabian Dubai Gold.",
        "full_description": "Original Manufacturer oil made only perfume inspired by luxury Arabian Dubai Gold. Opulent royal saffron, golden amber, damask rose, and precious Cambodian agarwood.",
        "fragrance_family": "Oriental Amber Oud",
        "top_notes": "Royal Saffron, Bergamot, Cardamom",
        "heart_notes": "Damask Rose, Amber, Incense",
        "base_notes": "Cambodian Agarwood, White Musk, Patchouli",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "Roja Mischief (Hardik Pandya)",
        "slug": "roja-mischief-hardik-pandya",
        "short_description": "Original Manufacturer oil made only perfume inspired by Roja Mischief (signature scent of Hardik Pandya).",
        "full_description": "Original Manufacturer oil made only perfume inspired by Roja Mischief, worn by Hardik Pandya. Crisp bergamot, violet leaf, aromatic spice, and luxurious soft leather.",
        "fragrance_family": "Citrus Woody Chypre",
        "top_notes": "Bergamot, Lemon, Grapefruit, Lime",
        "heart_notes": "Lily-of-the-Valley, Rose de Mai, Jasmin de Grasse",
        "base_notes": "Galbanum, Cedarwood, Pink Pepper, Benzoin, Leather",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "Creed Silver Mountain (Shahid Kapoor/ Virat Kohli)",
        "slug": "creed-silver-mountain-shahid-kapoor-virat-kohli",
        "short_description": "Original Manufacturer oil made only perfume inspired by Creed Silver Mountain Water (Shahid Kapoor / Virat Kohli).",
        "full_description": "Original Manufacturer oil made only perfume inspired by Creed Silver Mountain Water, signature scent of Shahid Kapoor & Virat Kohli. Sparkling green tea, blackcurrant, alpine freshness, and creamy sandalwood.",
        "fragrance_family": "Fresh Aromatic",
        "top_notes": "Bergamot, Mandarin Orange",
        "heart_notes": "Green Tea, Blackcurrant",
        "base_notes": "Musk, Petitgrain, Sandalwood, Galbanum",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "Zara Unisex",
        "slug": "zara-unisex",
        "short_description": "Original Manufacturer oil made only perfume inspired by Zara Unisex Collection.",
        "full_description": "Original Manufacturer oil made only perfume inspired by Zara Unisex Collection. Clean, versatile crisp aromatics, subtle pink pepper, and velvety cedarwood.",
        "fragrance_family": "Fresh Woody Clean",
        "top_notes": "Mandarin, Pink Pepper, Clean Cotton Accord",
        "heart_notes": "White Tea, Cedarwood, Lily",
        "base_notes": "Amber, Vetiver, Soft White Musk",
        "featured": False,
        "bestseller": False,
    },
    {
        "name": "Invictus",
        "slug": "invictus",
        "short_description": "Original Manufacturer oil made only perfume inspired by Paco Rabanne Invictus.",
        "full_description": "Original Manufacturer oil made only perfume inspired by Paco Rabanne Invictus. Energizing marine accord, fresh grapefruit, aromatic bay leaf, and guaiac wood.",
        "fragrance_family": "Woody Aquatic",
        "top_notes": "Sea Notes, Grapefruit, Mandarin Orange",
        "heart_notes": "Bay Leaf, Jasmine",
        "base_notes": "Ambergris, Guaiac Wood, Oakmoss, Patchouli",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "Versace Eros",
        "slug": "versace-eros",
        "short_description": "Original Manufacturer oil made only perfume inspired by Versace Eros.",
        "full_description": "Original Manufacturer oil made only perfume inspired by Versace Eros. Crisp Italian mint, candied green apple, tonka bean, and warm cedarwood.",
        "fragrance_family": "Aromatic Fougere",
        "top_notes": "Mint, Green Apple, Lemon",
        "heart_notes": "Tonka Bean, Ambroxan, Geranium",
        "base_notes": "Madagascar Vanilla, Virginian Cedar, Atlas Cedar, Vetiver, Oakmoss",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "Men in Black",
        "slug": "men-in-black",
        "short_description": "Original Manufacturer oil made only perfume inspired by Bvlgari Man in Black.",
        "full_description": "Original Manufacturer oil made only perfume inspired by Bvlgari Man in Black. Vibrant spicy rum, magnetic leather, tuberose, and smoky guaiac wood.",
        "fragrance_family": "Amber Floral Spicy",
        "top_notes": "Spices, Rum, Tobacco",
        "heart_notes": "Leather, Iris, Tuberose",
        "base_notes": "Tonka Bean, Guaiac Wood, Benzoin",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "YSL Mon Paris",
        "slug": "ysl-mon-paris",
        "short_description": "Original Manufacturer oil made only perfume inspired by YSL Mon Paris.",
        "full_description": "Original Manufacturer oil made only perfume inspired by YSL Mon Paris. Sweet strawberry, raspberry, bergamot, white datura flower, and sensual patchouli.",
        "fragrance_family": "Chypre Fruity",
        "top_notes": "Strawberry, Raspberry, Pear, Calabrian Bergamot",
        "heart_notes": "Datura, Peony, Orange Blossom, Jasmine Sambac",
        "base_notes": "Indonesian Patchouli Leaf, White Musk, Ambroxan, Cedar",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "Balmain Paris",
        "slug": "balmain-paris",
        "short_description": "Original Manufacturer oil made only perfume inspired by Balmain Paris.",
        "full_description": "Original Manufacturer oil made only perfume inspired by Balmain Paris. Refined French elegance, powdery iris, velvety cedarwood, and warm sensual musk.",
        "fragrance_family": "Woody Floral Sophisticated",
        "top_notes": "Bergamot, Pink Pepper, Violet Leaves",
        "heart_notes": "French Iris, Damask Rose, Cedarwood",
        "base_notes": "Sandalwood, Tonka Bean, White Musk",
        "featured": False,
        "bestseller": True,
    },
]

CAR_CATALOG = [
    {
        "name": "Amber Noir Luxury Car Diffuser",
        "slug": "amber-noir-luxury-car-diffuser",
        "short_description": "Artisanal wooden car diffuser with amber, cedarwood, and rich leather notes. Lasts 60+ days.",
        "full_description": "Artisanal wooden car diffuser infused with amber, cedarwood, and leather notes. Features slow-evaporating natural beechwood cap. Keeps your car cabin effortlessly luxurious.",
        "fragrance_family": "Woody Leather",
        "top_notes": "Cardamom, Bergamot",
        "heart_notes": "Leather, Iris, Warm Amber",
        "base_notes": "Cedarwood, Vetiver, Sandalwood",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "Citrus Velvet Luxury Car Diffuser",
        "slug": "citrus-velvet-luxury-car-diffuser",
        "short_description": "Artisanal hanging car diffuser with Sicilian mandarin, blue eucalyptus, and fresh mint.",
        "full_description": "Eliminates vehicle odors instantly while delivering clean, awakening aroma. Crafted with natural essential oils and slow-diffusing wooden cap.",
        "fragrance_family": "Citrus Fresh",
        "top_notes": "Sicilian Mandarin, Mint, Lemon",
        "heart_notes": "Blue Eucalyptus, Rosemary",
        "base_notes": "Clean Musk, White Cedar",
        "featured": True,
        "bestseller": True,
    },
    {
        "name": "Royal Oud & Woods Luxury Car Diffuser",
        "slug": "royal-oud-woods-luxury-car-diffuser",
        "short_description": "Opulent Cambodian agarwood and smoky saffron designed for an executive car interior.",
        "full_description": "Bring royal nighttime grandeur into your car cabin. Rich notes of smoky agarwood, saffron, and white amber that diffuse gently without overwhelming.",
        "fragrance_family": "Oriental Woody",
        "top_notes": "Saffron, Rose, Bergamot",
        "heart_notes": "Agarwood (Oud), Labdanum",
        "base_notes": "Amber, Sandalwood, Musk",
        "featured": True,
        "bestseller": False,
    },
    {
        "name": "Aqua Marine Breeze Luxury Car Diffuser",
        "slug": "aqua-marine-breeze-luxury-car-diffuser",
        "short_description": "Coastal ocean breeze, sea salt spray, and refreshing driftwood for daily commuting freshness.",
        "full_description": "Crisp, airy, and rejuvenating. Aqua Marine Breeze brings Mediterranean ocean air, sea salt, and coastal woods into your daily drive.",
        "fragrance_family": "Aquatic Marine",
        "top_notes": "Marine Ozone, Sea Salt, Lemon",
        "heart_notes": "Water Lily, Sage",
        "base_notes": "Driftwood, Cedarwood",
        "featured": False,
        "bestseller": True,
    },
]


def seed_perfumes_catalog(cat_fine: Category, cat_car: Category):
    """Inserts all fine fragrances, car perfumes, variants, and combos."""
    created_variants = {}

    for pdata in PERFUMES_CATALOG:
        prod = Product.query.filter_by(slug=pdata["slug"]).first()
        if not prod:
            prod = Product(
                category_id=cat_fine.id,
                name=pdata["name"],
                slug=pdata["slug"],
                short_description=pdata["short_description"],
                full_description=pdata["full_description"],
                fragrance_family=pdata["fragrance_family"],
                top_notes=pdata["top_notes"],
                heart_notes=pdata["heart_notes"],
                base_notes=pdata["base_notes"],
                usage_instructions="Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.",
                active=True,
                featured=pdata["featured"],
                bestseller=pdata["bestseller"],
            )
            db.session.add(prod)
            db.session.flush()

            img = ProductImage(
                product_id=prod.id,
                image_key=PERFUME_IMG,
                alt_text=f"{prod.name} Luxury Eau De Parfum bottle",
                is_primary=True,
                display_order=0,
            )
            db.session.add(img)

            var_idx = 0
            if pdata["name"] in PERFUMES_WITH_30ML_OFFER:
                v30 = ProductVariant(
                    product_id=prod.id,
                    size_label="30ml EDP",
                    sku=f"{prod.slug[:8].upper()}-30ML",
                    price=Decimal("499.00"),
                    discounted_price=Decimal("380.00"),  # Pre-launch offer flat ₹380
                    stock=50,
                    display_order=var_idx,
                    active=True,
                )
                db.session.add(v30)
                db.session.flush()
                created_variants[v30.sku] = v30
                var_idx += 1

            v50 = ProductVariant(
                product_id=prod.id,
                size_label="50ml EDP",
                sku=f"{prod.slug[:8].upper()}-50ML",
                price=Decimal("799.00"),
                discounted_price=Decimal("649.00"),
                stock=45,
                display_order=var_idx,
                active=True,
            )
            db.session.add(v50)
            db.session.flush()
            created_variants[v50.sku] = v50
            var_idx += 1

            v100 = ProductVariant(
                product_id=prod.id,
                size_label="100ml EDP",
                sku=f"{prod.slug[:8].upper()}-100ML",
                price=Decimal("1399.00"),
                discounted_price=Decimal("1149.00"),
                stock=30,
                display_order=var_idx,
                active=True,
            )
            db.session.add(v100)
            db.session.flush()
            created_variants[v100.sku] = v100
        else:
            for v in prod.variants:
                created_variants[v.sku] = v

    for cdata in CAR_CATALOG:
        prod = Product.query.filter_by(slug=cdata["slug"]).first()
        if not prod:
            prod = Product(
                category_id=cat_car.id,
                name=cdata["name"],
                slug=cdata["slug"],
                short_description=cdata["short_description"],
                full_description=cdata["full_description"],
                fragrance_family=cdata["fragrance_family"],
                top_notes=cdata["top_notes"],
                heart_notes=cdata["heart_notes"],
                base_notes=cdata["base_notes"],
                usage_instructions="Invert bottle for 3 seconds to saturate wooden cap. Hang from rearview mirror.",
                active=True,
                featured=cdata["featured"],
                bestseller=cdata["bestseller"],
            )
            db.session.add(prod)
            db.session.flush()

            img = ProductImage(
                product_id=prod.id,
                image_key=CAR_IMG,
                alt_text=f"{prod.name} Luxury Wooden Car Diffuser",
                is_primary=True,
                display_order=0,
            )
            db.session.add(img)

            v10 = ProductVariant(
                product_id=prod.id,
                size_label="10ml Hanging Diffuser",
                sku=f"CAR-{prod.slug[:6].upper()}-10ML",
                price=Decimal("399.00"),
                discounted_price=Decimal("349.00"),
                stock=60,
                display_order=0,
                active=True,
            )
            db.session.add(v10)
            db.session.flush()
            created_variants[v10.sku] = v10

            v20 = ProductVariant(
                product_id=prod.id,
                size_label="Twin Pack (2 x 10ml)",
                sku=f"CAR-{prod.slug[:6].upper()}-20ML",
                price=Decimal("699.00"),
                discounted_price=Decimal("599.00"),
                stock=40,
                display_order=1,
                active=True,
            )
            db.session.add(v20)
            db.session.flush()
            created_variants[v20.sku] = v20
        else:
            for v in prod.variants:
                created_variants[v.sku] = v

    db.session.flush()

    # Special Bundles & Combos
    tam_dao = Product.query.filter_by(slug="tam-dao-srk").first()
    creed = Product.query.filter_by(slug="creed-silver-mountain-shahid-kapoor-virat-kohli").first()
    roja = Product.query.filter_by(slug="roja-mischief-hardik-pandya").first()
    davidoff = Product.query.filter_by(slug="davidoff-cool-water-akshay-kumar").first()

    tam_v50 = ProductVariant.query.filter_by(product_id=tam_dao.id, size_label="50ml EDP").first() if tam_dao else None
    creed_v50 = ProductVariant.query.filter_by(product_id=creed.id, size_label="50ml EDP").first() if creed else None
    roja_v50 = ProductVariant.query.filter_by(product_id=roja.id, size_label="50ml EDP").first() if roja else None
    davidoff_v50 = ProductVariant.query.filter_by(product_id=davidoff.id, size_label="50ml EDP").first() if davidoff else None

    combo1 = Combo.query.filter_by(slug="prestige-quad-collection-offer").first()
    if not combo1 and tam_v50 and creed_v50 and roja_v50 and davidoff_v50:
        combo1 = Combo(
            name="Prestige Quad Collection (Buy 4 @ ₹2249 Offer)",
            slug="prestige-quad-collection-offer",
            short_description="Special offer bundle: 4 signature 50ml Eau de Parfums at ₹2249 flat.",
            full_description="Exclusive pre-launch special offer! Get 4 of our most coveted 50ml Eau de Parfums: Tam Dao (SRK), Creed Silver Mountain (Shahid Kapoor/Virat Kohli), Roja Mischief (Hardik Pandya), and Davidoff Cool Water (Akshay Kumar).",
            combo_price=Decimal("2249.00"),
            image_key=PERFUME_IMG,
            display_order=1,
            active=True,
        )
        db.session.add(combo1)
        db.session.flush()
        for v in [tam_v50, creed_v50, roja_v50, davidoff_v50]:
            db.session.add(ComboItem(combo_id=combo1.id, product_variant_id=v.id, quantity=1))

    car_amber = Product.query.filter_by(slug="amber-noir-luxury-car-diffuser").first()
    car_citrus = Product.query.filter_by(slug="citrus-velvet-luxury-car-diffuser").first()
    car_oud = Product.query.filter_by(slug="royal-oud-woods-luxury-car-diffuser").first()

    car_amber_v = ProductVariant.query.filter_by(product_id=car_amber.id, size_label="10ml Hanging Diffuser").first() if car_amber else None
    car_citrus_v = ProductVariant.query.filter_by(product_id=car_citrus.id, size_label="10ml Hanging Diffuser").first() if car_citrus else None
    car_oud_v = ProductVariant.query.filter_by(product_id=car_oud.id, size_label="10ml Hanging Diffuser").first() if car_oud else None

    combo2 = Combo.query.filter_by(slug="luxury-car-diffuser-trio").first()
    if not combo2 and car_amber_v and car_citrus_v and car_oud_v:
        combo2 = Combo(
            name="Luxury Car Diffuser Trio Collection",
            slug="luxury-car-diffuser-trio",
            short_description="Artisanal 3-bottle car perfume collection (Gold, Black, & Frosted glass diffusers).",
            full_description="Elevate every drive with our 3-bottle luxury car perfume collection featuring Amber Noir, Citrus Velvet, and Royal Oud. Beautifully crafted with wooden diffusion caps.",
            combo_price=Decimal("849.00"),
            image_key=CAR_IMG,
            display_order=2,
            active=True,
        )
        db.session.add(combo2)
        db.session.flush()
        for v in [car_amber_v, car_citrus_v, car_oud_v]:
            db.session.add(ComboItem(combo_id=combo2.id, product_variant_id=v.id, quantity=1))

    combo3 = Combo.query.filter_by(slug="executive-duo-tam-dao-car").first()
    if not combo3 and tam_v50 and car_amber_v:
        combo3 = Combo(
            name="Executive Duo (Tam Dao 50ml + Amber Noir Car Diffuser)",
            slug="executive-duo-tam-dao-car",
            short_description="Personal signature perfume paired with premium car diffuser.",
            full_description="Signature warmth wherever you go: Tam Dao (SRK) 50ml Eau de Parfum paired with Amber Noir Luxury Car Diffuser 10ml.",
            combo_price=Decimal("899.00"),
            image_key=PERFUME_IMG,
            display_order=3,
            active=True,
        )
        db.session.add(combo3)
        db.session.flush()
        db.session.add(ComboItem(combo_id=combo3.id, product_variant_id=tam_v50.id, quantity=1))
        db.session.add(ComboItem(combo_id=combo3.id, product_variant_id=car_amber_v.id, quantity=1))

    db.session.flush()
