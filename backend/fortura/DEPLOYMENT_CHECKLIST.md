# Weighbridge Backend Deployment Checklist (Phase 4)

## 1. Environment

1. Copy `.env.example` to `.env` and update values.
2. Set production-safe values:
   - `DJANGO_DEBUG=False`
   - `DJANGO_SECRET_KEY=<strong-random-secret>`
   - `DJANGO_ALLOWED_HOSTS=<domain-or-ip-list>`
   - `DB_*` credentials
3. If using real WhatsApp provider, set:
   - `WHATSAPP_API_URL`
   - `WHATSAPP_API_TOKEN`
   - `WHATSAPP_SENDER_ID`
   - `WHATSAPP_AUTO_SEND_ON_SLIP_GENERATE=True` (optional)

## 2. Database

1. Verify MySQL user permissions on production DB.
2. Run migrations:

```powershell
python manage.py migrate
```

3. Optional quick check:

```powershell
python manage.py showmigrations
```

## 3. Application Validation

1. Run Django checks:

```powershell
python manage.py check
```

2. Validate deployment readiness API:

```text
GET /api/weighbridge-configs/deployment_readiness/
```

Expected:
- `ready_for_production: true`
- `blocker_count: 0`

## 4. Runtime Services

Run these as separate long-running processes/services:

1. Django API server
2. Serial reader:

```powershell
python manage.py start_serial_reader
```

3. (If needed) camera/printer specific OS services and drivers

## 5. Smoke Test Flow

1. Create customer/operator/vehicle.
2. Create weight record (`RECORD_SAVED`).
3. Confirm stable capture automation works.
4. Generate payment + QR.
5. Generate slip PDF.
6. Send WhatsApp (provider or virtual mode).
7. Export Excel/PDF report.

## 6. Operations

1. Enable daily DB backup job.
2. Monitor:
   - `/api/weighbridge-configs/hardware_health/`
   - `/api/weighbridge-configs/automation_health/`
   - `/api/weighbridge-configs/deployment_readiness/`
3. Keep audit logs and backup logs reviewed.
