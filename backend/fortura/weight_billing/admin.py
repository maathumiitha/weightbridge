from django.contrib import admin
from .models import (
    Customer, Operator, Vehicle, WeightRecord, WeightDrop, AuditLog,
    Payment, QRCode, PaymentSlip, WeightRecordPhoto, CompanyDetails,
    WeighbridgeConfig, LiveWeightReading, CameraConfig, PrinterConfig,
    # AI Monitoring models
    AIMonitoringConfig, ObjectDetectionLog, UnauthorizedPresenceAlert
)

# ==================== SECURITY IMPORTS ====================
# Import security models
from .models_security_data_management import (
    DateLockConfig,
    BackupConfig,
    BackupLog,
    TareWeightHistory,
    SecurityAuditLog
)


# ==================== SECURITY ADMIN ====================

@admin.register(DateLockConfig)
class DateLockConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_enabled', 'lock_days_after', 'allow_grace_period', 
                    'grace_period_hours', 'super_admin_override', 'is_active', 'updated_at']
    search_fields = ['name']
    list_filter = ['is_enabled', 'is_active', 'allow_grace_period', 'super_admin_override']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Settings', {
            'fields': ('name', 'is_enabled', 'is_active')
        }),
        ('Lock Configuration', {
            'fields': ('lock_days_after',),
            'description': 'Lock records after this many days (0 = lock immediately after date passes)'
        }),
        ('Grace Period', {
            'fields': ('allow_grace_period', 'grace_period_hours'),
            'description': 'Allow modifications during grace period after date'
        }),
        ('Exceptions', {
            'fields': ('super_admin_override',),
            'description': 'Allow super admins to edit locked records'
        }),
        ('Permanently Locked Dates', {
            'fields': ('locked_dates',),
            'description': 'JSON list of specific dates that are permanently locked (YYYY-MM-DD format)',
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of active date lock config
        if obj and obj.is_active:
            return False
        return True


@admin.register(BackupConfig)
class BackupConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_enabled', 'backup_frequency', 'backup_time', 
                    'retention_days', 'last_backup_date', 'last_backup_status', 
                    'is_active', 'updated_at']
    search_fields = ['name', 'backup_path']
    list_filter = ['is_enabled', 'is_active', 'backup_frequency', 'compress_backups', 
                   'include_media_files', 'last_backup_status']
    readonly_fields = ['last_backup_date', 'last_backup_status', 'last_backup_size_mb',
                      'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Settings', {
            'fields': ('name', 'is_enabled', 'is_active')
        }),
        ('Backup Schedule', {
            'fields': ('backup_frequency', 'custom_interval_hours', 'backup_time'),
            'description': 'Configure backup frequency and timing'
        }),
        ('Storage Settings', {
            'fields': ('backup_path', 'compress_backups', 'include_media_files')
        }),
        ('Retention Policy', {
            'fields': ('retention_days', 'keep_monthly_backups'),
            'description': 'Configure backup retention and cleanup'
        }),
        ('Notifications', {
            'fields': ('send_backup_notifications', 'notification_emails', 
                      'notify_on_success', 'notify_on_failure'),
            'classes': ('collapse',)
        }),
        ('Last Backup Status', {
            'fields': ('last_backup_date', 'last_backup_status', 'last_backup_size_mb'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of active backup config
        if obj and obj.is_active:
            return False
        return True


@admin.register(BackupLog)
class BackupLogAdmin(admin.ModelAdmin):
    list_display = ['backup_id', 'backup_config', 'backup_type', 'backup_status', 
                    'backup_size_mb', 'records_backed_up', 'duration_seconds',
                    'started_at', 'completed_at']
    search_fields = ['backup_id', 'backup_file_name', 'backup_file_path']
    list_filter = ['backup_status', 'backup_type', 'is_verified', 'started_at']
    readonly_fields = ['backup_id', 'started_at', 'completed_at', 'duration_seconds',
                      'backup_size_mb', 'records_backed_up', 'tables_backed_up',
                      'media_files_backed_up']
    date_hierarchy = 'started_at'
    
    fieldsets = (
        ('Backup Information', {
            'fields': ('backup_id', 'backup_config', 'backup_type', 'backup_status', 
                      'initiated_by')
        }),
        ('File Details', {
            'fields': ('backup_file_path', 'backup_file_name', 'backup_size_mb')
        }),
        ('Statistics', {
            'fields': ('records_backed_up', 'tables_backed_up', 'media_files_backed_up')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at', 'duration_seconds')
        }),
        ('Error Information', {
            'fields': ('error_message', 'error_details'),
            'classes': ('collapse',)
        }),
        ('Verification', {
            'fields': ('is_verified', 'verification_date'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Backups are created by system only
        return False
    
    def has_change_permission(self, request, obj=None):
        # Allow only verification status change
        return True
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of backup logs
        return False


@admin.register(TareWeightHistory)
class TareWeightHistoryAdmin(admin.ModelAdmin):
    list_display = ['history_id', 'vehicle', 'tare_weight', 'recorded_date', 
                    'weight_variance', 'variance_percentage', 'is_significant_variance',
                    'is_outlier', 'recorded_by']
    search_fields = ['history_id', 'vehicle__vehicle_number', 'weight_record__slip_number']
    list_filter = ['is_significant_variance', 'is_outlier', 'recorded_date', 'vehicle']
    readonly_fields = ['history_id', 'created_at', 'weight_variance', 'variance_percentage']
    date_hierarchy = 'recorded_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('history_id', 'vehicle', 'weight_record', 'recorded_by')
        }),
        ('Tare Weight Details', {
            'fields': ('tare_weight', 'recorded_date', 'recorded_time')
        }),
        ('Variance Analysis', {
            'fields': ('previous_tare_weight', 'weight_variance', 'variance_percentage',
                      'is_significant_variance', 'variance_notes')
        }),
        ('Statistical Analysis', {
            'fields': ('is_outlier',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Tare history is created automatically
        return False
    
    def has_change_permission(self, request, obj=None):
        # Allow only notes and flags update
        return True
    
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ['vehicle', 'weight_record', 'tare_weight',
                                          'recorded_date', 'recorded_time', 'recorded_by',
                                          'previous_tare_weight']
        return self.readonly_fields


@admin.register(SecurityAuditLog)
class SecurityAuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'action', 'username', 'affected_model', 
                    'affected_object_id', 'weight_record', 'is_suspicious', 
                    'requires_review', 'reviewed_by']
    search_fields = ['username', 'notes', 'affected_model', 'ip_address',
                    'weight_record__slip_number']
    list_filter = ['action', 'is_suspicious', 'requires_review', 'timestamp',
                   'affected_model']
    readonly_fields = ['timestamp', 'user', 'username', 'action', 'weight_record',
                      'old_values', 'new_values', 'ip_address', 'user_agent',
                      'session_id', 'affected_model', 'affected_object_id']
    date_hierarchy = 'timestamp'
    actions = ['mark_as_suspicious', 'mark_as_reviewed']
    
    fieldsets = (
        ('Action Information', {
            'fields': ('timestamp', 'action', 'user', 'username')
        }),
        ('Affected Record', {
            'fields': ('weight_record', 'affected_model', 'affected_object_id')
        }),
        ('Changes', {
            'fields': ('old_values', 'new_values'),
            'classes': ('collapse',)
        }),
        ('Request Context', {
            'fields': ('ip_address', 'user_agent', 'session_id'),
            'classes': ('collapse',)
        }),
        ('Security Flags', {
            'fields': ('is_suspicious', 'requires_review', 'reviewed_by', 'reviewed_at')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )
    
    def mark_as_suspicious(self, request, queryset):
        """Mark selected logs as suspicious"""
        count = queryset.update(is_suspicious=True, requires_review=True)
        self.message_user(request, f"{count} log(s) marked as suspicious")
    mark_as_suspicious.short_description = "Mark selected logs as suspicious"
    
    def mark_as_reviewed(self, request, queryset):
        """Mark selected logs as reviewed"""
        from django.utils import timezone
        count = 0
        for log in queryset:
            if log.requires_review:
                log.requires_review = False
                log.reviewed_by = request.user
                log.reviewed_at = timezone.now()
                log.save()
                count += 1
        self.message_user(request, f"{count} log(s) marked as reviewed")
    mark_as_reviewed.short_description = "Mark selected logs as reviewed"
    
    def has_add_permission(self, request):
        # Audit logs are created by system only
        return False
    
    def has_change_permission(self, request, obj=None):
        # Allow only review status change
        return True
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of audit logs
        return False


# ==================== CORE MODELS ADMIN ====================

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['driver_name', 'driver_phone', 'is_deleted', 'deleted_at', 
                    'deleted_by', 'created_at']
    search_fields = ['driver_name', 'driver_phone']
    list_filter = ['is_deleted', 'created_at', 'deleted_at']
    readonly_fields = ['is_deleted', 'deleted_at', 'deleted_by']
    
    def get_queryset(self, request):
        """Show all records including soft-deleted"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # Show all
        return qs.filter(is_deleted=False)  # Hide deleted for non-superusers


@admin.register(Operator)
class OperatorAdmin(admin.ModelAdmin):
    list_display = ['employee_name', 'employee_id', 'phone', 'is_active', 
                    'is_deleted', 'deleted_at', 'deleted_by', 'created_at']
    search_fields = ['employee_name', 'employee_id', 'phone']
    list_filter = ['is_active', 'is_deleted', 'created_at', 'deleted_at']
    readonly_fields = ['is_deleted', 'deleted_at', 'deleted_by']
    
    def get_queryset(self, request):
        """Show all records including soft-deleted"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # Show all
        return qs.filter(is_deleted=False)  # Hide deleted for non-superusers


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['vehicle_number', 'vehicle_type', 'capacity', 'last_known_tare',
                    'last_tare_date', 'is_active', 'is_deleted', 'deleted_at', 
                    'deleted_by', 'created_at']
    search_fields = ['vehicle_number', 'vehicle_type']
    list_filter = ['is_active', 'vehicle_type', 'is_deleted', 'created_at', 'deleted_at']
    readonly_fields = ['is_deleted', 'deleted_at', 'deleted_by', 'last_known_tare', 
                      'last_tare_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('vehicle_number', 'vehicle_type', 'capacity', 'is_active')
        }),
        ('Tare Weight Tracking', {
            'fields': ('last_known_tare', 'last_tare_date'),
            'classes': ('collapse',),
            'description': 'Automatically updated from weight records'
        }),
        ('Soft Delete Status', {
            'fields': ('is_deleted', 'deleted_at', 'deleted_by'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Show all records including soft-deleted"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # Show all
        return qs.filter(is_deleted=False)  # Hide deleted for non-superusers


# ==================== AUTOMATION HARDWARE ADMIN ====================

@admin.register(WeighbridgeConfig)
class WeighbridgeConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'port', 'baud_rate', 'is_connected', 'auto_capture_enabled', 
                    'is_active', 'last_connected']
    search_fields = ['name', 'port']
    list_filter = ['is_connected', 'is_active', 'auto_capture_enabled', 'parity']
    readonly_fields = ['is_connected', 'last_connected', 'connection_status_message', 
                      'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'is_active')
        }),
        ('Serial Port Configuration', {
            'fields': ('port', 'baud_rate', 'data_bits', 'stop_bits', 'parity')
        }),
        ('Stability Settings', {
            'fields': ('stability_threshold', 'stability_duration')
        }),
        ('Auto-Capture Settings', {
            'fields': ('auto_capture_enabled', 'auto_capture_delay')
        }),
        ('Connection Status', {
            'fields': ('is_connected', 'last_connected', 'connection_status_message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LiveWeightReading)
class LiveWeightReadingAdmin(admin.ModelAdmin):
    list_display = ['weighbridge_config', 'weight', 'is_stable', 'stability_duration', 'timestamp']
    search_fields = ['weighbridge_config__name', 'raw_data']
    list_filter = ['is_stable', 'weighbridge_config', 'timestamp']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Reading Information', {
            'fields': ('weighbridge_config', 'weight', 'is_stable')
        }),
        ('Stability Details', {
            'fields': ('stability_started_at', 'stability_duration')
        }),
        ('Raw Data', {
            'fields': ('raw_data',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )
    
    def has_add_permission(self, request):
        # Readings are created by hardware service only
        return False
    
    def has_change_permission(self, request, obj=None):
        # Readings should not be modified
        return False


@admin.register(CameraConfig)
class CameraConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'camera_type', 'position', 'is_connected', 'ai_monitoring_enabled',
                    'auto_snapshot_enabled', 'show_on_dashboard', 'is_active', 'display_order']
    search_fields = ['name', 'rtsp_url']
    list_filter = ['camera_type', 'position', 'is_connected', 'is_active', 
                   'ai_monitoring_enabled', 'auto_snapshot_enabled', 'show_on_dashboard']
    readonly_fields = ['is_connected', 'last_connected', 'connection_status_message',
                      'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'camera_type', 'position', 'is_active')
        }),
        ('Connection Settings', {
            'fields': ('camera_index', 'rtsp_url', 'username', 'password')
        }),
        ('AI Monitoring', {
            'fields': ('ai_monitoring_enabled',),
            'description': 'Enable AI-based object detection and unauthorized presence alerts'
        }),
        ('Auto-Snapshot Settings', {
            'fields': ('auto_snapshot_enabled', 'snapshot_on_first_weight', 'snapshot_on_second_weight')
        }),
        ('Quality Settings', {
            'fields': ('resolution_width', 'resolution_height', 'jpeg_quality')
        }),
        ('Display Settings', {
            'fields': ('show_on_dashboard', 'display_order')
        }),
        ('Connection Status', {
            'fields': ('is_connected', 'last_connected', 'connection_status_message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PrinterConfig)
class PrinterConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'printer_type', 'printer_name', 'is_ready', 'slip_engine_ready',
                    'auto_print_enabled', 'is_active', 'last_printed']
    search_fields = ['name', 'printer_name', 'ip_address']
    list_filter = ['printer_type', 'is_connected', 'is_ready', 'is_active', 
                   'auto_print_enabled', 'paper_size']
    readonly_fields = ['is_connected', 'is_ready', 'slip_engine_ready', 'last_printed',
                      'connection_status_message', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'printer_type', 'is_active')
        }),
        ('Printer Connection', {
            'fields': ('printer_name', 'ip_address', 'port')
        }),
        ('Paper Settings', {
            'fields': ('paper_size', 'paper_width_mm')
        }),
        ('Auto-Print Settings', {
            'fields': ('auto_print_enabled', 'auto_print_copies', 'auto_print_on_completion')
        }),
        ('Status', {
            'fields': ('is_connected', 'is_ready', 'slip_engine_ready', 'last_printed',
                      'connection_status_message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ==================== AI MONITORING ADMIN ====================

@admin.register(AIMonitoringConfig)
class AIMonitoringConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_enabled', 'detection_model', 'model_confidence_threshold',
                    'alert_on_person', 'alert_on_animal', 'is_active', 'last_detection_run']
    search_fields = ['name']
    list_filter = ['is_enabled', 'is_active', 'detection_model', 'alert_on_person', 
                   'alert_on_animal', 'alert_on_unknown_objects']
    readonly_fields = ['last_detection_run', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Settings', {
            'fields': ('name', 'is_enabled', 'is_active')
        }),
        ('Detection Model', {
            'fields': ('detection_model', 'model_confidence_threshold', 'detection_interval_seconds'),
            'description': 'Configure AI detection model and confidence settings'
        }),
        ('Authorization', {
            'fields': ('authorized_object_classes',),
            'description': 'JSON list of authorized object classes (e.g., ["car", "truck", "bus"])'
        }),
        ('Alert Settings', {
            'fields': ('alert_on_unauthorized_objects', 'unauthorized_object_threshold', 
                      'alert_cooldown_seconds', 'alert_on_person', 'alert_on_animal', 
                      'alert_on_unknown_objects', 'auto_snapshot_on_unauthorized')
        }),
        ('Notifications', {
            'fields': ('send_email_alerts', 'email_recipients', 'send_sms_alerts', 
                      'sms_recipients', 'show_dashboard_alerts', 'play_alert_sound'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('last_detection_run',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        # Prevent accidental deletion of AI config
        if obj and obj.is_active:
            return False
        return True


@admin.register(ObjectDetectionLog)
class ObjectDetectionLogAdmin(admin.ModelAdmin):
    list_display = ['detected_at', 'camera', 'object_type', 'object_class', 'confidence',
                    'is_authorized', 'alert_triggered', 'alert_acknowledged', 
                    'weight_record_display', 'detection_count']
    search_fields = ['object_class', 'camera__name', 'weight_record__slip_number']
    list_filter = ['is_authorized', 'alert_triggered', 'alert_acknowledged', 'object_type',
                   'camera', 'detected_at']
    readonly_fields = ['detected_at', 'bbox_x1', 'bbox_y1', 'bbox_x2', 'bbox_y2',
                      'confidence', 'detection_count']
    date_hierarchy = 'detected_at'
    
    fieldsets = (
        ('Detection Information', {
            'fields': ('camera', 'weight_record', 'detected_at')
        }),
        ('Object Details', {
            'fields': ('object_type', 'object_class', 'confidence', 'is_authorized')
        }),
        ('Bounding Box', {
            'fields': ('bbox_x1', 'bbox_y1', 'bbox_x2', 'bbox_y2'),
            'classes': ('collapse',)
        }),
        ('Alert Status', {
            'fields': ('alert_triggered', 'alert_acknowledged', 'acknowledged_by', 
                      'acknowledged_at', 'detection_count')
        }),
        ('Snapshot', {
            'fields': ('snapshot_image',)
        }),
    )
    
    def weight_record_display(self, obj):
        """Display slip number"""
        if obj.weight_record:
            return f"{obj.weight_record.slip_number}"
        return "-"
    weight_record_display.short_description = 'Weight Record'
    
    def has_add_permission(self, request):
        # Detections are created by AI service only
        return False
    
    def has_change_permission(self, request, obj=None):
        # Allow only acknowledging
        return True
    
    def get_readonly_fields(self, request, obj=None):
        if obj:
            # Make most fields readonly except acknowledgment
            return self.readonly_fields + ['camera', 'weight_record', 'object_type',
                                          'object_class', 'is_authorized', 'alert_triggered',
                                          'snapshot_image']
        return self.readonly_fields


@admin.register(UnauthorizedPresenceAlert)
class UnauthorizedPresenceAlertAdmin(admin.ModelAdmin):
    list_display = ['alert_id', 'triggered_at', 'camera', 'object_description', 
                    'severity', 'status', 'weight_record_display', 'acknowledged_by',
                    'email_sent', 'sms_sent', 'dashboard_notified']
    search_fields = ['alert_id', 'object_description', 'alert_message', 
                    'camera__name', 'weight_record__slip_number']
    list_filter = ['status', 'severity', 'camera', 'email_sent', 'sms_sent', 
                   'dashboard_notified', 'triggered_at']
    readonly_fields = ['alert_id', 'triggered_at', 'resolved_at', 'acknowledged_at',
                      'email_sent', 'sms_sent', 'dashboard_notified']
    date_hierarchy = 'triggered_at'
    actions = ['mark_as_resolved', 'mark_as_false_positive']
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('alert_id', 'detection', 'camera', 'weight_record', 'triggered_at')
        }),
        ('Alert Details', {
            'fields': ('object_description', 'alert_message', 'severity', 'status')
        }),
        ('Snapshot', {
            'fields': ('alert_snapshot',)
        }),
        ('Notifications', {
            'fields': ('email_sent', 'sms_sent', 'dashboard_notified'),
            'classes': ('collapse',)
        }),
        ('Response', {
            'fields': ('acknowledged_by', 'acknowledged_at', 'resolved_at', 'resolution_notes')
        }),
    )
    
    def weight_record_display(self, obj):
        """Display slip number"""
        if obj.weight_record:
            return f"{obj.weight_record.slip_number}"
        return "-"
    weight_record_display.short_description = 'Weight Record'
    
    def mark_as_resolved(self, request, queryset):
        """Mark selected alerts as resolved"""
        from django.utils import timezone
        count = 0
        for alert in queryset:
            if alert.status in ['ACTIVE', 'ACKNOWLEDGED']:
                alert.status = 'RESOLVED'
                alert.resolved_at = timezone.now()
                alert.save()
                count += 1
        self.message_user(request, f"{count} alert(s) marked as resolved")
    mark_as_resolved.short_description = "Mark selected alerts as resolved"
    
    def mark_as_false_positive(self, request, queryset):
        """Mark selected alerts as false positive"""
        from django.utils import timezone
        count = 0
        for alert in queryset:
            if alert.status in ['ACTIVE', 'ACKNOWLEDGED', 'RESOLVED']:
                alert.status = 'FALSE_POSITIVE'
                alert.resolved_at = timezone.now()
                alert.save()
                count += 1
        self.message_user(request, f"{count} alert(s) marked as false positive")
    mark_as_false_positive.short_description = "Mark selected alerts as false positive"
    
    def has_add_permission(self, request):
        # Alerts are created by AI service only
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Only allow deletion of false positives
        if obj and obj.status == 'FALSE_POSITIVE':
            return True
        return False


# ==================== WEIGHT RECORD ADMIN ====================

class WeightDropInline(admin.TabularInline):
    model = WeightDrop
    extra = 0
    readonly_fields = ['net_weight', 'timestamp']
    fields = ['drop_number', 'gross_weight', 'tare_weight', 'net_weight', 'remarks', 'timestamp']


class WeightRecordPhotoInline(admin.TabularInline):
    """Inline for displaying photos in weight record admin"""
    model = WeightRecordPhoto
    extra = 0
    readonly_fields = ['uploaded_at', 'photo', 'is_auto_captured', 'captured_weight', 
                      'camera', 'detection']
    fields = ['photo', 'camera', 'detection', 'photo_type', 'weight_stage', 'is_auto_captured', 
              'captured_weight', 'caption', 'display_order', 'uploaded_by', 'uploaded_at']


@admin.register(WeightRecord)
class WeightRecordAdmin(admin.ModelAdmin):
    list_display = ['slip_number', 'date', 'shift', 'customer', 'vehicle', 
                    'status', 'operator_first_weight', 'operator_second_weight',
                    'first_weight_auto_captured', 'second_weight_auto_captured',
                    'slip_auto_printed', 'has_unauthorized_detections', 
                    'unauthorized_detection_count', 'is_deleted', 'net_weight', 
                    'total_amount', 'created_at']
    search_fields = ['slip_number', 'customer__driver_name', 'vehicle__vehicle_number', 
                    'operator_first_weight__employee_name', 'operator_second_weight__employee_name', 'material_type']
    list_filter = ['date', 'shift', 'status', 'is_multi_drop', 'first_weight_auto_captured',
                   'second_weight_auto_captured', 'slip_auto_printed', 
                   'has_unauthorized_detections', 'is_deleted', 'created_at']
    date_hierarchy = 'date'
    readonly_fields = ['slip_number', 'net_weight', 'total_amount', 'gross_weight', 
                      'tare_weight', 'first_weight_time', 'second_weight_time',
                      'current_live_weight', 'last_weight_update',
                      'first_weight_stable_detected_time', 'first_weight_stability_duration',
                      'second_weight_stable_detected_time', 'second_weight_stability_duration',
                      'slip_printed_time', 'slip_print_count',
                      'has_unauthorized_detections', 'unauthorized_detection_count',
                      'is_deleted', 'deleted_at', 'deleted_by',
                      'is_date_locked', 'date_locked_at', 'last_modified_by',
                      'modification_count', 'created_at', 'updated_at']
    inlines = [WeightDropInline, WeightRecordPhotoInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('slip_number', 'customer', 'vehicle', 'date', 'shift', 'status')
        }),
        ('Security Status', {
            'fields': ('has_unauthorized_detections', 'unauthorized_detection_count',
                      'is_date_locked', 'date_locked_at', 'last_modified_by', 
                      'modification_count'),
            'classes': ('collapse',),
            'description': 'AI monitoring and date lock status'
        }),
        ('Soft Delete Status', {
            'fields': ('is_deleted', 'deleted_at', 'deleted_by'),
            'classes': ('collapse',)
        }),
        ('Live Weight Monitoring', {
            'fields': ('current_live_weight', 'last_weight_update'),
            'classes': ('collapse',)
        }),
        ('First Weight', {
            'fields': ('first_weight', 'first_weight_time', 'operator_first_weight',
                      'first_weight_stable_detected_time', 'first_weight_stability_duration',
                      'first_weight_auto_captured'),
            'classes': ('collapse',)
        }),
        ('Second Weight', {
            'fields': ('second_weight', 'second_weight_time', 'operator_second_weight',
                      'second_weight_stable_detected_time', 'second_weight_stability_duration',
                      'second_weight_auto_captured'),
            'classes': ('collapse',)
        }),
        ('Calculated Weights', {
            'fields': ('gross_weight', 'tare_weight', 'net_weight', 'is_multi_drop')
        }),
        ('Material & Pricing', {
            'fields': ('material_type', 'rate_per_unit', 'total_amount')
        }),
        ('Slip Printing', {
            'fields': ('slip_printed_time', 'slip_auto_printed', 'slip_print_count'),
            'classes': ('collapse',)
        }),
        ('Additional Info', {
            'fields': ('remarks', 'created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        """Show all records including soft-deleted for superusers"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # Show all
        return qs.filter(is_deleted=False)  # Hide deleted for non-superusers
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status in ['COMPLETED', 'CANCELLED']:
            # Make most fields readonly for completed/cancelled records
            return self.readonly_fields + ['customer', 'vehicle', 'date', 'shift', 
                                          'first_weight', 'second_weight', 
                                          'operator_first_weight', 'operator_second_weight',
                                          'material_type', 'rate_per_unit']
        return self.readonly_fields


@admin.register(WeightDrop)
class WeightDropAdmin(admin.ModelAdmin):
    list_display = ['weight_record', 'drop_number', 'gross_weight', 'tare_weight', 
                    'net_weight', 'timestamp']
    search_fields = ['weight_record__slip_number', 'weight_record__customer__driver_name', 
                    'weight_record__vehicle__vehicle_number']
    list_filter = ['timestamp']
    readonly_fields = ['net_weight', 'timestamp']
    
    fieldsets = (
        ('Drop Information', {
            'fields': ('weight_record', 'drop_number')
        }),
        ('Weight Measurements', {
            'fields': ('gross_weight', 'tare_weight', 'net_weight')
        }),
        ('Additional Details', {
            'fields': ('remarks', 'timestamp')
        }),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'action', 'weight_record_display', 'payment', 'detection',
                    'alert_display', 'user', 'ip_address']
    search_fields = ['user', 'notes', 'weight_record__slip_number', 
                    'weight_record__customer__driver_name', 'alert__alert_id']
    list_filter = ['action', 'timestamp']
    readonly_fields = ['timestamp', 'weight_record', 'payment', 'detection', 'alert',
                      'action', 'user', 'ip_address', 'user_agent', 'old_values', 
                      'new_values', 'calculation_details']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Audit Information', {
            'fields': ('timestamp', 'action', 'weight_record', 'payment', 'detection', 'alert', 'user')
        }),
        ('Request Details', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Changes', {
            'fields': ('old_values', 'new_values', 'calculation_details')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )
    
    def weight_record_display(self, obj):
        """Display slip number instead of ID"""
        if obj.weight_record:
            return f"{obj.weight_record.slip_number}"
        return "-"
    weight_record_display.short_description = 'Weight Record'
    
    def alert_display(self, obj):
        """Display alert ID"""
        if obj.alert:
            return f"{obj.alert.alert_id}"
        return "-"
    alert_display.short_description = 'Alert'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


# ==================== PAYMENT ADMIN ====================

class QRCodeInline(admin.TabularInline):
    model = QRCode
    extra = 0
    readonly_fields = ['qr_id', 'generated_at', 'scan_count']
    fields = ['qr_id', 'is_active', 'scan_count', 'expires_at', 'generated_at']
    can_delete = False


class PaymentSlipInline(admin.TabularInline):
    model = PaymentSlip
    extra = 0
    readonly_fields = ['slip_id', 'slip_number', 'slip_status', 'is_auto_printed', 
                      'generated_at', 'printed_at']
    fields = ['slip_id', 'slip_number', 'slip_status', 'is_auto_printed', 'printer',
              'generated_by', 'printed_by', 'printer_name', 'generated_at', 'printed_at']
    can_delete = False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'weight_record_display', 'amount', 'payment_method', 
                    'payment_status', 'transaction_date', 'created_at']
    search_fields = ['payment_id', 'weight_record__slip_number', 
                    'weight_record__customer__driver_name', 
                    'weight_record__vehicle__vehicle_number', 'upi_transaction_id']
    list_filter = ['payment_status', 'payment_method', 'transaction_date', 'created_at']
    readonly_fields = ['payment_id', 'created_at', 'updated_at', 'transaction_date']
    date_hierarchy = 'created_at'
    inlines = [QRCodeInline, PaymentSlipInline]
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('payment_id', 'weight_record', 'amount', 'payment_method', 'payment_status')
        }),
        ('UPI Details', {
            'fields': ('upi_qr_data', 'upi_transaction_id', 'upi_transaction_ref')
        }),
        ('Transaction Details', {
            'fields': ('transaction_date', 'created_at', 'updated_at')
        }),
        ('Additional Info', {
            'fields': ('remarks',)
        }),
    )
    
    def weight_record_display(self, obj):
        """Display slip number and customer"""
        if obj.weight_record:
            return f"{obj.weight_record.slip_number} - {obj.weight_record.customer.driver_name}"
        return "-"
    weight_record_display.short_description = 'Weight Record'
    
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ['weight_record']
        return self.readonly_fields


@admin.register(QRCode)
class QRCodeAdmin(admin.ModelAdmin):
    list_display = ['qr_id', 'payment', 'is_active', 'scan_count', 'expires_at', 'generated_at']
    search_fields = ['qr_id', 'payment__payment_id', 'payment__weight_record__slip_number',
                    'payment__weight_record__customer__driver_name']
    list_filter = ['is_active', 'generated_at', 'expires_at']
    readonly_fields = ['qr_id', 'qr_string', 'qr_image', 'generated_at', 'scan_count']
    date_hierarchy = 'generated_at'
    
    fieldsets = (
        ('QR Information', {
            'fields': ('qr_id', 'payment', 'is_active')
        }),
        ('QR Data', {
            'fields': ('qr_string', 'qr_image'),
            'classes': ('collapse',)
        }),
        ('Scan Details', {
            'fields': ('scan_count', 'expires_at', 'generated_at')
        }),
    )
    
    def has_add_permission(self, request):
        return False


@admin.register(PaymentSlip)
class PaymentSlipAdmin(admin.ModelAdmin):
    list_display = ['slip_id', 'slip_number', 'payment_display', 'slip_status', 
                    'is_auto_printed', 'printer_display', 'printed_by', 
                    'print_count', 'generated_at', 'printed_at']
    search_fields = ['slip_id', 'slip_number', 'payment__payment_id', 
                    'payment__weight_record__slip_number',
                    'payment__weight_record__customer__driver_name']
    list_filter = ['slip_status', 'is_auto_printed', 'auto_print_failed', 
                   'generated_at', 'printed_at', 'printer_name']
    readonly_fields = ['slip_id', 'slip_number', 'slip_content', 'pdf_file', 
                      'is_auto_printed', 'auto_print_failed', 'auto_print_error',
                      'generated_at', 'printed_at', 'created_at', 'updated_at']
    date_hierarchy = 'generated_at'
    
    fieldsets = (
        ('Slip Information', {
            'fields': ('slip_id', 'slip_number', 'payment', 'slip_status')
        }),
        ('PDF File', {
            'fields': ('pdf_file',)
        }),
        ('Printer', {
            'fields': ('printer',)
        }),
        ('Generation Details', {
            'fields': ('generated_by', 'generated_at')
        }),
        ('Print Details', {
            'fields': ('printed_by', 'printer_name', 'print_count', 'printed_at')
        }),
        ('Auto-Print Status', {
            'fields': ('is_auto_printed', 'auto_print_failed', 'auto_print_error'),
            'classes': ('collapse',)
        }),
        ('Slip Content', {
            'fields': ('slip_content',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def payment_display(self, obj):
        """Display weight record slip number"""
        if obj.payment and obj.payment.weight_record:
            return f"{obj.payment.weight_record.slip_number}"
        return "-"
    payment_display.short_description = 'Weight Record'
    
    def printer_display(self, obj):
        """Display printer name"""
        if obj.printer:
            return obj.printer.name
        return "-"
    printer_display.short_description = 'Printer'
    
    def has_add_permission(self, request):
        return False 
    
    def has_delete_permission(self, request, obj=None):
        # Only allow deletion of draft slips
        if obj and obj.slip_status in ['PRINTED', 'SENT']:
            return False
        return True


# ==================== WEIGHT RECORD PHOTO ADMIN ====================

@admin.register(WeightRecordPhoto)
class WeightRecordPhotoAdmin(admin.ModelAdmin):
    list_display = ['weight_record_display', 'camera_display', 'detection_display',
                    'photo_type', 'weight_stage', 'is_auto_captured', 'captured_weight', 
                    'caption', 'display_order', 'uploaded_by', 'uploaded_at']
    search_fields = ['weight_record__slip_number', 'weight_record__customer__driver_name', 
                    'caption', 'photo_type', 'camera__name']
    list_filter = ['photo_type', 'weight_stage', 'is_auto_captured', 'timestamp_added',
                   'camera', 'uploaded_at']
    readonly_fields = ['uploaded_at', 'is_auto_captured', 'captured_weight']
    date_hierarchy = 'uploaded_at'
    
    fieldsets = (
        ('Photo Information', {
            'fields': ('weight_record', 'photo', 'camera', 'detection', 'photo_type', 
                      'weight_stage', 'caption')
        }),
        ('Auto-Capture Details', {
            'fields': ('is_auto_captured', 'captured_weight', 'timestamp_added'),
            'classes': ('collapse',)
        }),
        ('Display Settings', {
            'fields': ('display_order',)
        }),
        ('Upload Details', {
            'fields': ('uploaded_by', 'uploaded_at')
        }),
    )
    
    def weight_record_display(self, obj):
        """Display slip number"""
        if obj.weight_record:
            return f"{obj.weight_record.slip_number}"
        return "-"
    weight_record_display.short_description = 'Weight Record'
    
    def camera_display(self, obj):
        """Display camera name""" 
        if obj.camera:
            return f"{obj.camera.name} ({obj.camera.get_position_display()})"
        return "-"
    camera_display.short_description = 'Camera'
    
    def detection_display(self, obj):
        """Display if linked to detection"""
        if obj.detection:
            return f"Detection #{obj.detection.id} ({obj.detection.get_object_type_display()})"
        return "-"
    detection_display.short_description = 'Detection'
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return self.readonly_fields + ['weight_record', 'photo', 'weight_stage', 
                                          'camera', 'detection']
        return self.readonly_fields


# ==================== COMPANY DETAILS ADMIN ====================

@admin.register(CompanyDetails)
class CompanyDetailsAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'company_phone', 'company_email', 'gstin', 
                    'is_active', 'updated_at']
    search_fields = ['company_name', 'gstin', 'pan', 'company_email']
    list_filter = ['is_active', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Company Information', {
            'fields': ('company_name', 'company_address', 'company_phone', 
                      'company_email', 'company_logo')
        }),
        ('Tax & Registration Details', {
            'fields': ('gstin', 'pan')
        }),
        ('UPI Payment Details', {
            'fields': ('upi_id', 'upi_name'),
            'description': 'Configure UPI details for payment QR codes'
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'account_number', 'ifsc_code'),
            'classes': ('collapse',)
        }),
        ('Slip Configuration', {
            'fields': ('slip_header_text', 'slip_footer_text'),
            'classes': ('collapse',)
        }),
        ('Status & Timestamps', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of company details
        return False
    
    def has_add_permission(self, request):
        # Only allow one company record
        if CompanyDetails.objects.filter(is_active=True).exists():
            return False
        return True