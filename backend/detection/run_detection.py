import time
from backend.detection.velocity_detector import VelocityDetector
from backend.detection.collector_detector import CollectorDetector
from backend.detection.distributor_detector import DistributorDetector
from backend.detection.cycle_detector import CycleDetector
from backend.detection.terminal_detector import TerminalDetector
from backend.detection.risk_engine import RiskEngine
from backend.detection.trail_engine import TrailEngine

DB_PATH = "storage/tracex.duckdb"

def run_all():
    print("Starting TraceX Phase 3 Detection Engine...")
    risk_engine = RiskEngine()
    
    # 1. Velocity Detector
    t0 = time.time()
    vel_detector = VelocityDetector(DB_PATH)
    vel_results = vel_detector.detect()
    t_vel = time.time() - t0
    print(f"Velocity Detector: {len(vel_results)} candidates in {t_vel:.2f}s")
    risk_engine.add_detections(vel_results)
    
    # 2. Collector Detector
    t0 = time.time()
    col_detector = CollectorDetector(DB_PATH, min_unique_senders=5)
    col_results = col_detector.detect()
    t_col = time.time() - t0
    print(f"Collector Detector (L1): {len(col_results)} candidates in {t_col:.2f}s")
    risk_engine.add_detections(col_results)
    
    # 3. Distributor Detector
    t0 = time.time()
    dist_detector = DistributorDetector(DB_PATH)
    dist_results = dist_detector.detect()
    t_dist = time.time() - t0
    print(f"Distributor Detector (L2): {len(dist_results)} candidates in {t_dist:.2f}s")
    risk_engine.add_detections(dist_results)
    
    # 4. Cycle Detector
    t0 = time.time()
    cycle_detector = CycleDetector(DB_PATH)
    cycle_results = cycle_detector.detect()
    t_cycle = time.time() - t0
    print(f"Cycle Detector: {len(cycle_results)} candidates in {t_cycle:.2f}s")
    risk_engine.add_detections(cycle_results)
    
    # 5. Terminal Detector
    t0 = time.time()
    term_detector = TerminalDetector(DB_PATH)
    term_results = term_detector.detect()
    t_term = time.time() - t0
    print(f"Terminal Detector (L3): {len(term_results)} candidates in {t_term:.2f}s")
    risk_engine.add_detections(term_results)
    
    all_risks = risk_engine.get_all_risks()
    high_risks = [r for r in all_risks if r["mule_risk_index"] >= 50]
    print(f"Total Unique Suspect Accounts: {len(all_risks)}")
    print(f"High Risk Accounts (>= 50): {len(high_risks)}")
    
    # Benchmark 4-hop trail
    print("\nBenchmarking 4-Hop Traversal...")
    if high_risks:
        sample_victim = high_risks[0]["account_id"]
    else:
        sample_victim = "100000000001" # Fallback dummy
        
    trail_eng = TrailEngine(DB_PATH)
    t0 = time.time()
    trail_res = trail_eng.get_4_hop_trail(sample_victim)
    t_trail = time.time() - t0
    print(f"4-Hop Trace for {sample_victim}: {len(trail_res['nodes'])} nodes, {len(trail_res['edges'])} edges in {t_trail:.4f}s")

if __name__ == "__main__":
    run_all()
