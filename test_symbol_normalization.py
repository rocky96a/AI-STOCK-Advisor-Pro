from backend.data.symbol_utils import normalize_symbol


def test_stock_symbols():
    assert normalize_symbol("TCS") == "TCS.NS"
    assert normalize_symbol("RELIANCE") == "RELIANCE.NS"
    assert normalize_symbol("INFY") == "INFY.NS"
    assert normalize_symbol("TCS.NS") == "TCS.NS"


def test_index_symbols():
    assert normalize_symbol("NIFTY 50") == "^NSEI"
    assert normalize_symbol("NIFTY50") == "^NSEI"
    assert normalize_symbol("^NSEI") == "^NSEI"
    assert normalize_symbol("SENSEX") == "^BSESN"
    assert normalize_symbol("BANK NIFTY") == "^NSEBANK"
    assert normalize_symbol("BANKNIFTY") == "^NSEBANK"


def test_no_index_suffix():
    assert ".NS" not in normalize_symbol("^NSEI")
    assert ".NS" not in normalize_symbol("^BSESN")
    assert ".NS" not in normalize_symbol("^NSEBANK")
