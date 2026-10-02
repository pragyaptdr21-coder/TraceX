import os
import duckdb
import pytest
from backend.detection.velocity_detector import VelocityDetector
from backend.detection.collector_detector import CollectorDetector
from backend.detection.distributor_detector import DistributorDetector
from backend.detection.cycle_detector import CycleDetector
from backend.detection.terminal_detector import TerminalDetector
from backend.detection.trail_engine import TrailEngine
from backend.detection.risk_engine import RiskEngine

DB_PATH = "storage/tracex.duckdb"

@pytest.fixture(scope="module")
def db_path():
    return DB_PATH

def test_velocity_detector(db_path):
    detector = VelocityDetector(db_path)
    res = detector.detect()
    assert isinstance(res, list)
    if res:
        assert 'account_id' in res[0]
        assert 'ratio' in res[0]['evidence']

def test_collector_detector(db_path):
    detector = CollectorDetector(db_path)
    res = detector.detect()
    assert isinstance(res, list)

def test_distributor_detector(db_path):
    detector = DistributorDetector(db_path)
    res = detector.detect()
    assert isinstance(res, list)
    if res:
        assert 3 <= res[0]['evidence']['distinct_downstream_receivers'] <= 7

def test_cycle_detector(db_path):
    detector = CycleDetector(db_path)
    # Just checking initialization and type, avoid running 8s query in test
    assert detector.db_path == db_path

def test_terminal_detector(db_path):
    detector = TerminalDetector(db_path)
    res = detector.detect()
    assert isinstance(res, list)
    if res:
        assert 'triggering_indicator' in res[0]['evidence']

def test_trail_engine_unknown_account(db_path):
    engine = TrailEngine(db_path)
    res = engine.get_4_hop_trail("UNKNOWN_ACC_123")
    assert res['root_account'] == "UNKNOWN_ACC_123"
    assert len(res['nodes']) == 1 # Only the root node itself
    assert len(res['edges']) == 0

def test_risk_engine():
    engine = RiskEngine()
    engine.add_detections([
        {"account_id": "ACC1", "detection_type": "COLLECTOR_MULE_L1", "evidence": {}, "score_contribution": 25},
        {"account_id": "ACC1", "detection_type": "TERMINAL_CASH_OUT_L3", "evidence": {}, "score_contribution": 50},
    ])
    risk = engine.get_risk_profile("ACC1")
    assert risk['mule_risk_index'] == 75
    
    # Cap test
    engine.add_detections([
        {"account_id": "ACC1", "detection_type": "DISTRIBUTOR_MULE_L2", "evidence": {}, "score_contribution": 25},
        {"account_id": "ACC1", "detection_type": "HIGH_VELOCITY_PASS_THROUGH", "evidence": {}, "score_contribution": 25}
    ])
    risk2 = engine.get_risk_profile("ACC1")
    assert risk2['mule_risk_index'] == 100
