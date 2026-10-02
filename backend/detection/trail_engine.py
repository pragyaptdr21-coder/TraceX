import duckdb
from typing import List, Dict, Any

class TrailEngine:
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def get_4_hop_trail(self, victim_account: str, max_hops: int = 4) -> Dict[str, Any]:
        """
        Executes a Breadth-First Search (BFS) to trace downstream funds up to 4 hops.
        Maintains visited sets to prevent infinite loops from cycles.
        """
        con = duckdb.connect(self.db_path, read_only=True)
        
        visited_accounts = {victim_account}
        current_layer = [victim_account]
        
        nodes = [{"id": victim_account, "layer": 0}]
        edges = []
        
        for hop in range(1, max_hops + 1):
            if not current_layer:
                break
                
            # If layer is huge, truncate to prevent memory explosion/latency (e.g., > 5000 accounts)
            if len(current_layer) > 2000:
                current_layer = current_layer[:2000]
                
            # Build an efficient IN clause using direct string interpolation for list
            # DuckDB parser parses this in <1ms and vectorizes it.
            accs_list_str = ", ".join([f"'{acc}'" for acc in current_layer])
            
            query = f"""
                SELECT 
                    Sender_Account, 
                    Receiver_Account, 
                    Sender_IFSC,
                    Receiver_IFSC,
                    Transaction_ID, 
                    Amount, 
                    Timestamp, 
                    Payment_Mode
                FROM transactions
                WHERE Sender_Account IN ({accs_list_str})
            """
            
            results = con.execute(query).fetchall()
            
            next_layer = set()
            for row in results:
                sender = row[0]
                receiver = row[1]
                tx_id = row[4]
                
                edges.append({
                    "source": sender,
                    "target": receiver,
                    "sender_ifsc": row[2],
                    "receiver_ifsc": row[3],
                    "transaction_id": row[4],
                    "amount": float(row[5]),
                    "timestamp": str(row[6]),
                    "payment_mode": row[7],
                    "hop": hop
                })
                
                if receiver not in visited_accounts:
                    visited_accounts.add(receiver)
                    next_layer.add(receiver)
                    nodes.append({"id": receiver, "layer": hop})
                    
            current_layer = list(next_layer)
            
        con.close()
        
        return {
            "root_account": victim_account,
            "nodes": nodes,
            "edges": edges,
            "total_hops": hop if edges else 0
        }
