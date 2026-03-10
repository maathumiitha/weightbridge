# Phase 5 UAT Checklist

Use this checklist for final acceptance testing before frontend go-live.

## A. Pre-Checks

1. `python manage.py check` returns no issues.
2. `GET /api/weighbridge-configs/deployment_readiness/` returns:
   - `ready_for_production: true`
   - `blocker_count: 0`
3. Required master data exists:
   - at least 1 customer
   - at least 1 vehicle
   - at least 1 operator
4. Hardware configs exist and are active:
   - weighbridge
   - >= 1 camera
   - >= 1 printer
5. Company details are active and `upi_id` is present.

## B. Core Weighment Workflow (Single Vehicle)

1. Create weight record with status `RECORD_SAVED`.
2. Run serial reader (`python manage.py start_serial_reader --test-mode` or real mode).
3. Wait stable detection for first weight.
4. Verify record status updates to `FIRST_WEIGHT_CAPTURED`.
5. Call `POST /api/weight-records/{id}/vehicle_leaves/`.
6. Call `POST /api/weight-records/{id}/vehicle_returns/`.
7. Wait next stable detection.
8. Verify record reaches `COMPLETED`.
9. Confirm fields are populated:
   - `first_weight`, `second_weight`
   - `gross_weight`, `tare_weight`, `net_weight`
   - `total_amount`

Expected result: end-to-end status transitions complete without manual DB edits.

## C. Payment, QR, Slip

1. Create payment for completed record (or use existing payment endpoint flow).
2. Generate QR:
   - `POST /api/qrcodes/generate/` (or payment QR endpoint in use)
3. Verify QR exists and linked to payment.
4. Generate slip:
   - `POST /api/payment-slips/generate/`
5. Download slip PDF:
   - `GET /api/payment-slips/{slip_id}/download_pdf/`
6. Mark/verify print flow if required:
   - `POST /api/payment-slips/{slip_id}/print_slip/`

Expected result: QR + PDF slip generated successfully and linked records are correct.

## D. WhatsApp Flow (Current Virtual Mode)

1. Trigger send:
   - `POST /api/payment-slips/{slip_id}/send_whatsapp/`
2. Check status:
   - `GET /api/payment-slips/{slip_id}/whatsapp_status/`
3. Retry once:
   - `POST /api/payment-slips/{slip_id}/retry_whatsapp/`

Expected result: status returns `QUEUED_VIRTUAL` in current setup.

## E. Reports

1. Fetch records:
   - `POST /api/reports/fetch_records/`
2. Aggregate totals:
   - `POST /api/reports/aggregate_totals/`
3. Export Excel:
   - `POST /api/reports/export_excel/`
4. Export PDF:
   - `POST /api/reports/export_pdf/`
5. Operator filter test:
   - include `operator` in filter and verify expected records are returned.

Expected result: all report endpoints return valid output; exports download successfully.

## F. Security & Audit

1. Confirm audit logs are written for key events:
   - weight capture
   - payment/QR/slip
   - WhatsApp send/retry
2. Check soft-delete behavior for master records (no hard delete by default users).
3. Check date lock rules if enabled.

## G. Failure/Recovery Checks

1. Keep record in pending state and verify automation health:
   - `GET /api/weighbridge-configs/automation_health/`
2. Verify no crash if no pending records (log should safely show "No pending records for automation").
3. Verify system resumes after server restart.

## H. UAT Sign-Off

Mark each item: `PASS` / `FAIL` / `N/A`.

Sign-off fields:
- Tester name:
- Date:
- Build/commit:
- Environment:
- Open critical issues:
- Final decision: `GO` / `NO-GO`
