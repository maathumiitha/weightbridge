from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

# Import from security models file
from .models_security_data_management import (
    SoftDeleteModel,
    check_date_lock,
    log_security_action,
    TareWeightHistory
)


class Customer(SoftDeleteModel):  # Changed from models.Model
    driver_name = models.CharField(max_length=200)
    driver_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customers'
        ordering = ['driver_name']

    def __str__(self):
        return self.driver_name


class Operator(SoftDeleteModel):  # Changed from models.Model
    employee_name = models.CharField(max_length=200)
    employee_id = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'operators'
        ordering = ['employee_name']

    def __str__(self):
        return self.employee_name


class Vehicle(SoftDeleteModel):  # Changed from models.Model
    vehicle_number = models.CharField(max_length=50, unique=True)
    vehicle_type = models.CharField(max_length=100)
    capacity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    is_active = models.BooleanField(default=True)
    
    # NEW FIELDS for tare weight tracking
    last_known_tare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Most recent tare weight recorded"
    )
    last_tare_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehicles'
        ordering = ['vehicle_number']

    def __str__(self):
        return self.vehicle_number
    
    # NEW METHOD
    def update_tare_weight(self, tare_weight, date):
        """Update vehicle's last known tare weight"""
        self.last_known_tare = tare_weight
        self.last_tare_date = date
        self.save()


# ==================== WEIGHBRIDGE HARDWARE CONFIGURATION ====================
class WeighbridgeConfig(models.Model):
    """Configuration for weighbridge hardware integration"""
    name = models.CharField(max_length=200, default="Main Weighbridge")
    
    # Serial/COM port configuration
    port = models.CharField(max_length=50, default='COM1', help_text="Serial port (e.g., COM1, /dev/ttyUSB0)")
    baud_rate = models.IntegerField(default=9600)
    data_bits = models.IntegerField(default=8)
    stop_bits = models.IntegerField(default=1)
    parity = models.CharField(max_length=10, default='NONE', choices=[
        ('NONE', 'None'),
        ('EVEN', 'Even'),
        ('ODD', 'Odd'),
    ])
    
    # Weight stability settings
    stability_threshold = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        default=Decimal('0.50'),
        help_text="Weight variance threshold (kg) for stability detection"
    )
    stability_duration = models.IntegerField(
        default=3,
        help_text="Duration (seconds) weight must remain stable"
    )
    
    # Auto-capture settings
    auto_capture_enabled = models.BooleanField(default=True)
    auto_capture_delay = models.IntegerField(
        default=2,
        help_text="Delay (seconds) after stability before auto-capture"
    )
    
    # Hardware status
    is_connected = models.BooleanField(default=False)
    last_connected = models.DateTimeField(null=True, blank=True)
    connection_status_message = models.TextField(blank=True)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'weighbridge_config'
        verbose_name = 'Weighbridge Configuration'
        verbose_name_plural = 'Weighbridge Configurations'
    
    def __str__(self):
        return f"{self.name} - {self.port}"


class LiveWeightReading(models.Model):
    """Store live weight readings from weighbridge"""
    weighbridge_config = models.ForeignKey(
        WeighbridgeConfig,
        on_delete=models.CASCADE,
        related_name='live_readings'
    )
    
    # Current weight reading
    weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Stability indicators
    is_stable = models.BooleanField(default=False)
    stability_started_at = models.DateTimeField(null=True, blank=True)
    stability_duration = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="How long (seconds) weight has been stable"
    )
    
    # Raw data from weighbridge
    raw_data = models.TextField(blank=True)
    
    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'live_weight_readings'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['weighbridge_config', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.weight} kg - {'Stable' if self.is_stable else 'Unstable'}"


# ==================== CAMERA CONFIGURATION ====================
class CameraConfig(models.Model):
    """Configuration for camera system"""
    CAMERA_TYPE_CHOICES = [
        ('USB', 'USB Camera'),
        ('IP', 'IP Camera'),
        ('RTSP', 'RTSP Stream'),
    ]
    
    CAMERA_POSITION_CHOICES = [
        ('FRONT', 'Front'),
        ('BACK', 'Back'),
        ('LEFT', 'Left'),
        ('RIGHT', 'Right'),
        ('TOP', 'Top'),
    ]
    
    name = models.CharField(max_length=200, help_text="Camera identifier (e.g., Camera 1)")
    camera_type = models.CharField(max_length=20, choices=CAMERA_TYPE_CHOICES, default='USB')
    position = models.CharField(max_length=20, choices=CAMERA_POSITION_CHOICES, default='FRONT')
    
    # Camera connection details
    camera_index = models.IntegerField(
        default=0,
        help_text="USB camera index or IP camera ID"
    )
    rtsp_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="RTSP URL for IP cameras (e.g., rtsp://192.168.1.100:554/stream)"
    )
    username = models.CharField(max_length=100, blank=True)
    password = models.CharField(max_length=100, blank=True)
    
    # Auto-snapshot settings
    auto_snapshot_enabled = models.BooleanField(default=True)
    snapshot_on_first_weight = models.BooleanField(default=True)
    snapshot_on_second_weight = models.BooleanField(default=True)
    
    # Snapshot quality settings
    resolution_width = models.IntegerField(default=1920)
    resolution_height = models.IntegerField(default=1080)
    jpeg_quality = models.IntegerField(default=90, help_text="JPEG quality (1-100)")
    
    # Display settings
    show_on_dashboard = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    
    # Camera status
    is_active = models.BooleanField(default=True)
    is_connected = models.BooleanField(default=False)
    last_connected = models.DateTimeField(null=True, blank=True)
    connection_status_message = models.TextField(blank=True)
    
    # AI Monitoring settings
    ai_monitoring_enabled = models.BooleanField(
        default=False,
        help_text="Enable AI-based object detection and monitoring"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'camera_config'
        ordering = ['display_order', 'name']
        verbose_name = 'Camera Configuration'
        verbose_name_plural = 'Camera Configurations'
    
    def __str__(self):
        return f"{self.name} - {self.get_position_display()}"


# ==================== AI MONITORING CONFIGURATION ====================
class AIMonitoringConfig(models.Model):
    """Configuration for AI-based monitoring and object detection"""
    
    # Object detection model settings
    DETECTION_MODEL_CHOICES = [
        ('YOLO_V8', 'YOLOv8 (Recommended)'),
        ('YOLO_V5', 'YOLOv5'),
        ('FASTER_RCNN', 'Faster R-CNN'),
        ('SSD', 'SSD MobileNet'),
    ]
    
    name = models.CharField(max_length=200, default="AI Monitoring System")
    is_enabled = models.BooleanField(default=True)
    
    # Detection model configuration
    detection_model = models.CharField(
        max_length=20,
        choices=DETECTION_MODEL_CHOICES,
        default='YOLO_V8'
    )
    model_confidence_threshold = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.50'),
        help_text="Minimum confidence (0.0-1.0) for object detection"
    )
    
    # Detection frequency
    detection_interval_seconds = models.IntegerField(
        default=2,
        help_text="How often to run detection (seconds)"
    )
    
    # Authorized objects (vehicles only)
    authorized_object_classes = models.JSONField(
        default=list,
        help_text="List of authorized object classes (e.g., ['car', 'truck', 'bus', 'motorcycle'])"
    )
    
    # Alert settings for unauthorized presence
    alert_on_unauthorized_objects = models.BooleanField(
        default=True,
        help_text="Send alerts when non-vehicle objects are detected"
    )
    unauthorized_object_threshold = models.IntegerField(
        default=3,
        help_text="Number of consecutive detections before alerting"
    )
    alert_cooldown_seconds = models.IntegerField(
        default=60,
        help_text="Minimum time between alerts for same object type"
    )
    
    # Person detection settings
    alert_on_person = models.BooleanField(
        default=True,
        help_text="Alert when person is detected in restricted area"
    )
    
    # Animal detection settings
    alert_on_animal = models.BooleanField(
        default=True,
        help_text="Alert when animal is detected"
    )
    
    # Unknown object settings
    alert_on_unknown_objects = models.BooleanField(
        default=True,
        help_text="Alert on objects that are not vehicles"
    )
    
    # Auto-snapshot on detection
    auto_snapshot_on_unauthorized = models.BooleanField(
        default=True,
        help_text="Automatically capture snapshot when unauthorized object detected"
    )
    
    # Notification settings
    send_email_alerts = models.BooleanField(default=False)
    email_recipients = models.TextField(
        blank=True,
        help_text="Comma-separated email addresses"
    )
    send_sms_alerts = models.BooleanField(default=False)
    sms_recipients = models.TextField(
        blank=True,
        help_text="Comma-separated phone numbers"
    )
    
    # Dashboard alerts
    show_dashboard_alerts = models.BooleanField(default=True)
    play_alert_sound = models.BooleanField(default=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    last_detection_run = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ai_monitoring_config'
        verbose_name = 'AI Monitoring Configuration'
        verbose_name_plural = 'AI Monitoring Configurations'
    
    def __str__(self):
        return f"{self.name} - {'Enabled' if self.is_enabled else 'Disabled'}"


# ==================== OBJECT DETECTION LOG ====================
class ObjectDetectionLog(models.Model):
    """Log all object detections from cameras"""
    
    OBJECT_TYPE_CHOICES = [
        # Vehicles (Authorized)
        ('CAR', 'Car'),
        ('TRUCK', 'Truck'),
        ('BUS', 'Bus'),
        ('MOTORCYCLE', 'Motorcycle'),
        ('BICYCLE', 'Bicycle'),
        
        # Unauthorized Objects
        ('PERSON', 'Person'),
        ('DOG', 'Dog'),
        ('CAT', 'Cat'),
        ('BIRD', 'Bird'),
        ('ANIMAL_OTHER', 'Other Animal'),
        ('UNKNOWN', 'Unknown Object'),
    ]
    
    camera = models.ForeignKey(
        CameraConfig,
        on_delete=models.CASCADE,
        related_name='detections'
    )
    
    weight_record = models.ForeignKey(
        'WeightRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='detections',
        help_text="Associated weight record if detection occurred during weighment"
    )
    
    # Detection details
    object_type = models.CharField(max_length=20, choices=OBJECT_TYPE_CHOICES)
    object_class = models.CharField(max_length=100, help_text="Raw class name from model")
    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        help_text="Detection confidence (0.0-1.0)"
    )
    
    # Bounding box coordinates (normalized 0-1)
    bbox_x1 = models.DecimalField(max_digits=6, decimal_places=4)
    bbox_y1 = models.DecimalField(max_digits=6, decimal_places=4)
    bbox_x2 = models.DecimalField(max_digits=6, decimal_places=4)
    bbox_y2 = models.DecimalField(max_digits=6, decimal_places=4)
    
    # Authorization status
    is_authorized = models.BooleanField(
        default=False,
        help_text="Whether this object type is authorized in the area"
    )
    
    # Alert triggered
    alert_triggered = models.BooleanField(default=False)
    alert_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        Operator,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    # Snapshot
    snapshot_image = models.ImageField(
        upload_to='detections/%Y/%m/%d/',
        null=True,
        blank=True
    )
    
    # Detection metadata
    detection_count = models.IntegerField(
        default=1,
        help_text="Number of times this object was detected consecutively"
    )
    
    # Timestamp
    detected_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'object_detection_log'
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['-detected_at']),
            models.Index(fields=['camera', '-detected_at']),
            models.Index(fields=['is_authorized']),
            models.Index(fields=['alert_triggered']),
            models.Index(fields=['object_type']),
        ]
    
    def __str__(self):
        return f"{self.get_object_type_display()} detected at {self.detected_at} ({'Auth' if self.is_authorized else 'Unauth'})"
    
    def acknowledge_alert(self, operator):
        """Acknowledge this detection alert"""
        self.alert_acknowledged = True
        self.acknowledged_by = operator
        self.acknowledged_at = timezone.now()
        self.save()


# ==================== UNAUTHORIZED PRESENCE ALERT ====================
class UnauthorizedPresenceAlert(models.Model):
    """Alert records for unauthorized presence detections"""
    
    ALERT_SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    ALERT_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ACKNOWLEDGED', 'Acknowledged'),
        ('RESOLVED', 'Resolved'),
        ('FALSE_POSITIVE', 'False Positive'),
    ]
    
    alert_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Detection reference
    detection = models.ForeignKey(
        ObjectDetectionLog,
        on_delete=models.CASCADE,
        related_name='alerts'
    )
    
    camera = models.ForeignKey(
        CameraConfig,
        on_delete=models.CASCADE,
        related_name='alerts'
    )
    
    weight_record = models.ForeignKey(
        'WeightRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='presence_alerts'
    )
    
    # Alert details
    alert_message = models.TextField()
    object_description = models.CharField(max_length=200)
    severity = models.CharField(max_length=10, choices=ALERT_SEVERITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=ALERT_STATUS_CHOICES, default='ACTIVE')
    
    # Snapshot at time of alert
    alert_snapshot = models.ImageField(
        upload_to='alerts/%Y/%m/%d/',
        null=True,
        blank=True
    )
    
    # Notification tracking
    email_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    dashboard_notified = models.BooleanField(default=False)
    
    # Response tracking
    acknowledged_by = models.ForeignKey(
        Operator,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_presence_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    # Timestamps
    triggered_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'unauthorized_presence_alerts'
        ordering = ['-triggered_at']
        indexes = [
            models.Index(fields=['alert_id']),
            models.Index(fields=['-triggered_at']),
            models.Index(fields=['status']),
            models.Index(fields=['severity']),
            models.Index(fields=['camera']),
        ]
    
    def __str__(self):
        return f"Alert {self.alert_id} - {self.object_description} - {self.get_severity_display()}"
    
    def acknowledge(self, operator, notes=''):
        """Acknowledge this alert"""
        self.status = 'ACKNOWLEDGED'
        self.acknowledged_by = operator
        self.acknowledged_at = timezone.now()
        if notes:
            self.resolution_notes = notes
        self.save()
    
    def resolve(self, operator, notes=''):
        """Mark alert as resolved"""
        self.status = 'RESOLVED'
        self.resolved_at = timezone.now()
        if not self.acknowledged_by:
            self.acknowledged_by = operator
            self.acknowledged_at = timezone.now()
        if notes:
            self.resolution_notes = notes
        self.save()
    
    def mark_false_positive(self, operator, notes=''):
        """Mark alert as false positive"""
        self.status = 'FALSE_POSITIVE'
        self.resolved_at = timezone.now()
        self.acknowledged_by = operator
        self.acknowledged_at = timezone.now()
        self.resolution_notes = f"False Positive: {notes}"
        self.save()


# ==================== PRINTER CONFIGURATION ====================
class PrinterConfig(models.Model):
    """Configuration for thermal/slip printer"""
    PRINTER_TYPE_CHOICES = [
        ('THERMAL', 'Thermal Printer'),
        ('LASER', 'Laser Printer'),
        ('INKJET', 'Inkjet Printer'),
        ('DOT_MATRIX', 'Dot Matrix Printer'),
    ]
    
    PAPER_SIZE_CHOICES = [
        ('80MM', '80mm (Thermal)'),
        ('58MM', '58mm (Thermal)'),
        ('A4', 'A4'),
        ('A5', 'A5'),
        ('LETTER', 'Letter'),
    ]
    
    name = models.CharField(max_length=200)
    printer_type = models.CharField(max_length=20, choices=PRINTER_TYPE_CHOICES, default='THERMAL')
    
    # Printer connection
    printer_name = models.CharField(
        max_length=200,
        help_text="System printer name (from OS)"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="For network printers"
    )
    port = models.IntegerField(
        default=9100,
        help_text="Network printer port"
    )
    
    # Paper settings
    paper_size = models.CharField(max_length=20, choices=PAPER_SIZE_CHOICES, default='80MM')
    paper_width_mm = models.IntegerField(default=80)
    
    # Auto-print settings
    auto_print_enabled = models.BooleanField(
        default=True,
        help_text="Automatically print slip when weighment is complete"
    )
    auto_print_copies = models.IntegerField(
        default=1,
        help_text="Number of copies to print automatically"
    )
    auto_print_on_completion = models.BooleanField(
        default=True,
        help_text="Print when status becomes COMPLETED"
    )
    
    # Printer ready indicator
    is_ready = models.BooleanField(default=False)
    slip_engine_ready = models.BooleanField(
        default=False,
        help_text="Whether the slip generation engine is initialized"
    )
    
    # Printer status
    is_active = models.BooleanField(default=True)
    is_connected = models.BooleanField(default=False)
    last_printed = models.DateTimeField(null=True, blank=True)
    connection_status_message = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'printer_config'
        verbose_name = 'Printer Configuration'
        verbose_name_plural = 'Printer Configurations'
    
    def __str__(self):
        return f"{self.name} - {self.printer_name}"


# ==================== COMPANY DETAILS MODEL ====================
class CompanyDetails(models.Model):
    """Model for storing company information for slip generation"""
    company_name = models.CharField(max_length=300)
    company_address = models.TextField()
    company_phone = models.CharField(max_length=50, blank=True)
    company_email = models.EmailField(blank=True)
    company_logo = models.ImageField(upload_to='company/', blank=True, null=True)
    
    # Tax and registration details
    gstin = models.CharField(max_length=15, blank=True)
    pan = models.CharField(max_length=10, blank=True)
    
    # UPI details for payment
    upi_id = models.CharField(max_length=100, blank=True)
    upi_name = models.CharField(max_length=200, blank=True)
    
    # Bank details
    bank_name = models.CharField(max_length=200, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    ifsc_code = models.CharField(max_length=11, blank=True)
    
    # Slip configuration
    slip_header_text = models.TextField(blank=True, help_text="Custom header text for slips")
    slip_footer_text = models.TextField(blank=True, help_text="Custom footer text for slips")
    
    # Make sure only one company record exists
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'company_details'
        verbose_name = 'Company Details'
        verbose_name_plural = 'Company Details'

    def __str__(self):
        return self.company_name


class WeightRecord(SoftDeleteModel):  # Changed from models.Model
    SHIFT_CHOICES = [
        ('MORNING', 'Morning'),
        ('AFTERNOON', 'Afternoon'),
        ('NIGHT', 'Night'),
    ]
    
    STATUS_CHOICES = [
        ('RECORD_SAVED', 'Record Saved in Database'),
        ('VEHICLE_LEFT', 'Vehicle Left'),
        ('FIRST_WEIGHT_PENDING', 'First Weight Pending'),
        ('FIRST_WEIGHT_STABLE', 'First Weight Stable Detected'),
        ('FIRST_WEIGHT_CAPTURED', 'First Weight Captured'),
        ('VEHICLE_RETURNED', 'Vehicle Returned'),
        ('SECOND_WEIGHT_PENDING', 'Second Weight Pending'),
        ('SECOND_WEIGHT_STABLE', 'Second Weight Stable Detected'),
        ('SECOND_WEIGHT_CAPTURED', 'Second Weight Captured'),
        ('WEIGHTS_CALCULATED', 'Weights Calculated'),
        ('CHARGES_CALCULATED', 'Charges Calculated'),
        ('QR_GENERATED', 'QR Code Generated'),
        ('SLIP_PRINTED', 'Slip Printed'),
        ('COMPLETED', 'Weighment Complete'),
        ('CANCELLED', 'Cancelled'),
    ]

    # Unique slip number
    slip_number = models.CharField(max_length=100, unique=True, editable=False)
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='weight_records')
    operator_first_weight = models.ForeignKey(
        Operator, 
        on_delete=models.CASCADE, 
        related_name='first_weight_records',
        null=True,
        blank=True
    )
    operator_second_weight = models.ForeignKey(
        Operator, 
        on_delete=models.CASCADE, 
        related_name='second_weight_records',
        null=True,
        blank=True
    )
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='weight_records')
    
    date = models.DateField()
    shift = models.CharField(max_length=20, choices=SHIFT_CHOICES)
    
    # Status tracking (follows the complete workflow)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='RECORD_SAVED')
    
    # NEW FIELDS for date lock tracking
    is_date_locked = models.BooleanField(
        default=False,
        help_text="Whether this record's date is locked from editing"
    )
    date_locked_at = models.DateTimeField(null=True, blank=True)
    
    # NEW FIELDS for modification tracking
    last_modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='modified_weight_records'
    )
    modification_count = models.IntegerField(
        default=0,
        help_text="Number of times record has been modified"
    )
    
    # ==================== WEIGHBRIDGE HARDWARE INTEGRATION ====================
    # Current live weight from weighbridge
    current_live_weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        null=True,
        blank=True,
        help_text="Current weight being received from weighbridge"
    )
    last_weight_update = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time weight was updated from weighbridge"
    )
    
    # Vehicle movement tracking
    vehicle_left_time = models.DateTimeField(null=True, blank=True, help_text="When vehicle left after first weight")
    vehicle_returned_time = models.DateTimeField(null=True, blank=True, help_text="When vehicle returned for second weight")
    
    # First weight data
    first_weight = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        null=True,
        blank=True
    )
    first_weight_time = models.DateTimeField(null=True, blank=True)
    first_weight_stable_detected_time = models.DateTimeField(null=True, blank=True, help_text="When first weight became stable")
    first_weight_stability_duration = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="How long first weight was stable (seconds)"
    )
    first_weight_auto_captured = models.BooleanField(default=False, help_text="Was first weight auto-captured on stability?")
    
    # Second weight data
    second_weight = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        null=True,
        blank=True
    )
    second_weight_time = models.DateTimeField(null=True, blank=True)
    second_weight_stable_detected_time = models.DateTimeField(null=True, blank=True, help_text="When second weight became stable")
    second_weight_stability_duration = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="How long second weight was stable (seconds)"
    )
    second_weight_auto_captured = models.BooleanField(default=False, help_text="Was second weight auto-captured on stability?")
    
    # Calculated weights (auto-calculated after both weights captured)
    gross_weight = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        null=True,
        blank=True
    )
    tare_weight = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        null=True,
        blank=True
    )
    net_weight = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        null=True,
        blank=True
    )
    weights_calculated_time = models.DateTimeField(null=True, blank=True, help_text="When gross/tare/net were calculated")
    
    # Material and pricing
    material_type = models.CharField(max_length=200)
    rate_per_unit = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00')
    )
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        null=True,
        blank=True
    )
    charges_calculated_time = models.DateTimeField(null=True, blank=True, help_text="When charges were calculated")
    
    # QR Code generation tracking
    qr_generated_time = models.DateTimeField(null=True, blank=True, help_text="When QR code was generated")
    
    # ==================== AUTO-PRINT TRACKING ====================
    slip_printed_time = models.DateTimeField(null=True, blank=True, help_text="When slip was printed")
    slip_auto_printed = models.BooleanField(default=False, help_text="Was slip auto-printed?")
    slip_print_count = models.IntegerField(default=0, help_text="Number of times slip was printed")
    
    # Completion tracking
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When weighment was completed")
    
    # Multi-drop support
    is_multi_drop = models.BooleanField(default=False)
    
    # Security tracking
    has_unauthorized_detections = models.BooleanField(
        default=False,
        help_text="Flag if unauthorized objects were detected during this weighment"
    )
    unauthorized_detection_count = models.IntegerField(
        default=0,
        help_text="Count of unauthorized detections during weighment"
    )
    
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'weight_records'
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['shift']),
            models.Index(fields=['customer']),
            models.Index(fields=['vehicle']),
            models.Index(fields=['status']),
            models.Index(fields=['slip_number']),
            models.Index(fields=['has_unauthorized_detections']),
            models.Index(fields=['is_date_locked']),  # NEW INDEX
        ]

    def __str__(self):
        return f"{self.slip_number} - {self.customer.driver_name} - {self.status}"
    
    # NEW METHOD
    def check_date_lock(self, user=None):
        """Check if record date is locked"""
        return check_date_lock(self.date, user)

    def save(self, *args, **kwargs):
        # NEW CODE: Check date lock before saving modifications
        if self.pk and not kwargs.get('skip_date_lock_check'):
            if self.check_date_lock():
                raise PermissionDenied(
                    f"Cannot modify record from {self.date}. Date is locked."
                )
        
        # NEW CODE: Track modifications
        if self.pk:
            self.modification_count += 1
        
        # Generate slip number if not exists
        if not self.slip_number:
            self.slip_number = self.generate_slip_number()
        
        # Auto-calculate weights when both weights are captured
        if self.first_weight and self.second_weight and not self.weights_calculated_time:
            self.calculate_weights()
            
            # NEW CODE: Store tare weight in history
            if self.tare_weight:
                TareWeightHistory.objects.create(
                    vehicle=self.vehicle,
                    weight_record=self,
                    tare_weight=self.tare_weight,
                    recorded_date=self.date,
                    recorded_time=timezone.now(),
                    recorded_by=self.operator_second_weight
                )
                
                # Update vehicle's last known tare
                self.vehicle.update_tare_weight(self.tare_weight, self.date)
            
        # Auto-calculate charges when net weight is available
        if self.net_weight and self.rate_per_unit and not self.charges_calculated_time:
            self.calculate_charges()
                
        super().save(*args, **kwargs)
    
    def generate_slip_number(self):
        """Generate unique slip number"""
        today = timezone.now()
        prefix = f"WS{today.strftime('%Y%m%d')}"
        
        # Get last slip number for today
        last_record = WeightRecord.objects.filter(
            slip_number__startswith=prefix
        ).order_by('-slip_number').first()
        
        if last_record:
            last_number = int(last_record.slip_number[-4:])
            new_number = last_number + 1
        else:
            new_number = 1
            
        return f"{prefix}{new_number:04d}"
    
    def update_live_weight(self, weight):
        """Update current live weight from weighbridge"""
        self.current_live_weight = weight
        self.last_weight_update = timezone.now()
        self.save(update_fields=['current_live_weight', 'last_weight_update', 'updated_at'])
    
    def mark_vehicle_left(self):
        """Mark that vehicle has left after first weight"""
        self.vehicle_left_time = timezone.now()
        self.status = 'VEHICLE_LEFT'
        self.save()
    
    def mark_vehicle_returned(self):
        """Mark that vehicle has returned for second weight"""
        self.vehicle_returned_time = timezone.now()
        self.status = 'VEHICLE_RETURNED'
        self.save()
    
    def detect_first_weight_stable(self, stability_duration=None):
        """Mark first weight as stable"""
        self.first_weight_stable_detected_time = timezone.now()
        if stability_duration:
            self.first_weight_stability_duration = stability_duration
        self.status = 'FIRST_WEIGHT_STABLE'
        self.save()
    
    def detect_second_weight_stable(self, stability_duration=None):
        """Mark second weight as stable"""
        self.second_weight_stable_detected_time = timezone.now()
        if stability_duration:
            self.second_weight_stability_duration = stability_duration
        self.status = 'SECOND_WEIGHT_STABLE'
        self.save()
    
    def capture_first_weight(self, weight, operator, auto_captured=False):
        """Capture first weight"""
        self.first_weight = weight
        self.first_weight_time = timezone.now()
        self.operator_first_weight = operator
        self.first_weight_auto_captured = auto_captured
        self.status = 'FIRST_WEIGHT_CAPTURED'
        self.save()
        
    def capture_second_weight(self, weight, operator, auto_captured=False):
        """Capture second weight"""
        self.second_weight = weight
        self.second_weight_time = timezone.now()
        self.operator_second_weight = operator
        self.second_weight_auto_captured = auto_captured
        self.status = 'SECOND_WEIGHT_CAPTURED'
        self.save()
    
    def calculate_weights(self):
        """Calculate gross, tare, and net weights"""
        if self.first_weight and self.second_weight:
            self.gross_weight = max(self.first_weight, self.second_weight)
            self.tare_weight = min(self.first_weight, self.second_weight)
            self.net_weight = self.gross_weight - self.tare_weight
            self.weights_calculated_time = timezone.now()
            self.status = 'WEIGHTS_CALCULATED'
    
    def calculate_charges(self):
        """Calculate total charges"""
        if self.net_weight and self.rate_per_unit:
            self.total_amount = self.net_weight * self.rate_per_unit
            self.charges_calculated_time = timezone.now()
            self.status = 'CHARGES_CALCULATED'
    
    def mark_qr_generated(self):
        """Mark that QR code has been generated"""
        self.qr_generated_time = timezone.now()
        self.status = 'QR_GENERATED'
        self.save()
    
    def mark_slip_printed(self, auto_printed=False):
        """Mark that slip has been printed"""
        self.slip_printed_time = timezone.now()
        self.slip_auto_printed = auto_printed
        self.slip_print_count += 1
        self.status = 'SLIP_PRINTED'
        self.save()
    
    def mark_completed(self):
        """Mark weighment as complete"""
        self.completed_at = timezone.now()
        self.status = 'COMPLETED'
        self.save()
    
    def record_unauthorized_detection(self):
        """Record that an unauthorized object was detected"""
        self.has_unauthorized_detections = True
        self.unauthorized_detection_count += 1
        self.save(update_fields=['has_unauthorized_detections', 'unauthorized_detection_count', 'updated_at'])
    
    def calculate_from_drops(self):
        """Calculate final net weight from all drops"""
        if self.is_multi_drop:
            drops = self.drops.all()
            if drops.exists():
                # Sum all net weights from drops
                total_net = sum(drop.net_weight for drop in drops)
                self.net_weight = total_net
                if self.rate_per_unit:
                    self.total_amount = self.net_weight * self.rate_per_unit
                self.save()
                return total_net
        return self.net_weight


class WeightDrop(models.Model):
    """Model for storing individual weight drops in multi-drop scenarios"""
    weight_record = models.ForeignKey(
        WeightRecord, 
        on_delete=models.CASCADE, 
        related_name='drops'
    )
    drop_number = models.IntegerField()
    gross_weight = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tare_weight = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    net_weight = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True)
    
    class Meta:
        db_table = 'weight_drops'
        ordering = ['drop_number']
        unique_together = ['weight_record', 'drop_number']
    
    def __str__(self):
        return f"Drop {self.drop_number} - Record {self.weight_record.id}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate net weight for each drop
        self.net_weight = self.gross_weight - self.tare_weight
        super().save(*args, **kwargs)
        
        # Update parent weight record's total
        self.weight_record.calculate_from_drops()


# ==================== PHOTO/IMAGE MODEL ====================
class WeightRecordPhoto(models.Model):
    """Model for storing photos associated with weight records"""
    PHOTO_TYPE_CHOICES = [
        ('VEHICLE_FRONT', 'Vehicle Front'),
        ('VEHICLE_BACK', 'Vehicle Back'),
        ('VEHICLE_SIDE', 'Vehicle Side'),
        ('MATERIAL', 'Material'),
        ('WEIGHBRIDGE', 'Weighbridge Display'),
        ('FIRST_WEIGHT', 'First Weight'),
        ('SECOND_WEIGHT', 'Second Weight'),
        ('AUTO_SNAPSHOT', 'Auto Snapshot'),
        ('DETECTION_SNAPSHOT', 'Detection Snapshot'),
        ('OTHER', 'Other'),
    ]
    
    WEIGHT_STAGE_CHOICES = [
        ('FIRST', 'First Weight'),
        ('SECOND', 'Second Weight'),
        ('BOTH', 'Both'),
    ]
    
    weight_record = models.ForeignKey(
        WeightRecord,
        on_delete=models.CASCADE,
        related_name='photos'
    )
    
    # Camera that captured the photo
    camera = models.ForeignKey(
        CameraConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='captured_photos'
    )
    
    # Detection reference (if this photo was captured due to detection)
    detection = models.ForeignKey(
        ObjectDetectionLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='photos'
    )
    
    photo = models.ImageField(upload_to='weight_records/%Y/%m/%d/')
    photo_type = models.CharField(max_length=20, choices=PHOTO_TYPE_CHOICES, default='OTHER')
    weight_stage = models.CharField(max_length=10, choices=WEIGHT_STAGE_CHOICES, default='FIRST')
    caption = models.CharField(max_length=200, blank=True)
    
    # Auto-capture tracking
    is_auto_captured = models.BooleanField(
        default=False,
        help_text="Was this photo automatically captured on stable weight?"
    )
    captured_weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Weight value when photo was captured"
    )
    
    # Timestamp information
    timestamp_added = models.BooleanField(default=False, help_text="Was timestamp added to image?")
    
    # Order for display
    display_order = models.IntegerField(default=0)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        Operator,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_photos'
    )
    
    class Meta:
        db_table = 'weight_record_photos'
        ordering = ['display_order', 'uploaded_at']
        verbose_name = 'Weight Record Photo'
        verbose_name_plural = 'Weight Record Photos'
        indexes = [
            models.Index(fields=['weight_record']),
            models.Index(fields=['photo_type']),
            models.Index(fields=['weight_stage']),
            models.Index(fields=['is_auto_captured']),
        ]
    
    def __str__(self):
        return f"{self.get_photo_type_display()} - {self.get_weight_stage_display()} - Record {self.weight_record.slip_number}"


# ==================== PAYMENT MODELS ====================

class Payment(models.Model):
    """Model for storing payment transactions linked to weight records"""
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('UPI', 'UPI'),
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CHEQUE', 'Cheque'),
    ]
    
    # Unique payment ID
    payment_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Link to weight record
    weight_record = models.ForeignKey(
        WeightRecord,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    # Payment details
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='UPI')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    
    # UPI specific fields
    upi_transaction_id = models.CharField(max_length=200, blank=True)
    upi_transaction_ref = models.CharField(max_length=200, blank=True)
    upi_qr_data = models.TextField(blank=True)  # Store UPI QR string
    
    # Transaction details
    transaction_date = models.DateTimeField(null=True, blank=True)
    
    # Additional info
    remarks = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        indexes = [
            models.Index(fields=['payment_id']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['weight_record']),
            models.Index(fields=['upi_transaction_id']),
        ]
    
    def __str__(self):
        return f"Payment {self.payment_id} - {self.payment_status}"
    
    def mark_success(self, transaction_id='', transaction_ref=''):
        """Mark payment as successful"""
        self.payment_status = 'SUCCESS'
        self.transaction_date = timezone.now()
        if transaction_id:
            self.upi_transaction_id = transaction_id
        if transaction_ref:
            self.upi_transaction_ref = transaction_ref
        self.save()
    
    def mark_failed(self, reason=''):
        """Mark payment as failed"""
        self.payment_status = 'FAILED'
        self.remarks = reason
        self.save()


class QRCode(models.Model):
    """Model for storing generated QR codes"""
    qr_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='qr_codes'
    )
    
    # QR Code data
    qr_string = models.TextField()  # UPI deep link string
    qr_image = models.TextField(blank=True)  # Base64 encoded QR image
    
    # Metadata
    generated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    scan_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'qr_codes'
        ordering = ['-generated_at']
        verbose_name = 'QR Code'
        verbose_name_plural = 'QR Codes'
        indexes = [
            models.Index(fields=['qr_id']),
            models.Index(fields=['payment']),
        ]
    
    def __str__(self):
        return f"QR {self.qr_id} - Payment {self.payment.payment_id}"
    
    def mark_scanned(self):
        """Mark QR as scanned"""
        self.scan_count += 1
        self.save()

class PaymentSlip(models.Model):
    """Model for storing printed payment slips"""
    SLIP_STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('GENERATED', 'Generated'),
        ('PRINTING', 'Printing'),
        ('PRINTED', 'Printed'),
        ('PRINT_FAILED', 'Print Failed'),
        ('SENT', 'Sent'),
        ('ARCHIVED', 'Archived'),
    ]
    
    slip_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='slips'
    )
    
    # Printer used
    printer = models.ForeignKey(
        PrinterConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='printed_slips'
    )
    
    # Slip details
    slip_number = models.CharField(max_length=100, unique=True)
    slip_status = models.CharField(max_length=20, choices=SLIP_STATUS_CHOICES, default='DRAFT')
    
    # Auto-print tracking
    is_auto_printed = models.BooleanField(default=False, help_text="Was this slip auto-printed?")
    auto_print_failed = models.BooleanField(default=False)
    auto_print_error = models.TextField(blank=True)
    
    # Generated slip files
    pdf_file = models.FileField(upload_to='slips/pdf/%Y/%m/%d/', blank=True, null=True)
    
    # Slip content (JSON format for flexibility)
    slip_content = models.JSONField(null=True, blank=True)
    
    # Print details
    printed_at = models.DateTimeField(null=True, blank=True)
    printed_by = models.ForeignKey(
        Operator,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='printed_slips'
    )
    printer_name = models.CharField(max_length=200, blank=True)
    print_count = models.IntegerField(default=0)
    
    # Generation details
    generated_at = models.DateTimeField(default=timezone.now)
    generated_by = models.ForeignKey(
        Operator,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_slips'
    )
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payment_slips'
        ordering = ['-created_at']
        verbose_name = 'Payment Slip'     
        verbose_name_plural = 'Payment Slips'
        indexes = [
            models.Index(fields=['slip_id']),
            models.Index(fields=['slip_number']),
            models.Index(fields=['payment']),
            models.Index(fields=['slip_status']),
            models.Index(fields=['is_auto_printed']),
        ]
    
    def __str__(self):
        return f"Slip {self.slip_number} - Payment {self.payment.payment_id}"
    
    def mark_printed(self, operator=None, printer_name='', auto_printed=False):
        """Mark slip as printed"""
        self.slip_status = 'PRINTED'
        self.printed_at = timezone.now()
        self.printed_by = operator
        self.printer_name = printer_name
        self.is_auto_printed = auto_printed
        self.print_count += 1
        self.save()
    
    def mark_print_failed(self, error_message=''):
        """Mark slip printing as failed"""
        self.slip_status = 'PRINT_FAILED'
        self.auto_print_failed = True
        self.auto_print_error = error_message
        self.save()


class AuditLog(models.Model):
    """Model for storing audit logs of all weight transactions"""
    ACTION_CHOICES = [
        ('CREATE', 'Created'),
        ('UPDATE', 'Updated'),
        ('DELETE', 'Deleted'),
        ('CALCULATE', 'Calculated'),
        ('EXPORT', 'Exported'),
        ('MULTI_DROP_ADD', 'Multi-Drop Added'),
        ('MULTI_DROP_CALCULATE', 'Multi-Drop Calculated'),
        # Complete workflow actions
        ('RECORD_SAVED', 'Record Saved in Database'),
        ('VEHICLE_LEFT', 'Vehicle Left'),
        ('FIRST_WEIGHT_STABLE_DETECTED', 'First Weight Stable Detected'),
        ('FIRST_WEIGHT_CAPTURED', 'First Weight Captured'),
        ('FIRST_WEIGHT_AUTO_CAPTURED', 'First Weight Auto-Captured'),
        ('VEHICLE_RETURNED', 'Vehicle Returned'),
        ('SECOND_WEIGHT_STABLE_DETECTED', 'Second Weight Stable Detected'),
        ('SECOND_WEIGHT_CAPTURED', 'Second Weight Captured'),
        ('SECOND_WEIGHT_AUTO_CAPTURED', 'Second Weight Auto-Captured'),
        ('WEIGHTS_CALCULATED', 'Weights Calculated'),
        ('CHARGES_CALCULATED', 'Charges Calculated'),
        # Payment-related actions
        ('PAYMENT_INITIATED', 'Payment Initiated'),
        ('QR_GENERATED', 'QR Code Generated'),
        ('SLIP_GENERATED', 'Slip Generated'),
        ('SLIP_AUTO_PRINTED', 'Slip Auto-Printed'),
        ('SLIP_PRINTED', 'Slip Printed'),
        ('SLIP_PRINT_FAILED', 'Slip Print Failed'),
        ('PAYMENT_SCANNED', 'QR Scanned'),
        ('PAYMENT_SUCCESS', 'Payment Success'),
        ('PAYMENT_FAILED', 'Payment Failed'),
        ('PAYMENT_UPDATED', 'Payment Updated'),
        # Photo-related actions
        ('PHOTO_UPLOADED', 'Photo Uploaded'),
        ('PHOTO_AUTO_CAPTURED', 'Photo Auto-Captured'),
        ('PHOTO_DELETED', 'Photo Deleted'),    
        ('TIMESTAMP_ADDED', 'Timestamp Added to Photo'),
        # Hardware status
        ('WEIGHBRIDGE_CONNECTED', 'Weighbridge Connected'),
        ('WEIGHBRIDGE_DISCONNECTED', 'Weighbridge Disconnected'),
        ('CAMERA_CONNECTED', 'Camera Connected'),
        ('CAMERA_DISCONNECTED', 'Camera Disconnected'),
        ('PRINTER_READY', 'Printer Ready'),
        ('PRINTER_NOT_READY', 'Printer Not Ready'),
        ('LIVE_WEIGHT_UPDATE', 'Live Weight Updated'),
        # AI Monitoring actions
        ('AI_MONITORING_ENABLED', 'AI Monitoring Enabled'),
        ('AI_MONITORING_DISABLED', 'AI Monitoring Disabled'),
        ('OBJECT_DETECTED', 'Object Detected'),
        ('UNAUTHORIZED_PRESENCE_DETECTED', 'Unauthorized Presence Detected'),
        ('PRESENCE_ALERT_TRIGGERED', 'Presence Alert Triggered'),
        ('PRESENCE_ALERT_ACKNOWLEDGED', 'Presence Alert Acknowledged'),
        ('PRESENCE_ALERT_RESOLVED', 'Presence Alert Resolved'),
        ('DETECTION_SNAPSHOT_CAPTURED', 'Detection Snapshot Captured'),
        # Completion
        ('WEIGHMENT_COMPLETE', 'Weighment Complete'),  
    ]
    
    weight_record = models.ForeignKey(
        WeightRecord, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='audit_logs'
    )
    
    # Link to payment (optional)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    
    # Link to detection (optional)
    detection = models.ForeignKey(
        ObjectDetectionLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    
    # Link to alert (optional)
    alert = models.ForeignKey(
        UnauthorizedPresenceAlert,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    
    action = models.CharField(max_length=40, choices=ACTION_CHOICES)
    user = models.CharField(max_length=200, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Store old and new values for updates
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    
    # Additional context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    # Calculation details
    calculation_details = models.JSONField(null=True, blank=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']

        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['action']), 
            models.Index(fields=['weight_record']),
            models.Index(fields=['payment']),
            models.Index(fields=['detection']),
            models.Index(fields=['alert']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.timestamp}"