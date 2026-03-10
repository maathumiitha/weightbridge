# UAT Defect Log Template

Use this file to track defects found while executing `UAT_CHECKLIST_PHASE5.md`.

## Defect Entries

1. Defect ID: `RPT-001`
   - Reported date: 2026-03-02
   - Reported by: sreeharish
   - Module: `Report`
   - Related UAT step: Section E (`aggregate_totals`, `export_excel`, `export_pdf`)
   - Severity: `High`
   - Priority: `P1`
   - Environment: Local DEV/UAT (`127.0.0.1:8000`)
   - Preconditions: Records exist with mixed/null numeric fields during report export
   - Steps to reproduce:
     - POST `/api/reports/export_excel/` with `{}`
     - POST `/api/reports/export_pdf/` with `{}`
     - POST `/api/reports/aggregate_totals/` with `{}`
   - Expected result:
     - Aggregate should return totals
     - Excel/PDF should download successfully
   - Actual result:
     - `aggregate_totals` serializer validation failed for partial/null record fields
     - Excel/PDF raised `TypeError` for `None` numeric formatting/conversion
   - Evidence (screenshot/log/API response):
     - Browser/API error screenshots captured during UAT session
   - Status: `Closed`
   - Assignee: Backend (Codex)
   - Fix commit/PR: Local patch in:
     - `backend/fortura/weight_billing/report_views.py`
     - `backend/fortura/weight_billing/serializers.py`
   - Retest result:
     - `aggregate_totals` success (`total_records=3`, `total_amount=98089.43`)
     - Excel export success (`report.xlsx` exists)
     - PDF export success (`report.pdf` exists)
   - Closure date: 2026-03-02

## Daily Summary
- Open defects: 0
- Ready for retest: 0
- Closed today: 1
- Blocked items: 0 (Note: WhatsApp provider remains virtual-mode by design)
