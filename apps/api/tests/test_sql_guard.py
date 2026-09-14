from app.modules.sql.guard import assert_readonly


def test_select_allowed():
    assert_readonly("SELECT * FROM orders LIMIT 10")


def test_drop_rejected():
    try:
        assert_readonly("DROP TABLE orders")
        assert False, "should reject"
    except ValueError as exc:
        assert "SELECT" in str(exc)
