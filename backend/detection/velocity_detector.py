import duckdb
from typing import List, Dict

class VelocityDetector:
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def detect(self) -> List[Dict]:
        """
        Detects High-Velocity Pass-Through accounts.
        Requirement: >= 90% of incoming funds dispersed within 3-15 minutes across multiple transfers.
        """
        con = duckdb.connect(self.db_path)
        query = """
            SELECT 
                tin.Receiver_Account as account_id,
                tin.Transaction_ID as incoming_tx,
                tin.Amount as incoming_amount,
                tin.Timestamp as incoming_ts,
                count(tout.Transaction_ID) as out_count,
                sum(tout.Amount) as out_amount,
                list(tout.Transaction_ID) as outgoing_txs
            FROM transactions tin
            JOIN transactions tout 
              ON tin.Receiver_Account = tout.Sender_Account
            WHERE tin.is_invalid_timestamp = False 
              AND tout.is_invalid_timestamp = False
              AND tout.Timestamp >= tin.Timestamp + INTERVAL 3 MINUTE
              AND tout.Timestamp <= tin.Timestamp + INTERVAL 15 MINUTE
            GROUP BY tin.Receiver_Account, tin.Transaction_ID, tin.Amount, tin.Timestamp
            HAVING sum(tout.Amount) >= 0.9 * tin.Amount
               AND count(tout.Transaction_ID) > 1
        """
        results = con.execute(query).fetchall()
        con.close()
        
        detections = []
        for row in results:
            detections.append({
                "account_id": row[0],
                "detection_type": "HIGH_VELOCITY_PASS_THROUGH",
                "evidence": {
                    "incoming_tx": row[1],
                    "incoming_amount": float(row[2]),
                    "incoming_ts": str(row[3]),
                    "out_count": row[4],
                    "out_amount": float(row[5]),
                    "outgoing_txs": row[6],
                    "ratio": float(row[5]) / float(row[2])
                },
                "score_contribution": 25
            })
        return detections
