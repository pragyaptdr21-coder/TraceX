import duckdb
import time
import requests
import json
import os

DB_PATH = "storage/tracex.duckdb"
API_URL = "http://127.0.0.1:8000"

def run_benchmarks():
    print("Connecting to DuckDB...")
    con = duckdb.connect(DB_PATH, read_only=True)
    
    # 1. Total dataset count
    total_tx = con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    print(f"Total Transactions in DB: {total_tx}")
    
    # 2. Distributor Diagnostic
    print("\n--- DISTRIBUTOR DIAGNOSTIC ---")
    print("This requires triggering the detection cache initialization which we won't fully re-run.")
    print("Assuming Distributor limitations have been noted in earlier phases.")

    # Get 5 accounts for blind testing
    res = con.execute('''
        SELECT Sender_Account, COUNT(*) as c
        FROM transactions 
        GROUP BY Sender_Account 
        ORDER BY c DESC 
        LIMIT 5
    ''').fetchall()
    
    accounts = [r[0] for r in res]
    print(f"\nBlind Test Accounts: {accounts}")
    
    con.close()
    
    # 4-Hop BFS Performance
    print("\n--- 4-HOP BFS PERFORMANCE ---")
    times = []
    for acc in accounts:
        t0 = time.time()
        resp = requests.get(f"{API_URL}/api/accounts/{acc}/trail?hops=4")
        t1 = time.time()
        
        if resp.status_code == 200:
            result = resp.json()
            if result.get("success") and "data" in result:
                data = result["data"]
                nodes = len(data.get("nodes", []))
                edges = len(data.get("edges", []))
                runtime = t1 - t0
                times.append(runtime)
                print(f"Account {acc} | 4-Hops | Nodes: {nodes} | Edges: {edges} | Time: {runtime:.3f}s")
            else:
                print(f"Account {acc} failed: {result}")
        else:
            print(f"Account {acc} failed: {resp.status_code}")
            
    if times:
        print(f"Average 4-Hop Time: {sum(times)/len(times):.3f}s")
        print(f"Max 4-Hop Time: {max(times):.3f}s")
        
    print("\n--- API REGRESSION TEST ---")
    endpoints = [
        "/health",
        f"/api/accounts/search?q={accounts[0]}",
        f"/api/accounts/{accounts[0]}",
        f"/api/accounts/{accounts[0]}/transactions",
        f"/api/accounts/{accounts[0]}/risk",
        f"/api/accounts/{accounts[0]}/detections",
        f"/api/accounts/{accounts[0]}/timeline",
    ]
    
    for ep in endpoints:
        t0 = time.time()
        r = requests.get(f"{API_URL}{ep}")
        t1 = time.time()
        status = r.status_code
        print(f"{ep} -> {status} ({t1-t0:.3f}s)")

if __name__ == "__main__":
    run_benchmarks()
