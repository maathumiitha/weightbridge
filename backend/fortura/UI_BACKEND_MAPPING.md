# UI to Backend Mapping (Super Admin)

This document maps Super Admin UI screens/widgets to current backend APIs.

## 1. Dashboard

| UI Widget | Backend Endpoint | Notes |
|---|---|---|
| Deployment readiness | `GET /api/weighbridge-configs/deployment_readiness/` | Use `ready_for_production`, `blockers`, `warnings` |
| Hardware status cards | `GET /api/weighbridge-configs/hardware_health/` | Use `summary`, `weighbridge`, `cameras`, `printers` |
| Automation queue health | `GET /api/weighbridge-configs/automation_health/` | Use `pending_record_count`, `recent_automation_actions` |
| Today weighments | `POST /api/reports/fetch_records/` | Apply today date filter; count results |
| Revenue summary | `POST /api/reports/aggregate_totals/` | Use `total_amount` and totals |

## 2. Branches

| UI Widget | Backend Endpoint | Notes |
|---|---|---|
| Branch directory/cards | Not available | Needs new `Branch` backend model/API |
| Branch status/connectivity map | Not available | Needs backend extension |
| Regional branch distribution | Not available | Needs backend extension |

## 3. Users

| UI Widget | Backend Endpoint | Notes |
|---|---|---|
| Operator list | `GET /api/operators/` | Current backend user-like operational entity |
| Create operator | `POST /api/operators/` | |
| Update operator | `PATCH /api/operators/{id}/` | |
| Disable/delete operator | `DELETE /api/operators/{id}/` | Soft-delete logic applies |
| Enterprise IAM (full role hierarchy) | Partial | Not fully available as dedicated IAM module |

## 4. Transactions

| UI Widget | Backend Endpoint | Notes |
|---|---|---|
| Transaction table | `GET /api/weight-records/` | Primary source |
| Transaction details | `GET /api/weight-records/{id}/` | |
| Vehicle flow actions | `POST /api/weight-records/{id}/vehicle_leaves/`, `POST /api/weight-records/{id}/vehicle_returns/` | Stable capture handled by serial reader |
| Proofs/photos | `GET /api/photos/?weight_record_id={id}` | |
| CSV export in transaction page | No direct transaction CSV API | Use report export APIs or frontend CSV conversion |

## 5. Billing Settings

| UI Widget | Backend Endpoint | Notes |
|---|---|---|
| Company profile and slip metadata | `GET/POST/PATCH /api/company-details/` | Includes UPI fields, slip header/footer |
| Global pricing rules | Not global | Rate currently per `weight-record` |
| Payment method toggles | Not available | Needs dedicated backend config model |
| Invoice template configuration | Partial | Basic via company/slip fields; full template config not exposed |

## 6. Revenue Dashboard

| UI Widget | Backend Endpoint | Notes |
|---|---|---|
| Revenue totals | `POST /api/reports/aggregate_totals/` | |
| Filtered data table | `POST /api/reports/fetch_records/` | |
| Excel export | `POST /api/reports/export_excel/` | File response |
| PDF export | `POST /api/reports/export_pdf/` | File response |

## 7. Machine Monitoring

| UI Widget | Backend Endpoint | Notes |
|---|---|---|
| Live weight feed | `GET /api/live-weight-readings/` | |
| Weighbridge config/test | `GET/POST/PATCH /api/weighbridge-configs/`, `POST /api/weighbridge-configs/{id}/test_connection/` | |
| Machine inventory/downtime cards | Not available | Needs backend machine model |

## 8. Camera Monitoring

| UI Widget | Backend Endpoint | Notes |
|---|---|---|
| Camera list/config | `GET/POST/PATCH /api/camera-configs/` | |
| Camera test | `POST /api/camera-configs/{id}/test_connection/` | |
| Detection logs | `GET /api/object-detections/` | |
| Unauthorized alerts | `GET /api/presence-alerts/` | |

## 9. Reports

| UI Widget | Backend Endpoint | Notes |
|---|---|---|
| Filtered report list | `POST /api/reports/fetch_records/` | |
| Aggregate cards | `POST /api/reports/aggregate_totals/` | |
| Export Excel/PDF | `POST /api/reports/export_excel/`, `POST /api/reports/export_pdf/` | |

## 10. Audit Logs / System Health

| UI Widget | Backend Endpoint | Notes |
|---|---|---|
| Operational audit logs | `GET /api/audit-logs/` | |
| Security audit logs | `GET /api/security-audit-logs/` | |
| System health | `GET /api/weighbridge-configs/hardware_health/`, `GET /api/weighbridge-configs/automation_health/`, `GET /api/weighbridge-configs/deployment_readiness/` | |

## 11. Payment / QR / Slip / WhatsApp

| UI Widget | Backend Endpoint | Notes |
|---|---|---|
| Payments | `GET/POST/PATCH /api/payments/` | |
| Generate QR | `POST /api/qrcodes/generate/` | |
| Generate slip | `POST /api/payment-slips/generate/` | |
| Download slip PDF | `GET /api/payment-slips/{slip_id}/download_pdf/` | |
| WhatsApp send/status/retry | `POST /api/payment-slips/{slip_id}/send_whatsapp/`, `GET /api/payment-slips/{slip_id}/whatsapp_status/`, `POST /api/payment-slips/{slip_id}/retry_whatsapp/` | Virtual mode currently |

## UI Team Action Summary

1. Implement directly from mapped endpoints above.
2. Mark unsupported modules as `Phase 2 UI`:
   - Branch management
   - Machine inventory/downtime
   - Full IAM module
   - Global billing configuration engine
3. Avoid hardcoded KPI widgets without matching API fields.
