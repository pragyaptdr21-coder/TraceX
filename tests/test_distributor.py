import duckdb
import pytest
from backend.detection.distributor_detector import DistributorDetector

@pytest.fixture
def test_db():
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE transactions (
            Transaction_ID VARCHAR,
            Sender_Account VARCHAR,
            Receiver_Account VARCHAR,
            Amount DOUBLE,
            Timestamp TIMESTAMP,
            is_invalid_timestamp BOOLEAN DEFAULT False
        )
    """)
    yield con
    con.close()

def test_distributor_3_distinct_receivers(test_db):
    test_db.execute("""
        INSERT INTO transactions VALUES 
        ('IN1', 'EXT', 'MULE', 1000, '2026-01-01 10:00:00', False),
        ('OUT1', 'MULE', 'R1', 300, '2026-01-01 10:05:00', False),
        ('OUT2', 'MULE', 'R2', 300, '2026-01-01 10:10:00', False),
        ('OUT3', 'MULE', 'R3', 300, '2026-01-01 10:15:00', False)
    """)
    detector = DistributorDetector(":memory:")
    original_connect = duckdb.connect
    duckdb.connect = lambda db_path: test_db
    res = detector.detect()
    duckdb.connect = original_connect
    
    assert len(res) == 1
    assert res[0]['account_id'] == 'MULE'
    assert res[0]['evidence']['distinct_downstream_receivers'] == 3

def test_distributor_7_distinct_receivers(test_db):
    test_db.execute("""
        INSERT INTO transactions VALUES 
        ('IN1', 'EXT', 'MULE', 1000, '2026-01-01 10:00:00', False),
        ('OUT1', 'MULE', 'R1', 100, '2026-01-01 10:05:00', False),
        ('OUT2', 'MULE', 'R2', 100, '2026-01-01 10:10:00', False),
        ('OUT3', 'MULE', 'R3', 100, '2026-01-01 10:15:00', False),
        ('OUT4', 'MULE', 'R4', 100, '2026-01-01 10:20:00', False),
        ('OUT5', 'MULE', 'R5', 100, '2026-01-01 10:25:00', False),
        ('OUT6', 'MULE', 'R6', 100, '2026-01-01 10:30:00', False),
        ('OUT7', 'MULE', 'R7', 100, '2026-01-01 10:35:00', False)
    """)
    detector = DistributorDetector(":memory:")
    original_connect = duckdb.connect
    duckdb.connect = lambda db_path: test_db
    res = detector.detect()
    duckdb.connect = original_connect
    
    assert len(res) == 1
    assert res[0]['evidence']['distinct_downstream_receivers'] == 7

def test_distributor_2_distinct_receivers_not_detected(test_db):
    test_db.execute("""
        INSERT INTO transactions VALUES 
        ('IN1', 'EXT', 'MULE', 1000, '2026-01-01 10:00:00', False),
        ('OUT1', 'MULE', 'R1', 500, '2026-01-01 10:05:00', False),
        ('OUT2', 'MULE', 'R2', 500, '2026-01-01 10:10:00', False)
    """)
    detector = DistributorDetector(":memory:")
    original_connect = duckdb.connect
    duckdb.connect = lambda db_path: test_db
    res = detector.detect()
    duckdb.connect = original_connect
    assert len(res) == 0

def test_distributor_8_distinct_receivers_not_detected(test_db):
    test_db.execute("""
        INSERT INTO transactions VALUES 
        ('IN1', 'EXT', 'MULE', 1000, '2026-01-01 10:00:00', False)
    """)
    for i in range(1, 9):
        test_db.execute(f"INSERT INTO transactions VALUES ('OUT{i}', 'MULE', 'R{i}', 100, '2026-01-01 10:05:0{i}', False)")
    
    detector = DistributorDetector(":memory:")
    original_connect = duckdb.connect
    duckdb.connect = lambda db_path: test_db
    res = detector.detect()
    duckdb.connect = original_connect
    assert len(res) == 0

def test_distributor_multiple_to_same_receiver(test_db):
    test_db.execute("""
        INSERT INTO transactions VALUES 
        ('IN1', 'EXT', 'MULE', 1000, '2026-01-01 10:00:00', False),
        ('OUT1', 'MULE', 'R1', 200, '2026-01-01 10:05:00', False),
        ('OUT2', 'MULE', 'R1', 200, '2026-01-01 10:10:00', False),
        ('OUT3', 'MULE', 'R2', 200, '2026-01-01 10:15:00', False),
        ('OUT4', 'MULE', 'R3', 200, '2026-01-01 10:20:00', False)
    """)
    detector = DistributorDetector(":memory:")
    original_connect = duckdb.connect
    duckdb.connect = lambda db_path: test_db
    res = detector.detect()
    duckdb.connect = original_connect
    assert len(res) == 1
    assert res[0]['evidence']['distinct_downstream_receivers'] == 3

def test_distributor_outgoing_before_incoming_excluded(test_db):
    test_db.execute("""
        INSERT INTO transactions VALUES 
        ('IN1', 'EXT', 'MULE', 1000, '2026-01-01 10:00:00', False),
        ('OUT_BEFORE1', 'MULE', 'R1', 200, '2026-01-01 09:00:00', False),
        ('OUT_BEFORE2', 'MULE', 'R2', 200, '2026-01-01 09:10:00', False),
        ('OUT_BEFORE3', 'MULE', 'R3', 200, '2026-01-01 09:20:00', False),
        ('OUT_AFTER1', 'MULE', 'R4', 200, '2026-01-01 10:30:00', False),
        ('OUT_AFTER2', 'MULE', 'R5', 200, '2026-01-01 10:40:00', False)
    """)
    detector = DistributorDetector(":memory:")
    original_connect = duckdb.connect
    duckdb.connect = lambda db_path: test_db
    res = detector.detect()
    duckdb.connect = original_connect
    assert len(res) == 0

def test_distributor_small_incoming_unrelated_large_outgoing(test_db):
    # Test 7: Small incoming amount followed by unrelated large outgoing activity
    test_db.execute("""
        INSERT INTO transactions VALUES 
        ('IN1', 'EXT', 'MULE', 250, '2026-01-01 10:00:00', False),
        ('OUT1', 'MULE', 'R1', 5000, '2026-01-01 10:05:00', False),
        ('OUT2', 'MULE', 'R2', 5000, '2026-01-01 10:10:00', False),
        ('OUT3', 'MULE', 'R3', 5000, '2026-01-01 10:15:00', False)
    """)
    detector = DistributorDetector(":memory:")
    original_connect = duckdb.connect
    duckdb.connect = lambda db_path: test_db
    res = detector.detect()
    duckdb.connect = original_connect
    assert len(res) == 0

def test_distributor_multiple_incoming_transactions(test_db):
    # Test 8: Prevent cross-inbound contamination
    test_db.execute("""
        INSERT INTO transactions VALUES 
        ('IN1', 'EXT', 'MULE', 5000, '2026-01-01 10:00:00', False),
        ('OUT1', 'MULE', 'R1', 1000, '2026-01-01 10:02:00', False),
        ('IN2', 'EXT', 'MULE', 50000, '2026-01-01 10:03:00', False),
        ('OUT2', 'MULE', 'R2', 10000, '2026-01-01 10:04:00', False),
        ('OUT3', 'MULE', 'R3', 10000, '2026-01-01 10:05:00', False)
    """)
    detector = DistributorDetector(":memory:")
    original_connect = duckdb.connect
    duckdb.connect = lambda db_path: test_db
    res = detector.detect()
    duckdb.connect = original_connect
    assert len(res) == 0

def test_distributor_normal_daily_activity(test_db):
    # Test 9: Normal daily fan-out activity unrelated to a specific incoming flow (long window)
    test_db.execute("""
        INSERT INTO transactions VALUES 
        ('IN1', 'EXT', 'MULE', 1000, '2026-01-01 10:00:00', False),
        ('OUT1', 'MULE', 'R1', 300, '2026-01-01 11:00:00', False),
        ('OUT2', 'MULE', 'R2', 300, '2026-01-01 16:00:00', False),
        ('OUT3', 'MULE', 'R3', 300, '2026-01-01 22:00:00', False)
    """)
    detector = DistributorDetector(":memory:")
    original_connect = duckdb.connect
    duckdb.connect = lambda db_path: test_db
    res = detector.detect()
    duckdb.connect = original_connect
    # Should be 0 because 16:00 and 22:00 are outside the 4 hour engineering window
    assert len(res) == 0
