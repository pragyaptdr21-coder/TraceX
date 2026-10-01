import duckdb
import pytest
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "../storage/tracex.duckdb")

def test_database_exists():
    assert os.path.exists(DB_PATH)

def test_schema_columns():
    con = duckdb.connect(DB_PATH)
    columns = [col[0] for col in con.execute("DESCRIBE transactions").fetchall()]
    expected_cols = [
        "Transaction_ID", "Sender_Account", "Receiver_Account", 
        "Sender_IFSC", "Receiver_IFSC", "Amount", "Timestamp", 
        "Payment_Mode", "Narration", "IP_Address", "Device_Type", 
        "internal_id", "is_missing_sender", "is_missing_receiver", 
        "is_invalid_amount", "is_missing_payment_mode", 
        "is_missing_narration", "is_missing_ip", "is_missing_device", 
        "is_duplicate_tx"
    ]
    for col in expected_cols:
        assert col in columns

def test_row_count():
    con = duckdb.connect(DB_PATH)
    count = con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    assert count == 2000000

def test_account_and_txn_are_strings():
    con = duckdb.connect(DB_PATH)
    types = {row[0]: row[1] for row in con.execute("DESCRIBE transactions").fetchall()}
    assert types["Sender_Account"] == "VARCHAR"
    assert types["Receiver_Account"] == "VARCHAR"
    assert types["Transaction_ID"] == "VARCHAR"

def test_timestamp_handling():
    con = duckdb.connect(DB_PATH)
    types = {row[0]: row[1] for row in con.execute("DESCRIBE transactions").fetchall()}
    assert types["Timestamp"] == "TIMESTAMP"
    
def test_duplicate_ids_reported_not_removed():
    con = duckdb.connect(DB_PATH)
    duplicates = con.execute("SELECT COUNT(*) FROM transactions WHERE is_duplicate_tx = True").fetchone()[0]
    assert duplicates > 0 
    
def test_device_type_exists():
    con = duckdb.connect(DB_PATH)
    columns = [col[0] for col in con.execute("DESCRIBE transactions").fetchall()]
    assert "Device_Type" in columns

def test_account_service_works():
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from backend.services.account_service import get_account_summary
    
    con = duckdb.connect(DB_PATH)
    sample_acc = con.execute("SELECT Sender_Account FROM transactions LIMIT 1").fetchone()[0]
    
    summary = get_account_summary(sample_acc)
    assert 'incoming_count' in summary
    assert 'incoming_amount' in summary
    assert 'outgoing_amount' in summary
