import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import duckdb
import os

from backend.services.account_service import (
    get_account_transactions,
    get_account_incoming,
    get_account_outgoing,
    get_account_summary
)
from backend.detection.velocity_detector import VelocityDetector
from backend.detection.collector_detector import CollectorDetector
from backend.detection.distributor_detector import DistributorDetector
from backend.detection.cycle_detector import CycleDetector
from backend.detection.terminal_detector import TerminalDetector
from backend.detection.risk_engine import RiskEngine
from backend.detection.trail_engine import TrailEngine

from backend.evaluation.engine import (
    DEFAULT_DB_PATH,
    EvaluationResult,
    evaluate_predictions,
    run_evaluation,
)
from backend.evaluation.ground_truth import (
    EXPECTED_MULE_ACCOUNTS,
    EXPECTED_REGULAR_ACCOUNTS,
    load_ground_truth_from_rows,
)
from backend.evaluation.predictions import (
    DEFAULT_RISK_THRESHOLD,
    get_predictions,
)
from backend.evaluation.report import render_report

DB_PATH = os.path.join(os.path.dirname(__file__), "../storage/tracex.duckdb")

# Global cache for detection results
app_state = {
    "risk_engine": None,
    "detections_map": {}
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-compute detections on startup to avoid running 25-second queries on every request.
    print("Starting TraceX API Server...")
    print("Initializing global detection cache (this takes ~30 seconds)...")
    
    risk_engine = RiskEngine()
    
    vel_results = VelocityDetector(DB_PATH).detect()
    risk_engine.add_detections(vel_results)
    
    col_results = CollectorDetector(DB_PATH, min_unique_senders=5).detect()
    risk_engine.add_detections(col_results)
    
    dist_results = DistributorDetector(DB_PATH).detect()
    risk_engine.add_detections(dist_results)
    
    cycle_results = CycleDetector(DB_PATH).detect()
    risk_engine.add_detections(cycle_results)
    
    term_results = TerminalDetector(DB_PATH).detect()
    risk_engine.add_detections(term_results)
    
    app_state["risk_engine"] = risk_engine
    
    # Build quick lookup map for detections
    for d in (vel_results + col_results + dist_results + cycle_results + term_results):
        acc = d["account_id"]
        if acc not in app_state["detections_map"]:
            app_state["detections_map"][acc] = []
        app_state["detections_map"][acc].append(d)
        
    print("Detection cache initialized.")
    yield
    print("Shutting down TraceX API Server.")

app = FastAPI(title="TraceX Backend API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys([
        os.environ.get("TRACE_X_FRONTEND_ORIGIN", "http://localhost:5173"),
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ])),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _get_con():
    return duckdb.connect(DB_PATH, read_only=True)

@app.get("/health")
def health_check():
    try:
        # Verify db is reachable
        con = _get_con()
        con.execute("SELECT 1").fetchone()
        con.close()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/accounts/search")
def search_accounts(q: str = Query(..., min_length=1)):
    """Find matching account IDs using a fast DuckDB LIKE query (limited to 50 results)."""
    con = _get_con()
    query = """
        SELECT DISTINCT Sender_Account as account_id 
        FROM transactions 
        WHERE Sender_Account LIKE ? 
        UNION 
        SELECT DISTINCT Receiver_Account as account_id 
        FROM transactions 
        WHERE Receiver_Account LIKE ?
        LIMIT 50
    """
    pattern = f"%{q}%"
    results = con.execute(query, [pattern, pattern]).fetchall()
    con.close()
    
    return {
        "success": True,
        "data": [{"account_id": row[0]} for row in results]
    }

@app.get("/api/accounts/{account_id}")
def get_account_summary_api(account_id: str):
    """Returns account summary combining DB stats and Risk Engine results."""
    try:
        summary = get_account_summary(account_id)
        if summary["total_transactions"] == 0:
            raise HTTPException(status_code=404, detail="Account not found")
            
        risk_profile = app_state["risk_engine"].get_risk_profile(account_id)
        summary["mule_risk_index"] = risk_profile["mule_risk_index"]
        summary["signals"] = risk_profile["signals"]
        
        return {"success": True, "data": summary}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(e)}}

@app.get("/api/accounts/{account_id}/transactions")
def get_transactions(
    account_id: str, 
    direction: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Returns transactions for an account with optional filters."""
    con = _get_con()
    
    base_query = "SELECT * FROM transactions WHERE "
    params = []
    
    if direction == "incoming":
        base_query += "Receiver_Account = ?"
        params.append(account_id)
    elif direction == "outgoing":
        base_query += "Sender_Account = ?"
        params.append(account_id)
    else:
        base_query += "(Sender_Account = ? OR Receiver_Account = ?)"
        params.extend([account_id, account_id])
        
    base_query += " ORDER BY Timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    df = con.execute(base_query, params).pl()
    con.close()
    
    # Convert dates/times to string for JSON serialization
    # pl DataFrames can be converted directly to dicts.
    # Convert timestamps in python
    data = []
    for row in df.to_dicts():
        if "Timestamp" in row and row["Timestamp"]:
            row["Timestamp"] = str(row["Timestamp"])
        data.append(row)
        
    return {"success": True, "data": data}

@app.get("/api/accounts/{account_id}/risk")
def get_risk(account_id: str):
    """Exposes existing Risk Engine result."""
    risk_profile = app_state["risk_engine"].get_risk_profile(account_id)
    return {"success": True, "data": risk_profile}

@app.get("/api/accounts/{account_id}/detections")
def get_detections(account_id: str):
    """Exposes detector outputs for a specific account from the global cache."""
    dets = app_state["detections_map"].get(account_id, [])
    return {"success": True, "data": dets}

@app.get("/api/accounts/{account_id}/trail")
def get_trail(
    account_id: str,
    hops: int = Query(4, ge=1, le=4),
    max_edges: Optional[int] = Query(1500, ge=1, le=5000),
    full: bool = Query(False),
):
    """Exposes the 4-hop BFS Trail Engine result."""
    try:
        trail_eng = TrailEngine(DB_PATH)
        trail_result = trail_eng.get_4_hop_trail(account_id, max_hops=hops)

        # Keep the browser investigation view responsive for high-degree accounts.
        # The BFS remains owned by TrailEngine; this only scopes the API payload
        # to the graph viewport's practical rendering budget.
        if full:
            max_edges = None
        if max_edges is not None:
            total_edges = len(trail_result["edges"])
            scoped_edges = trail_result["edges"][:max_edges]
            scoped_accounts = {account_id}
            for edge in scoped_edges:
                scoped_accounts.add(edge["source"])
                scoped_accounts.add(edge["target"])
            trail_result["edges"] = scoped_edges
            trail_result["nodes"] = [
                node for node in trail_result["nodes"] if node["id"] in scoped_accounts
            ]
            trail_result["truncated"] = total_edges > len(scoped_edges)
            trail_result["edge_limit"] = max_edges
        return {"success": True, "data": trail_result}
    except Exception as e:
        return {"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(e)}}

@app.get("/api/accounts/{account_id}/timeline")
def get_timeline(account_id: str):
    """
    Since the timeline requires chronological transaction data for playback, 
    we can reuse the existing transactions logic but ordered ASC and fetching everything.
    """
    con = _get_con()
    query = """
        SELECT Transaction_ID, Sender_Account, Receiver_Account, Amount, Timestamp, Payment_Mode
        FROM transactions
        WHERE Sender_Account = ? OR Receiver_Account = ?
        ORDER BY Timestamp ASC
    """
    df = con.execute(query, [account_id, account_id]).pl()
    con.close()
    
    data = []
    for row in df.to_dicts():
        if "Timestamp" in row and row["Timestamp"]:
            row["Timestamp"] = str(row["Timestamp"])
        data.append(row)
        
    return {"success": True, "data": data}

from pydantic import BaseModel
from typing import List
from fastapi.responses import StreamingResponse, Response
import io
import csv
from .ai_service import generate_case_summary, generate_freeze_requisition, generate_section_91_notice
from .pdf_service import export_pdf

class EvidencePayload(BaseModel):
    evidence_data: dict

class ExportPDFPayload(BaseModel):
    title: str
    content: str

@app.post("/api/case-diary/generate")
def api_generate_case_summary(req: EvidencePayload):
    summary = generate_case_summary(req.evidence_data)
    return {"success": True, "data": summary}

@app.post("/api/freeze-requisition/generate")
def api_generate_freeze_requisition(req: EvidencePayload):
    draft = generate_freeze_requisition(req.evidence_data)
    return {"success": True, "data": draft}

@app.post("/api/section-91-notice/generate")
def api_generate_section_91_notice(req: EvidencePayload):
    notice = generate_section_91_notice(req.evidence_data)
    return {"success": True, "data": notice}

@app.post("/api/case-diary/export")
def api_export_case_diary(req: ExportPDFPayload):
    pdf_bytes = export_pdf(req.title, req.content)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=Case_Diary.pdf"}
    )

@app.post("/api/freeze-requisition/export")
def api_export_freeze_requisition(req: ExportPDFPayload):
    pdf_bytes = export_pdf(req.title, req.content)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=Freeze_Requisition.pdf"}
    )

@app.post("/api/section-91-notice/export")
def api_export_section_91_notice(req: ExportPDFPayload):
    pdf_bytes = export_pdf(req.title, req.content)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=Section_91_Notice.pdf"}
    )

class ExportRequest(BaseModel):
    transaction_ids: List[str]
    metadata: dict = None

class GroundTruthRow(BaseModel):
    account_id: str
    label: int

class EvaluationRequest(BaseModel):
    """Optional ground-truth input for the precision/recall evaluation.

    Every field is optional so an empty POST is valid: it evaluates against
    evaluation/ground_truth.csv, which is the normal path.
    """
    ground_truth: List[GroundTruthRow] = None
    ground_truth_path: str = None
    threshold: int = None
    refresh: bool = False
    allow_population_mismatch: bool = False
    expected_mule_accounts: int = None
    expected_regular_accounts: int = None

@app.post("/api/investigations/export")
def export_investigation(req: ExportRequest):
    """Exports full transaction records for the requested transaction IDs."""
    if not req.transaction_ids:
        return {"success": False, "error": "No transaction IDs provided"}
        
    con = _get_con()
    
    # We use duckdb to fetch all fields for these transaction IDs
    # Using parameterized query for IN clause
    placeholders = ",".join(["?"] * len(req.transaction_ids))
    query = f"""
        SELECT *
        FROM transactions
        WHERE Transaction_ID IN ({placeholders})
        ORDER BY Timestamp ASC
    """
    
    df = con.execute(query, req.transaction_ids).pl()
    con.close()
    
    # Create CSV in memory
    output = io.StringIO()
    # Write metadata if any at the top as comments
    if req.metadata:
        for k, v in req.metadata.items():
            output.write(f"# {k}: {v}\n")
            
    # Convert Polars df to dicts and write with standard csv module
    records = df.to_dicts()
    if records:
        writer = csv.DictWriter(output, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=investigation_export.csv"}
    )

# ---------------------------------------------------------------------------
# Detection evaluation (precision / recall)
#
# These endpoints score the existing detector pipeline against externally
# supplied ground truth. They deliberately hold no labels of their own: with no
# official ground_truth.csv the response is NOT_AVAILABLE and carries no metric
# keys, so a missing label set can never be mistaken for a real score.
# ---------------------------------------------------------------------------

def _known_accounts() -> set:
    """Account ids present in the 2M dataset, for label validation."""
    try:
        con = _get_con()
        rows = con.execute(
            "SELECT DISTINCT Sender_Account FROM transactions "
            "UNION SELECT DISTINCT Receiver_Account FROM transactions"
        ).fetchall()
        con.close()
        return {r[0] for r in rows if r and r[0]}
    except Exception:
        # Validation of "account exists in dataset" degrades gracefully; the
        # structural and population checks still run.
        return set()


@app.get("/api/evaluation/precision-recall")
def get_precision_recall(
    threshold: int = Query(DEFAULT_RISK_THRESHOLD, ge=0, le=100),
    refresh: bool = Query(False),
    allow_population_mismatch: bool = Query(False),
):
    """Evaluate using evaluation/ground_truth.csv."""
    result = run_evaluation(
        db_path=DB_PATH,
        threshold=threshold,
        risk_engine=app_state["risk_engine"],
        known_accounts=_known_accounts(),
        refresh=refresh,
        allow_population_mismatch=allow_population_mismatch,
    )
    return _evaluation_response(result)


@app.post("/api/evaluation/precision-recall")
def post_precision_recall(req: EvaluationRequest):
    """Evaluate using an inline, validated ground-truth payload.

    The payload follows the same rules as the CSV file, including the
    1,500 / 23,500 population check.
    """
    if req.ground_truth:
        labels = load_ground_truth_from_rows(
            req.ground_truth,
            source="request",
            known_accounts=_known_accounts(),
            expected_mules=req.expected_mule_accounts or EXPECTED_MULE_ACCOUNTS,
            expected_regular=req.expected_regular_accounts or EXPECTED_REGULAR_ACCOUNTS,
            allow_population_mismatch=req.allow_population_mismatch,
        )
        if not labels.is_usable:
            return _evaluation_response(EvaluationResult(status=labels.status, ground_truth=labels))

        predictions = get_predictions(
            DB_PATH,
            threshold=req.threshold or DEFAULT_RISK_THRESHOLD,
            risk_engine=app_state["risk_engine"],
            refresh=req.refresh,
        )
        return _evaluation_response(evaluate_predictions(labels, predictions))

    # No inline labels: fall back to the file on disk.
    result = run_evaluation(
        db_path=DB_PATH,
        ground_truth_path=req.ground_truth_path,
        threshold=req.threshold or DEFAULT_RISK_THRESHOLD,
        risk_engine=app_state["risk_engine"],
        known_accounts=_known_accounts(),
        refresh=req.refresh,
        allow_population_mismatch=req.allow_population_mismatch,
    )
    return _evaluation_response(result)


def _evaluation_response(result: EvaluationResult) -> dict:
    payload = result.as_dict()
    return {"success": result.has_metrics, "data": payload}


@app.get("/api/evaluation/report")
def download_evaluation_report():
    """Return the text evaluation report as a downloadable file."""
    result = run_evaluation(
        db_path=DB_PATH,
        risk_engine=app_state["risk_engine"],
        known_accounts=_known_accounts(),
    )
    text = render_report(result)
    return Response(
        content=text,
        media_type="text/plain",
        headers={
            "Content-Disposition": "attachment; filename=TraceX_Precision_Recall_Evaluation_Report.txt"
        },
    )

