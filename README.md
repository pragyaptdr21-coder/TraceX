# TraceX

## Cyber Money Trail Intelligence Platform

TraceX is a standalone cyber financial investigation platform designed to help investigators analyze suspicious transaction networks, trace money movement, identify suspicious financial patterns, and generate investigation-ready evidence.

The implementation is guided by an internal requirements document.

### Future Architecture

Module A
High-Throughput Ingestion & Normalization
*(IMPLEMENTED — PHASE 2)*

**Performance Note:**
- Target: 2,000,000+ records / <= 60 sec
- TraceX currently has a complete ~2-million-row dataset available.
- Phase 2 ingestion uses: Excel/CSV → Polars/efficient parsing → normalization → DuckDB
- Current benchmark: 2,000,000 records / ~6.5s (Read: ~0.6s, Normalize: ~0.7s, DB write: ~5.2s)
- Final 2M benchmark: PASS

↓
Module B
Mule Ring Detection & Graph Analytics
*(NOT IMPLEMENTED YET)*
↓
Module C
Interactive Law Enforcement Flow Graph
*(NOT IMPLEMENTED YET)*
↓
Module D
Local AI Case Officer & Legal Notice Generator
*(NOT IMPLEMENTED YET)*

### Evaluation Areas
- Blind Victim Query
- Detection Precision & Recall
- Court-Ready Output & Usability
- Architecture & Engineering Rigor
