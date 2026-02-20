# views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from decimal import Decimal
# ==================== SECURITY IMPORTS ====================
from django.core.exceptions import PermissionDenied
from .models_security_data_management import log_security_action

from .models import (
    Customer, Operator, Vehicle, WeightRecord, AuditLog,
    WeightRecordPhoto, Payment, QRCode, PaymentSlip,
    WeighbridgeConfig, LiveWeightReading, CameraConfig, PrinterConfig,
    # New AI Monitoring models
    AIMonitoringConfig, ObjectDetectionLog, UnauthorizedPresenceAlert
)
from .serializers import (
    CustomerSerializer, OperatorSerializer, VehicleSerializer,
    WeightRecordSerializer, AuditLogSerializer, WeightRecordPhotoSerializer,
    WeighbridgeConfigSerializer, LiveWeightReadingSerializer,
    CameraConfigSerializer, PrinterConfigSerializer,
    # New AI Monitoring serializers (you'll need to create these)
    AIMonitoringConfigSerializer, ObjectDetectionLogSerializer,
    UnauthorizedPresenceAlertSerializer
)
from .utils import create_audit_log


# ==================== CUSTOMER VIEWSET WITH SOFT DELETE ====================
class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    
    def get_queryset(self):
        """Filter out soft-deleted customers"""
        return Customer.objects.filter(is_deleted=False)
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete instead of hard delete"""
        instance = self.get_object()
        
        # Only super admins can delete
        if not request.user.is_superuser:
            log_security_action(
                user=request.user,
                action='DELETE_DENIED',
                model_name='Customer',
                record_id=instance.id,
                notes='Non-superuser attempted to delete customer'
            )
            raise PermissionDenied("Only super administrators can delete customers.")
        
        # Perform soft delete
        instance.deleted_by = request.user
        instance.deleted_at = timezone.now()
        instance.is_deleted = True
        instance.save()
        
        # Log the action
        log_security_action(
            user=request.user,
            action='SOFT_DELETE',
            model_name='Customer',
            record_id=instance.id,
            notes=f'Customer {instance.customer_name} soft deleted'
        )
        
        return Response(
            {'message': 'Customer deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )


# ==================== OPERATOR VIEWSET WITH SOFT DELETE ====================
class OperatorViewSet(viewsets.ModelViewSet):
    serializer_class = OperatorSerializer
    
    def get_queryset(self):
        """Filter out soft-deleted operators"""
        return Operator.objects.filter(is_deleted=False)
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete instead of hard delete"""
        instance = self.get_object()
        
        # Only super admins can delete
        if not request.user.is_superuser:
            log_security_action(
                user=request.user,
                action='DELETE_DENIED',
                model_name='Operator',
                record_id=instance.id,
                notes='Non-superuser attempted to delete operator'
            )
            raise PermissionDenied("Only super administrators can delete operators.")
        
        # Perform soft delete
        instance.deleted_by = request.user
        instance.deleted_at = timezone.now()
        instance.is_deleted = True
        instance.save()
        
        # Log the action
        log_security_action(
            user=request.user,
            action='SOFT_DELETE',
            model_name='Operator',
            record_id=instance.id,
            notes=f'Operator {instance.employee_name} soft deleted'
        )
        
        return Response(
            {'message': 'Operator deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )


# ==================== VEHICLE VIEWSET WITH SOFT DELETE ====================
class VehicleViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleSerializer
    
    def get_queryset(self):
        """Filter out soft-deleted vehicles"""
        return Vehicle.objects.filter(is_deleted=False)
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete instead of hard delete"""
        instance = self.get_object()
        
        # Only super admins can delete
        if not request.user.is_superuser:
            log_security_action(
                user=request.user,
                action='DELETE_DENIED',
                model_name='Vehicle',
                record_id=instance.id,
                notes='Non-superuser attempted to delete vehicle'
            )
            raise PermissionDenied("Only super administrators can delete vehicles.")
        
        # Perform soft delete
        instance.deleted_by = request.user
        instance.deleted_at = timezone.now()
        instance.is_deleted = True
        instance.save()
        
        # Log the action
        log_security_action(
            user=request.user,
            action='SOFT_DELETE',
            model_name='Vehicle',
            record_id=instance.id,
            notes=f'Vehicle {instance.vehicle_number} soft deleted'
        )
        
        return Response(
            {'message': 'Vehicle deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )


# ==================== HARDWARE CONFIGURATION VIEWSETS ====================

class WeighbridgeConfigViewSet(viewsets.ModelViewSet):
    """ViewSet for weighbridge hardware configuration"""
    queryset = WeighbridgeConfig.objects.all()
    serializer_class = WeighbridgeConfigSerializer
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test weighbridge connection"""
        config = self.get_object()
        
        try:
            # This would integrate with your serial port library
            # For now, just update status
            config.is_connected = True
            config.last_connected = timezone.now()
            config.connection_status_message = "Connection successful"
            config.save()
            
            return Response({
                'success': True,
                'message': 'Weighbridge connected successfully',
                'port': config.port,
                'status': 'connected'
            })
        except Exception as e:
            config.is_connected = False
            config.connection_status_message = str(e)
            config.save()
            
            return Response({
                'success': False,
                'message': f'Connection failed: {str(e)}',
                'status': 'disconnected'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def disconnect(self, request, pk=None):
        """Disconnect weighbridge"""
        config = self.get_object()
        config.is_connected = False
        config.connection_status_message = "Manually disconnected"
        config.save()
        
        return Response({
            'success': True,
            'message': 'Weighbridge disconnected',
            'status': 'disconnected'
        })


class CameraConfigViewSet(viewsets.ModelViewSet):
    """ViewSet for camera configuration"""
    queryset = CameraConfig.objects.all()
    serializer_class = CameraConfigSerializer
    
    def get_queryset(self):
        queryset = CameraConfig.objects.all()
        
        # Filter by active
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by show on dashboard
        show_on_dashboard = self.request.query_params.get('show_on_dashboard')
        if show_on_dashboard is not None:
            queryset = queryset.filter(show_on_dashboard=show_on_dashboard.lower() == 'true')
        
        # Filter by AI monitoring enabled
        ai_monitoring_enabled = self.request.query_params.get('ai_monitoring_enabled')
        if ai_monitoring_enabled is not None:
            queryset = queryset.filter(ai_monitoring_enabled=ai_monitoring_enabled.lower() == 'true')
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test camera connection"""
        camera = self.get_object()
        
        try:
            # This would integrate with your camera library (OpenCV, etc.)
            # For now, just update status
            camera.is_connected = True
            camera.last_connected = timezone.now()
            camera.connection_status_message = "Camera connected successfully"
            camera.save()
            
            # Create audit log
            create_audit_log(
                weight_record=None,
                action='CAMERA_CONNECTED',
                request=request,
                new_values={
                    'camera': camera.name,
                    'position': camera.position,
                    'ai_monitoring_enabled': camera.ai_monitoring_enabled
                },
                notes=f'Camera {camera.name} connected successfully'
            )
            
            return Response({
                'success': True,
                'message': f'{camera.name} connected successfully',
                'camera': camera.name,
                'position': camera.position,
                'ai_monitoring_enabled': camera.ai_monitoring_enabled,
                'status': 'connected'
            })
        except Exception as e:
            camera.is_connected = False
            camera.connection_status_message = str(e)
            camera.save()
            
            # Create audit log
            create_audit_log(
                weight_record=None,
                action='CAMERA_DISCONNECTED',
                request=request,
                new_values={
                    'camera': camera.name,
                    'error': str(e)
                },
                notes=f'Camera {camera.name} connection failed: {str(e)}'
            )
            
            return Response({
                'success': False,
                'message': f'Camera connection failed: {str(e)}',
                'status': 'disconnected'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def disconnect(self, request, pk=None):
        """Disconnect camera"""
        camera = self.get_object()
        camera.is_connected = False
        camera.connection_status_message = "Manually disconnected"
        camera.save()
        
        return Response({
            'success': True,
            'message': f'{camera.name} disconnected',
            'status': 'disconnected'
        })
    
    @action(detail=True, methods=['post'])
    def enable_ai_monitoring(self, request, pk=None):
        """Enable AI monitoring for this camera"""
        camera = self.get_object()
        camera.ai_monitoring_enabled = True
        camera.save()
        
        # Create audit log
        create_audit_log(
            weight_record=None,
            action='AI_MONITORING_ENABLED',
            request=request,
            new_values={
                'camera': camera.name,
                'ai_monitoring_enabled': True
            },
            notes=f'AI monitoring enabled on camera {camera.name}'
        )
        
        return Response({
            'success': True,
            'message': f'AI monitoring enabled on {camera.name}',
            'ai_monitoring_enabled': True
        })
    
    @action(detail=True, methods=['post'])
    def disable_ai_monitoring(self, request, pk=None):
        """Disable AI monitoring for this camera"""
        camera = self.get_object()
        camera.ai_monitoring_enabled = False
        camera.save()
        
        # Create audit log
        create_audit_log(
            weight_record=None,
            action='AI_MONITORING_DISABLED',
            request=request,
            new_values={
                'camera': camera.name,
                'ai_monitoring_enabled': False
            },
            notes=f'AI monitoring disabled on camera {camera.name}'
        )
        
        return Response({
            'success': True,
            'message': f'AI monitoring disabled on {camera.name}',
            'ai_monitoring_enabled': False
        })
    
    @action(detail=True, methods=['post'])
    def capture_snapshot(self, request, pk=None):
        """Manually trigger camera snapshot"""
        camera = self.get_object()
        weight_record_id = request.data.get('weight_record_id')
        
        if not weight_record_id:
            return Response(
                {'error': 'weight_record_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            weight_record = WeightRecord.objects.get(id=weight_record_id)
            
            # This would integrate with your camera capture logic
            # For now, return success
            
            return Response({
                'success': True,
                'message': f'Snapshot captured from {camera.name}',
                'camera': camera.name,
                'weight_record': weight_record.slip_number
            })
        except WeightRecord.DoesNotExist:
            return Response(
                {'error': 'Weight record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def detection_stats(self, request, pk=None):
        """Get detection statistics for this camera"""
        camera = self.get_object()
        
        # Get today's stats
        today = timezone.now().date()
        today_detections = ObjectDetectionLog.objects.filter(
            camera=camera,
            detected_at__date=today
        )
        
        total_today = today_detections.count()
        authorized_today = today_detections.filter(is_authorized=True).count()
        unauthorized_today = today_detections.filter(is_authorized=False).count()
        alerts_today = UnauthorizedPresenceAlert.objects.filter(
            camera=camera,
            triggered_at__date=today
        ).count()
        
        return Response({
            'camera': camera.name,
            'date': today.isoformat(),
            'total_detections': total_today,
            'authorized_detections': authorized_today,
            'unauthorized_detections': unauthorized_today,
            'alerts_triggered': alerts_today,
            'ai_monitoring_enabled': camera.ai_monitoring_enabled
        })


class PrinterConfigViewSet(viewsets.ModelViewSet):
    """ViewSet for printer configuration"""
    queryset = PrinterConfig.objects.all()
    serializer_class = PrinterConfigSerializer
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test printer connection"""
        printer = self.get_object()
        
        try:
            # This would integrate with your printer library
            # For now, just update status
            printer.is_connected = True
            printer.is_ready = True
            printer.slip_engine_ready = True
            printer.connection_status_message = "Printer ready"
            printer.save()
            
            # Create audit log
            create_audit_log(
                weight_record=None,
                action='PRINTER_READY',
                request=request,
                new_values={
                    'printer': printer.name,
                    'status': 'ready'
                },
                notes=f'Printer {printer.name} is ready'
            )
            
            return Response({
                'success': True,
                'message': f'{printer.name} is ready',
                'printer': printer.name,
                'status': 'ready',
                'slip_engine_ready': True
            })
        except Exception as e:
            printer.is_connected = False
            printer.is_ready = False
            printer.connection_status_message = str(e)
            printer.save()
            
            # Create audit log
            create_audit_log(
                weight_record=None,
                action='PRINTER_NOT_READY',
                request=request,
                new_values={
                    'printer': printer.name,
                    'status': 'not_ready',
                    'error': str(e)
                },
                notes=f'Printer {printer.name} connection failed: {str(e)}'
            )
            
            return Response({
                'success': False,
                'message': f'Printer connection failed: {str(e)}',
                'status': 'not_ready'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def print_test_page(self, request, pk=None):
        """Print a test page"""
        printer = self.get_object()
        
        if not printer.is_ready:
            return Response(
                {'error': 'Printer is not ready'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # This would integrate with your printer library
            # For now, just update last printed time
            printer.last_printed = timezone.now()
            printer.save()
            
            return Response({
                'success': True,
                'message': 'Test page sent to printer',
                'printer': printer.name
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


# ==================== AI MONITORING CONFIGURATION VIEWSET ====================

class AIMonitoringConfigViewSet(viewsets.ModelViewSet):
    """ViewSet for AI monitoring configuration"""
    queryset = AIMonitoringConfig.objects.all()
    serializer_class = AIMonitoringConfigSerializer
    
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """Enable AI monitoring system"""
        config = self.get_object()
        config.is_enabled = True
        config.save()
        
        # Create audit log
        create_audit_log(
            weight_record=None,
            action='AI_MONITORING_ENABLED',
            request=request,
            new_values={
                'config': config.name,
                'is_enabled': True
            },
            notes=f'AI monitoring system "{config.name}" enabled'
        )
        
        return Response({
            'success': True,
            'message': f'AI monitoring system "{config.name}" enabled',
            'is_enabled': True
        })
    
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """Disable AI monitoring system"""
        config = self.get_object()
        config.is_enabled = False
        config.save()
        
        # Create audit log
        create_audit_log(
            weight_record=None,
            action='AI_MONITORING_DISABLED',
            request=request,
            new_values={
                'config': config.name,
                'is_enabled': False
            },
            notes=f'AI monitoring system "{config.name}" disabled'
        )
        
        return Response({
            'success': True,
            'message': f'AI monitoring system "{config.name}" disabled',
            'is_enabled': False
        })
    
    @action(detail=False, methods=['get'])
    def active_config(self, request):
        """Get the active AI monitoring configuration"""
        config = AIMonitoringConfig.objects.filter(is_active=True, is_enabled=True).first()
        
        if not config:
            return Response({
                'message': 'No active AI monitoring configuration found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(config)
        return Response(serializer.data)


# ==================== OBJECT DETECTION LOG VIEWSET ====================

class ObjectDetectionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for object detection logs (read-only, created by detection service)"""
    queryset = ObjectDetectionLog.objects.all()
    serializer_class = ObjectDetectionLogSerializer
    
    def get_queryset(self):
        queryset = ObjectDetectionLog.objects.select_related(
            'camera', 
            'weight_record', 
            'acknowledged_by'
        ).all()
        
        # Filter by camera
        camera_id = self.request.query_params.get('camera_id')
        if camera_id:
            queryset = queryset.filter(camera_id=camera_id)
        
        # Filter by weight record
        weight_record_id = self.request.query_params.get('weight_record_id')
        if weight_record_id:
            queryset = queryset.filter(weight_record_id=weight_record_id)
        
        # Filter by authorized status
        is_authorized = self.request.query_params.get('is_authorized')
        if is_authorized is not None:
            queryset = queryset.filter(is_authorized=is_authorized.lower() == 'true')
        
        # Filter by alert triggered
        alert_triggered = self.request.query_params.get('alert_triggered')
        if alert_triggered is not None:
            queryset = queryset.filter(alert_triggered=alert_triggered.lower() == 'true')
        
        # Filter by object type
        object_type = self.request.query_params.get('object_type')
        if object_type:
            queryset = queryset.filter(object_type=object_type.upper())
        
        # Filter by date
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(detected_at__date=date)
        
        # Limit results
        limit = self.request.query_params.get('limit', 100)
        queryset = queryset[:int(limit)]
        
        return queryset.order_by('-detected_at')
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge a detection alert"""
        detection = self.get_object()
        operator_id = request.data.get('operator_id')
        
        if not operator_id:
            return Response(
                {'error': 'operator_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            operator = Operator.objects.get(id=operator_id)
            detection.acknowledge_alert(operator)
            
            return Response({
                'success': True,
                'message': 'Detection alert acknowledged',
                'acknowledged_by': operator.employee_name,
                'acknowledged_at': detection.acknowledged_at.isoformat()
            })
        except Operator.DoesNotExist:
            return Response(
                {'error': 'Operator not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def recent_unauthorized(self, request):
        """Get recent unauthorized detections"""
        minutes = int(request.query_params.get('minutes', 30))
        cutoff_time = timezone.now() - timezone.timedelta(minutes=minutes)
        
        detections = ObjectDetectionLog.objects.filter(
            is_authorized=False,
            detected_at__gte=cutoff_time
        ).select_related('camera', 'weight_record').order_by('-detected_at')
        
        serializer = self.get_serializer(detections, many=True)
        return Response({
            'count': detections.count(),
            'time_range_minutes': minutes,
            'detections': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get detection statistics"""
        # Get date range
        start_date = request.query_params.get('start_date', timezone.now().date())
        end_date = request.query_params.get('end_date', timezone.now().date())
        
        detections = ObjectDetectionLog.objects.filter(
            detected_at__date__gte=start_date,
            detected_at__date__lte=end_date
        )
        
        total = detections.count()
        authorized = detections.filter(is_authorized=True).count()
        unauthorized = detections.filter(is_authorized=False).count()
        alerts_triggered = detections.filter(alert_triggered=True).count()
        
        # Group by object type
        by_type = {}
        for detection in detections:
            obj_type = detection.get_object_type_display()
            if obj_type not in by_type:
                by_type[obj_type] = 0
            by_type[obj_type] += 1
        
        return Response({
            'date_range': {
                'start': start_date,
                'end': end_date
            },
            'total_detections': total,
            'authorized': authorized,
            'unauthorized': unauthorized,
            'alerts_triggered': alerts_triggered,
            'by_object_type': by_type
        })


# ==================== UNAUTHORIZED PRESENCE ALERT VIEWSET ====================

class UnauthorizedPresenceAlertViewSet(viewsets.ModelViewSet):
    """ViewSet for unauthorized presence alerts"""
    queryset = UnauthorizedPresenceAlert.objects.all()
    serializer_class = UnauthorizedPresenceAlertSerializer
    
    def get_queryset(self):
        queryset = UnauthorizedPresenceAlert.objects.select_related(
            'detection',
            'camera',
            'weight_record',
            'acknowledged_by'
        ).all()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        
        # Filter by severity
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity.upper())
        
        # Filter by camera
        camera_id = self.request.query_params.get('camera_id')
        if camera_id:
            queryset = queryset.filter(camera_id=camera_id)
        
        # Filter by weight record
        weight_record_id = self.request.query_params.get('weight_record_id')
        if weight_record_id:
            queryset = queryset.filter(weight_record_id=weight_record_id)
        
        # Filter by date
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(triggered_at__date=date)
        
        return queryset.order_by('-triggered_at')
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge an alert"""
        alert = self.get_object()
        operator_id = request.data.get('operator_id')
        notes = request.data.get('notes', '')
        
        if not operator_id:
            return Response(
                {'error': 'operator_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            operator = Operator.objects.get(id=operator_id)
            alert.acknowledge(operator, notes)
            
            # Create audit log
            create_audit_log(
                weight_record=alert.weight_record,
                alert=alert,
                detection=alert.detection,
                action='PRESENCE_ALERT_ACKNOWLEDGED',
                request=request,
                new_values={
                    'alert_id': str(alert.alert_id),
                    'acknowledged_by': operator.employee_name,
                    'notes': notes
                },
                notes=f'Alert {alert.alert_id} acknowledged by {operator.employee_name}: {notes}'
            )
            
            serializer = self.get_serializer(alert)
            return Response({
                'success': True,
                'message': 'Alert acknowledged successfully',
                'data': serializer.data
            })
        except Operator.DoesNotExist:
            return Response(
                {'error': 'Operator not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve an alert"""
        alert = self.get_object()
        operator_id = request.data.get('operator_id')
        notes = request.data.get('notes', '')
        
        if not operator_id:
            return Response(
                {'error': 'operator_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            operator = Operator.objects.get(id=operator_id)
            alert.resolve(operator, notes)
            
            # Create audit log
            create_audit_log(
                weight_record=alert.weight_record,
                alert=alert,
                detection=alert.detection,
                action='PRESENCE_ALERT_RESOLVED',
                request=request,
                new_values={
                    'alert_id': str(alert.alert_id),
                    'resolved_by': operator.employee_name,
                    'notes': notes
                },
                notes=f'Alert {alert.alert_id} resolved by {operator.employee_name}: {notes}'
            )
            
            serializer = self.get_serializer(alert)
            return Response({
                'success': True,
                'message': 'Alert resolved successfully',
                'data': serializer.data
            })
        except Operator.DoesNotExist:
            return Response(
                {'error': 'Operator not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def mark_false_positive(self, request, pk=None):
        """Mark alert as false positive"""
        alert = self.get_object()
        operator_id = request.data.get('operator_id')
        notes = request.data.get('notes', '')
        
        if not operator_id:
            return Response(
                {'error': 'operator_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            operator = Operator.objects.get(id=operator_id)
            alert.mark_false_positive(operator, notes)
            
            # Create audit log
            create_audit_log(
                weight_record=alert.weight_record,
                alert=alert,
                detection=alert.detection,
                action='PRESENCE_ALERT_RESOLVED',
                request=request,
                new_values={
                    'alert_id': str(alert.alert_id),
                    'marked_by': operator.employee_name,
                    'status': 'FALSE_POSITIVE',
                    'notes': notes
                },
                notes=f'Alert {alert.alert_id} marked as false positive by {operator.employee_name}: {notes}'
            )
            
            serializer = self.get_serializer(alert)
            return Response({
                'success': True,
                'message': 'Alert marked as false positive',
                'data': serializer.data
            })
        except Operator.DoesNotExist:
            return Response(
                {'error': 'Operator not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def active_alerts(self, request):
        """Get all active alerts"""
        alerts = self.get_queryset().filter(status='ACTIVE')
        serializer = self.get_serializer(alerts, many=True)
        return Response({
            'count': alerts.count(),
            'alerts': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def unresolved_alerts(self, request):
        """Get all unresolved alerts (active + acknowledged)"""
        alerts = self.get_queryset().filter(status__in=['ACTIVE', 'ACKNOWLEDGED'])
        serializer = self.get_serializer(alerts, many=True)
        return Response({
            'count': alerts.count(),
            'alerts': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get alert statistics"""
        # Get date range
        start_date = request.query_params.get('start_date', timezone.now().date())
        end_date = request.query_params.get('end_date', timezone.now().date())
        
        alerts = UnauthorizedPresenceAlert.objects.filter(
            triggered_at__date__gte=start_date,
            triggered_at__date__lte=end_date
        )
        
        total = alerts.count()
        active = alerts.filter(status='ACTIVE').count()
        acknowledged = alerts.filter(status='ACKNOWLEDGED').count()
        resolved = alerts.filter(status='RESOLVED').count()
        false_positives = alerts.filter(status='FALSE_POSITIVE').count()
        
        # Group by severity
        by_severity = {
            'LOW': alerts.filter(severity='LOW').count(),
            'MEDIUM': alerts.filter(severity='MEDIUM').count(),
            'HIGH': alerts.filter(severity='HIGH').count(),
            'CRITICAL': alerts.filter(severity='CRITICAL').count()
        }
        
        return Response({
            'date_range': {
                'start': start_date,
                'end': end_date
            },
            'total_alerts': total,
            'by_status': {
                'active': active,
                'acknowledged': acknowledged,
                'resolved': resolved,
                'false_positive': false_positives
            },
            'by_severity': by_severity
        })


class LiveWeightReadingViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for live weight readings (read-only, created by hardware service)"""
    queryset = LiveWeightReading.objects.all()
    serializer_class = LiveWeightReadingSerializer
    
    def get_queryset(self):
        queryset = LiveWeightReading.objects.select_related('weighbridge_config').all()
        
        # Filter by weighbridge
        weighbridge_id = self.request.query_params.get('weighbridge_id')
        if weighbridge_id:
            queryset = queryset.filter(weighbridge_config_id=weighbridge_id)
        
        # Filter by stability
        is_stable = self.request.query_params.get('is_stable')
        if is_stable is not None:
            queryset = queryset.filter(is_stable=is_stable.lower() == 'true')
        
        # Get latest N readings
        limit = self.request.query_params.get('limit', 100)
        queryset = queryset[:int(limit)]
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Get the latest weight reading"""
        weighbridge_id = request.query_params.get('weighbridge_id')
        
        if weighbridge_id:
            reading = LiveWeightReading.objects.filter(
                weighbridge_config_id=weighbridge_id
            ).order_by('-timestamp').first()
        else:
            reading = LiveWeightReading.objects.order_by('-timestamp').first()
        
        if not reading:
            return Response({
                'weight': 0,
                'is_stable': False,
                'message': 'No readings available'
            })
        
        serializer = self.get_serializer(reading)
        return Response(serializer.data)


# ==================== WEIGHT RECORD VIEWSET WITH AUTOMATION & SECURITY ====================

class WeightRecordViewSet(viewsets.ModelViewSet):
    serializer_class = WeightRecordSerializer

    def get_queryset(self):
        """Filter out soft-deleted weight records"""
        queryset = WeightRecord.objects.select_related(
            'customer', 
            'operator_first_weight', 
            'operator_second_weight', 
            'vehicle'
        ).prefetch_related('photos', 'detections', 'presence_alerts').filter(is_deleted=False)
        
        # Apply filters
        date = self.request.query_params.get('date')
        shift = self.request.query_params.get('shift')
        vehicle = self.request.query_params.get('vehicle')
        customer = self.request.query_params.get('customer')
        operator = self.request.query_params.get('operator')
        status_filter = self.request.query_params.get('status')
        slip_number = self.request.query_params.get('slip_number')
        has_unauthorized = self.request.query_params.get('has_unauthorized_detections')

        if date:
            queryset = queryset.filter(date=date)
        if shift:
            queryset = queryset.filter(shift=shift)
        if vehicle:
            queryset = queryset.filter(vehicle_id=vehicle)
        if customer:
            queryset = queryset.filter(customer_id=customer)
        if operator:
            queryset = queryset.filter(
                operator_first_weight_id=operator
            ) | queryset.filter(
                operator_second_weight_id=operator
            )
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if slip_number:
            queryset = queryset.filter(slip_number__icontains=slip_number)
        if has_unauthorized is not None:
            queryset = queryset.filter(has_unauthorized_detections=has_unauthorized.lower() == 'true')

        return queryset
    
    def perform_create(self, serializer):
        """Override create to add audit log"""
        instance = serializer.save()
        create_audit_log(
            weight_record=instance,
            action='RECORD_SAVED',
            request=self.request,
            new_values=serializer.data,
            notes='Weight record created and saved in database'
        )
    
    def update(self, request, *args, **kwargs):
        """Override update to check date lock"""
        instance = self.get_object()
        
        # Check if date is locked
        try:
            instance.check_date_lock()
        except PermissionDenied as e:
            # Log the denied attempt
            log_security_action(
                user=request.user,
                action='UPDATE_DENIED',
                model_name='WeightRecord',
                record_id=instance.id,
                notes=f'Date lock prevented update: {str(e)}'
            )
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Proceed with normal update
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """Override partial_update to check date lock"""
        instance = self.get_object()
        
        # Check if date is locked
        try:
            instance.check_date_lock()
        except PermissionDenied as e:
            # Log the denied attempt
            log_security_action(
                user=request.user,
                action='UPDATE_DENIED',
                model_name='WeightRecord',
                record_id=instance.id,
                notes=f'Date lock prevented partial update: {str(e)}'
            )
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Proceed with normal partial update
        return super().partial_update(request, *args, **kwargs)
    
    def perform_update(self, serializer):
        """Override update to add audit log"""
        old_instance = self.get_object()
        old_values = WeightRecordSerializer(old_instance).data
        
        instance = serializer.save()
        create_audit_log(
            weight_record=instance,
            action='UPDATE',
            request=self.request,
            old_values=old_values,
            new_values=serializer.data,
            notes='Weight record updated'
        )
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete instead of hard delete"""
        instance = self.get_object()
        
        # Only super admins can delete
        if not request.user.is_superuser:
            log_security_action(
                user=request.user,
                action='DELETE_DENIED',
                model_name='WeightRecord',
                record_id=instance.id,
                notes='Non-superuser attempted to delete weight record'
            )
            raise PermissionDenied("Only super administrators can delete weight records.")
        
        # Check if date is locked
        try:
            instance.check_date_lock()
        except PermissionDenied as e:
            # Log the denied attempt
            log_security_action(
                user=request.user,
                action='DELETE_DENIED',
                model_name='WeightRecord',
                record_id=instance.id,
                notes=f'Date lock prevented delete: {str(e)}'
            )
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Perform soft delete
        old_values = WeightRecordSerializer(instance).data
        instance.deleted_by = request.user
        instance.deleted_at = timezone.now()
        instance.is_deleted = True
        instance.save()
        
        # Log the action
        log_security_action(
            user=request.user,
            action='SOFT_DELETE',
            model_name='WeightRecord',
            record_id=instance.id,
            notes=f'Weight record {instance.slip_number} soft deleted'
        )
        
        create_audit_log(
            weight_record=instance,
            action='DELETE',
            request=request,
            old_values=old_values,
            notes='Weight record soft deleted'
        )
        
        return Response(
            {'message': 'Weight record deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )
    
    # ==================== LIVE WEIGHT MONITORING ====================
    
    @action(detail=True, methods=['post'])
    def update_live_weight(self, request, pk=None):
        """
        Update live weight from weighbridge (called by hardware service)
        Expected payload: {
            "weight": 1500.50,
            "raw_data": "optional raw data from weighbridge"
        }
        """
        weight_record = self.get_object()
        weight = request.data.get('weight')
        
        if weight is None:
            return Response(
                {'error': 'weight is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            weight_record.update_live_weight(Decimal(str(weight)))
            
            return Response({
                'success': True,
                'weight': weight,
                'last_update': weight_record.last_weight_update.isoformat(),
                'message': 'Live weight updated'
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def get_live_weight(self, request, pk=None):
        """Get current live weight for a weight record"""
        weight_record = self.get_object()
        
        return Response({
            'weight': weight_record.current_live_weight,
            'last_update': weight_record.last_weight_update.isoformat() if weight_record.last_weight_update else None,
            'status': weight_record.status
        })
    
    # ==================== SECURITY & DETECTION ENDPOINTS ====================
    
    @action(detail=True, methods=['get'])
    def security_summary(self, request, pk=None):
        """Get security summary including detections and alerts"""
        weight_record = self.get_object()
        
        detections = weight_record.detections.all()
        unauthorized_detections = detections.filter(is_authorized=False)
        alerts = weight_record.presence_alerts.all()
        active_alerts = alerts.filter(status__in=['ACTIVE', 'ACKNOWLEDGED'])
        
        return Response({
            'slip_number': weight_record.slip_number,
            'has_unauthorized_detections': weight_record.has_unauthorized_detections,
            'unauthorized_detection_count': weight_record.unauthorized_detection_count,
            'total_detections': detections.count(),
            'unauthorized_detections': unauthorized_detections.count(),
            'total_alerts': alerts.count(),
            'active_alerts': active_alerts.count(),
            'detections_detail': ObjectDetectionLogSerializer(unauthorized_detections, many=True).data,
            'alerts_detail': UnauthorizedPresenceAlertSerializer(active_alerts, many=True).data
        })
    
    # ==================== VEHICLE MOVEMENT ENDPOINTS ====================
    
    @action(detail=True, methods=['post'])
    def vehicle_leaves(self, request, pk=None):
        """
        Mark that vehicle has left after first weight
        Expected payload: {
            "operator_id": 1 (optional)
        }
        """
        weight_record = self.get_object()
        
        # Validate status
        if weight_record.status != 'FIRST_WEIGHT_CAPTURED':
            return Response(
                {'error': 'Cannot mark vehicle as left. First weight not captured.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            weight_record.mark_vehicle_left()
            
            # Create audit log
            create_audit_log(
                weight_record=weight_record,
                action='VEHICLE_LEFT',
                request=request,
                new_values={
                    'vehicle_left_time': weight_record.vehicle_left_time.isoformat(),
                    'vehicle': weight_record.vehicle.vehicle_number
                },
                notes=f'Vehicle {weight_record.vehicle.vehicle_number} left after first weight'
            )
            
            serializer = self.get_serializer(weight_record)
            return Response({
                'success': True,
                'message': 'Vehicle marked as left',
                'data': serializer.data
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def vehicle_returns(self, request, pk=None):
        """
        Mark that vehicle has returned for second weight
        Expected payload: {
            "operator_id": 1 (optional)
        }
        """
        weight_record = self.get_object()
        
        # Validate status
        if weight_record.status != 'VEHICLE_LEFT':
            return Response(
                {'error': 'Cannot mark vehicle as returned. Vehicle has not left yet.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            weight_record.mark_vehicle_returned()
            
            # Create audit log
            create_audit_log(
                weight_record=weight_record,
                action='VEHICLE_RETURNED',
                request=request,
                new_values={
                    'vehicle_returned_time': weight_record.vehicle_returned_time.isoformat(),
                    'vehicle': weight_record.vehicle.vehicle_number
                },
                notes=f'Vehicle {weight_record.vehicle.vehicle_number} returned for second weight'
            )
            
            serializer = self.get_serializer(weight_record)
            return Response({
                'success': True,
                'message': 'Vehicle marked as returned',
                'data': serializer.data
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # ==================== FIRST WEIGHT ENDPOINTS WITH AUTOMATION ====================
    
    @action(detail=True, methods=['post'])
    def detect_first_weight_stable(self, request, pk=None):
        """
        Detect that first weight is stable (called by hardware service)
        Expected payload: {
            "current_weight": 1500.50,
            "variance": 0.5 (optional),
            "stability_duration": 3.2 (seconds)
        }
        """
        weight_record = self.get_object()
        
        current_weight = request.data.get('current_weight')
        variance = request.data.get('variance', 0)
        stability_duration = request.data.get('stability_duration', 0)
        
        if not current_weight:
            return Response(
                {'error': 'current_weight is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            weight_record.detect_first_weight_stable(stability_duration=stability_duration)
            
            # Create audit log
            create_audit_log(
                weight_record=weight_record,
                action='FIRST_WEIGHT_STABLE_DETECTED',
                request=request,
                new_values={
                    'stable_weight': str(current_weight),
                    'variance': str(variance),
                    'stability_duration': str(stability_duration),
                    'timestamp': weight_record.first_weight_stable_detected_time.isoformat()
                },
                notes=f'First weight stable detected: {current_weight} kg (variance: {variance}, stable for {stability_duration}s)'
            )
            
            # Trigger auto-capture cameras if enabled
            auto_capture_cameras = CameraConfig.objects.filter(
                auto_snapshot_enabled=True,
                snapshot_on_first_weight=True,
                is_active=True,
                is_connected=True
            )
            
            camera_list = [cam.name for cam in auto_capture_cameras]
            
            return Response({
                'success': True,
                'status': 'stable',
                'weight': current_weight,
                'stability_duration': stability_duration,
                'message': 'First weight is stable and ready for capture',
                'auto_capture_cameras': camera_list,
                'camera_count': len(camera_list)
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def capture_first_weight(self, request, pk=None):
        """
        Capture first weight (manual or auto)
        Expected payload: {
            "weight": 1500.50,
            "operator_id": 1,
            "auto_captured": false,
            "images": [base64_encoded_images] (optional),
            "camera_snapshots": [
                {
                    "camera_id": 1,
                    "image": base64_data,
                    "timestamp": "2026-01-27T10:15:42"
                }
            ]
        }
        """
        weight_record = self.get_object()
        
        # Validate status
        valid_statuses = ['FIRST_WEIGHT_PENDING', 'FIRST_WEIGHT_STABLE', 'RECORD_SAVED']
        if weight_record.status not in valid_statuses:
            return Response(
                {'error': f'Cannot capture first weight. Current status: {weight_record.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        weight = request.data.get('weight')
        operator_id = request.data.get('operator_id')
        auto_captured = request.data.get('auto_captured', False)
        
        if not weight or not operator_id:
            return Response(
                {'error': 'Weight and operator_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            operator = Operator.objects.get(id=operator_id)
            
            # Capture first weight
            weight_record.capture_first_weight(
                weight=weight, 
                operator=operator,
                auto_captured=auto_captured
            )
            
            # Handle camera snapshots if provided
            camera_snapshots = request.data.get('camera_snapshots', [])
            saved_photos = []
            
            for snapshot in camera_snapshots:
                camera_id = snapshot.get('camera_id')
                image_data = snapshot.get('image')
                
                if camera_id and image_data:
                    try:
                        camera = CameraConfig.objects.get(id=camera_id)
                        photo = WeightRecordPhoto.objects.create(
                            weight_record=weight_record,
                            camera=camera,
                            photo=image_data,  # You'll need to handle base64 to file conversion
                            photo_type='FIRST_WEIGHT',
                            weight_stage='FIRST',
                            is_auto_captured=auto_captured,
                            captured_weight=weight,
                            timestamp_added=True,
                            caption=f'Auto-captured by {camera.name}' if auto_captured else f'Captured by {camera.name}',
                            uploaded_by=operator
                        )
                        saved_photos.append({
                            'camera': camera.name,
                            'photo_id': photo.id
                        })
                    except CameraConfig.DoesNotExist:
                        pass
            
            # Create audit log
            action_type = 'FIRST_WEIGHT_AUTO_CAPTURED' if auto_captured else 'FIRST_WEIGHT_CAPTURED'
            create_audit_log(
                weight_record=weight_record,
                action=action_type,
                request=request,
                new_values={
                    'first_weight': str(weight),
                    'operator': operator.employee_name,
                    'auto_captured': auto_captured,
                    'photos_captured': len(saved_photos),
                    'cameras': [p['camera'] for p in saved_photos],
                    'timestamp': weight_record.first_weight_time.isoformat()
                },
                notes=f'First weight {"auto-" if auto_captured else ""}captured: {weight} kg by {operator.employee_name}, {len(saved_photos)} photo(s) captured'
            )
            
            # Log photo auto-capture if applicable
            if auto_captured and saved_photos:
                create_audit_log(
                    weight_record=weight_record,
                    action='PHOTO_AUTO_CAPTURED',
                    request=request,
                    new_values={
                        'weight_stage': 'FIRST',
                        'photo_count': len(saved_photos),
                        'cameras': [p['camera'] for p in saved_photos]
                    },
                    notes=f'{len(saved_photos)} photo(s) auto-captured on first weight stability'
                )
            
            serializer = self.get_serializer(weight_record)
            return Response({
                'success': True,
                'message': f'First weight {"auto-" if auto_captured else ""}captured successfully',
                'photos_captured': len(saved_photos),
                'cameras': saved_photos,
                'data': serializer.data
            })
            
        except Operator.DoesNotExist:
            return Response(
                {'error': 'Operator not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # ==================== SECOND WEIGHT ENDPOINTS WITH AUTOMATION ====================
    
    @action(detail=True, methods=['post'])
    def detect_second_weight_stable(self, request, pk=None):
        """
        Detect that second weight is stable (called by hardware service)
        Expected payload: {
            "current_weight": 500.50,
            "variance": 0.5 (optional),
            "stability_duration": 3.2 (seconds)
        }
        """
        weight_record = self.get_object()
        
        current_weight = request.data.get('current_weight')
        variance = request.data.get('variance', 0)
        stability_duration = request.data.get('stability_duration', 0)
        
        if not current_weight:
            return Response(
                {'error': 'current_weight is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            weight_record.detect_second_weight_stable(stability_duration=stability_duration)
            
            # Create audit log
            create_audit_log(
                weight_record=weight_record,
                action='SECOND_WEIGHT_STABLE_DETECTED',
                request=request,
                new_values={
                    'stable_weight': str(current_weight),
                    'variance': str(variance),
                    'stability_duration': str(stability_duration),
                    'timestamp': weight_record.second_weight_stable_detected_time.isoformat()
                },
                notes=f'Second weight stable detected: {current_weight} kg (variance: {variance}, stable for {stability_duration}s)'
            )
            
            # Trigger auto-capture cameras if enabled
            auto_capture_cameras = CameraConfig.objects.filter(
                auto_snapshot_enabled=True,
                snapshot_on_second_weight=True,
                is_active=True,
                is_connected=True
            )
            
            camera_list = [cam.name for cam in auto_capture_cameras]
            
            return Response({
                'success': True,
                'status': 'stable',
                'weight': current_weight,
                'stability_duration': stability_duration,
                'message': 'Second weight is stable and ready for capture',
                'auto_capture_cameras': camera_list,
                'camera_count': len(camera_list)
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def capture_second_weight(self, request, pk=None):
        """
        Capture second weight (manual or auto)
        Expected payload: {
            "weight": 500.50,
            "operator_id": 1,
            "auto_captured": false,
            "images": [base64_encoded_images] (optional),
            "camera_snapshots": [
                {
                    "camera_id": 1,
                    "image": base64_data,
                    "timestamp": "2026-01-27T10:15:42"
                }
            ]
        }
        """
        weight_record = self.get_object()
        
        # Validate status
        valid_statuses = ['VEHICLE_RETURNED', 'SECOND_WEIGHT_PENDING', 'SECOND_WEIGHT_STABLE']
        if weight_record.status not in valid_statuses:
            return Response(
                {'error': f'Cannot capture second weight. Current status: {weight_record.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        weight = request.data.get('weight')
        operator_id = request.data.get('operator_id')
        auto_captured = request.data.get('auto_captured', False)
        
        if not weight or not operator_id:
            return Response(
                {'error': 'Weight and operator_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            operator = Operator.objects.get(id=operator_id)
            
            # Capture second weight (this will auto-calculate weights)
            weight_record.capture_second_weight(
                weight=weight, 
                operator=operator,
                auto_captured=auto_captured
            )
            
            # Handle camera snapshots if provided
            camera_snapshots = request.data.get('camera_snapshots', [])
            saved_photos = []
            
            for snapshot in camera_snapshots:
                camera_id = snapshot.get('camera_id')
                image_data = snapshot.get('image')
                
                if camera_id and image_data:
                    try:
                        camera = CameraConfig.objects.get(id=camera_id)
                        photo = WeightRecordPhoto.objects.create(
                            weight_record=weight_record,
                            camera=camera,
                            photo=image_data,  # You'll need to handle base64 to file conversion
                            photo_type='SECOND_WEIGHT',
                            weight_stage='SECOND',
                            is_auto_captured=auto_captured,
                            captured_weight=weight,
                            timestamp_added=True,
                            caption=f'Auto-captured by {camera.name}' if auto_captured else f'Captured by {camera.name}',
                            uploaded_by=operator
                        )
                        saved_photos.append({
                            'camera': camera.name,
                            'photo_id': photo.id
                        })
                    except CameraConfig.DoesNotExist:
                        pass
            
            # Create audit log
            action_type = 'SECOND_WEIGHT_AUTO_CAPTURED' if auto_captured else 'SECOND_WEIGHT_CAPTURED'
            create_audit_log(
                weight_record=weight_record,
                action=action_type,
                request=request,
                new_values={
                    'second_weight': str(weight),
                    'operator': operator.employee_name,
                    'auto_captured': auto_captured,
                    'photos_captured': len(saved_photos),
                    'cameras': [p['camera'] for p in saved_photos],
                    'timestamp': weight_record.second_weight_time.isoformat(),
                    'gross_weight': str(weight_record.gross_weight),
                    'tare_weight': str(weight_record.tare_weight),
                    'net_weight': str(weight_record.net_weight)
                },
                notes=f'Second weight {"auto-" if auto_captured else ""}captured: {weight} kg by {operator.employee_name}. Net: {weight_record.net_weight} kg, {len(saved_photos)} photo(s) captured'
            )
            
            # Log photo auto-capture if applicable
            if auto_captured and saved_photos:
                create_audit_log(
                    weight_record=weight_record,
                    action='PHOTO_AUTO_CAPTURED',
                    request=request,
                    new_values={
                        'weight_stage': 'SECOND',
                        'photo_count': len(saved_photos),
                        'cameras': [p['camera'] for p in saved_photos]
                    },
                    notes=f'{len(saved_photos)} photo(s) auto-captured on second weight stability'
                )
            
            serializer = self.get_serializer(weight_record)
            return Response({
                'success': True,
                'message': f'Second weight {"auto-" if auto_captured else ""}captured successfully',
                'photos_captured': len(saved_photos),
                'cameras': saved_photos,
                'weights': {
                    'gross': str(weight_record.gross_weight),
                    'tare': str(weight_record.tare_weight),
                    'net': str(weight_record.net_weight)
                },
                'data': serializer.data
            })
            
        except Operator.DoesNotExist:
            return Response(
                {'error': 'Operator not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # ==================== CALCULATION ENDPOINTS ====================
    
    @action(detail=True, methods=['post'])
    def calculate_weights(self, request, pk=None):
        """
        Manually trigger weight calculation (gross, tare, net)
        Usually auto-calculated when second weight is captured
        """
        weight_record = self.get_object()
        
        if not weight_record.first_weight or not weight_record.second_weight:
            return Response(
                {'error': 'Both first and second weights must be captured'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            weight_record.calculate_weights()
            
            # Create audit log
            create_audit_log(
                weight_record=weight_record,
                action='WEIGHTS_CALCULATED',
                request=request,
                new_values={
                    'gross_weight': str(weight_record.gross_weight),
                    'tare_weight': str(weight_record.tare_weight),
                    'net_weight': str(weight_record.net_weight),
                    'timestamp': weight_record.weights_calculated_time.isoformat()
                },
                calculation_details={
                    'first_weight': str(weight_record.first_weight),
                    'second_weight': str(weight_record.second_weight),
                    'gross': str(weight_record.gross_weight),
                    'tare': str(weight_record.tare_weight),
                    'net': str(weight_record.net_weight)
                },
                notes=f'Weights calculated - Gross: {weight_record.gross_weight}, Tare: {weight_record.tare_weight}, Net: {weight_record.net_weight}'
            )
            
            serializer = self.get_serializer(weight_record)
            return Response({
                'success': True,
                'message': 'Weights calculated successfully',
                'data': serializer.data
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def calculate_charges(self, request, pk=None):
        """
        Calculate total charges based on net weight and rate
        Expected payload: {
            "rate_per_unit": 10.50 (optional, uses existing if not provided)
        }
        """
        weight_record = self.get_object()
        
        if not weight_record.net_weight:
            return Response(
                {'error': 'Net weight must be calculated first'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Update rate if provided
            rate_per_unit = request.data.get('rate_per_unit')
            if rate_per_unit:
                weight_record.rate_per_unit = rate_per_unit
                weight_record.save()
            
            weight_record.calculate_charges()
            
            # Create audit log
            create_audit_log(
                weight_record=weight_record,
                action='CHARGES_CALCULATED',
                request=request,
                new_values={
                    'net_weight': str(weight_record.net_weight),
                    'rate_per_unit': str(weight_record.rate_per_unit),
                    'total_amount': str(weight_record.total_amount),
                    'timestamp': weight_record.charges_calculated_time.isoformat()
                },
                calculation_details={
                    'net_weight': str(weight_record.net_weight),
                    'rate': str(weight_record.rate_per_unit),
                    'total': str(weight_record.total_amount),
                    'formula': f'{weight_record.net_weight} × {weight_record.rate_per_unit} = {weight_record.total_amount}'
                },
                notes=f'Charges calculated: {weight_record.net_weight} kg × ₹{weight_record.rate_per_unit} = ₹{weight_record.total_amount}'
            )
            
            serializer = self.get_serializer(weight_record)
            return Response({
                'success': True,
                'message': 'Charges calculated successfully',
                'data': serializer.data
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # ==================== QR AND SLIP ENDPOINTS ====================
    
    @action(detail=True, methods=['post'])
    def generate_qr(self, request, pk=None):
        """
        Generate QR code for payment
        This will be implemented in slip_views.py but we track it here
        """
        weight_record = self.get_object()
        
        if not weight_record.total_amount:
            return Response(
                {'error': 'Charges must be calculated before generating QR'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            weight_record.mark_qr_generated()
            
            # Create audit log
            create_audit_log(
                weight_record=weight_record,
                action='QR_GENERATED',
                request=request,
                new_values={
                    'qr_generated_time': weight_record.qr_generated_time.isoformat(),
                    'amount': str(weight_record.total_amount)
                },
                notes=f'QR code generated for payment of ₹{weight_record.total_amount}'
            )
            
            serializer = self.get_serializer(weight_record)
            return Response({
                'success': True,
                'message': 'QR code generation marked',
                'data': serializer.data
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def print_slip(self, request, pk=None):
        """
        Print slip (manual or auto)
        Expected payload: {
            "printer_id": 1 (optional, uses default if not provided),
            "auto_printed": false,
            "copies": 1
        }
        """
        weight_record = self.get_object()
        printer_id = request.data.get('printer_id')
        auto_printed = request.data.get('auto_printed', False)
        copies = request.data.get('copies', 1)
        
        # Get printer
        if printer_id:
            try:
                printer = PrinterConfig.objects.get(id=printer_id, is_active=True)
            except PrinterConfig.DoesNotExist:
                return Response(
                    {'error': 'Printer not found or inactive'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Get default printer (first ready one)
            printer = PrinterConfig.objects.filter(
                is_active=True,
                is_ready=True,
                slip_engine_ready=True
            ).first()
            
            if not printer:
                return Response(
                    {'error': 'No ready printer available'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            # Mark slip as printed
            weight_record.mark_slip_printed(auto_printed=auto_printed)
            
            # Update printer last printed time
            printer.last_printed = timezone.now()
            printer.save()
            
            # Create audit log
            action_type = 'SLIP_AUTO_PRINTED' if auto_printed else 'SLIP_PRINTED'
            create_audit_log(
                weight_record=weight_record,
                action=action_type,
                request=request,
                new_values={
                    'slip_printed_time': weight_record.slip_printed_time.isoformat(),
                    'printer': printer.name,
                    'auto_printed': auto_printed,
                    'copies': copies,
                    'print_count': weight_record.slip_print_count
                },
                notes=f'Slip {"auto-" if auto_printed else ""}printed on {printer.name} ({copies} {"copy" if copies == 1 else "copies"})'
            )
            
            serializer = self.get_serializer(weight_record)
            return Response({
                'success': True,
                'message': f'Slip {"auto-" if auto_printed else ""}printed successfully',
                'printer': printer.name,
                'copies': copies,
                'print_count': weight_record.slip_print_count,
                'data': serializer.data
            })
            
        except Exception as e:
            # Create failure audit log
            create_audit_log(
                weight_record=weight_record,
                action='SLIP_PRINT_FAILED',
                request=request,
                new_values={
                    'printer': printer.name if printer else 'Unknown',
                    'error': str(e)
                },
                notes=f'Slip print failed: {str(e)}'
            )
            
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def complete_weighment(self, request, pk=None):
        """
        Mark weighment as complete
        Expected payload: {
            "operator_id": 1 (optional),
            "auto_print": true (optional, trigger auto-print if enabled)
        }
        """
        weight_record = self.get_object()
        
        # Validate that all required steps are done
        if not weight_record.first_weight or not weight_record.second_weight:
            return Response(
                {'error': 'Both weights must be captured'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not weight_record.net_weight:
            return Response(
                {'error': 'Weights must be calculated'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            weight_record.mark_completed()
            
            # Check if auto-print should be triggered
            auto_print = request.data.get('auto_print', True)
            slip_printed = False
            printer_name = None
            
            if auto_print:
                # Find printer with auto-print enabled
                auto_printer = PrinterConfig.objects.filter(
                    is_active=True,
                    is_ready=True,
                    slip_engine_ready=True,
                    auto_print_enabled=True,
                    auto_print_on_completion=True
                ).first()
                
                if auto_printer:
                    try:
                        # Trigger auto-print
                        weight_record.mark_slip_printed(auto_printed=True)
                        auto_printer.last_printed = timezone.now()
                        auto_printer.save()
                        slip_printed = True
                        printer_name = auto_printer.name
                        
                        # Create auto-print audit log
                        create_audit_log(
                            weight_record=weight_record,
                            action='SLIP_AUTO_PRINTED',
                            request=request,
                            new_values={
                                'slip_printed_time': weight_record.slip_printed_time.isoformat(),
                                'printer': auto_printer.name,
                                'auto_printed': True,
                                'copies': auto_printer.auto_print_copies
                            },
                            notes=f'Slip auto-printed on completion via {auto_printer.name}'
                        )
                    except Exception as e:
                        # Log print failure but continue with completion
                        create_audit_log(
                            weight_record=weight_record,
                            action='SLIP_PRINT_FAILED',
                            request=request,
                            new_values={
                                'printer': auto_printer.name,
                                'error': str(e)
                            },
                            notes=f'Auto-print failed on completion: {str(e)}'
                        )
            
            # Create completion audit log
            create_audit_log(
                weight_record=weight_record,
                action='WEIGHMENT_COMPLETE',
                request=request,
                new_values={
                    'completed_at': weight_record.completed_at.isoformat(),
                    'slip_number': weight_record.slip_number,
                    'net_weight': str(weight_record.net_weight),
                    'total_amount': str(weight_record.total_amount) if weight_record.total_amount else None,
                    'auto_printed': slip_printed,
                    'printer': printer_name,
                    'has_unauthorized_detections': weight_record.has_unauthorized_detections,
                    'unauthorized_detection_count': weight_record.unauthorized_detection_count
                },
                notes=f'Weighment completed - Slip: {weight_record.slip_number}, Net: {weight_record.net_weight} kg{"(auto-printed)" if slip_printed else ""}{"- SECURITY ALERT: " + str(weight_record.unauthorized_detection_count) + " unauthorized detections" if weight_record.has_unauthorized_detections else ""}'
            )
            
            serializer = self.get_serializer(weight_record)
            return Response({
                'success': True,
                'message': 'Weighment completed successfully',
                'auto_printed': slip_printed,
                'printer': printer_name,
                'security_alert': weight_record.has_unauthorized_detections,
                'unauthorized_detections': weight_record.unauthorized_detection_count,
                'data': serializer.data
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # ==================== PHOTO MANAGEMENT ====================
    
    @action(detail=True, methods=['post'])
    def upload_photos(self, request, pk=None):
        """
        Upload photos for a weight record
        Expected payload: {
            "photos": [
                {
                    "image": base64_or_file,
                    "photo_type": "VEHICLE_FRONT",
                    "weight_stage": "FIRST",
                    "caption": "Front view",
                    "camera_id": 1 (optional),
                    "detection_id": 1 (optional, if photo is from detection)
                }
            ],
            "operator_id": 1
        }
        """
        weight_record = self.get_object()
        photos_data = request.data.get('photos', [])
        operator_id = request.data.get('operator_id')
        
        if not photos_data:
            return Response(
                {'error': 'No photos provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            operator = None
            if operator_id:
                operator = Operator.objects.get(id=operator_id)
            
            uploaded_photos = []
            for photo_data in photos_data:
                camera_id = photo_data.get('camera_id')
                detection_id = photo_data.get('detection_id')
                camera = None
                detection = None
                
                if camera_id:
                    try:
                        camera = CameraConfig.objects.get(id=camera_id)
                    except CameraConfig.DoesNotExist:
                        pass
                
                if detection_id:
                    try:
                        detection = ObjectDetectionLog.objects.get(id=detection_id)
                    except ObjectDetectionLog.DoesNotExist:
                        pass
                
                photo = WeightRecordPhoto.objects.create(
                    weight_record=weight_record,
                    camera=camera,
                    detection=detection,
                    photo=photo_data.get('image'),
                    photo_type=photo_data.get('photo_type', 'OTHER'),
                    weight_stage=photo_data.get('weight_stage', 'FIRST'),
                    caption=photo_data.get('caption', ''),
                    uploaded_by=operator
                )
                uploaded_photos.append(photo)
            
            # Create audit log
            create_audit_log(
                weight_record=weight_record,
                action='PHOTO_UPLOADED',
                request=request,
                new_values={
                    'photo_count': len(uploaded_photos),
                    'operator': operator.employee_name if operator else 'Unknown'
                },
                notes=f'{len(uploaded_photos)} photo(s) uploaded'
            )
            
            serializer = WeightRecordPhotoSerializer(uploaded_photos, many=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Operator.DoesNotExist:
            return Response(
                {'error': 'Operator not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # ==================== QUERY ENDPOINTS ====================
    
    @action(detail=False, methods=['get'])
    def pending_first_weight(self, request):
        """Get all records pending first weight capture"""
        queryset = self.get_queryset().filter(status__in=['RECORD_SAVED', 'FIRST_WEIGHT_PENDING', 'FIRST_WEIGHT_STABLE'])
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_second_weight(self, request):
        """Get all records pending second weight capture"""
        queryset = self.get_queryset().filter(status__in=['VEHICLE_RETURNED', 'SECOND_WEIGHT_PENDING', 'SECOND_WEIGHT_STABLE'])
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def vehicle_left_records(self, request):
        """Get all records where vehicle has left"""
        queryset = self.get_queryset().filter(status='VEHICLE_LEFT')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Get all completed weight records"""
        queryset = self.get_queryset().filter(status='COMPLETED')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def in_progress(self, request):
        """Get all in-progress weight records"""
        in_progress_statuses = [
            'RECORD_SAVED', 'FIRST_WEIGHT_PENDING', 'FIRST_WEIGHT_STABLE',
            'FIRST_WEIGHT_CAPTURED', 'VEHICLE_LEFT', 'VEHICLE_RETURNED',
            'SECOND_WEIGHT_PENDING', 'SECOND_WEIGHT_STABLE', 'SECOND_WEIGHT_CAPTURED',
            'WEIGHTS_CALCULATED', 'CHARGES_CALCULATED', 'QR_GENERATED', 'SLIP_PRINTED'
        ]
        queryset = self.get_queryset().filter(status__in=in_progress_statuses)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def with_security_alerts(self, request):
        """Get all weight records with unauthorized detections"""
        queryset = self.get_queryset().filter(has_unauthorized_detections=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'records': serializer.data
        })


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing audit logs"""
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    
    def get_queryset(self):
        queryset = AuditLog.objects.select_related(
            'weight_record', 
            'payment',
            'detection',
            'alert'
        ).all()
        
        # Filter by weight record
        weight_record_id = self.request.query_params.get('weight_record_id')
        if weight_record_id:
            queryset = queryset.filter(weight_record_id=weight_record_id)
        
        # Filter by slip number
        slip_number = self.request.query_params.get('slip_number')
        if slip_number:
            queryset = queryset.filter(weight_record__slip_number=slip_number)
        
        # Filter by payment
        payment_id = self.request.query_params.get('payment_id')
        if payment_id:
            queryset = queryset.filter(payment__payment_id=payment_id)
        
        # Filter by detection
        detection_id = self.request.query_params.get('detection_id')
        if detection_id:
            queryset = queryset.filter(detection_id=detection_id)
        
        # Filter by alert
        alert_id = self.request.query_params.get('alert_id')
        if alert_id:
            queryset = queryset.filter(alert__alert_id=alert_id)
        
        # Filter by action
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset


class WeightRecordPhotoViewSet(viewsets.ModelViewSet):
    """ViewSet for managing weight record photos"""
    queryset = WeightRecordPhoto.objects.all()
    serializer_class = WeightRecordPhotoSerializer
    
    def get_queryset(self):
        queryset = WeightRecordPhoto.objects.select_related(
            'weight_record', 
            'uploaded_by',
            'camera',
            'detection'
        ).all()
        
        # Filter by weight record
        weight_record_id = self.request.query_params.get('weight_record_id')
        if weight_record_id:
            queryset = queryset.filter(weight_record_id=weight_record_id)
        
        # Filter by weight stage
        weight_stage = self.request.query_params.get('weight_stage')
        if weight_stage:
            queryset = queryset.filter(weight_stage=weight_stage)
        
        # Filter by photo type
        photo_type = self.request.query_params.get('photo_type')
        if photo_type:
            queryset = queryset.filter(photo_type=photo_type)
        
        # Filter by auto-captured
        is_auto_captured = self.request.query_params.get('is_auto_captured')
        if is_auto_captured is not None:
            queryset = queryset.filter(is_auto_captured=is_auto_captured.lower() == 'true')
        
        # Filter by camera
        camera_id = self.request.query_params.get('camera_id')
        if camera_id:
            queryset = queryset.filter(camera_id=camera_id)
        
        # Filter by detection
        detection_id = self.request.query_params.get('detection_id')
        if detection_id:
            queryset = queryset.filter(detection_id=detection_id)
        
        return queryset
    
    def perform_destroy(self, instance):
        """Override delete to add audit log"""
        weight_record = instance.weight_record
        create_audit_log(
            weight_record=weight_record,
            action='PHOTO_DELETED',
            request=self.request,
            old_values={
                'photo_type': instance.photo_type,
                'weight_stage': instance.weight_stage,
                'camera': instance.camera.name if instance.camera else None,
                'detection_linked': instance.detection is not None
            },
            notes=f'Photo deleted: {instance.get_photo_type_display()}'
        )
        instance.delete()