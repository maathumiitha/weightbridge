from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied


# ==================== 1. SOFT DELETE BASE MODEL ====================
class SoftDeleteModel(models.Model):
    """
    Base model with soft delete functionality.
    NO DELETE WITHOUT SUPER ADMIN requirement.
    
    Usage: Make your models inherit from this class
    Example: class Customer(SoftDeleteModel)
    """
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_deleted'
    )
    
    class Meta:
        abstract = True
    
    def soft_delete(self, user):
        """Soft delete - requires super admin permission"""
        if not user.is_superuser:
            raise PermissionDenied("Only super admin can delete records")
        
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()
    
    def restore(self, user):
        """Restore soft deleted record - requires super admin"""
        if not user.is_superuser:
            raise PermissionDenied("Only super admin can restore records")
        
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()


# ==================== 2. DATE LOCK CONFIGURATION ====================
class DateLockConfig(models.Model):
    """
    Configuration for locking past dates to prevent modifications.
    LOCK PAST DATES feature.
    """
    name = models.CharField(max_length=200, default="Date Lock System")
    
    # Lock settings
    is_enabled = models.BooleanField(
        default=True,
        help_text="Enable date-based record locking"
    )
    
    lock_days_after = models.IntegerField(
        default=7,
        help_text="Lock records after this many days (0 = lock immediately after date passes)"
    )
    
    # Grace period settings
    allow_grace_period = models.BooleanField(
        default=True,
        help_text="Allow modifications during grace period"
    )
    grace_period_hours = models.IntegerField(
        default=24,
        help_text="Grace period in hours after date before lock takes effect"
    )
    
    # Exceptions
    super_admin_override = models.BooleanField(
        default=True,
        help_text="Allow super admins to edit locked records"
    )
    
    # Specific date locks
    locked_dates = models.JSONField(
        default=list,
        help_text="List of specific dates that are permanently locked (YYYY-MM-DD format)"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'date_lock_config'
        verbose_name = 'Date Lock Configuration'
        verbose_name_plural = 'Date Lock Configurations'
    
    def __str__(self):
        return f"{self.name} - {'Enabled' if self.is_enabled else 'Disabled'}"
    
    def is_date_locked(self, date, user=None):
        """Check if a date is locked for editing"""
        if not self.is_enabled:
            return False
        
        # Super admin override
        if user and user.is_superuser and self.super_admin_override:
            return False
        
        # Check if date is in permanently locked dates
        date_str = date.strftime('%Y-%m-%d')
        if date_str in self.locked_dates:
            return True
        
        # Calculate lock date based on configuration
        now = timezone.now()
        
        # Apply grace period if enabled
        if self.allow_grace_period:
            lock_threshold = now - timezone.timedelta(
                days=self.lock_days_after,
                hours=self.grace_period_hours
            )
        else:
            lock_threshold = now - timezone.timedelta(days=self.lock_days_after)
        
        # Convert date to datetime for comparison
        date_dt = timezone.make_aware(
            timezone.datetime.combine(date, timezone.datetime.min.time())
        )
        
        return date_dt < lock_threshold


# ==================== 3. BACKUP CONFIGURATION ====================
class BackupConfig(models.Model):
    """
    Configuration for automatic database backups.
    DAILY BACKUP feature.
    """
    BACKUP_FREQUENCY_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('CUSTOM', 'Custom Interval'),
    ]
    
    name = models.CharField(max_length=200, default="Backup System")
    
    # Backup settings
    is_enabled = models.BooleanField(default=True)
    backup_frequency = models.CharField(
        max_length=20,
        choices=BACKUP_FREQUENCY_CHOICES,
        default='DAILY'
    )
    custom_interval_hours = models.IntegerField(
        default=24,
        help_text="For custom frequency, backup interval in hours"
    )
    
    # Backup time
    backup_time = models.TimeField(
        default=timezone.datetime.strptime('02:00', '%H:%M').time(),
        help_text="Preferred time for daily backups (24-hour format)"
    )
    
    # Backup storage
    backup_path = models.CharField(
        max_length=500,
        default='/backups/',
        help_text="Directory path for storing backups"
    )
    
    # Retention settings
    retention_days = models.IntegerField(
        default=90,
        help_text="Keep backups for this many days before auto-deletion"
    )
    keep_monthly_backups = models.BooleanField(
        default=True,
        help_text="Keep one backup per month indefinitely"
    )
    
    # Backup options
    compress_backups = models.BooleanField(
        default=True,
        help_text="Compress backup files to save space"
    )
    include_media_files = models.BooleanField(
        default=True,
        help_text="Include uploaded media files in backup"
    )
    
    # Status tracking
    last_backup_date = models.DateTimeField(null=True, blank=True)
    last_backup_status = models.CharField(max_length=50, blank=True)
    last_backup_size_mb = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Notifications
    send_backup_notifications = models.BooleanField(default=True)
    notification_emails = models.TextField(
        blank=True,
        help_text="Comma-separated email addresses for backup notifications"
    )
    notify_on_success = models.BooleanField(default=False)
    notify_on_failure = models.BooleanField(default=True)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'backup_config'
        verbose_name = 'Backup Configuration'
        verbose_name_plural = 'Backup Configurations'
    
    def __str__(self):
        return f"{self.name} - {self.get_backup_frequency_display()}"


class BackupLog(models.Model):
    """
    Log of all backup operations.
    Part of DAILY BACKUP feature.
    """
    BACKUP_STATUS_CHOICES = [
        ('STARTED', 'Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('PARTIAL', 'Partial Success'),
    ]
    
    backup_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    backup_config = models.ForeignKey(
        BackupConfig,
        on_delete=models.CASCADE,
        related_name='backup_logs'
    )
    
    # Backup details
    backup_type = models.CharField(
        max_length=20,
        choices=[
            ('AUTO', 'Automatic'),
            ('MANUAL', 'Manual'),
            ('SCHEDULED', 'Scheduled'),
        ],
        default='AUTO'
    )
    backup_status = models.CharField(
        max_length=20,
        choices=BACKUP_STATUS_CHOICES,
        default='STARTED'
    )
    
    # File information
    backup_file_path = models.CharField(max_length=500, blank=True)
    backup_file_name = models.CharField(max_length=200, blank=True)
    backup_size_mb = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Statistics
    records_backed_up = models.IntegerField(default=0)
    tables_backed_up = models.IntegerField(default=0)
    media_files_backed_up = models.IntegerField(default=0)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    
    # Error tracking
    error_message = models.TextField(blank=True)
    error_details = models.JSONField(null=True, blank=True)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    
    # Initiated by
    initiated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='initiated_backups'
    )
    
    class Meta:
        db_table = 'backup_logs'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['backup_id']),
            models.Index(fields=['-started_at']),
            models.Index(fields=['backup_status']),
        ]
    
    def __str__(self):
        return f"Backup {self.backup_id} - {self.backup_status} - {self.started_at}"
    
    def mark_completed(self, status='SUCCESS'):
        """Mark backup as completed"""
        self.backup_status = status
        self.completed_at = timezone.now()
        self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        self.save()
    
    def mark_failed(self, error_message='', error_details=None):
        """Mark backup as failed"""
        self.backup_status = 'FAILED'
        self.completed_at = timezone.now()
        self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        self.error_message = error_message
        if error_details:
            self.error_details = error_details
        self.save()


# ==================== 4. TARE WEIGHT HISTORY ====================
class TareWeightHistory(models.Model):
    """
    Long-term storage of tare weights for vehicles.
    STORE TARE HISTORY LONG TERM feature.
    
    NOTE: This model references Vehicle and WeightRecord from main models.
    Make sure to import them or use string references.
    """
    history_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Vehicle reference - Use string reference to avoid circular import
    vehicle = models.ForeignKey(
        'weight_billing.Vehicle',
        on_delete=models.CASCADE,
        related_name='tare_history'
    )
    
    # Weight record reference (source of tare weight)
    weight_record = models.ForeignKey(
        'weight_billing.WeightRecord',
        on_delete=models.CASCADE,
        related_name='tare_history_entries'
    )
    
    # Tare weight details
    tare_weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # When this tare was recorded
    recorded_date = models.DateField()
    recorded_time = models.DateTimeField()
    
    # Operator who recorded it
    recorded_by = models.ForeignKey(
        'weight_billing.Operator',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_tare_weights'
    )
    
    # Variance tracking (compared to previous tare)
    previous_tare_weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    weight_variance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Difference from previous tare weight"
    )
    variance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Percentage variance from previous tare"
    )
    
    # Flags for unusual variances
    is_significant_variance = models.BooleanField(
        default=False,
        help_text="Flag if variance exceeds threshold (>5%)"
    )
    variance_notes = models.TextField(blank=True)
    
    # Statistical data
    is_outlier = models.BooleanField(
        default=False,
        help_text="Statistical outlier based on historical data"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'tare_weight_history'
        ordering = ['-recorded_date', '-recorded_time']
        indexes = [
            models.Index(fields=['vehicle', '-recorded_date']),
            models.Index(fields=['history_id']),
            models.Index(fields=['-recorded_date']),
            models.Index(fields=['is_significant_variance']),
        ]
        verbose_name = 'Tare Weight History'
        verbose_name_plural = 'Tare Weight Histories'
    
    def __str__(self):
        return f"{self.vehicle.vehicle_number} - {self.tare_weight} kg - {self.recorded_date}"
    
    def calculate_variance(self):
        """Calculate variance from previous tare weight"""
        # Get previous tare weight for this vehicle
        previous = TareWeightHistory.objects.filter(
            vehicle=self.vehicle,
            recorded_date__lt=self.recorded_date
        ).order_by('-recorded_date').first()
        
        if previous:
            self.previous_tare_weight = previous.tare_weight
            self.weight_variance = self.tare_weight - previous.tare_weight
            
            if previous.tare_weight > 0:
                self.variance_percentage = (
                    (self.weight_variance / previous.tare_weight) * 100
                )
                
                # Flag significant variances (>5%)
                if abs(self.variance_percentage) > 5:
                    self.is_significant_variance = True
        
        self.save()
    
    @classmethod
    def get_vehicle_average_tare(cls, vehicle, days=30):
        """Get average tare weight for vehicle over specified days"""
        cutoff_date = timezone.now().date() - timezone.timedelta(days=days)
        
        history = cls.objects.filter(
            vehicle=vehicle,
            recorded_date__gte=cutoff_date,
            is_outlier=False  # Exclude outliers
        ).aggregate(
            avg_tare=models.Avg('tare_weight'),
            min_tare=models.Min('tare_weight'),
            max_tare=models.Max('tare_weight'),
            count=models.Count('id')
        )
        
        return history
    
    @classmethod
    def detect_outliers(cls, vehicle):
        """Detect statistical outliers in tare weight history"""
        from statistics import mean, stdev
        
        # Get last 100 tare weights for vehicle
        history = cls.objects.filter(vehicle=vehicle).order_by('-recorded_date')[:100]
        
        if history.count() < 10:  # Need minimum data
            return
        
        weights = [float(h.tare_weight) for h in history]
        avg = mean(weights)
        std = stdev(weights)
        
        # Mark outliers (> 2 standard deviations)
        for entry in history:
            z_score = abs((float(entry.tare_weight) - avg) / std) if std > 0 else 0
            if z_score > 2:
                entry.is_outlier = True
                entry.save()


# ==================== 5. ENHANCED AUDIT LOG ====================
class SecurityAuditLog(models.Model):
    """
    Comprehensive audit logging for all actions.
    LOG EVERY ACTION feature.
    
    This is separate from your main AuditLog to avoid conflicts.
    You can merge functionality into your existing AuditLog if preferred.
    """
    ACTION_CHOICES = [
        # Basic CRUD
        ('CREATE', 'Created'),
        ('UPDATE', 'Updated'),
        ('DELETE', 'Deleted'),
        ('VIEW', 'Viewed'),
        
        # Soft Delete Actions
        ('SOFT_DELETE', 'Soft Deleted'),
        ('RESTORE', 'Restored'),
        
        # Date Lock Actions
        ('DATE_LOCKED', 'Date Locked'),
        ('DATE_LOCK_OVERRIDE', 'Date Lock Overridden'),
        ('DATE_LOCK_ATTEMPT_BLOCKED', 'Date Lock Attempt Blocked'),
        
        # Backup Actions
        ('BACKUP_STARTED', 'Backup Started'),
        ('BACKUP_COMPLETED', 'Backup Completed'),
        ('BACKUP_FAILED', 'Backup Failed'),
        ('BACKUP_VERIFIED', 'Backup Verified'),
        
        # Tare Weight Actions
        ('TARE_HISTORY_RECORDED', 'Tare Weight History Recorded'),
        ('TARE_VARIANCE_DETECTED', 'Tare Weight Variance Detected'),
        ('TARE_OUTLIER_DETECTED', 'Tare Weight Outlier Detected'),
        
        # Security Actions
        ('LOGIN', 'User Login'),
        ('LOGOUT', 'User Logout'),
        ('LOGIN_FAILED', 'Login Failed'),
        ('PERMISSION_DENIED', 'Permission Denied'),
        ('UNAUTHORIZED_ACCESS', 'Unauthorized Access Attempt'),
        
        # Configuration Changes
        ('CONFIG_CHANGED', 'Configuration Changed'),
        ('SECURITY_SETTING_CHANGED', 'Security Setting Changed'),
    ]
    
    # Reference to weight record (if applicable)
    weight_record = models.ForeignKey(
        'weight_billing.WeightRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_audit_logs'
    )
    
    # Enhanced user tracking
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_audit_logs'
    )
    username = models.CharField(max_length=200, blank=True)
    
    # Action details
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Enhanced change tracking
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    
    # Context information
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_id = models.CharField(max_length=100, blank=True)
    
    # Additional details
    notes = models.TextField(blank=True)
    affected_model = models.CharField(max_length=100, blank=True, help_text="Model that was affected")
    affected_object_id = models.IntegerField(null=True, blank=True)
    
    # Security flags
    is_suspicious = models.BooleanField(
        default=False,
        help_text="Flag for suspicious activity"
    )
    requires_review = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_security_audit_logs'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'security_audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['action']), 
            models.Index(fields=['weight_record']),
            models.Index(fields=['user']),
            models.Index(fields=['is_suspicious']),
            models.Index(fields=['requires_review']),
            models.Index(fields=['affected_model', 'affected_object_id']),
        ]
        verbose_name = 'Security Audit Log'
        verbose_name_plural = 'Security Audit Logs'
    
    def __str__(self):
        return f"{self.action} - {self.username} - {self.timestamp}"
    
    @classmethod
    def log_action(cls, action, user=None, weight_record=None, old_values=None, 
                   new_values=None, notes='', request=None, affected_model=None, 
                   affected_object_id=None):
        """Helper method to create audit log entries"""
        log_entry = cls(
            action=action,
            user=user,
            username=user.username if user else 'System',
            weight_record=weight_record,
            old_values=old_values,
            new_values=new_values,
            notes=notes,
            affected_model=affected_model,
            affected_object_id=affected_object_id
        )
        
        if request:
            # Extract request metadata
            log_entry.ip_address = cls.get_client_ip(request)
            log_entry.user_agent = request.META.get('HTTP_USER_AGENT', '')
            if hasattr(request, 'session'):
                log_entry.session_id = request.session.session_key or ''
        
        log_entry.save()
        return log_entry
    
    @staticmethod
    def get_client_ip(request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def mark_suspicious(self, reason=''):
        """Mark this log entry as suspicious"""
        self.is_suspicious = True
        self.requires_review = True
        if reason:
            self.notes = f"{self.notes}\n[SUSPICIOUS] {reason}" if self.notes else f"[SUSPICIOUS] {reason}"
        self.save()
    
    def mark_reviewed(self, reviewed_by):
        """Mark log entry as reviewed"""
        self.requires_review = False
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.save()


# ==================== INTEGRATION HELPERS ====================

def add_date_lock_to_model(model_class):
    """
    Helper function to add date lock checking to your existing WeightRecord model.
    
    Usage in your main models.py:
        from models_security_data_management import add_date_lock_to_model
        
        class WeightRecord(models.Model):
            # ... your fields ...
            
            def save(self, *args, **kwargs):
                # Check date lock
                if self.pk and not kwargs.get('skip_date_lock_check'):
                    from models_security_data_management import check_date_lock
                    if check_date_lock(self.date, getattr(self, '_current_user', None)):
                        raise PermissionDenied(f"Cannot modify record from {self.date}. Date is locked.")
                super().save(*args, **kwargs)
    """
    pass


def check_date_lock(date, user=None):
    """
    Standalone function to check if a date is locked.
    Can be called from any model or view.
    
    Args:
        date: The date to check
        user: The user attempting the action (for super admin override)
    
    Returns:
        Boolean: True if date is locked, False otherwise
    """
    try:
        lock_config = DateLockConfig.objects.filter(is_active=True).first()
        if lock_config:
            return lock_config.is_date_locked(date, user)
    except DateLockConfig.DoesNotExist:
        pass
    return False


def log_security_action(action, user=None, **kwargs):
    """
    Standalone function to log security actions.
    
    Usage:
        from models_security_data_management import log_security_action
        
        log_security_action(
            action='SOFT_DELETE',
            user=request.user,
            weight_record=record,
            notes='User deleted record',
            request=request
        )
    """
    return SecurityAuditLog.log_action(action=action, user=user, **kwargs)


# ==================== MODEL MIXINS ====================

class DateLockMixin:
    """
    Mixin to add date lock checking to any model with a 'date' field.
    
    Usage:
        class WeightRecord(DateLockMixin, models.Model):
            date = models.DateField()
            # ... other fields ...
    """
    
    def check_date_lock(self, user=None):
        """Check if this record's date is locked"""
        if hasattr(self, 'date'):
            return check_date_lock(self.date, user)
        return False
    
    def save(self, *args, **kwargs):
        # Check date lock before saving modifications
        if self.pk and not kwargs.get('skip_date_lock_check'):
            if self.check_date_lock(getattr(self, '_current_user', None)):
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied(
                    f"Cannot modify record from {self.date}. Date is locked."
                )
        super().save(*args, **kwargs)


class AuditLogMixin:
    """
    Mixin to automatically log all changes to a model.
    
    Usage:
        class WeightRecord(AuditLogMixin, models.Model):
            # ... fields ...
    """
    
    def save(self, *args, **kwargs):
        # Track if this is a create or update
        is_new = self.pk is None
        
        # Get old values if updating
        old_values = None
        if not is_new:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                old_values = {
                    field.name: getattr(old_instance, field.name)
                    for field in self._meta.fields
                }
            except self.__class__.DoesNotExist:
                pass
        
        # Save the record
        super().save(*args, **kwargs)
        
        # Log the action
        action = 'CREATE' if is_new else 'UPDATE'
        new_values = {
            field.name: getattr(self, field.name)
            for field in self._meta.fields
        }
        
        log_security_action(    
            action=action,
            user=getattr(self, '_current_user', None),
            affected_model=self.__class__.__name__,
            affected_object_id=self.pk,
            old_values=old_values,
            new_values=new_values,   
            request=getattr(self, '_current_request', None)
        )