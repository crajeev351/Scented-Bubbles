import pytest
from app.models.pages import Page, format_page_content
from app.models.settings import Setting
from app.models.admins import Admin
from app.extensions import db


def test_format_page_content_preserves_existing_html():
    existing_html = "<p>At <strong>Scented Bubbles</strong>, we believe every space deserves luxury.</p>"
    formatted = format_page_content(existing_html)
    assert formatted == existing_html


def test_format_page_content_converts_plain_text_paragraphs():
    plain_text = (
        "Welcome to Scented Bubbles.\n\n"
        "Orders are dispatched within 24-48 business hours.\n\n"
        "Delivery takes 3 to 6 business days across India."
    )
    formatted = format_page_content(plain_text)
    assert "<p>Welcome to Scented Bubbles.</p>" in formatted
    assert "<p>Orders are dispatched within 24-48 business hours.</p>" in formatted
    assert "<p>Delivery takes 3 to 6 business days across India.</p>" in formatted


def test_format_page_content_handles_linebreaks_and_lists():
    plain_text = (
        "Shipping Information:\n"
        "Standard delivery via Blue Dart or Delhivery.\n\n"
        "Required Documents:\n\n"
        "- Order ID\n"
        "- Unboxing video\n"
        "- Clear photos of package"
    )
    formatted = format_page_content(plain_text)
    # Paragraph with line break
    assert "Shipping Information:<br>Standard delivery via Blue Dart or Delhivery." in formatted
    # Section title
    assert "<h3>Required Documents</h3>" in formatted or "<p>Required Documents:</p>" in formatted
    # Bullet list
    assert "<ul><li>Order ID</li><li>Unboxing video</li><li>Clear photos of package</li></ul>" in formatted


def test_format_page_content_handles_numbered_list():
    plain_text = (
        "1. Open the parcel carefully.\n"
        "2. Record a continuous unboxing video.\n"
        "3. Contact care within 48 hours."
    )
    formatted = format_page_content(plain_text)
    assert "<ol><li>Open the parcel carefully.</li><li>Record a continuous unboxing video.</li><li>Contact care within 48 hours.</li></ol>" in formatted


def test_page_model_formatted_content_property(app):
    with app.app_context():
        page = Page(
            slug="test-plain-policy",
            title="Test Plain Policy",
            content="This is paragraph one.\n\nThis is paragraph two.",
            is_active=True,
        )
        assert "<p>This is paragraph one.</p>" in page.formatted_content
        assert "<p>This is paragraph two.</p>" in page.formatted_content


def test_admin_saves_plain_text_policy_and_renders_on_storefront(client, app):
    with app.app_context():
        admin = Admin.query.filter_by(username="admin").first()
        if not admin:
            admin = Admin(username="admin", email="admin@scentedbubbles.com", is_active=True, role="superadmin")
            admin.set_password("AdminSecurePassword123!")
            db.session.add(admin)
            db.session.commit()
        admin_id = admin.id

        # Ensure page exists
        page = Page.query.filter_by(slug="shipping-policy").first()
        if not page:
            page = Page(slug="shipping-policy", title="Shipping Policy", content="<p>Old content</p>", is_active=True)
            db.session.add(page)
            db.session.commit()

        # Log in as admin
        with client.session_transaction() as sess:
            sess["admin_id"] = admin_id
            sess["admin_username"] = "admin"
            sess["admin_role"] = "superadmin"

        # POST non-HTML plain text as a non-technical admin would
        plain_input = (
            "We offer express shipping nationwide.\n\n"
            "All orders are packed in eco-friendly bubble cushions.\n\n"
            "- Free shipping above ₹999\n"
            "- Standard dispatch in 24 hours"
        )
        res = client.post(
            "/admin/pages/shipping-policy/edit",
            data={
                "title": "Shipping Policy | Scented Bubbles",
                "badge_tag": "Express Logistics",
                "subtitle": "Everything about our pan-India delivery network.",
                "content": plain_input,
                "is_active": "1",
            },
            follow_redirects=True,
        )
        assert res.status_code == 200

        # Check DB content is formatted
        updated_page = Page.query.filter_by(slug="shipping-policy").first()
        assert "<p>We offer express shipping nationwide.</p>" in updated_page.content
        assert "<ul><li>Free shipping above ₹999</li><li>Standard dispatch in 24 hours</li></ul>" in updated_page.content
        assert updated_page.badge_tag == "Express Logistics"
        assert updated_page.subtitle == "Everything about our pan-India delivery network."

    # Now verify public policy page renders with dynamic badge, subtitle, and body
    public_res = client.get("/policies/shipping-policy")
    assert public_res.status_code == 200
    html_text = public_res.get_data(as_text=True)
    assert "Express Logistics" in html_text
    assert "Everything about our pan-India delivery network." in html_text
    assert "We offer express shipping nationwide." in html_text
    assert "policy-page-body" in html_text


def test_about_page_header_and_features_dynamic_editing(client, app):
    with app.app_context():
        admin = Admin.query.filter_by(username="admin").first()
        if not admin:
            admin = Admin(username="admin", email="admin@scentedbubbles.com", is_active=True, role="superadmin")
            admin.set_password("AdminSecurePassword123!")
            db.session.add(admin)
            db.session.commit()
        admin_id = admin.id

        # Ensure about page exists
        page = Page.query.filter_by(slug="about-us").first()
        if not page:
            page = Page(slug="about-us", title="The Story of Scented Bubbles", content="<p>Story</p>", is_active=True)
            db.session.add(page)
            db.session.commit()

        with client.session_transaction() as sess:
            sess["admin_id"] = admin_id
            sess["admin_username"] = "admin"
            sess["admin_role"] = "superadmin"

        # Edit About page with custom badge, heading, subtitle, and features
        res = client.post(
            "/admin/pages/about-us/edit",
            data={
                "title": "Our Fragrance Odyssey",
                "badge_tag": "Artisanal Atelier",
                "subtitle": "Handcrafted perfumery formulated with quiet opulence.",
                "content": "Born from a devotion to French perfumery traditions.",
                "show_features": "1",
                "feature1_title": "Skin-Loving Botanical Extract",
                "feature1_desc": "Zero parabens, 100% cosmetic grade carriers.",
                "feature2_title": "Beechwood Evaporation",
                "feature2_desc": "Continuous sillage lasting up to 65 days.",
                "is_active": "1",
            },
            follow_redirects=True,
        )
        assert res.status_code == 200

    # Verify public About page renders new dynamic content
    res_pub = client.get("/about")
    assert res_pub.status_code == 200
    html = res_pub.get_data(as_text=True)
    assert "Artisanal Atelier" in html
    assert "Our Fragrance Odyssey" in html
    assert "Handcrafted perfumery formulated with quiet opulence." in html
    assert "Skin-Loving Botanical Extract" in html
    assert "Zero parabens, 100% cosmetic grade carriers." in html
    assert "Beechwood Evaporation" in html
    assert "Continuous sillage lasting up to 65 days." in html


def test_about_page_disable_features(client, app):
    with app.app_context():
        admin = Admin.query.filter_by(username="admin").first()
        if not admin:
            admin = Admin(username="admin", email="admin@scentedbubbles.com", is_active=True, role="superadmin")
            admin.set_password("AdminSecurePassword123!")
            db.session.add(admin)
            db.session.commit()
        admin_id = admin.id

        # Ensure about page exists
        page = Page.query.filter_by(slug="about-us").first()
        if not page:
            page = Page(slug="about-us", title="The Story of Scented Bubbles", content="<p>Story</p>", is_active=True)
            db.session.add(page)
            db.session.commit()

        with client.session_transaction() as sess:
            sess["admin_id"] = admin_id
            sess["admin_username"] = "admin"
            sess["admin_role"] = "superadmin"

        # Post without show_features
        res = client.post(
            "/admin/pages/about-us/edit",
            data={
                "title": "Minimalist Story",
                "badge_tag": "Our Essence",
                "subtitle": "Only pure aromas.",
                "content": "Minimalist handcrafted oils.",
                "feature1_title": "Feature 1",
                "feature1_desc": "Desc 1",
                "feature2_title": "Feature 2",
                "feature2_desc": "Desc 2",
                "is_active": "1",
            },
            follow_redirects=True,
        )
        assert res.status_code == 200

    res_pub = client.get("/about")
    assert res_pub.status_code == 200
    html = res_pub.get_data(as_text=True)
    assert "Minimalist Story" in html
    assert "Our Essence" in html
    # Features container should not be present when unchecked
    assert "Desc 1" not in html
    assert "Desc 2" not in html


def test_footer_dynamic_settings(client, app):
    with app.app_context():
        admin = Admin.query.filter_by(username="admin").first()
        if not admin:
            admin = Admin(username="admin", email="admin@scentedbubbles.com", is_active=True, role="superadmin")
            admin.set_password("AdminSecurePassword123!")
            db.session.add(admin)
            db.session.commit()
        admin_id = admin.id

        with client.session_transaction() as sess:
            sess["admin_id"] = admin_id
            sess["admin_username"] = "admin"
            sess["admin_role"] = "superadmin"

        # Update Store Settings including footer and business hours
        res = client.post(
            "/admin/settings",
            data={
                "company_name": "Scented Bubbles",
                "footer_text": "Bespoke fine fragrances distilled with organic passion.",
                "footer_tagline": "Pure Fragrance Alchemy & Automotive Elegance",
                "footer_copyright": "© 2026 Scented Bubbles Artisanal Labs.",
                "footer_col1_title": "Exclusive Blends",
                "footer_col2_title": "Help & Support",
                "footer_col3_title": "The Brand",
                "business_hours": "Monday – Friday, 9:00 AM – 8:00 PM IST",
                "support_whatsapp": "919876543210",
                "support_email": "care@scentedbubbles.com",
                "delivery_charge": "50.00",
                "free_delivery_threshold": "999.00",
                "cod_enabled": "false",
                "upi_id": "scentedbubbles@okaxis",
                "smtp_host": "smtp.gmail.com",
                "smtp_port": "587",
                "smtp_user": "test@gmail.com",
            },
            follow_redirects=True,
        )
        assert res.status_code == 200

    # Check that footer renders the new dynamic values on home page
    res_home = client.get("/")
    assert res_home.status_code == 200
    home_html = res_home.get_data(as_text=True)
    assert "Bespoke fine fragrances distilled with organic passion." in home_html
    assert "Pure Fragrance Alchemy &amp; Automotive Elegance" in home_html or "Pure Fragrance Alchemy & Automotive Elegance" in home_html
    assert "© 2026 Scented Bubbles Artisanal Labs." in home_html
    assert "Exclusive Blends" in home_html
    assert "Help &amp; Support" in home_html or "Help & Support" in home_html
    assert "The Brand" in home_html

    # Check contact page renders business hours
    res_contact = client.get("/contact")
    assert res_contact.status_code == 200
    contact_html = res_contact.get_data(as_text=True)
    assert "Monday – Friday, 9:00 AM – 8:00 PM IST" in contact_html
