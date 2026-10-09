"""连接真实本地 Doris 验证 collector(host=127.0.0.1:9030)。Doris 不可达时跳过。"""

import pytest

from app.modules.asset.collector import DorisMetadataConnector


@pytest.fixture(scope="module")
def doris():
    c = DorisMetadataConnector("127.0.0.1", 9030, "root", "")
    try:
        c.test_conn()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"本地 Doris 不可达: {e}")
    return c


def test_live_databases(doris):
    dbs = doris.list_databases()
    assert isinstance(dbs, list)
    assert "credit" in dbs


def test_live_credit_tables(doris):
    tables = doris.list_tables("credit")
    assert tables
    names = {t["name"] for t in tables}
    assert {"customer", "account", "loan_contract"} <= names
    for t in tables:
        assert "num_rows" in t and "data_size" in t and "engine" in t


def test_live_credit_columns(doris):
    cols = doris.list_columns("credit", "customer")
    assert cols
    by_name = {c["name"]: c for c in cols}
    assert "customer_id" in by_name
    # 校验所需列都存在
    assert "data_type" in by_name["customer_id"]
    assert "is_partition" in by_name["customer_id"]