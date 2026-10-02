import duckdb
from fastapi.testclient import TestClient

from backend.api import app
from backend.ai_service import generate_section_91_notice

DB_PATH = "storage/tracex.duckdb"


def real_evidence():
    con = duckdb.connect(DB_PATH, read_only=True)
    account = con.execute("SELECT Sender_Account FROM transactions LIMIT 1").fetchone()[0]
    row = con.execute(
        """
        SELECT Transaction_ID, Sender_Account, Receiver_Account, Amount, Timestamp,
               Sender_IFSC, Receiver_IFSC
        FROM transactions
        WHERE Sender_Account = ?
        ORDER BY Timestamp ASC
        LIMIT 1
        """,
        [account],
    ).fetchone()
    con.close()
    return account, row


def test_section_91_notice_is_evidence_grounded():
    account, row = real_evidence()
    tx_id, sender, receiver, amount, timestamp, sender_ifsc, receiver_ifsc = row
    evidence = {
        "source_account": account,
        "risk_information": {
            "mule_risk_index": 25,
            "signals": [{"type": "COLLECTOR_MULE_L1", "contribution": 25}],
        },
        "transactions": [{
            "transaction_id": tx_id,
            "source": sender,
            "target": receiver,
            "amount": float(amount),
            "timestamp": str(timestamp),
            "sender_ifsc": sender_ifsc,
            "receiver_ifsc": receiver_ifsc,
        }],
    }
    notice = generate_section_91_notice(evidence)

    assert account in notice
    assert str(tx_id) in notice
    assert str(amount) in notice
    assert str(timestamp) in notice
    assert str(sender_ifsc) in notice
    assert str(receiver_ifsc) in notice
    assert "COLLECTOR_MULE_L1" in notice
    assert "Not provided in source evidence" in notice
    assert "Case/FIR Reference: Not provided in source evidence" in notice
    assert "DRAFT - SECTION 94 BNSS" in notice
    assert "(CORRESPONDING TO SECTION 91 CrPC)" in notice
    assert "SUMMONS / WRITTEN ORDER TO PRODUCE DOCUMENT OR OTHER THING" in notice
    assert "FOR HUMAN REVIEW" in notice
    assert "FIR-" not in notice


def test_section_91_api_and_pdf_export():
    account, row = real_evidence()
    tx_id, sender, receiver, amount, timestamp, sender_ifsc, receiver_ifsc = row
    evidence = {
        "source_account": account,
        "risk_information": {"mule_risk_index": 0, "signals": []},
        "transactions": [{
            "transaction_id": tx_id,
            "source": sender,
            "target": receiver,
            "amount": float(amount),
            "timestamp": str(timestamp),
            "sender_ifsc": sender_ifsc,
            "receiver_ifsc": receiver_ifsc,
        }],
    }

    with TestClient(app) as client:
        response = client.post("/api/section-91-notice/generate", json={"evidence_data": evidence})
        assert response.status_code == 200
        notice = response.json()["data"]
        assert tx_id in notice

        pdf_response = client.post(
            "/api/section-91-notice/export",
            json={"title": "Section 91 Notice", "content": notice},
        )
        assert pdf_response.status_code == 200
        assert pdf_response.headers["content-type"] == "application/pdf"
        assert pdf_response.content.startswith(b"%PDF")
        assert len(pdf_response.content) > 500
