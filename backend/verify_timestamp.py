import openpyxl

def verify_timestamps(file_path):
    print("Loading workbook...")
    wb = openpyxl.load_workbook(file_path)
    sheet = wb["Transactions"]
    
    # Headers
    headers = [str(cell.value) for cell in sheet[1]]
    col_idx = {h: i for i, h in enumerate(headers)}
    ts_idx = col_idx.get("Timestamp")
    
    if ts_idx is None:
        print("Timestamp column not found.")
        return
        
    print(f"Timestamp column index: {ts_idx}")
    
    total_rows = sheet.max_row
    
    print("\n--- Inspecting first 10 Timestamp cells ---")
    for r in range(2, min(12, total_rows + 1)):
        cell = sheet[r][ts_idx]
        print(f"Row {r} (Coordinate {cell.coordinate}):")
        print(f"  Raw cell.value: {repr(cell.value)}")
        print(f"  Python type: {type(cell.value)}")
        print(f"  cell.data_type: {cell.data_type}")
        print(f"  Number format: {cell.number_format}")
        
    print("\n--- Inspecting middle 10 Timestamp cells ---")
    mid_start = max(2, total_rows // 2 - 5)
    for r in range(mid_start, min(mid_start + 10, total_rows + 1)):
        cell = sheet[r][ts_idx]
        print(f"Row {r} (Coordinate {cell.coordinate}):")
        print(f"  Raw cell.value: {repr(cell.value)}")
        print(f"  Python type: {type(cell.value)}")
        print(f"  cell.data_type: {cell.data_type}")
        print(f"  Number format: {cell.number_format}")
        
    print("\n--- Inspecting last 10 Timestamp cells ---")
    for r in range(max(2, total_rows - 9), total_rows + 1):
        cell = sheet[r][ts_idx]
        print(f"Row {r} (Coordinate {cell.coordinate}):")
        print(f"  Raw cell.value: {repr(cell.value)}")
        print(f"  Python type: {type(cell.value)}")
        print(f"  cell.data_type: {cell.data_type}")
        print(f"  Number format: {cell.number_format}")

if __name__ == "__main__":
    verify_timestamps("data/Dataset_VoidHacks.xlsx")
