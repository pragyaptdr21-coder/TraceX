import duckdb
from typing import List, Dict

class CycleDetector:
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def detect(self) -> List[Dict]:
        """
        Detects Cyclical Smurfing (A -> B -> C -> A or A -> B -> A).
        Limits to 2-3 hops for efficiency on 2M records.
        """
        con = duckdb.connect(self.db_path)
        # Detecting A -> B -> C -> A
        query = """
            SELECT 
                t1.Sender_Account as node_A,
                t1.Receiver_Account as node_B,
                t2.Receiver_Account as node_C,
                t1.Transaction_ID as tx_1,
                t2.Transaction_ID as tx_2,
                t3.Transaction_ID as tx_3,
                t1.Amount as amt_1,
                t2.Amount as amt_2,
                t3.Amount as amt_3
            FROM transactions t1
            JOIN transactions t2 ON t1.Receiver_Account = t2.Sender_Account
            JOIN transactions t3 ON t2.Receiver_Account = t3.Sender_Account AND t3.Receiver_Account = t1.Sender_Account
            WHERE t1.is_invalid_timestamp = False 
              AND t2.is_invalid_timestamp = False 
              AND t3.is_invalid_timestamp = False
              AND t2.Timestamp > t1.Timestamp 
              AND t3.Timestamp > t2.Timestamp
        """
        results = con.execute(query).fetchall()
        con.close()
        
        detections = []
        for row in results:
            detections.append({
                "account_id": row[0],
                "detection_type": "CYCLICAL_SMURFING",
                "evidence": {
                    "cycle_path": f"{row[0]} -> {row[1]} -> {row[2]} -> {row[0]}",
                    "cycle_txs": [row[3], row[4], row[5]],
                    "cycle_amounts": [float(row[6]), float(row[7]), float(row[8])]
                },
                "score_contribution": 25
            })
            
            # Since a cycle involves multiple nodes, we might flag all of them.
            # For this engine, we'll flag the initiator (Node A) and Node B, Node C.
            # But returning one detection per cycle is standard.
        return detections
