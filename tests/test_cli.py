from app.models.admins import Admin


def test_create_admin_cli(app):
    """Test interactive flask create-admin CLI command with valid credentials."""
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=["create-admin"],
        input="storeadmin\nadmin@scentedbubbles.com\nSecurePassword123!\nSecurePassword123!\n",
    )
    assert result.exit_code == 0
    assert "created successfully" in result.output

    with app.app_context():
        admin = Admin.query.filter_by(username="storeadmin").first()
        assert admin is not None
        assert admin.email == "admin@scentedbubbles.com"
        assert admin.check_password("SecurePassword123!") is True
        assert admin.check_password("WrongPassword") is False
