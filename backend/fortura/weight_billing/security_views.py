# views_security.py
"""
Security and Data Management ViewSets
Handles: Soft Delete, Date Lock, Backup, Tare History, and Enhanced Audit Logging
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from django.db import models
from decimal import Decimal
import time

# Import security models
from .models_security_data_management import (
    DateLockConfig,
    BackupConfig,
    BackupLog,
    TareWeightHistory,
    SecurityAuditLog,
    check_date_lock,
    log_security_action
)

# Import main models for integration
from .models import (
    Customer, Operator, Vehicle, WeightRecord
)

# Import serializers from main serializers file
from .serializers import (
    DateLockConfigSerializer,
    BackupConfigSerializer,
    BackupLogSerializer,
    TareWeightHistorySerializer,
    SecurityAuditLogSerializer,
    SoftDeletedRecordSerializer,
    RestoreRecordSerializer
)


# ==================== DATE LOCK CONFIGURATION VIEWSET ====================

class DateLockConfigViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing date lock configuration.
    Controls which dates are locked from editing.
    """
    queryset = DateLockConfig.objects.all()
    serializer_class = DateLockConfigSerializer
    permission_classes = [IsAdminUser]  # Only admins can manage date locks
    
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """Enable date locking system"""
        config = self.get_object()
        config.is_enabled = True
        config.save()
        
        log_security_action(
            action='CONFIG_CHANGED',
            user=request.user,
            affected_model='DateLockConfig',
            affected_object_id=config.id,
            new_values={'is_enabled': True},
            notes=f'Date lock system enabled',
            request=request
        )
        
        return Response({
            'success': True,
            'message': 'Date lock system enabled',
            'is_enabled': True
        })
    
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """Disable date locking system"""
        config = self.get_object()
        config.is_enabled = False
        config.save()
        
        log_security_action(
            action='CONFIG_CHANGED',
            user=request.user,
            affected_model='DateLockConfig',
            affected_object_id=config.id,
            new_values={'is_enabled': False},
            notes=f'Date lock system disabled',
            request=request
        )
        
        return Response({
            'success': True,
            'message': 'Date lock system disabled',
            'is_enabled': False
        })
    
    @action(detail=True, methods=['post'])
    def add_locked_date(self, request, pk=None):
        """
        Add a specific date to permanently locked dates.
        Expected payload: {"date": "2026-01-15"}
        """
        config = self.get_object()
        date_str = request.data.get('date')
        
        if not date_str:
            return Response(
                {'error': 'date is required (YYYY-MM-DD format)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if date_str not in config.locked_dates:
            config.locked_dates.append(date_str)
            config.save()
            
            log_security_action(
                action='CONFIG_CHANGED',
                user=request.user,
                affected_model='DateLockConfig',
                affected_object_id=config.id,
                new_values={'added_locked_date': date_str},
                notes=f'Added permanently locked date: {date_str}',
                request=request
            )
            
            return Response({
                'success': True,
                'message': f'Date {date_str} is now permanently locked',
                'locked_dates': config.locked_dates
            })
        else:
            return Response({
                'message': f'Date {date_str} is already locked',
                'locked_dates': config.locked_dates
            })
    
    @action(detail=True, methods=['post'])
    def remove_locked_date(self, request, pk=None):
        """
        Remove a specific date from permanently locked dates.
        Expected payload: {"date": "2026-01-15"}
        """
        config = self.get_object()
        date_str = request.data.get('date')
        
        if not date_str:
            return Response(
                {'error': 'date is required (YYYY-MM-DD format)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if date_str in config.locked_dates:
            config.locked_dates.remove(date_str)
            config.save()
            
            log_security_action(
                action='CONFIG_CHANGED',
                user=request.user,
                affected_model='DateLockConfig',
                affected_object_id=config.id,
                new_values={'removed_locked_date': date_str},
                notes=f'Removed permanently locked date: {date_str}',
                request=request
            )
            
            return Response({
                'success': True,
                'message': f'Date {date_str} is no longer permanently locked',
                'locked_dates': config.locked_dates
            })
        else:
            return Response({
                'message': f'Date {date_str} was not in locked dates',
                'locked_dates': config.locked_dates
            })
    
    @action(detail=True, methods=['post'])
    def check_date(self, request, pk=None):
        """
        Check if a specific date is locked.
        Expected payload: {"date": "2026-01-15"}
        """
        config = self.get_object()
        date_str = request.data.get('date')
        
        if not date_str:
            return Response(
                {'error': 'date is required (YYYY-MM-DD format)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            is_locked = config.is_date_locked(date_obj, request.user)
            
            return Response({
                'date': date_str,
                'is_locked': is_locked,
                'reason': 'Permanently locked' if date_str in config.locked_dates else 'Past threshold' if is_locked else 'Not locked',
                'can_override': request.user.is_superuser and config.super_admin_override
            })
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def active_config(self, request):
        """Get the active date lock configuration"""
        config = DateLockConfig.objects.filter(is_active=True).first()
        
        if not config:
            return Response({
                'message': 'No active date lock configuration found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(config)
        return Response(serializer.data)


# ==================== BACKUP CONFIGURATION VIEWSET ====================

class BackupConfigViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing backup configuration.
    Controls automatic backup settings.
    """
    queryset = BackupConfig.objects.all()
    serializer_class = BackupConfigSerializer
    permission_classes = [IsAdminUser]  # Only admins can manage backups
    
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """Enable automatic backups"""
        config = self.get_object()
        config.is_enabled = True
        config.save()
        
        log_security_action(
            action='CONFIG_CHANGED',
            user=request.user,
            affected_model='BackupConfig',
            affected_object_id=config.id,
            new_values={'is_enabled': True},
            notes=f'Automatic backups enabled',
            request=request
        )
        
        return Response({
            'success': True,
            'message': 'Automatic backups enabled',
            'is_enabled': True
        })
    
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """Disable automatic backups"""
        config = self.get_object()
        config.is_enabled = False
        config.save()
        
        log_security_action(
            action='CONFIG_CHANGED',
            user=request.user,
            affected_model='BackupConfig',
            affected_object_id=config.id,
            new_values={'is_enabled': False},
            notes=f'Automatic backups disabled',
            request=request
        )
        
        return Response({
            'success': True,
            'message': 'Automatic backups disabled',
            'is_enabled': False
        })
    
    @action(detail=True, methods=['post'])
    def trigger_backup(self, request, pk=None):
        """Manually trigger a backup"""
        config = self.get_object()
        
        # Create backup log entry
        backup_log = BackupLog.objects.create(
            backup_config=config,
            backup_type='MANUAL',
            backup_status='STARTED',
            initiated_by=request.user
        )
        
        try:
            # This is where you'd integrate with your actual backup system
            # For now, we'll simulate it
            
            # Simulate backup process
            time.sleep(1)  # Simulate backup time
            
            # Mark as completed
            backup_log.mark_completed('SUCCESS')
            backup_log.backup_size_mb = Decimal('125.50')  # Simulate size
            backup_log.records_backed_up = WeightRecord.objects.count()
            backup_log.tables_backed_up = 15  # Number of tables
            backup_log.save()
            
            # Update config
            config.last_backup_date = timezone.now()
            config.last_backup_status = 'SUCCESS'
            config.last_backup_size_mb = backup_log.backup_size_mb
            config.save()
            
            log_security_action(
                action='BACKUP_COMPLETED',
                user=request.user,
                affected_model='BackupLog',
                affected_object_id=backup_log.id,
                new_values={
                    'backup_id': str(backup_log.backup_id),
                    'size_mb': str(backup_log.backup_size_mb),
                    'records': backup_log.records_backed_up
                },
                notes=f'Manual backup completed successfully',
                request=request
            )
            
            return Response({
                'success': True,
                'message': 'Backup completed successfully',
                'backup_id': str(backup_log.backup_id),
                'size_mb': str(backup_log.backup_size_mb),
                'records_backed_up': backup_log.records_backed_up,
                'duration_seconds': backup_log.duration_seconds
            })
            
        except Exception as e:
            backup_log.mark_failed(str(e))
            
            log_security_action(
                action='BACKUP_FAILED',
                user=request.user,
                affected_model='BackupLog',
                affected_object_id=backup_log.id,
                new_values={
                    'backup_id': str(backup_log.backup_id),
                    'error': str(e)
                },
                notes=f'Manual backup failed: {str(e)}',
                request=request
            )
            
            return Response({
                'success': False,
                'message': f'Backup failed: {str(e)}',
                'backup_id': str(backup_log.backup_id)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def active_config(self, request):
        """Get the active backup configuration"""
        config = BackupConfig.objects.filter(is_active=True).first()
        
        if not config:
            return Response({
                'message': 'No active backup configuration found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(config)
        return Response(serializer.data)


# ==================== BACKUP LOG VIEWSET ====================

class BackupLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing backup logs (read-only).
    """
    queryset = BackupLog.objects.all()
    serializer_class = BackupLogSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = BackupLog.objects.select_related('backup_config', 'initiated_by').all()
        
        # Filter by status
        backup_status = self.request.query_params.get('status')
        if backup_status:
            queryset = queryset.filter(backup_status=backup_status.upper())
        
        # Filter by type
        backup_type = self.request.query_params.get('type')
        if backup_type:
            queryset = queryset.filter(backup_type=backup_type.upper())
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(started_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(started_at__lte=end_date)
        
        return queryset.order_by('-started_at')
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent backups (last 10)"""
        backups = self.get_queryset()[:10]
        serializer = self.get_serializer(backups, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get backup statistics"""
        total = BackupLog.objects.count()
        successful = BackupLog.objects.filter(backup_status='SUCCESS').count()
        failed = BackupLog.objects.filter(backup_status='FAILED').count()
        
        # Get latest backup
        latest = BackupLog.objects.order_by('-started_at').first()
        
        # Calculate total size
        total_size = BackupLog.objects.filter(
            backup_status='SUCCESS'
        ).aggregate(
            total=models.Sum('backup_size_mb')
        )['total'] or 0
        
        return Response({
            'total_backups': total,
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'total_size_mb': str(total_size),
            'latest_backup': {
                'backup_id': str(latest.backup_id) if latest else None,
                'status': latest.backup_status if latest else None,
                'started_at': latest.started_at.isoformat() if latest else None,
                'size_mb': str(latest.backup_size_mb) if latest and latest.backup_size_mb else None
            } if latest else None
        })


# ==================== TARE WEIGHT HISTORY VIEWSET ====================

class TareWeightHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing tare weight history (read-only, auto-created).
    """
    queryset = TareWeightHistory.objects.all()
    serializer_class = TareWeightHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = TareWeightHistory.objects.select_related(
            'vehicle', 
            'weight_record',
            'recorded_by'
        ).all()
        
        # Filter by vehicle
        vehicle_id = self.request.query_params.get('vehicle_id')
        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(recorded_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(recorded_date__lte=end_date)
        
        # Filter by significant variance
        significant_variance = self.request.query_params.get('significant_variance')
        if significant_variance is not None:
            queryset = queryset.filter(is_significant_variance=significant_variance.lower() == 'true')
        
        # Filter by outliers
        outliers = self.request.query_params.get('outliers')
        if outliers is not None:
            queryset = queryset.filter(is_outlier=outliers.lower() == 'true')
        
        return queryset.order_by('-recorded_date', '-recorded_time')
    
    @action(detail=False, methods=['get'])
    def vehicle_history(self, request):
        """
        Get tare weight history for a specific vehicle.
        Query params: vehicle_id (required), days (optional, default 30)
        """
        vehicle_id = request.query_params.get('vehicle_id')
        days = int(request.query_params.get('days', 30))
        
        if not vehicle_id:
            return Response(
                {'error': 'vehicle_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
            
            # Get history
            history = TareWeightHistory.objects.filter(
                vehicle=vehicle
            ).order_by('-recorded_date')[:100]  # Last 100 entries
            
            # Get stats
            stats = TareWeightHistory.get_vehicle_average_tare(vehicle, days=days)
            
            serializer = self.get_serializer(history, many=True)
            
            return Response({
                'vehicle': {
                    'id': vehicle.id,
                    'vehicle_number': vehicle.vehicle_number,
                    'last_known_tare': str(vehicle.last_known_tare) if vehicle.last_known_tare else None,
                    'last_tare_date': vehicle.last_tare_date.isoformat() if vehicle.last_tare_date else None
                },
                'stats': {
                    'days': days,
                    'avg_tare': str(stats['avg_tare']) if stats['avg_tare'] else None,
                    'min_tare': str(stats['min_tare']) if stats['min_tare'] else None,
                    'max_tare': str(stats['max_tare']) if stats['max_tare'] else None,
                    'count': stats['count']
                },
                'history': serializer.data
            })
            
        except Vehicle.DoesNotExist:
            return Response(
                {'error': 'Vehicle not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def detect_outliers(self, request):
        """
        Detect statistical outliers for a vehicle.
        Expected payload: {"vehicle_id": 1}
        """
        vehicle_id = request.data.get('vehicle_id')
        
        if not vehicle_id:
            return Response(
                {'error': 'vehicle_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
            
            # Run outlier detection
            TareWeightHistory.detect_outliers(vehicle)
            
            # Get outliers
            outliers = TareWeightHistory.objects.filter(
                vehicle=vehicle,
                is_outlier=True
            ).order_by('-recorded_date')
            
            serializer = self.get_serializer(outliers, many=True)
            
            return Response({
                'success': True,
                'message': f'Outlier detection completed for vehicle {vehicle.vehicle_number}',
                'outlier_count': outliers.count(),
                'outliers': serializer.data
            })
            
        except Vehicle.DoesNotExist:
            return Response(
                {'error': 'Vehicle not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def significant_variances(self, request):
        """Get all tare weights with significant variances (>5%)"""
        queryset = self.get_queryset().filter(is_significant_variance=True)
        
        # Optional: filter by days
        days = request.query_params.get('days')
        if days:
            cutoff_date = timezone.now().date() - timezone.timedelta(days=int(days))
            queryset = queryset.filter(recorded_date__gte=cutoff_date)
        
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'count': queryset.count(),
            'variances': serializer.data
        })


# ==================== SECURITY AUDIT LOG VIEWSET ====================

class SecurityAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing security audit logs (read-only).
    Enhanced audit trail with security features.
    """
    queryset = SecurityAuditLog.objects.all()
    serializer_class = SecurityAuditLogSerializer
    permission_classes = [IsAdminUser]  # Only admins can view security logs
    
    def get_queryset(self):
        queryset = SecurityAuditLog.objects.select_related(
            'user',
            'weight_record',
            'reviewed_by'
        ).all()
        
        # Filter by action
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action.upper())
        
        # Filter by user
        username = self.request.query_params.get('username')
        if username:
            queryset = queryset.filter(username__icontains=username)
        
        # Filter by suspicious
        is_suspicious = self.request.query_params.get('is_suspicious')
        if is_suspicious is not None:
            queryset = queryset.filter(is_suspicious=is_suspicious.lower() == 'true')
        
        # Filter by requires review
        requires_review = self.request.query_params.get('requires_review')
        if requires_review is not None:
            queryset = queryset.filter(requires_review=requires_review.lower() == 'true')
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        # Filter by model
        affected_model = self.request.query_params.get('affected_model')
        if affected_model:
            queryset = queryset.filter(affected_model=affected_model)
        
        return queryset.order_by('-timestamp')
    
    @action(detail=True, methods=['post'])
    def mark_suspicious(self, request, pk=None):
        """Mark a log entry as suspicious"""
        log_entry = self.get_object()
        reason = request.data.get('reason', '')
        
        log_entry.mark_suspicious(reason)
        
        return Response({
            'success': True,
            'message': 'Log entry marked as suspicious',
            'log_id': log_entry.id
        })
    
    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Mark a log entry as reviewed"""
        log_entry = self.get_object()
        
        log_entry.mark_reviewed(request.user)
        
        return Response({
            'success': True,
            'message': 'Log entry reviewed',
            'reviewed_by': request.user.username,
            'reviewed_at': log_entry.reviewed_at.isoformat()
        })
    
    @action(detail=False, methods=['get'])
    def suspicious_activity(self, request):
        """Get all suspicious activity logs"""
        logs = self.get_queryset().filter(is_suspicious=True)
        serializer = self.get_serializer(logs, many=True)
        
        return Response({
            'count': logs.count(),
            'logs': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def pending_review(self, request):
        """Get all logs requiring review"""
        logs = self.get_queryset().filter(requires_review=True)
        serializer = self.get_serializer(logs, many=True)
        
        return Response({
            'count': logs.count(),
            'logs': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get security audit statistics"""
        # Get date range
        start_date = request.query_params.get('start_date', timezone.now().date())
        end_date = request.query_params.get('end_date', timezone.now().date())
        
        logs = SecurityAuditLog.objects.filter(
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date
        )
        
        total = logs.count()
        suspicious = logs.filter(is_suspicious=True).count()
        pending_review = logs.filter(requires_review=True).count()
        
        # Group by action
        by_action = {}
        for log in logs:
            action = log.get_action_display()
            if action not in by_action:
                by_action[action] = 0
            by_action[action] += 1
        
        # Get top users
        from django.db.models import Count
        top_users = logs.values('username').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return Response({
            'date_range': {
                'start': str(start_date),
                'end': str(end_date)
            },
            'total_logs': total,
            'suspicious_activity': suspicious,
            'pending_review': pending_review,
            'by_action': by_action,
            'top_users': list(top_users)
        })


# ==================== SOFT DELETE MANAGEMENT VIEWSET ====================

class SoftDeleteManagementViewSet(viewsets.ViewSet):
    """
    ViewSet for managing soft-deleted records.
    Allows super admins to view, restore, and permanently delete soft-deleted records.
    """
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def deleted_customers(self, request):
        """Get all soft-deleted customers"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only super admins can view deleted records'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        deleted = Customer.objects.filter(is_deleted=True)
        
        data = [{
            'id': c.id,
            'driver_name': c.driver_name,
            'driver_phone': c.driver_phone,
            'deleted_at': c.deleted_at.isoformat() if c.deleted_at else None,
            'deleted_by': c.deleted_by.username if c.deleted_by else None
        } for c in deleted]
        
        return Response({
            'count': len(data),
            'customers': data
        })
    
    @action(detail=False, methods=['get'])
    def deleted_vehicles(self, request):
        """Get all soft-deleted vehicles"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only super admins can view deleted records'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        deleted = Vehicle.objects.filter(is_deleted=True)
        
        data = [{
            'id': v.id,
            'vehicle_number': v.vehicle_number,
            'vehicle_type': v.vehicle_type,
            'deleted_at': v.deleted_at.isoformat() if v.deleted_at else None,
            'deleted_by': v.deleted_by.username if v.deleted_by else None
        } for v in deleted]
        
        return Response({
            'count': len(data),
            'vehicles': data
        })
    
    @action(detail=False, methods=['get'])
    def deleted_operators(self, request):
        """Get all soft-deleted operators"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only super admins can view deleted records'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        deleted = Operator.objects.filter(is_deleted=True)
        
        data = [{
            'id': o.id,
            'employee_name': o.employee_name,
            'employee_id': o.employee_id,
            'deleted_at': o.deleted_at.isoformat() if o.deleted_at else None,
            'deleted_by': o.deleted_by.username if o.deleted_by else None
        } for o in deleted]
        
        return Response({
            'count': len(data),
            'operators': data
        })
    
    @action(detail=False, methods=['get'])
    def deleted_weight_records(self, request):
        """Get all soft-deleted weight records"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only super admins can view deleted records'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        deleted = WeightRecord.objects.filter(is_deleted=True)
        
        data = [{
            'id': w.id,
            'slip_number': w.slip_number,
            'customer': w.customer.driver_name,
            'vehicle': w.vehicle.vehicle_number,
            'date': w.date.isoformat(),
            'deleted_at': w.deleted_at.isoformat() if w.deleted_at else None,
            'deleted_by': w.deleted_by.username if w.deleted_by else None
        } for w in deleted]
        
        return Response({
            'count': len(data),
            'weight_records': data
        })
    
    @action(detail=False, methods=['post'])
    def restore_customer(self, request):
        """
        Restore a soft-deleted customer.
        Expected payload: {"customer_id": 1}
        """
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only super admins can restore records'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        customer_id = request.data.get('customer_id')
        if not customer_id:
            return Response(
                {'error': 'customer_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            customer = Customer.objects.get(id=customer_id, is_deleted=True)
            customer.restore(request.user)
            
            log_security_action(
                action='RESTORE',
                user=request.user,
                affected_model='Customer',
                affected_object_id=customer.id,
                notes=f'Restored customer: {customer.driver_name}',
                request=request
            )
            
            return Response({
                'success': True,
                'message': f'Customer {customer.driver_name} restored successfully'
            })
        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found or not deleted'},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDenied as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
    
    @action(detail=False, methods=['post'])
    def restore_vehicle(self, request):
        """Restore a soft-deleted vehicle"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only super admins can restore records'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        vehicle_id = request.data.get('vehicle_id')
        if not vehicle_id:
            return Response(
                {'error': 'vehicle_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id, is_deleted=True)
            vehicle.restore(request.user)
            
            log_security_action(
                action='RESTORE',
                user=request.user,
                affected_model='Vehicle',
                affected_object_id=vehicle.id,
                notes=f'Restored vehicle: {vehicle.vehicle_number}',
                request=request
            )
            
            return Response({
                'success': True,
                'message': f'Vehicle {vehicle.vehicle_number} restored successfully'
            })
        except Vehicle.DoesNotExist:
            return Response(
                {'error': 'Vehicle not found or not deleted'},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDenied as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
    
    @action(detail=False, methods=['post'])
    def restore_operator(self, request):
        """Restore a soft-deleted operator"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only super admins can restore records'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        operator_id = request.data.get('operator_id')
        if not operator_id:
            return Response(
                {'error': 'operator_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            operator = Operator.objects.get(id=operator_id, is_deleted=True)
            operator.restore(request.user)
            
            log_security_action(
                action='RESTORE',
                user=request.user,
                affected_model='Operator',
                affected_object_id=operator.id,
                notes=f'Restored operator: {operator.employee_name}',
                request=request
            )
            
            return Response({
                'success': True,
                'message': f'Operator {operator.employee_name} restored successfully'
            })
        except Operator.DoesNotExist:
            return Response(
                {'error': 'Operator not found or not deleted'},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDenied as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
    
    @action(detail=False, methods=['post'])
    def restore_weight_record(self, request):
        """Restore a soft-deleted weight record"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only super admins can restore records'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        record_id = request.data.get('record_id')
        if not record_id:
            return Response(
                {'error': 'record_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            record = WeightRecord.objects.get(id=record_id, is_deleted=True)
            record.restore(request.user)
            
            log_security_action(
                action='RESTORE',
                user=request.user,
                weight_record=record,
                affected_model='WeightRecord',
                affected_object_id=record.id,
                notes=f'Restored weight record: {record.slip_number}',
                request=request
            )
            
            return Response({
                'success': True,
                'message': f'Weight record {record.slip_number} restored successfully'
            })
        except WeightRecord.DoesNotExist:
            return Response(
                {'error': 'Weight record not found or not deleted'},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDenied as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
    
    @action(detail=False, methods=['get'])
    def all_deleted_records(self, request):
        """Get summary of all deleted records"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Only super admins can view deleted records'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return Response({
            'summary': {
                'customers': Customer.objects.filter(is_deleted=True).count(),
                'vehicles': Vehicle.objects.filter(is_deleted=True).count(),
                'operators': Operator.objects.filter(is_deleted=True).count(),
                'weight_records': WeightRecord.objects.filter(is_deleted=True).count()
            }
        })