# Phase 5 - Today Action List (Exact Order)

## Status Update (2026-03-02)

- Step 1: Completed
- Step 2: Completed
- Step 3: Completed
- Step 4: Completed
- Step 5: Completed (backend sign-off prepared)
- Step 6: Not needed (no open blockers)

### Recorded outputs

- Aggregate totals:
  - `total_records: 3`
  - `total_amount: 98089.43`
- Export:
  - Excel: success (`report.xlsx`)
  - PDF: success (`report.pdf`)
- WhatsApp:
  - `QUEUED_VIRTUAL` (expected in virtual mode)

## 1. Start services

Terminal 1:
```powershell
python manage.py runserver
```

Terminal 2:
```powershell
python manage.py start_serial_reader --test-mode
```

## 2. Confirm readiness

Open:
`GET /api/weighbridge-configs/deployment_readiness/`

Expected:
- `ready_for_production: true`
- `blocker_count: 0`

## 3. Run one complete E2E flow

1. Create/confirm master data:
   - customer, vehicle, operator
2. Create weight record (`RECORD_SAVED`)
3. Wait first stable capture
4. Call:
   - `POST /api/weight-records/{id}/vehicle_leaves/`
   - `POST /api/weight-records/{id}/vehicle_returns/`
5. Wait second stable capture and completion
6. Generate payment + QR
7. Generate slip PDF
8. Send WhatsApp (virtual mode is fine)
9. Export report (Excel and PDF)

## 4. Fill UAT documents

1. Mark results in:
   - `UAT_CHECKLIST_PHASE5.md`
2. If any issue:
   - log in `UAT_DEFECT_LOG_TEMPLATE.md`

## 5. Final sign-off

After all PASS:
- Fill `PHASE5_SIGNOFF_TEMPLATE.md`
- Mark decision `GO`

## 6. If anything fails

Send me:
1. Endpoint used
2. Request JSON
3. Exact response/error
4. Screenshot/terminal output

I will patch immediately and give retest steps.
