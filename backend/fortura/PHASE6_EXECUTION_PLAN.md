# Phase 6 Execution Plan

Date: 2026-03-02  
Project: OFFLINE WEIGHBRIDGE AUTOMATION SYSTEM

## Phase 5 Closure Status

Phase 5 backend validation is complete.

- Reports fixed and passing (`fetch_records`, `aggregate_totals`, `export_excel`, `export_pdf`)
- End-to-end backend flow validated
- UAT/signoff docs prepared

Remaining from Phase 5 (non-blocking):
- Real WhatsApp provider credentials and live-send validation
- Full frontend binding pass

---

## Phase 6 Goal

Complete production-ready integration layer:
- frontend-to-backend contract completion,
- role-wise screen/API wiring,
- real WhatsApp/live integrations,
- release readiness package.

---

## Workstream A: Frontend Integration Finalization

1. Freeze API contract
- Use `backend/fortura/UI_BACKEND_MAPPING.md` as baseline.
- Mark each screen as:
  - `READY`
  - `NEEDS_BACKEND_EXTENSION`
  - `UI_CHANGE_REQUIRED`

2. Complete core screen integration
- Weighment entry/update lifecycle
- Vehicle leave/return actions
- Payment/QR/slip generation
- Report filters + exports

3. Role-wise access validation
- Super Admin
- Technician Admin
- Customer Admin
- Shift Admin (Operator)


Acceptance:
- All existing screens call valid endpoints with expected payloads.
- No hardcoded/dummy data in production paths.

---

## Workstream B: Enterprise Feature Gap Closure

Implement missing backend items needed by UI (as identified in mapping):
- Branch management/summary APIs
- Expanded user/role admin APIs if UI requires extra fields
- Connectivity/health summary endpoints for dashboards
- Global billing settings endpoints (if UI expects editable settings)

Acceptance:
- Every “Needs backend extension” item in mapping is either implemented or formally deferred with reason.

---

## Workstream C: Real WhatsApp and External Integrations

1. Configure provider env:
- `WHATSAPP_API_URL`
- `WHATSAPP_API_TOKEN`
- `WHATSAPP_SENDER_ID`
- `WHATSAPP_AUTO_SEND_ON_SLIP_GENERATE=True` (if required)

2. Validate live send on test number
- `send_whatsapp`
- `whatsapp_status`
- `retry_whatsapp`

Acceptance:
- Status transitions from virtual mode behavior to real provider response.
- Delivery audit entries captured.

---

## Workstream D: Production Readiness and Release

1. Run final checklist:
- `DEPLOYMENT_CHECKLIST.md`
- `HANDOVER_RUNBOOK_PHASE5.md`
- readiness endpoint must show no blockers

2. Data safety checks
- backup schedule enabled
- restore drill documented
- date lock/permission controls verified

3. Release package
- final API list
- env var list
- rollback notes
- known limitations list

Acceptance:
- GO/NO-GO sheet signed by QA + tech lead + business owner.

---

## Suggested Execution Order

1. Workstream A (frontend contract finalization)  
2. Workstream B (missing backend extensions)  
3. Workstream C (real WhatsApp provider)  
4. Workstream D (release readiness + handover)

---

## Current Decision

Phase 5: **Completed**  
Phase 6: **Started**
