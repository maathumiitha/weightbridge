# Phase 5 Handover Runbook

## 1. Daily Startup

1. Open backend terminal in `backend/fortura`.
2. Start API:

```powershell
python manage.py runserver
```

3. Start serial reader in second terminal:

```powershell
python manage.py start_serial_reader --test-mode
```

Use real serial mode in production by removing `--test-mode`.

## 2. Daily Health Checks

1. Hardware health:
   - `GET /api/weighbridge-configs/hardware_health/`
2. Automation queue:
   - `GET /api/weighbridge-configs/automation_health/`
3. Deployment readiness:
   - `GET /api/weighbridge-configs/deployment_readiness/`

## 3. Standard Operational Flow

1. Ensure customer, vehicle, operator exist.
2. Create weight record (`RECORD_SAVED`).
3. First stable -> first weight capture.
4. Mark vehicle leave/return.
5. Second stable -> second weight capture + auto calculation.
6. Generate payment + QR + slip PDF.
7. Send WhatsApp (virtual now, provider later).
8. Export day-end reports (Excel/PDF).

## 4. Common Issues and Quick Actions

1. "No pending records for automation"
   - Check weight record status; ensure it is in automation flow.
2. FK invalid pk errors
   - Verify customer/vehicle/operator IDs exist and are numeric.
3. Missing Python package
   - Install package in active Python environment.
4. MySQL access denied
   - Verify DB user/password in env/settings and privileges.
5. Root URL shows 404
   - expected; use `/api/...` endpoints.

## 5. WhatsApp Modes

Current mode:
- Virtual queue mode (no real sending).

To enable real sending later, set:
- `WHATSAPP_API_URL`
- `WHATSAPP_API_TOKEN`
- `WHATSAPP_SENDER_ID`
- optional `WHATSAPP_AUTO_SEND_ON_SLIP_GENERATE=True`

## 6. Backup and Data Safety

1. Keep daily DB backup schedule.
2. Do not use destructive DB cleanup in production.
3. Review audit logs periodically.

## 7. Pre-Go-Live Final Check

1. Complete `UAT_CHECKLIST_PHASE5.md`.
2. Ensure all critical items are PASS.
3. Confirm no unresolved blocker in deployment readiness.
4. Freeze build and tag release.
