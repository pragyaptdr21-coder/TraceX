import duckdb
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "../../storage/tracex.duckdb")

def _get_con():
    # DuckDB operates best with a persistent connection per thread, but for our simple 
    # read-only queries we can just connect. For production read-only access is good.
    return duckdb.connect(DB_PATH, read_only=True)

def get_account_transactions(account_id: str):
    """Returns all transactions where account is sender or receiver"""
    con = _get_con()
    query = """
        SELECT * FROM transactions
        WHERE Sender_Account = ? OR Receiver_Account = ?
        ORDER BY internal_id
    """
    return con.execute(query, [account_id, account_id]).pl()

def get_account_incoming(account_id: str):
    """Returns all transactions where account is receiver"""
    con = _get_con()
    query = """
        SELECT * FROM transactions
        WHERE Receiver_Account = ?
        ORDER BY internal_id
    """
    return con.execute(query, [account_id]).pl()

def get_account_outgoing(account_id: str):
    """Returns all transactions where account is sender"""
    con = _get_con()
    query = """
        SELECT * FROM transactions
        WHERE Sender_Account = ?
        ORDER BY internal_id
    """
    return con.execute(query, [account_id]).pl()

def get_account_counterparties(account_id: str):
    """Returns unique counterparties for the given account"""
    con = _get_con()
    query = """
        SELECT DISTINCT Receiver_Account as counterparty, 'outgoing' as direction
        FROM transactions
        WHERE Sender_Account = ?
        UNION
        SELECT DISTINCT Sender_Account as counterparty, 'incoming' as direction
        FROM transactions
        WHERE Receiver_Account = ?
    """
    return con.execute(query, [account_id, account_id]).pl()

def get_account_summary(account_id: str):
    """Returns summary stats for the given account"""
    con = _get_con()
    
    # Calculate incoming
    in_query = "SELECT COUNT(*) as count, SUM(Amount) as total FROM transactions WHERE Receiver_Account = ?"
    in_res = con.execute(in_query, [account_id]).fetchone()
    
    # Calculate outgoing
    out_query = "SELECT COUNT(*) as count, SUM(Amount) as total FROM transactions WHERE Sender_Account = ?"
    out_res = con.execute(out_query, [account_id]).fetchone()
    
    # Unique counterparties
    cp_query = """
        SELECT COUNT(DISTINCT cp) FROM (
            SELECT Receiver_Account as cp FROM transactions WHERE Sender_Account = ?
            UNION
            SELECT Sender_Account as cp FROM transactions WHERE Receiver_Account = ?
        )
    """
    cp_res = con.execute(cp_query, [account_id, account_id]).fetchone()
    
    return {
        "account_id": account_id,
        "incoming_count": in_res[0],
        "incoming_amount": in_res[1] or 0.0,
        "outgoing_count": out_res[0],
        "outgoing_amount": out_res[1] or 0.0,
        "total_transactions": in_res[0] + out_res[0],
        "unique_counterparties": cp_res[0]
    }
