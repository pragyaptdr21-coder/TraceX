import duckdb
from typing import List, Dict

class CollectorDetector:
    def __init__(self, db_path: str, min_unique_senders: int = 5):
        self.db_path = db_path
        self.min_unique_senders = min_unique_senders
        
    def detect(self) -> List[Dict]:
        """
        Detects Collector Mules (L1).
        Requirement: High in-degree centrality, multiple distinct senders depositing money into a single node.
        """
        con = duckdb.connect(self.db_path)
        query = f"""
            SELECT 
                Receiver_Account as account_id,
                count(DISTINCT Sender_Account) as unique_senders,
                count(Transaction_ID) as incoming_tx_count,
                sum(Amount) as total_incoming,
                list(Sender_Account)[1:10] as sample_senders
            FROM transactions
            GROUP BY Receiver_Account
            HAVING count(DISTINCT Sender_Account) >= {self.min_unique_senders}
        """
        results = con.execute(query).fetchall()
        con.close()
        
        detections = []
        for row in results:
            detections.append({
                "account_id": row[0],
                "detection_type": "COLLECTOR_MULE_L1",
                "evidence": {
                    "unique_senders": row[1],
                    "incoming_tx_count": row[2],
                    "total_incoming": float(row[3]),
                    "sample_senders": row[4]
                },
                "score_contribution": 25
            })
        return detections
