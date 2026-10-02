import duckdb
from typing import List, Dict

class DistributorDetector:
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def detect(self) -> List[Dict]:
        """
        Detects Distributor Mules (L2).
        Requirement: High out-degree centrality, slicing incoming funds into 3-7 downstream accounts.
        
        Engineering Choices for strict attribution:
        1. Temporal Attribution: A 4-hour window is used. This is a TraceX engineering choice to distinguish rapid automated slicing from normal daily account usage, without confusing it with the 3-15 minute rule for L1 Pass-Through.
        2. Amount Attribution: The cumulative outgoing amount must be between 50% and 150% of the incoming amount. This ensures we don't flag unrelated massive outgoing transfers as being sliced from a tiny inbound transaction.
        3. Cross-Inbound Protection: Outgoing transactions are only attributed to an incoming transaction if they occur before the NEXT incoming transaction. This prevents blind attribution of all outgoing activity to the first inbound transaction.
        """
        con = duckdb.connect(self.db_path)
        query = """
            WITH inbound_txs AS (
                SELECT 
                    Transaction_ID,
                    Receiver_Account,
                    Sender_Account,
                    Amount,
                    Timestamp,
                    LEAD(Timestamp) OVER (PARTITION BY Receiver_Account ORDER BY Timestamp ASC) as next_inbound_timestamp
                FROM transactions
                WHERE is_invalid_timestamp = False
            )
            SELECT 
                tin.Receiver_Account as account_id,
                tin.Transaction_ID as inbound_transaction_id,
                tin.Sender_Account as inbound_sender,
                tin.Amount as inbound_amount,
                tin.Timestamp as inbound_timestamp,
                count(DISTINCT tout.Receiver_Account) as distinct_downstream_receivers,
                list({'transaction_id': tout.Transaction_ID, 'receiver': tout.Receiver_Account, 'amount': tout.Amount, 'timestamp': cast(tout.Timestamp as VARCHAR)} ORDER BY tout.Timestamp ASC)[1:20] as downstream_transactions,
                sum(tout.Amount) as outbound_amount
            FROM inbound_txs tin
            JOIN transactions tout 
              ON tin.Receiver_Account = tout.Sender_Account
            WHERE tout.is_invalid_timestamp = False
              AND tout.Timestamp > tin.Timestamp
              AND tout.Timestamp <= tin.Timestamp + INTERVAL 4 HOUR
              AND (tin.next_inbound_timestamp IS NULL OR tout.Timestamp <= tin.next_inbound_timestamp)
            GROUP BY tin.Receiver_Account, tin.Transaction_ID, tin.Sender_Account, tin.Amount, tin.Timestamp
            HAVING count(DISTINCT tout.Receiver_Account) BETWEEN 3 AND 7
               AND sum(tout.Amount) >= tin.Amount * 0.5 
               AND sum(tout.Amount) <= tin.Amount * 1.5
        """
        results = con.execute(query).fetchall()
        con.close()
        
        detections = []
        for row in results:
            detections.append({
                "account_id": row[0],
                "detection_type": "DISTRIBUTOR_MULE_L2",
                "evidence": {
                    "inbound_transaction_id": row[1],
                    "inbound_sender": row[2],
                    "inbound_amount": float(row[3]),
                    "inbound_timestamp": str(row[4]),
                    "distinct_downstream_receivers": row[5],
                    "downstream_transactions": row[6],
                    "cumulative_outbound_amount": float(row[7]),
                    "reason": f"Account received {row[3]} and distributed {row[7]} to {row[5]} distinct downstream accounts within 4 hours, representing strict slicing."
                },
                "score_contribution": 25
            })
        return detections
