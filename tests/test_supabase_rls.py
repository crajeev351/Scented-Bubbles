from unittest.mock import MagicMock, patch
from pathlib import Path


def test_enable_rls_cli_help(app):
    """Test flask enable-rls --help works properly."""
    runner = app.test_cli_runner()
    result = runner.invoke(args=["enable-rls", "--help"])
    assert result.exit_code == 0
    assert "Enables Row Level Security (RLS) on all public tables" in result.output


def test_supabase_enable_rls_sql_file_covers_all_tables():
    """Ensure supabase_enable_rls.sql contains statements for all 18 tables flagged by Supabase linter."""
    sql_path = Path(__file__).resolve().parent.parent / "supabase_enable_rls.sql"
    assert sql_path.exists()
    content = sql_path.read_text(encoding="utf-8")

    expected_tables = [
        "admins",
        "banners",
        "order_counters",
        "pages",
        "settings",
        "users",
        "categories",
        "customers",
        "products",
        "orders",
        "combos",
        "product_categories",
        "product_variants",
        "product_images",
        "payments",
        "order_status_history",
        "combo_items",
        "order_items",
    ]

    for table in expected_tables:
        assert f"ALTER TABLE IF EXISTS public.{table} ENABLE ROW LEVEL SECURITY;" in content


def test_enable_rls_script_logic():
    """Test enable_rls execution logic handles tables requiring RLS."""
    from scripts.enable_rls import enable_rls

    mock_conn = MagicMock()
    # Mocking pg_tables query response: 2 tables with RLS False, 1 with RLS True
    mock_conn.execute.return_value.fetchall.side_effect = [
        [("admins", False), ("products", False), ("orders", True)],
        [("admins", True), ("products", True), ("orders", True)],
    ]

    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn

    with patch("scripts.enable_rls.create_engine", return_value=mock_engine):
        enable_rls("postgresql://user:pass@host:5432/db")

    # Verify ALTER TABLE executed for the tables where RLS was False
    executed_statements = [str(call.args[0]) for call in mock_conn.execute.call_args_list]
    assert any('ALTER TABLE public."admins" ENABLE ROW LEVEL SECURITY;' in stmt for stmt in executed_statements)
    assert any('ALTER TABLE public."products" ENABLE ROW LEVEL SECURITY;' in stmt for stmt in executed_statements)
    assert mock_conn.commit.called
