from rest_framework import serializers
from .models import (
    Customer, Operator, Vehicle, WeightRecord, WeightDrop, AuditLog,
    Payment, QRCode, PaymentSlip, WeightRecordPhoto, CompanyDetails,
    WeighbridgeConfig, LiveWeightReading, CameraConfig, PrinterConfig,
    # AI Monitoring models
    AIMonitoringConfig, ObjectDetectionLog, UnauthorizedPresenceAlert
)
# ==================== SECURITY IMPORTS ====================
from .models_security_data_management import (
    DateLockConfig, BackupConfig, BackupLog, TareWeightHistory, SecurityAuditLog
)


# ==================== SECURITY SERIALIZERS ====================

class DateLockConfigSerializer(serializers.ModelSerializer):
    """Serializer for Date Lock Configuration"""
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = DateLockConfig
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_status_display(self, obj):
        return {
            'is_enabled': obj.is_enabled,
            'lock_date': obj.lock_date.isoformat() if obj.lock_date else None,
            'days_to_lock': obj.days_to_lock,
            'message': f"Dates before {obj.lock_date} are locked" if obj.is_enabled and obj.lock_date else "Date locking disabled"
        }
    
    def validate_days_to_lock(self, value):
        """Validate days to lock"""
        if value < 0:
            raise serializers.ValidationError("Days to lock cannot be negative")
        if value > 365:
            raise serializers.ValidationError("Days to lock should not exceed 365 days")
        return value


class BackupConfigSerializer(serializers.ModelSerializer):
    """Serializer for Backup Configuration"""
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    backup_status = serializers.SerializerMethodField()
    next_backup_time = serializers.SerializerMethodField()
    
    class Meta:
        model = BackupConfig
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'last_backup_time']
    
    def get_backup_status(self, obj):
        return {
            'is_enabled': obj.is_enabled,
            'frequency': obj.get_frequency_display(),
            'last_backup': obj.last_backup_time.isoformat() if obj.last_backup_time else None,
            'backup_path': obj.backup_path,
            'retain_days': obj.backup_retention_days
        }
    
    def get_next_backup_time(self, obj):
        """Calculate next expected backup time"""
        if not obj.is_enabled or not obj.last_backup_time:
            return None
        
        from datetime import timedelta
        if obj.frequency == 'DAILY':
            next_time = obj.last_backup_time + timedelta(days=1)
        elif obj.frequency == 'WEEKLY':
            next_time = obj.last_backup_time + timedelta(weeks=1)
        elif obj.frequency == 'MONTHLY':
            next_time = obj.last_backup_time + timedelta(days=30)
        else:
            return None
        
        return next_time.isoformat()
    
    def validate_backup_retention_days(self, value):
        """Validate backup retention days"""
        if value < 7:
            raise serializers.ValidationError("Backup retention should be at least 7 days")
        if value > 365:
            raise serializers.ValidationError("Backup retention should not exceed 365 days")
        return value


class BackupLogSerializer(serializers.ModelSerializer):
    """Serializer for Backup Logs"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    triggered_by_name = serializers.CharField(source='triggered_by.username', read_only=True, allow_null=True)
    backup_info = serializers.SerializerMethodField()
    time_info = serializers.SerializerMethodField()
    
    class Meta:
        model = BackupLog
        fields = '__all__'
        read_only_fields = ['backup_started_at', 'backup_completed_at']
    
    def get_backup_info(self, obj):
        return {
            'status': obj.get_status_display(),
            'file_path': obj.backup_file_path,
            'file_size_mb': round(obj.backup_file_size / (1024 * 1024), 2) if obj.backup_file_size else None,
            'is_automated': obj.is_automated,
            'error_message': obj.error_message
        }
    
    def get_time_info(self, obj):
        """Get time-related information"""
        duration = None
        if obj.backup_started_at and obj.backup_completed_at:
            delta = obj.backup_completed_at - obj.backup_started_at
            duration = delta.total_seconds()
        
        return {
            'started_at': obj.backup_started_at.isoformat() if obj.backup_started_at else None,
            'completed_at': obj.backup_completed_at.isoformat() if obj.backup_completed_at else None,
            'duration_seconds': duration
        }


class TareWeightHistorySerializer(serializers.ModelSerializer):
    """Serializer for Tare Weight History"""
    vehicle_number = serializers.CharField(source='vehicle.vehicle_number', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.username', read_only=True, allow_null=True)
    weight_record_slip = serializers.CharField(source='weight_record.slip_number', read_only=True, allow_null=True)
    change_info = serializers.SerializerMethodField()
    
    class Meta:
        model = TareWeightHistory
        fields = '__all__'
        read_only_fields = ['recorded_at']
    
    def get_change_info(self, obj):
        """Get information about tare weight change"""
        change_kg = None
        change_percent = None
        
        if obj.previous_tare_weight and obj.tare_weight:
            change_kg = float(obj.tare_weight - obj.previous_tare_weight)
            if obj.previous_tare_weight != 0:
                change_percent = (change_kg / float(obj.previous_tare_weight)) * 100
        
        return {
            'tare_weight': float(obj.tare_weight),
            'previous_tare_weight': float(obj.previous_tare_weight) if obj.previous_tare_weight else None,
            'change_kg': change_kg,
            'change_percent': round(change_percent, 2) if change_percent else None,
            'is_significant_change': abs(change_kg) > 50 if change_kg else False
        }


class SecurityAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for Security Audit Logs"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    action_display = serializers.SerializerMethodField()
    record_info = serializers.SerializerMethodField()
    
    class Meta:
        model = SecurityAuditLog
        fields = '__all__'
        read_only_fields = ['timestamp']
    
    def get_action_display(self, obj):
        """Get human-readable action"""
        action_map = {
            'SOFT_DELETE': 'Record Soft Deleted',
            'RESTORE': 'Record Restored',
            'UPDATE_DENIED': 'Update Denied (Date Locked)',
            'DELETE_DENIED': 'Delete Denied (Permission/Date Lock)',
            'DATE_LOCK_ENABLED': 'Date Lock Enabled',
            'DATE_LOCK_DISABLED': 'Date Lock Disabled',
            'BACKUP_TRIGGERED': 'Backup Triggered',
            'TARE_UPDATED': 'Tare Weight Updated'
        }
        return action_map.get(obj.action, obj.action)
    
    def get_record_info(self, obj):
        """Get record information"""
        return {
            'model': obj.model_name,
            'record_id': obj.record_id,
            'user': obj.user.username,
            'action': self.get_action_display(obj),
            'notes': obj.notes
        }


class SoftDeletedRecordSerializer(serializers.Serializer):
    """Serializer for soft-deleted records"""
    id = serializers.IntegerField()
    deleted_at = serializers.DateTimeField()
    deleted_by = serializers.CharField()
    model_type = serializers.CharField()
    record_info = serializers.DictField()


class RestoreRecordSerializer(serializers.Serializer):
    """Serializer for restoring soft-deleted records"""
    record_id = serializers.IntegerField()
    model_type = serializers.ChoiceField(choices=['customer', 'operator', 'vehicle', 'weight_record'])


class TareVarianceReportSerializer(serializers.Serializer):
    """Serializer for tare weight variance report"""
    vehicle_id = serializers.IntegerField()
    vehicle_number = serializers.CharField()
    history_count = serializers.IntegerField()
    average_tare = serializers.DecimalField(max_digits=10, decimal_places=2)
    min_tare = serializers.DecimalField(max_digits=10, decimal_places=2)
    max_tare = serializers.DecimalField(max_digits=10, decimal_places=2)
    variance = serializers.DecimalField(max_digits=10, decimal_places=2)
    std_deviation = serializers.DecimalField(max_digits=10, decimal_places=2)
    recent_tare = serializers.DecimalField(max_digits=10, decimal_places=2)
    is_outlier = serializers.BooleanField()


class DateLockStatusSerializer(serializers.Serializer):
    """Serializer for checking date lock status"""
    date = serializers.DateField()
    is_locked = serializers.BooleanField()
    lock_config_id = serializers.IntegerField(allow_null=True)
    message = serializers.CharField()


# ==================== ORIGINAL SERIALIZERS ====================

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'


class OperatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Operator
        fields = '__all__'


class VehicleSerializer(serializers.ModelSerializer):
    # Add tare weight history info
    tare_history_count = serializers.SerializerMethodField()
    last_tare_update = serializers.SerializerMethodField()
    
    class Meta:
        model = Vehicle
        fields = '__all__'
    
    def get_tare_history_count(self, obj):
        """Get count of tare weight history records"""
        if hasattr(obj, 'tare_history'):
            return obj.tare_history.count()
        return 0
    
    def get_last_tare_update(self, obj):
        """Get last tare weight update info"""
        return {
            'last_known_tare': float(obj.last_known_tare) if obj.last_known_tare else None,
            'last_tare_date': obj.last_tare_date.isoformat() if obj.last_tare_date else None
        }


# ==================== HARDWARE CONFIGURATION SERIALIZERS ====================

class WeighbridgeConfigSerializer(serializers.ModelSerializer):
    """Serializer for Weighbridge Configuration"""
    connection_status = serializers.SerializerMethodField()
    parity_display = serializers.CharField(source='get_parity_display', read_only=True)
    
    class Meta:
        model = WeighbridgeConfig
        fields = '__all__'
        read_only_fields = ['is_connected', 'last_connected', 'connection_status_message']
    
    def get_connection_status(self, obj):
        return {
            'is_connected': obj.is_connected,
            'last_connected': obj.last_connected.isoformat() if obj.last_connected else None,
            'status_message': obj.connection_status_message,
            'is_active': obj.is_active
        }
    
    def validate_stability_threshold(self, value):
        """Validate stability threshold"""
        if value < 0:
            raise serializers.ValidationError("Stability threshold must be positive")
        if value > 100:
            raise serializers.ValidationError("Stability threshold seems too high")
        return value
    
    def validate_stability_duration(self, value):
        """Validate stability duration"""
        if value < 1:
            raise serializers.ValidationError("Stability duration must be at least 1 second")
        if value > 60:
            raise serializers.ValidationError("Stability duration should not exceed 60 seconds")
        return value


class LiveWeightReadingSerializer(serializers.ModelSerializer):
    """Serializer for Live Weight Readings"""
    weighbridge_name = serializers.CharField(source='weighbridge_config.name', read_only=True)
    stability_status = serializers.SerializerMethodField()
    time_since_reading = serializers.SerializerMethodField()
    
    class Meta:
        model = LiveWeightReading
        fields = '__all__'
        read_only_fields = ['timestamp']
    
    def get_stability_status(self, obj):
        return {
            'is_stable': obj.is_stable,
            'stability_started_at': obj.stability_started_at.isoformat() if obj.stability_started_at else None,
            'stability_duration': float(obj.stability_duration),
            'message': f'Stable for {obj.stability_duration}s' if obj.is_stable else 'Unstable'
        }
    
    def get_time_since_reading(self, obj):
        """Calculate time elapsed since reading in seconds"""
        from django.utils import timezone
        delta = timezone.now() - obj.timestamp
        return delta.total_seconds()


class LiveWeightCreateSerializer(serializers.Serializer):
    """Serializer for creating live weight readings (used by hardware service)"""
    weighbridge_config_id = serializers.IntegerField()
    weight = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    is_stable = serializers.BooleanField(default=False)
    stability_duration = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)
    raw_data = serializers.CharField(required=False, allow_blank=True)
    
    def validate_weight(self, value):
        if value < 0:
            raise serializers.ValidationError("Weight cannot be negative")
        if value > 999999:
            raise serializers.ValidationError("Weight value seems unrealistic")
        return value


class CameraConfigSerializer(serializers.ModelSerializer):
    """Serializer for Camera Configuration"""
    connection_status = serializers.SerializerMethodField()
    camera_type_display = serializers.CharField(source='get_camera_type_display', read_only=True)
    position_display = serializers.CharField(source='get_position_display', read_only=True)
    ai_status = serializers.SerializerMethodField()
    
    class Meta:
        model = CameraConfig
        fields = '__all__'
        read_only_fields = ['is_connected', 'last_connected', 'connection_status_message']
    
    def get_connection_status(self, obj):
        return {
            'is_connected': obj.is_connected,
            'last_connected': obj.last_connected.isoformat() if obj.last_connected else None,
            'status_message': obj.connection_status_message,
            'is_active': obj.is_active
        }
    
    def get_ai_status(self, obj):
        """Get AI monitoring status"""
        return {
            'ai_monitoring_enabled': obj.ai_monitoring_enabled,
            'is_active': obj.is_active,
            'is_connected': obj.is_connected
        }
    
    def validate_resolution_width(self, value):
        """Validate resolution width"""
        if value < 320 or value > 3840:
            raise serializers.ValidationError("Width must be between 320 and 3840 pixels")
        return value
    
    def validate_resolution_height(self, value):
        """Validate resolution height"""
        if value < 240 or value > 2160:
            raise serializers.ValidationError("Height must be between 240 and 2160 pixels")
        return value
    
    def validate_jpeg_quality(self, value):
        """Validate JPEG quality"""
        if value < 1 or value > 100:
            raise serializers.ValidationError("JPEG quality must be between 1 and 100")
        return value


class CameraSnapshotSerializer(serializers.Serializer):
    """Serializer for camera snapshot data"""
    camera_id = serializers.IntegerField()
    image = serializers.CharField(help_text="Base64 encoded image data")
    timestamp = serializers.DateTimeField(required=False)
    
    def validate_image(self, value):
        """Validate base64 image data"""
        if not value:
            raise serializers.ValidationError("Image data is required")
        # Additional validation for base64 format can be added here
        return value


class PrinterConfigSerializer(serializers.ModelSerializer):
    """Serializer for Printer Configuration"""
    connection_status = serializers.SerializerMethodField()
    printer_type_display = serializers.CharField(source='get_printer_type_display', read_only=True)
    paper_size_display = serializers.CharField(source='get_paper_size_display', read_only=True)
    status_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = PrinterConfig
        fields = '__all__'
        read_only_fields = [
            'is_connected', 
            'last_printed', 
            'connection_status_message',
            'is_ready',
            'slip_engine_ready'
        ]
    
    def get_connection_status(self, obj):
        return {
            'is_connected': obj.is_connected,
            'is_ready': obj.is_ready,
            'slip_engine_ready': obj.slip_engine_ready,
            'last_printed': obj.last_printed.isoformat() if obj.last_printed else None,
            'status_message': obj.connection_status_message,
            'is_active': obj.is_active
        }
    
    def get_status_summary(self, obj):
        """Get human-readable status summary"""
        if not obj.is_active:
            return "Inactive"
        if not obj.is_connected:
            return "Disconnected"
        if not obj.is_ready:
            return "Not Ready"
        if not obj.slip_engine_ready:
            return "Slip Engine Not Ready"
        return "Ready"
    
    def validate_auto_print_copies(self, value):
        """Validate number of copies"""
        if value < 1 or value > 10:
            raise serializers.ValidationError("Copies must be between 1 and 10")
        return value


# ==================== AI MONITORING SERIALIZERS ====================

class AIMonitoringConfigSerializer(serializers.ModelSerializer):
    """Serializer for AI Monitoring Configuration"""
    detection_model_display = serializers.CharField(source='get_detection_model_display', read_only=True)
    status_summary = serializers.SerializerMethodField()
    alert_settings = serializers.SerializerMethodField()
    notification_settings = serializers.SerializerMethodField()
    
    class Meta:
        model = AIMonitoringConfig
        fields = '__all__'
        read_only_fields = ['last_detection_run', 'created_at', 'updated_at']
    
    def get_status_summary(self, obj):
        """Get AI monitoring status summary"""
        return {
            'is_enabled': obj.is_enabled,
            'is_active': obj.is_active,
            'detection_model': obj.detection_model,
            'last_run': obj.last_detection_run.isoformat() if obj.last_detection_run else None
        }
    
    def get_alert_settings(self, obj):
        """Get alert configuration"""
        return {
            'alert_on_unauthorized_objects': obj.alert_on_unauthorized_objects,
            'alert_on_person': obj.alert_on_person,
            'alert_on_animal': obj.alert_on_animal,
            'alert_on_unknown_objects': obj.alert_on_unknown_objects,
            'unauthorized_object_threshold': obj.unauthorized_object_threshold,
            'alert_cooldown_seconds': obj.alert_cooldown_seconds,
            'auto_snapshot_on_unauthorized': obj.auto_snapshot_on_unauthorized
        }
    
    def get_notification_settings(self, obj):
        """Get notification configuration"""
        return {
            'send_email_alerts': obj.send_email_alerts,
            'send_sms_alerts': obj.send_sms_alerts,
            'show_dashboard_alerts': obj.show_dashboard_alerts,
            'play_alert_sound': obj.play_alert_sound,
            'email_recipients': obj.email_recipients.split(',') if obj.email_recipients else [],
            'sms_recipients': obj.sms_recipients.split(',') if obj.sms_recipients else []
        }
    
    def validate_model_confidence_threshold(self, value):
        """Validate confidence threshold"""
        if value < 0 or value > 1:
            raise serializers.ValidationError("Confidence threshold must be between 0.0 and 1.0")
        return value
    
    def validate_unauthorized_object_threshold(self, value):
        """Validate detection threshold"""
        if value < 1 or value > 100:
            raise serializers.ValidationError("Threshold must be between 1 and 100")
        return value


class ObjectDetectionLogSerializer(serializers.ModelSerializer):
    """Serializer for Object Detection Logs"""
    camera_name = serializers.CharField(source='camera.name', read_only=True)
    camera_position = serializers.CharField(source='camera.get_position_display', read_only=True)
    weight_record_slip = serializers.CharField(source='weight_record.slip_number', read_only=True)
    object_type_display = serializers.CharField(source='get_object_type_display', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.employee_name', read_only=True)
    snapshot_url = serializers.SerializerMethodField()
    detection_details = serializers.SerializerMethodField()
    
    class Meta:
        model = ObjectDetectionLog
        fields = '__all__'
        read_only_fields = ['detected_at']
    
    def get_snapshot_url(self, obj):
        """Get snapshot image URL"""
        if obj.snapshot_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.snapshot_image.url)
            return obj.snapshot_image.url
        return None
    
    def get_detection_details(self, obj):
        """Get detailed detection information"""
        return {
            'object_type': obj.get_object_type_display(),
            'object_class': obj.object_class,
            'confidence': float(obj.confidence),
            'is_authorized': obj.is_authorized,
            'alert_triggered': obj.alert_triggered,
            'bounding_box': {
                'x1': float(obj.bbox_x1),
                'y1': float(obj.bbox_y1),
                'x2': float(obj.bbox_x2),
                'y2': float(obj.bbox_y2)
            },
            'detection_count': obj.detection_count
        }


class UnauthorizedPresenceAlertSerializer(serializers.ModelSerializer):
    """Serializer for Unauthorized Presence Alerts"""
    camera_name = serializers.CharField(source='camera.name', read_only=True)
    camera_position = serializers.CharField(source='camera.get_position_display', read_only=True)
    weight_record_slip = serializers.CharField(source='weight_record.slip_number', read_only=True)
    detection_details = ObjectDetectionLogSerializer(source='detection', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.employee_name', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    alert_snapshot_url = serializers.SerializerMethodField()
    alert_info = serializers.SerializerMethodField()
    time_info = serializers.SerializerMethodField()
    
    class Meta:
        model = UnauthorizedPresenceAlert
        fields = '__all__'
        read_only_fields = ['alert_id', 'triggered_at', 'resolved_at', 'acknowledged_at']
    
    def get_alert_snapshot_url(self, obj):
        """Get alert snapshot URL"""
        if obj.alert_snapshot:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.alert_snapshot.url)
            return obj.alert_snapshot.url
        return None
    
    def get_alert_info(self, obj):
        """Get alert summary information"""
        return {
            'severity': obj.get_severity_display(),
            'status': obj.get_status_display(),
            'object_description': obj.object_description,
            'camera': obj.camera.name,
            'camera_position': obj.camera.get_position_display(),
            'weight_record': obj.weight_record.slip_number if obj.weight_record else None,
            'notifications': {
                'email_sent': obj.email_sent,
                'sms_sent': obj.sms_sent,
                'dashboard_notified': obj.dashboard_notified
            }
        }
    
    def get_time_info(self, obj):
        """Get time-related information"""
        from django.utils import timezone
        
        time_since_trigger = None
        if obj.triggered_at:
            delta = timezone.now() - obj.triggered_at
            time_since_trigger = delta.total_seconds()
        
        return {
            'triggered_at': obj.triggered_at.isoformat() if obj.triggered_at else None,
            'acknowledged_at': obj.acknowledged_at.isoformat() if obj.acknowledged_at else None,
            'resolved_at': obj.resolved_at.isoformat() if obj.resolved_at else None,
            'time_since_trigger_seconds': time_since_trigger
        }


class AcknowledgeAlertSerializer(serializers.Serializer):
    """Serializer for acknowledging alerts"""
    operator_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)


class ResolveAlertSerializer(serializers.Serializer):
    """Serializer for resolving alerts"""
    operator_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)
    mark_as_false_positive = serializers.BooleanField(default=False)


# ==================== WEIGHT RECORD SERIALIZERS ====================

class WeightRecordSerializer(serializers.ModelSerializer):
    customer_driver_name = serializers.CharField(source='customer.driver_name', read_only=True)
    operator_first_weight_name = serializers.CharField(source='operator_first_weight.employee_name', read_only=True, allow_null=True)
    operator_second_weight_name = serializers.CharField(source='operator_second_weight.employee_name', read_only=True, allow_null=True)
    vehicle_number = serializers.CharField(source='vehicle.vehicle_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    shift_display = serializers.CharField(source='get_shift_display', read_only=True)
    
    # Include photo counts
    first_weight_photo_count = serializers.SerializerMethodField()
    second_weight_photo_count = serializers.SerializerMethodField()
    auto_captured_photo_count = serializers.SerializerMethodField()
    total_photo_count = serializers.SerializerMethodField()
    
    # Live weight information
    live_weight_info = serializers.SerializerMethodField()
    
    # Automation flags
    automation_status = serializers.SerializerMethodField()
    
    # Security/AI monitoring info
    security_status = serializers.SerializerMethodField()
    
    # SECURITY: Date lock info
    date_lock_status = serializers.SerializerMethodField()

    class Meta:
        model = WeightRecord
        fields = '__all__'
        read_only_fields = [
            'slip_number', 
            'net_weight', 
            'total_amount', 
            'gross_weight', 
            'tare_weight',
            'first_weight_time',
            'second_weight_time',
            'status',
            'current_live_weight',
            'last_weight_update',
            'first_weight_stable_detected_time',
            'second_weight_stable_detected_time',
            'slip_printed_time',
            'has_unauthorized_detections',
            'unauthorized_detection_count',
            # Security fields
            'is_deleted',
            'deleted_at',
            'deleted_by',
            'is_date_locked',
            'date_locked_at',
            'last_modified_by',
            'modification_count'
        ]
    
    def get_first_weight_photo_count(self, obj):
        return obj.photos.filter(weight_stage='FIRST').count()
    
    def get_second_weight_photo_count(self, obj):
        return obj.photos.filter(weight_stage='SECOND').count()
    
    def get_auto_captured_photo_count(self, obj):
        return obj.photos.filter(is_auto_captured=True).count()
    
    def get_total_photo_count(self, obj):
        return obj.photos.count()
    
    def get_live_weight_info(self, obj):
        """Get current live weight information"""
        return {
            'current_weight': float(obj.current_live_weight) if obj.current_live_weight else None,
            'last_update': obj.last_weight_update.isoformat() if obj.last_weight_update else None
        }
    
    def get_automation_status(self, obj):
        """Get automation-related status flags"""
        return {
            'first_weight_auto_captured': obj.first_weight_auto_captured,
            'second_weight_auto_captured': obj.second_weight_auto_captured,
            'slip_auto_printed': obj.slip_auto_printed,
            'slip_print_count': obj.slip_print_count,
            'first_weight_stability_duration': float(obj.first_weight_stability_duration) if obj.first_weight_stability_duration else None,
            'second_weight_stability_duration': float(obj.second_weight_stability_duration) if obj.second_weight_stability_duration else None
        }
    
    def get_security_status(self, obj):
        """Get security/AI monitoring status"""
        return {
            'has_unauthorized_detections': obj.has_unauthorized_detections,
            'unauthorized_detection_count': obj.unauthorized_detection_count,
            'total_detections': obj.detections.count() if hasattr(obj, 'detections') else 0,
            'active_alerts': obj.presence_alerts.filter(status__in=['ACTIVE', 'ACKNOWLEDGED']).count() if hasattr(obj, 'presence_alerts') else 0
        }
    
    def get_date_lock_status(self, obj):
        """Get date lock status for this record"""
        try:
            is_locked = obj.check_date_lock()
            return {
                'is_date_locked': obj.is_date_locked,
                'date_locked_at': obj.date_locked_at.isoformat() if obj.date_locked_at else None,
                'can_edit': not is_locked,
                'modification_count': obj.modification_count
            }
        except:
            return {
                'is_date_locked': False,
                'can_edit': True,
                'modification_count': obj.modification_count
            }


class WeightRecordDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer with all related data"""
    customer = CustomerSerializer(read_only=True)
    operator_first_weight = OperatorSerializer(read_only=True, allow_null=True)
    operator_second_weight = OperatorSerializer(read_only=True, allow_null=True)
    vehicle = VehicleSerializer(read_only=True)
    photos = serializers.SerializerMethodField()
    first_weight_photos = serializers.SerializerMethodField()
    second_weight_photos = serializers.SerializerMethodField()
    auto_captured_photos = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    shift_display = serializers.CharField(source='get_shift_display', read_only=True)
    
    # AI Monitoring data
    detections = serializers.SerializerMethodField()
    unauthorized_detections = serializers.SerializerMethodField()
    presence_alerts = serializers.SerializerMethodField()
    
    class Meta:
        model = WeightRecord
        fields = '__all__'
    
    def get_photos(self, obj):
        photos = obj.photos.all()
        return WeightRecordPhotoSerializer(photos, many=True, context=self.context).data
    
    def get_first_weight_photos(self, obj):
        photos = obj.photos.filter(weight_stage='FIRST')
        return WeightRecordPhotoSerializer(photos, many=True, context=self.context).data
    
    def get_second_weight_photos(self, obj):
        photos = obj.photos.filter(weight_stage='SECOND')
        return WeightRecordPhotoSerializer(photos, many=True, context=self.context).data
    
    def get_auto_captured_photos(self, obj):
        photos = obj.photos.filter(is_auto_captured=True)
        return WeightRecordPhotoSerializer(photos, many=True, context=self.context).data
    
    def get_detections(self, obj):
        """Get all detections for this weight record"""
        if hasattr(obj, 'detections'):
            detections = obj.detections.all()
            return ObjectDetectionLogSerializer(detections, many=True, context=self.context).data
        return []
    
    def get_unauthorized_detections(self, obj):
        """Get only unauthorized detections"""
        if hasattr(obj, 'detections'):
            detections = obj.detections.filter(is_authorized=False)
            return ObjectDetectionLogSerializer(detections, many=True, context=self.context).data
        return []
    
    def get_presence_alerts(self, obj):
        """Get all presence alerts for this weight record"""
        if hasattr(obj, 'presence_alerts'):
            alerts = obj.presence_alerts.all()
            return UnauthorizedPresenceAlertSerializer(alerts, many=True, context=self.context).data
        return []


class WeightRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new weight records"""
    
    class Meta:
        model = WeightRecord
        fields = [
            'customer', 
            'vehicle', 
            'date', 
            'shift', 
            'material_type', 
            'rate_per_unit',
            'is_multi_drop',
            'remarks'
        ]
    
    def validate(self, data):
        """Validate weight record data"""
        # Additional validation can be added here
        return data


class CaptureWeightSerializer(serializers.Serializer):
    """Serializer for capturing weight (first or second)"""
    weight = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    operator_id = serializers.IntegerField()
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        allow_empty=True
    )
    camera_snapshots = serializers.ListField(
        child=CameraSnapshotSerializer(),
        required=False,
        allow_empty=True
    )
    auto_captured = serializers.BooleanField(default=False)
    remarks = serializers.CharField(required=False, allow_blank=True, max_length=500)
    
    def validate_weight(self, value):
        if value <= 0:
            raise serializers.ValidationError("Weight must be greater than 0")
        return value


class StableWeightSerializer(serializers.Serializer):
    """Serializer for stable weight detection"""
    current_weight = serializers.DecimalField(max_digits=10, decimal_places=2)
    is_stable = serializers.BooleanField()
    operator_id = serializers.IntegerField(required=False)
    stability_duration = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=0)
    variance = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)


class AutoCaptureSerializer(serializers.Serializer):
    """Serializer for auto-capture functionality"""
    weight = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    operator_id = serializers.IntegerField()
    stage = serializers.ChoiceField(choices=['FIRST', 'SECOND'])
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        allow_empty=True
    )
    camera_snapshots = serializers.ListField(
        child=CameraSnapshotSerializer(),
        required=False,
        allow_empty=True
    )
    timestamp = serializers.DateTimeField(required=False)


class UpdateLiveWeightSerializer(serializers.Serializer):
    """Serializer for updating live weight on a weight record"""
    weight = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    raw_data = serializers.CharField(required=False, allow_blank=True)


class ReportFilterSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    shift = serializers.ChoiceField(choices=WeightRecord.SHIFT_CHOICES, required=False)
    vehicle = serializers.IntegerField(required=False)
    customer = serializers.IntegerField(required=False)
    operator = serializers.IntegerField(required=False)
    status = serializers.ChoiceField(choices=WeightRecord.STATUS_CHOICES, required=False)


class ReportDataSerializer(serializers.Serializer):
    slip_number = serializers.CharField()
    date = serializers.DateField()
    shift = serializers.CharField()
    vehicle_number = serializers.CharField()
    customer_driver_name = serializers.CharField()
    operator_first_weight_name = serializers.CharField(allow_blank=True, required=False, default='')
    operator_second_weight_name = serializers.CharField(allow_blank=True, required=False, default='')
    first_weight = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True, required=False, default=0)
    first_weight_time = serializers.DateTimeField()
    second_weight = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    second_weight_time = serializers.DateTimeField(allow_null=True)
    gross_weight = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True, required=False, default=0)
    tare_weight = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True, required=False, default=0)
    net_weight = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True, required=False, default=0)
    material_type = serializers.CharField(allow_blank=True, required=False, default='')
    rate_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True, required=False, default=0)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, required=False, default=0)
    status = serializers.CharField()
    remarks = serializers.CharField(allow_blank=True, required=False, default='')


class AggregatedReportSerializer(serializers.Serializer):
    total_records = serializers.IntegerField()
    total_gross_weight = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_tare_weight = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_net_weight = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    records = ReportDataSerializer(many=True)


# ==================== CALCULATION LOGIC SERIALIZERS ====================

class WeightDropSerializer(serializers.ModelSerializer):
    """Serializer for individual weight drops"""
    class Meta:
        model = WeightDrop
        fields = '__all__'
        read_only_fields = ['net_weight', 'timestamp']


class WeightDropCreateSerializer(serializers.Serializer):
    """Serializer for creating a single drop"""
    gross_weight = serializers.DecimalField(max_digits=10, decimal_places=2)
    tare_weight = serializers.DecimalField(max_digits=10, decimal_places=2)
    remarks = serializers.CharField(required=False, allow_blank=True)


class MultiDropCreateSerializer(serializers.Serializer):
    """Serializer for creating multiple drops at once"""
    weight_record_id = serializers.IntegerField()
    drops = serializers.ListField(
        child=WeightDropCreateSerializer()
    )


class WeightRecordWithDropsSerializer(serializers.ModelSerializer):
    """Weight record serializer with drops included"""
    drops = WeightDropSerializer(many=True, read_only=True)
    customer_driver_name = serializers.CharField(source='customer.driver_name', read_only=True)
    operator_first_weight_name = serializers.CharField(source='operator_first_weight.employee_name', read_only=True, allow_null=True)
    operator_second_weight_name = serializers.CharField(source='operator_second_weight.employee_name', read_only=True, allow_null=True)
    vehicle_number = serializers.CharField(source='vehicle.vehicle_number', read_only=True)
    total_drops = serializers.SerializerMethodField()

    class Meta:
        model = WeightRecord
        fields = '__all__'
        read_only_fields = ['net_weight', 'total_amount']
    
    def get_total_drops(self, obj):
        return obj.drops.count() if obj.is_multi_drop else 0


class CalculationSerializer(serializers.Serializer):
    """Serializer for manual weight calculations"""
    gross_weight = serializers.DecimalField(max_digits=10, decimal_places=2)
    tare_weight = serializers.DecimalField(max_digits=10, decimal_places=2)
    net_weight = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    rate_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit logs"""
    weight_record_info = serializers.SerializerMethodField()
    payment_info = serializers.SerializerMethodField()
    detection_info = serializers.SerializerMethodField()
    alert_info = serializers.SerializerMethodField()
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = '__all__'
    
    def get_weight_record_info(self, obj):
        if obj.weight_record:
            return {
                'id': obj.weight_record.id,
                'slip_number': obj.weight_record.slip_number,
                'customer': obj.weight_record.customer.driver_name,
                'vehicle': obj.weight_record.vehicle.vehicle_number,
                'date': obj.weight_record.date,
                'shift': obj.weight_record.shift,
                'status': obj.weight_record.status
            }
        return None
    
    def get_payment_info(self, obj):
        if obj.payment:
            return {
                'payment_id': str(obj.payment.payment_id),
                'amount': str(obj.payment.amount),
                'status': obj.payment.payment_status
            }
        return None
    
    def get_detection_info(self, obj):
        """Get detection information if linked"""
        if obj.detection:
            return {
                'detection_id': obj.detection.id,
                'object_type': obj.detection.get_object_type_display(),
                'object_class': obj.detection.object_class,
                'is_authorized': obj.detection.is_authorized,
                'detected_at': obj.detection.detected_at.isoformat()
            }
        return None
    
    def get_alert_info(self, obj):
        """Get alert information if linked"""
        if obj.alert:
            return {
                'alert_id': str(obj.alert.alert_id),
                'severity': obj.alert.get_severity_display(),
                'status': obj.alert.get_status_display(),
                'object_description': obj.alert.object_description,
                'triggered_at': obj.alert.triggered_at.isoformat()
            }
        return None


class MultiDropSummarySerializer(serializers.Serializer):
    """Serializer for multi-drop calculation summary"""
    weight_record_id = serializers.IntegerField()
    total_drops = serializers.IntegerField()
    drops = WeightDropSerializer(many=True)
    total_gross_weight = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_tare_weight = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_net_weight = serializers.DecimalField(max_digits=15, decimal_places=2)
    final_amount = serializers.DecimalField(max_digits=15, decimal_places=2)


# ==================== PHOTO SERIALIZERS ====================

class WeightRecordPhotoSerializer(serializers.ModelSerializer):
    """Serializer for Weight Record Photos"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.employee_name', read_only=True, allow_null=True)
    camera_name = serializers.CharField(source='camera.name', read_only=True, allow_null=True)
    camera_position = serializers.CharField(source='camera.get_position_display', read_only=True, allow_null=True)
    photo_type_display = serializers.CharField(source='get_photo_type_display', read_only=True)
    weight_stage_display = serializers.CharField(source='get_weight_stage_display', read_only=True)
    photo_url = serializers.SerializerMethodField()
    capture_info = serializers.SerializerMethodField()
    detection_info = serializers.SerializerMethodField()
    
    class Meta:
        model = WeightRecordPhoto
        fields = '__all__'
        read_only_fields = ['uploaded_at']
    
    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None
    
    def get_capture_info(self, obj):
        """Get capture-related information"""
        return {
            'is_auto_captured': obj.is_auto_captured,
            'captured_weight': float(obj.captured_weight) if obj.captured_weight else None,
            'timestamp_added': obj.timestamp_added,
            'camera_id': obj.camera.id if obj.camera else None,
            'camera_name': obj.camera.name if obj.camera else None,
            'camera_position': obj.camera.get_position_display() if obj.camera else None
        }
    
    def get_detection_info(self, obj):
        """Get detection information if photo was captured from detection"""
        if obj.detection:
            return {
                'detection_id': obj.detection.id,
                'object_type': obj.detection.get_object_type_display(),
                'is_authorized': obj.detection.is_authorized,
                'detected_at': obj.detection.detected_at.isoformat()
            }
        return None


class WeightRecordPhotoCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating weight record photos"""
    
    class Meta:
        model = WeightRecordPhoto
        fields = [
            'weight_record', 
            'camera',
            'detection',
            'photo', 
            'photo_type', 
            'weight_stage',
            'caption', 
            'display_order', 
            'uploaded_by',
            'is_auto_captured',
            'captured_weight',
            'timestamp_added'
        ]
    
    def validate_photo(self, value):
        """Validate photo file"""
        # Check file size (max 5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Photo size should not exceed 5MB")
        
        # Check file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("Only JPEG, PNG, and GIF images are allowed")
        
        return value


class BulkPhotoUploadSerializer(serializers.Serializer):
    """Serializer for bulk photo upload"""
    photos = serializers.ListField(
        child=serializers.DictField()
    )
    operator_id = serializers.IntegerField(required=False)
    
    def validate_photos(self, value):
        if not value:
            raise serializers.ValidationError("At least one photo is required")
        return value


# ==================== COMPANY DETAILS SERIALIZERS ====================

class CompanyDetailsSerializer(serializers.ModelSerializer):
    """Serializer for Company Details"""
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CompanyDetails
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_logo_url(self, obj):
        if obj.company_logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.company_logo.url)
            return obj.company_logo.url
        return None
    
    def validate_gstin(self, value):
        """Validate GSTIN format (15 characters)"""
        if value and len(value) != 15:
            raise serializers.ValidationError("GSTIN must be 15 characters long")
        return value
    
    def validate_pan(self, value):
        """Validate PAN format (10 characters)"""
        if value and len(value) != 10:
            raise serializers.ValidationError("PAN must be 10 characters long")
        return value
    
    def validate_ifsc_code(self, value):
        """Validate IFSC code format (11 characters)"""
        if value and len(value) != 11:
            raise serializers.ValidationError("IFSC code must be 11 characters long")
        return value


# ==================== PAYMENT SERIALIZERS ====================

class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model"""
    weight_record_details = serializers.SerializerMethodField()
    customer_driver_name = serializers.CharField(source='weight_record.customer.driver_name', read_only=True)
    vehicle_number = serializers.CharField(source='weight_record.vehicle.vehicle_number', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['payment_id', 'created_at', 'updated_at', 'transaction_date']
    
    def get_weight_record_details(self, obj):
        return {
            'id': obj.weight_record.id,
            'slip_number': obj.weight_record.slip_number,
            'customer': obj.weight_record.customer.driver_name,
            'vehicle': obj.weight_record.vehicle.vehicle_number,
            'date': str(obj.weight_record.date),
            'shift': obj.weight_record.shift,
            'material_type': obj.weight_record.material_type,
            'first_weight': str(obj.weight_record.first_weight) if obj.weight_record.first_weight else None,
            'second_weight': str(obj.weight_record.second_weight) if obj.weight_record.second_weight else None,
            'net_weight': str(obj.weight_record.net_weight) if obj.weight_record.net_weight else None,
            'total_amount': str(obj.weight_record.total_amount) if obj.weight_record.total_amount else None,
            'status': obj.weight_record.status
        }


class PaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payments"""
    
    class Meta:
        model = Payment
        fields = ['weight_record', 'amount', 'payment_method', 'remarks']
    
    def validate_amount(self, value):
        """Validate payment amount"""
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than 0")
        return value
    
    def validate(self, data):
        """Validate payment against weight record"""
        weight_record = data.get('weight_record')
        amount = data.get('amount')
        
        if weight_record:
            # Check if weight record is completed
            if weight_record.status != 'COMPLETED':
                raise serializers.ValidationError({
                    'weight_record': 'Weight record must be completed before creating payment'
                })
            
            # Check if amount matches weight record total
            if weight_record.total_amount and amount != weight_record.total_amount:
                raise serializers.ValidationError({
                    'amount': f'Payment amount ({amount}) does not match weight record total amount ({weight_record.total_amount})'
                })
        
        return data


class QRCodeSerializer(serializers.ModelSerializer):
    """Serializer for QR Code model"""
    payment_details = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = QRCode
        fields = '__all__'
        read_only_fields = ['qr_id', 'generated_at']
    
    def get_payment_details(self, obj):
        return {
            'payment_id': str(obj.payment.payment_id),
            'amount': str(obj.payment.amount),
            'status': obj.payment.payment_status,
            'customer': obj.payment.weight_record.customer.driver_name,
            'vehicle': obj.payment.weight_record.vehicle.vehicle_number,
            'slip_number': obj.payment.weight_record.slip_number
        }
    
    def get_is_expired(self, obj):
        from django.utils import timezone
        if obj.expires_at:
            return obj.expires_at < timezone.now()
        return False


class PaymentSlipSerializer(serializers.ModelSerializer):
    """Serializer for Payment Slip model"""
    payment_details = serializers.SerializerMethodField()
    printer_name_display = serializers.CharField(source='printer.name', read_only=True, allow_null=True)
    printed_by_name = serializers.CharField(source='printed_by.employee_name', read_only=True, allow_null=True)
    generated_by_name = serializers.CharField(source='generated_by.employee_name', read_only=True, allow_null=True)
    slip_status_display = serializers.CharField(source='get_slip_status_display', read_only=True)
    pdf_url = serializers.SerializerMethodField()
    auto_print_info = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentSlip
        fields = '__all__'
        read_only_fields = ['slip_id', 'printed_at', 'generated_at', 'created_at', 'updated_at']
    
    def get_payment_details(self, obj):
        return {
            'payment_id': str(obj.payment.payment_id),
            'amount': str(obj.payment.amount),
            'status': obj.payment.payment_status,
            'customer': obj.payment.weight_record.customer.driver_name,
            'vehicle': obj.payment.weight_record.vehicle.vehicle_number,
            'date': str(obj.payment.weight_record.date),
            'shift': obj.payment.weight_record.shift,
            'slip_number': obj.payment.weight_record.slip_number
        }
    
    def get_pdf_url(self, obj):
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None
    
    def get_auto_print_info(self, obj):
        """Get auto-print related information"""
        return {
            'is_auto_printed': obj.is_auto_printed,
            'auto_print_failed': obj.auto_print_failed,
            'auto_print_error': obj.auto_print_error,
            'print_count': obj.print_count,
            'printer': obj.printer.name if obj.printer else None
        }


class PaymentSlipDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Payment Slip with all related data"""
    payment = PaymentSerializer(read_only=True)
    printer = PrinterConfigSerializer(read_only=True)
    photos = serializers.SerializerMethodField()
    first_weight_photos = serializers.SerializerMethodField()
    second_weight_photos = serializers.SerializerMethodField()
    qr_code = serializers.SerializerMethodField()
    company_details = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentSlip
        fields = '__all__'
    
    def get_photos(self, obj):
        photos = obj.payment.weight_record.photos.all()
        return WeightRecordPhotoSerializer(photos, many=True, context=self.context).data
    
    def get_first_weight_photos(self, obj):
        photos = obj.payment.weight_record.photos.filter(weight_stage='FIRST')
        return WeightRecordPhotoSerializer(photos, many=True, context=self.context).data
    
    def get_second_weight_photos(self, obj):
        photos = obj.payment.weight_record.photos.filter(weight_stage='SECOND')
        return WeightRecordPhotoSerializer(photos, many=True, context=self.context).data
    
    def get_qr_code(self, obj):
        qr = obj.payment.qr_codes.filter(is_active=True).first()
        if qr:
            return QRCodeSerializer(qr, context=self.context).data
        return None
    
    def get_company_details(self, obj):
        company = CompanyDetails.objects.filter(is_active=True).first()
        if company:
            return CompanyDetailsSerializer(company, context=self.context).data
        return None


# ==================== PAYMENT REQUEST/RESPONSE SERIALIZERS ====================

class GenerateQRRequestSerializer(serializers.Serializer):
    """Request serializer for QR generation"""
    payment_id = serializers.UUIDField()


class GenerateQRResponseSerializer(serializers.Serializer):
    """Response serializer for QR generation"""
    success = serializers.BooleanField()
    payment_id = serializers.UUIDField()
    qr_id = serializers.UUIDField()
    qr_string = serializers.CharField()
    qr_image = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    status = serializers.CharField()
    customer = serializers.CharField()
    vehicle = serializers.CharField()


class UpdatePaymentStatusSerializer(serializers.Serializer):
    """Serializer for updating payment status"""
    status = serializers.ChoiceField(choices=['SUCCESS', 'FAILED', 'CANCELLED'])
    transaction_id = serializers.CharField(required=False, allow_blank=True)
    transaction_ref = serializers.CharField(required=False, allow_blank=True)
    remarks = serializers.CharField(required=False, allow_blank=True, max_length=500)


class PrintSlipRequestSerializer(serializers.Serializer):
    """Request serializer for printing slip"""
    printer_id = serializers.IntegerField(required=False)
    operator_id = serializers.IntegerField(required=False)
    auto_printed = serializers.BooleanField(default=False)
    copies = serializers.IntegerField(default=1, min_value=1, max_value=10)


class GenerateSlipRequestSerializer(serializers.Serializer):
    """Request serializer for generating slip"""
    payment_id = serializers.UUIDField()
    operator_id = serializers.IntegerField(required=False)


class DropDataSerializer(serializers.Serializer): 
    """Serializer for drop data in multi-drop creation"""    
    gross_weight = serializers.DecimalField(max_digits=10, decimal_places=2)
    tare_weight = serializers.DecimalField(max_digits=10, decimal_places=2)
    remarks = serializers.CharField(required=False, allow_blank=True, max_length=500)
    
    def validate(self, data):   
        if data['tare_weight'] > data['gross_weight']: 
            raise serializers.ValidationError("Tare weight cannot be greater than gross weight")
        return data


# ==================== AUTOMATION DASHBOARD SERIALIZERS ====================

class AutomationDashboardSerializer(serializers.Serializer):
    """Serializer for automation dashboard summary"""
    weighbridge_status = serializers.SerializerMethodField()
    camera_status = serializers.SerializerMethodField()
    printer_status = serializers.SerializerMethodField()
    ai_monitoring_status = serializers.SerializerMethodField()
    current_live_weight = serializers.SerializerMethodField()
    pending_captures = serializers.SerializerMethodField()
    security_summary = serializers.SerializerMethodField()
    # SECURITY: Add security dashboard info
    security_config = serializers.SerializerMethodField()
    
    def get_weighbridge_status(self, obj):
        weighbridge = WeighbridgeConfig.objects.filter(is_active=True).first()
        if weighbridge:
            return {
                'connected': weighbridge.is_connected,
                'name': weighbridge.name,
                'port': weighbridge.port,
                'auto_capture_enabled': weighbridge.auto_capture_enabled
            }
        return None
    
    def get_camera_status(self, obj):
        cameras = CameraConfig.objects.filter(is_active=True)
        ai_enabled_cameras = cameras.filter(ai_monitoring_enabled=True)
        return {
            'total': cameras.count(),
            'connected': cameras.filter(is_connected=True).count(),
            'ai_monitoring_enabled': ai_enabled_cameras.count(),
            'cameras': CameraConfigSerializer(cameras, many=True).data
        }
    
    def get_printer_status(self, obj):
        printers = PrinterConfig.objects.filter(is_active=True)
        ready_printer = printers.filter(is_ready=True, slip_engine_ready=True).first()
        return {
            'total': printers.count(),
            'ready': printers.filter(is_ready=True, slip_engine_ready=True).count(),
            'auto_print_enabled': ready_printer.auto_print_enabled if ready_printer else False,
            'printers': PrinterConfigSerializer(printers, many=True).data
        }
    
    def get_ai_monitoring_status(self, obj):
        """Get AI monitoring system status"""
        config = AIMonitoringConfig.objects.filter(is_active=True, is_enabled=True).first()
        if config:
            return {
                'enabled': config.is_enabled,
                'detection_model': config.get_detection_model_display(),
                'last_run': config.last_detection_run.isoformat() if config.last_detection_run else None,
                'alert_settings': {
                    'alert_on_person': config.alert_on_person,
                    'alert_on_animal': config.alert_on_animal,
                    'auto_snapshot': config.auto_snapshot_on_unauthorized
                }
            }
        return {'enabled': False}
    
    def get_current_live_weight(self, obj):
        latest_reading = LiveWeightReading.objects.order_by('-timestamp').first()
        if latest_reading:
            return LiveWeightReadingSerializer(latest_reading).data
        return None
    
    def get_pending_captures(self, obj):
        first_weight_pending = WeightRecord.objects.filter(
            status__in=['RECORD_SAVED', 'FIRST_WEIGHT_PENDING', 'FIRST_WEIGHT_STABLE']
        ).count()
        second_weight_pending = WeightRecord.objects.filter(
            status__in=['VEHICLE_RETURNED', 'SECOND_WEIGHT_PENDING', 'SECOND_WEIGHT_STABLE']
        ).count()
        return { 
            'first_weight': first_weight_pending,
            'second_weight': second_weight_pending,
            'total': first_weight_pending + second_weight_pending
        }
    
    def get_security_summary(self, obj):
        """Get security/AI monitoring summary"""
        from django.utils import timezone
        today = timezone.now().date()
        
        # Today's stats
        today_detections = ObjectDetectionLog.objects.filter(detected_at__date=today)
        today_unauthorized = today_detections.filter(is_authorized=False)
        today_alerts = UnauthorizedPresenceAlert.objects.filter(triggered_at__date=today)
        active_alerts = UnauthorizedPresenceAlert.objects.filter(status__in=['ACTIVE', 'ACKNOWLEDGED'])
        
        # Weight records with security issues
        records_with_alerts = WeightRecord.objects.filter(
            has_unauthorized_detections=True,
            date=today
        ) 
        
        return {
            'today': {
                'total_detections': today_detections.count(),
                'unauthorized_detections': today_unauthorized.count(),
                'alerts_triggered': today_alerts.count()
            },
            'current': {
                'active_alerts': active_alerts.count(),
                'records_with_alerts': records_with_alerts.count()
            }
        }
    
    def get_security_config(self, obj):            
        """Get security configuration status"""
        date_lock = DateLockConfig.objects.filter(is_enabled=True).first()
        backup = BackupConfig.objects.filter(is_enabled=True).first()
        
        return {
            'date_lock': {
                'enabled': date_lock.is_enabled if date_lock else False,
                'lock_date': date_lock.lock_date.isoformat() if date_lock and date_lock.lock_date else None,
                'days_locked': date_lock.days_to_lock if date_lock else 0
            },
            'backup': {
                'enabled': backup.is_enabled if backup else False,
                'frequency': backup.get_frequency_display() if backup else None,
                'last_backup': backup.last_backup_time.isoformat() if backup and backup.last_backup_time else None
            }
        }
