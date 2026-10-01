import time
import polars as pl
import duckdb
import os

def run_ingestion(source_file, db_path):
    print("Starting Phase 2 Ingestion...")
    start_total = time.time()
    
    # 1. Read source
    t0 = time.time()
    print(f"Reading {source_file}...")
    if source_file.endswith(".csv"):
        df = pl.read_csv(source_file)
    else:
        df = pl.read_excel(source_file, sheet_name="Transactions")
    read_time = time.time() - t0
    print(f"Read {df.shape[0]} rows in {read_time:.2f}s")
    
    # 2. Normalization & Data Quality
    t0 = time.time()
    print("Normalizing data and generating quality flags...")
    
    # Trim whitespaces for string columns and cast accounts to string explicitly to preserve identifiers
    string_cols = ["Transaction_ID", "Sender_Account", "Receiver_Account", 
                   "Sender_IFSC", "Receiver_IFSC", 
                   "Payment_Mode", "Narration", "IP_Address", "Device_Type"]
                   
    for col in string_cols:
        if col in df.columns:
            df = df.with_columns(pl.col(col).cast(pl.Utf8).str.strip_chars())
            
    # Add an internal row identifier
    df = df.with_row_index("internal_id")
    
    # Handle Timestamps
    if "Timestamp" in df.columns:
        # Check if they are literal '########'
        df = df.with_columns(
            pl.col("Timestamp").cast(pl.Utf8).str.strip_chars()
        )
        invalid_ts_mask = pl.col("Timestamp").eq("########") | pl.col("Timestamp").is_null()
        df = df.with_columns(
            invalid_ts_mask.alias("is_invalid_timestamp")
        )
        # Convert valid timestamps to Datetime
        df = df.with_columns(
            pl.when(pl.col("is_invalid_timestamp")).then(None)
              .otherwise(pl.col("Timestamp").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False))
              .alias("Timestamp")
        )
    
    # Quality flags
    flags = [
        pl.col("Sender_Account").is_null().alias("is_missing_sender"),
        pl.col("Receiver_Account").is_null().alias("is_missing_receiver"),
        pl.col("Amount").is_null().or_(pl.col("Amount") < 0).alias("is_invalid_amount"),
        pl.col("Payment_Mode").is_null().alias("is_missing_payment_mode"),
        pl.col("Narration").is_null().alias("is_missing_narration"),
        pl.col("IP_Address").is_null().alias("is_missing_ip")
    ]
    if "Device_Type" in df.columns:
        flags.append(pl.col("Device_Type").is_null().alias("is_missing_device"))
        
    df = df.with_columns(flags)
    
    # Flag duplicates
    if "Transaction_ID" in df.columns:
        duplicate_mask = df.group_by("Transaction_ID").agg(pl.len().alias("count")).filter(pl.col("count") > 1)
        duplicate_ids = duplicate_mask["Transaction_ID"].to_list()
        df = df.with_columns(
            pl.col("Transaction_ID").is_in(duplicate_ids).alias("is_duplicate_tx")
        )
    
    norm_time = time.time() - t0
    print(f"Normalization completed in {norm_time:.2f}s")
    
    # 3. Insert into DuckDB
    t0 = time.time()
    print(f"Writing to DuckDB at {db_path}...")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    con = duckdb.connect(db_path)
    # create table from DataFrame
    con.execute("CREATE OR REPLACE TABLE transactions AS SELECT * FROM df")
    
    # Create indexes for fast Account and Transaction lookups
    con.execute("CREATE INDEX idx_sender ON transactions(Sender_Account)")
    con.execute("CREATE INDEX idx_receiver ON transactions(Receiver_Account)")
    con.execute("CREATE INDEX idx_tx_id ON transactions(Transaction_ID)")
    
    write_time = time.time() - t0
    total_time = time.time() - start_total
    
    # DB Size
    db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
    
    print(f"Database written and indexed in {write_time:.2f}s")
    print(f"Total ingestion time: {total_time:.2f}s")
    print(f"Database size: {db_size_mb:.2f} MB")
    import resource
    import sys
    peak_mem_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 # Linux is KB
    if sys.platform == "darwin": # macOS ru_maxrss is in bytes
        peak_mem_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)
        
    print(f"Peak memory usage: {peak_mem_mb:.2f} MB")
    
    return {
        "read_time": read_time,
        "norm_time": norm_time,
        "write_time": write_time,
        "total_time": total_time,
        "db_size_mb": db_size_mb,
        "rows": df.shape[0],
        "columns": df.shape[1]
    }

if __name__ == "__main__":
    run_ingestion("data/VoidHacks8_MuleAccount_2M_Transactions.csv", "storage/tracex.duckdb")
