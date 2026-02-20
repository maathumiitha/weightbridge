from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomerViewSet, 
    OperatorViewSet, 
    VehicleViewSet,
    WeightRecordViewSet,
    AuditLogViewSet,
    WeightRecordPhotoViewSet,
    # Automation hardware viewsets
    WeighbridgeConfigViewSet,
    LiveWeightReadingViewSet,
    CameraConfigViewSet,
    PrinterConfigViewSet,
    # AI Monitoring viewsets
    AIMonitoringConfigViewSet,
    ObjectDetectionLogViewSet,
    UnauthorizedPresenceAlertViewSet
)
from .calculation_views import CalculationViewSet
from .multidrop_views import MultiDropViewSet
from .report_views import ReportViewSet

# Import all slip generation related viewsets from slip_views.py
from .slip_views import (
    PaymentViewSet,
    QRCodeViewSet,
    PaymentSlipViewSet,
    CompanyDetailsViewSet
)

# ==================== SECURITY IMPORTS ====================
# Import security ViewSets from views_security.py
from .security_views import (
    DateLockConfigViewSet,
    BackupConfigViewSet,
    BackupLogViewSet,
    TareWeightHistoryViewSet,
    SecurityAuditLogViewSet,
    SoftDeleteManagementViewSet
)

router = DefaultRouter()

# Core models
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'operators', OperatorViewSet, basename='operator')
router.register(r'vehicles', VehicleViewSet, basename='vehicle')

# ==================== AUTOMATION HARDWARE ====================
# Weighbridge hardware configuration and live readings
router.register(r'weighbridge-configs', WeighbridgeConfigViewSet, basename='weighbridge-config')
router.register(r'live-weight-readings', LiveWeightReadingViewSet, basename='live-weight-reading')

# Camera system configuration (1-4 cameras)
router.register(r'camera-configs', CameraConfigViewSet, basename='camera-config')

# Printer configuration and management
router.register(r'printer-configs', PrinterConfigViewSet, basename='printer-config')

# ==================== AI MONITORING & SECURITY ====================
# AI monitoring system configuration
router.register(r'ai-monitoring-configs', AIMonitoringConfigViewSet, basename='ai-monitoring-config')

# Object detection logs (read-only, created by detection service)
router.register(r'object-detections', ObjectDetectionLogViewSet, basename='object-detection')

# Unauthorized presence alerts
router.register(r'presence-alerts', UnauthorizedPresenceAlertViewSet, basename='presence-alert')

# ==================== SECURITY & DATA MANAGEMENT ====================
# Date Lock System - Lock Past Dates
router.register(r'date-lock-config', DateLockConfigViewSet, basename='date-lock-config')

# Backup System - Daily Backup
router.register(r'backup-config', BackupConfigViewSet, basename='backup-config')
router.register(r'backup-logs', BackupLogViewSet, basename='backup-log')

# Tare Weight History - Store Tare History Long Term
router.register(r'tare-history', TareWeightHistoryViewSet, basename='tare-history')

# Security Audit Logs - Log Every Action
router.register(r'security-audit-logs', SecurityAuditLogViewSet, basename='security-audit-log')

# Soft Delete Management - No Delete Without Super Admin
router.register(r'soft-delete', SoftDeleteManagementViewSet, basename='soft-delete')

# ==================== WEIGHT RECORDS & OPERATIONS ====================
# Weight records and operations
router.register(r'weight-records', WeightRecordViewSet, basename='weight-record')
router.register(r'calculations', CalculationViewSet, basename='calculation')
router.register(r'multi-drops', MultiDropViewSet, basename='multi-drop')

# ==================== PAYMENT SYSTEM ====================
# Payment system (all from slip_views.py)
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'qrcodes', QRCodeViewSet, basename='qrcode')
router.register(r'payment-slips', PaymentSlipViewSet, basename='payment-slip')

# ==================== PHOTOS & COMPANY ====================
# Photos and company details
router.register(r'photos', WeightRecordPhotoViewSet, basename='photo')
router.register(r'company-details', CompanyDetailsViewSet, basename='company-details')

# ==================== REPORTS & AUDIT ====================
# Reports and audit
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('', include(router.urls)),
]