from typing import List, Dict

class RiskEngine:
    def __init__(self):
        # We will hold aggregated detections here
        self.account_risks = {}
        
    def add_detections(self, detections: List[Dict]):
        """
        Adds raw detections and updates the Mule Risk Index.
        """
        for d in detections:
            acc = d["account_id"]
            if acc not in self.account_risks:
                self.account_risks[acc] = {
                    "account_id": acc,
                    "mule_risk_index": 0,
                    "signals": [],
                    "evidence_summary": []
                }
            
            # Prevent duplicate signal types for the same account if we just want to flag "detected"
            existing_signals = [s["type"] for s in self.account_risks[acc]["signals"]]
            if d["detection_type"] not in existing_signals:
                self.account_risks[acc]["signals"].append({
                    "type": d["detection_type"],
                    "contribution": d["score_contribution"]
                })
                self.account_risks[acc]["mule_risk_index"] += d["score_contribution"]
                
                # Cap at 100
                if self.account_risks[acc]["mule_risk_index"] > 100:
                    self.account_risks[acc]["mule_risk_index"] = 100
                    
            self.account_risks[acc]["evidence_summary"].append(d["evidence"])
            
    def get_risk_profile(self, account_id: str) -> Dict:
        return self.account_risks.get(account_id, {
            "account_id": account_id,
            "mule_risk_index": 0,
            "signals": [],
            "evidence_summary": []
        })
        
    def get_all_risks(self) -> List[Dict]:
        return list(self.account_risks.values())
