import pytest
from app.models.pages import Page, format_page_content
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
        from app.models.admins import Admin
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

    # Now verify public policy page renders with paragraphs
    public_res = client.get("/policies/shipping-policy")
    assert public_res.status_code == 200
    html_text = public_res.get_data(as_text=True)
    assert "We offer express shipping nationwide." in html_text
    assert "policy-page-body" in html_text
