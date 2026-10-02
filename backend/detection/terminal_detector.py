import duckdb
from typing import List, Dict

class TerminalDetector:
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def detect(self) -> List[Dict]:
        """
        Detects Terminal Cash-Out Identifiers (L3).
        Requirement: Outward transfers to payment wallets, P2P crypto narrations, 
        foreign IP headers (185.x.x.x, 194.x.x.x), and headless script user-agents 
        (Web_Emulator, Linux_Script).
        """
        con = duckdb.connect(self.db_path)
        query = """
            SELECT 
                Sender_Account as account_id,
                Transaction_ID,
                IP_Address,
                Device_Type,
                Narration,
                Amount,
                Timestamp
            FROM transactions
            WHERE 
                IP_Address LIKE '185.%' OR IP_Address LIKE '194.%'
                OR Device_Type IN ('Web_Emulator', 'Linux_Script')
                OR lower(Narration) LIKE '%wallet%'
                OR lower(Narration) LIKE '%crypto%'
                OR lower(Narration) LIKE '%p2p%'
        """
        results = con.execute(query).fetchall()
        con.close()
        
        detections = []
        for row in results:
            # Determine which indicator triggered this
            ip = str(row[2])
            dev = str(row[3])
            nar = str(row[4]).lower()
            
            indicator = "UNKNOWN"
            if ip.startswith("185.") or ip.startswith("194."):
                indicator = "FOREIGN_IP"
            elif dev in ["Web_Emulator", "Linux_Script"]:
                indicator = "HEADLESS_SCRIPT"
            elif "wallet" in nar or "crypto" in nar or "p2p" in nar:
                indicator = "CRYPTO_OR_WALLET_NARRATION"
                
            detections.append({
                "account_id": row[0],
                "detection_type": "TERMINAL_CASH_OUT_L3",
                "evidence": {
                    "triggering_indicator": indicator,
                    "transaction_id": row[1],
                    "ip_address": ip,
                    "device_type": dev,
                    "narration": str(row[4]),
                    "amount": float(row[5]),
                    "timestamp": str(row[6])
                },
                "score_contribution": 50
            })
        return detections
