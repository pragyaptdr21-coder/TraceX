import duckdb
import time

def run():
    print("Running new Distributor L2 on 2M dataset...")
    start = time.time()
    
    from backend.detection.distributor_detector import DistributorDetector
    detector = DistributorDetector("storage/tracex.duckdb")
    detections = detector.detect()
    
    duration = time.time() - start
    
    total_detections = len(detections)
    unique_accounts = len(set([d['account_id'] for d in detections]))
    avg_per_account = total_detections / unique_accounts if unique_accounts > 0 else 0
    
    receiver_counts = {3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
    for d in detections:
        r_count = d['evidence']['distinct_downstream_receivers']
        if r_count in receiver_counts:
            receiver_counts[r_count] += 1
            
    # Need UNIQUE accounts per receiver count as asked.
    acc_rec_map = {}
    for d in detections:
        acc = d['account_id']
        r = d['evidence']['distinct_downstream_receivers']
        if acc not in acc_rec_map:
            acc_rec_map[acc] = set()
        acc_rec_map[acc].add(r)
        
    uniq_receiver_counts = {3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
    for acc, r_set in acc_rec_map.items():
        for r in r_set:
            if r in uniq_receiver_counts:
                uniq_receiver_counts[r] += 1
    
    print(f"Total detections: {total_detections}")
    print(f"Unique accounts: {unique_accounts}")
    print(f"Time: {duration:.2f} seconds")
    
    examples = ""
    seen_accs = set()
    ex_count = 0
    for d in detections:
        if ex_count >= 10:
            break
        acc = d['account_id']
        if acc in seen_accs:
            continue
        seen_accs.add(acc)
        ex_count += 1
        
        examples += f"\nDistributor account: {acc}\n"
        examples += f"Incoming:\n"
        examples += f"Sender: {d['evidence']['inbound_sender']}\n"
        examples += f"Receiver: {acc}\n"
        examples += f"Amount: {d['evidence']['inbound_amount']}\n"
        examples += f"Timestamp: {d['evidence']['inbound_timestamp']}\n"
        examples += f"Transaction ID: {d['evidence']['inbound_transaction_id']}\n"
        
        examples += f"\nDownstream:\n"
        for out in d['evidence']['downstream_transactions']:
            examples += f"- Transaction ID: {out['transaction_id']} | Receiver: {out['receiver']} | Amount: {out['amount']} | Timestamp: {out['timestamp']}\n"
            
        examples += f"\nDistinct receivers: {d['evidence']['distinct_downstream_receivers']}\n"
        examples += f"Cumulative associated outbound amount: {d['evidence']['cumulative_outbound_amount']}\n"
        examples += f"Temporal relationship: {d['evidence']['inbound_timestamp']} -> {d['evidence']['downstream_transactions'][0]['timestamp']}\n"
        examples += f"Attribution explanation: {d['evidence']['reason']}\n"
        examples += "-" * 40
        
    report = f"""TraceX Phase 3 - Distributor L2 Final Report
=============================================

OLD PROBLEM:
The previous Distributor L2 implementation detected any fan-out of 3-7 distinct receivers within a 24-hour window following any inbound transaction. This led to massive false positives (1,384,689 detections across 23,638 accounts) because ordinary daily account activity was falsely attributed as "slicing" of specific incoming funds.

NEW ALGORITHM:
The new implementation requires strict attribution between the incoming funds and subsequent distribution.
It guarantees that:
1. The downstream transactions occur AFTER the specific incoming transaction.
2. The downstream transactions occur BEFORE any subsequent incoming transaction (cross-inbound protection).
3. The cumulative downstream amount closely matches the incoming amount.
4. The distribution happens within a focused temporal window.
5. The evidence is chronologically ordered.

ENGINEERING CHOICES:
The Problem Statement requires "High out-degree centrality, slicing incoming funds into 3-7 downstream accounts."
To mathematically define "slicing", TraceX implemented these specific engineering choices:

1. Temporal Attribution (4 hours): Reduced from 24 hours to 4 hours to distinguish rapid automated distribution from organic daily spending. We deliberately did NOT copy the 3-15 minute rule because the PDF restricts that specifically to L1 High-Velocity Pass-Through.
2. Amount Attribution (50% to 150%): The sum of the subsequent outgoing transactions must fall between 0.5x and 1.5x of the inbound amount. This guarantees that we aren't flagging an account that receives ₹100 and sends ₹50,000 as "distributing" that ₹100.
3. Cross-Inbound Protection: Uses a SQL Window function `LEAD(Timestamp)` to ensure outgoing transactions are only attributed to an incoming transaction if they happen before the NEXT incoming transaction.

TESTS:
All 9 edge-case test scenarios pass successfully (unit tests).

BEFORE VS AFTER NUMBERS:
Before detection rows: 1,384,689
After detection rows: {total_detections}

Before unique accounts: 23,638
After unique accounts: {unique_accounts}

Execution Time: {duration:.2f} seconds
Average detection rows per account: {avg_per_account:.2f}

Receiver Counts (Unique Accounts):
3 receivers: {uniq_receiver_counts[3]}
4 receivers: {uniq_receiver_counts[4]}
5 receivers: {uniq_receiver_counts[5]}
6 receivers: {uniq_receiver_counts[6]}
7 receivers: {uniq_receiver_counts[7]}

10 REAL EXAMPLES:
{examples}

LIMITATIONS:
The exact 4-hour window and 50-150% amount constraints are rigid. Some sophisticated mules might intentionally distribute amounts over multiple days or slice only 20% of an inbound to evade this strict attribution.
"""
    
    with open("reports/TraceX_Phase3_Distributor_L2_Final_Report.txt", "w") as f:
        f.write(report)
        
    print(f"\nFinal Stats:")
    print(f"Before unique accounts: 23638")
    print(f"After unique accounts: {unique_accounts}")
    print(f"Before detection rows: 1384689")
    print(f"After detection rows: {total_detections}")

if __name__ == "__main__":
    run()
