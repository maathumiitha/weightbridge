# calculation_views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import PermissionDenied
from decimal import Decimal
from .models import WeightRecord
from .serializers import CalculationSerializer, WeightRecordSerializer
from .utils import create_audit_log

# ==================== SECURITY IMPORTS ====================
from .models_security_data_management import (
    check_date_lock,
    log_security_action
)


class CalculationViewSet(viewsets.ViewSet):
    """ViewSet for handling weight calculations"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def calculate_weight(self, request):
        """Calculate net weight from gross and tare weights"""
        serializer = CalculationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        gross = Decimal(str(serializer.validated_data['gross_weight']))
        tare = Decimal(str(serializer.validated_data['tare_weight']))
        net = gross - tare
        
        result = {
            'gross_weight': gross,
            'tare_weight': tare,
            'net_weight': net
        }
        
        # Calculate total amount if rate is provided
        if 'rate_per_unit' in serializer.validated_data:
            rate = Decimal(str(serializer.validated_data['rate_per_unit']))
            total = net * rate
            result['rate_per_unit'] = rate
            result['total_amount'] = total
        
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def recalculate_record(self, request):
        """Recalculate a weight record"""
        record_id = request.data.get('record_id')
        
        try:
            record = WeightRecord.objects.get(id=record_id)
            
            # ==================== SECURITY: DATE LOCK CHECK ====================
            if check_date_lock(record.date, request.user):
                log_security_action(
                    action='DATE_LOCK_ATTEMPT_BLOCKED',
                    user=request.user,
                    weight_record=record,
                    affected_model='WeightRecord',
                    affected_object_id=record.id,
                    notes=f'Attempt to recalculate record for locked date: {record.date}',
                    request=request
                )
                raise PermissionDenied(
                    f"Cannot recalculate record from {record.date}. Date is locked."
                )
            
            old_net = record.net_weight
            old_amount = record.total_amount
            
            # Recalculate
            record.net_weight = record.gross_weight - record.tare_weight
            record.total_amount = record.net_weight * record.rate_per_unit
            record.save()
            
            # Create audit log
            create_audit_log(
                weight_record=record,
                action='CALCULATE',
                request=request,
                calculation_details={
                    'old_net_weight': str(old_net),
                    'new_net_weight': str(record.net_weight),
                    'old_total_amount': str(old_amount),
                    'new_total_amount': str(record.total_amount)
                },
                notes='Weight record recalculated'
            )
            
            # ==================== SECURITY: AUDIT LOG ====================
            log_security_action(
                action='UPDATE',
                user=request.user,
                weight_record=record,
                affected_model='WeightRecord',
                affected_object_id=record.id,
                old_values={
                    'net_weight': str(old_net),
                    'total_amount': str(old_amount)
                },
                new_values={
                    'net_weight': str(record.net_weight),
                    'total_amount': str(record.total_amount)
                },
                notes=f'Recalculated weight record {record.slip_number}',
                request=request
            )
            
            serializer = WeightRecordSerializer(record)
            return Response(serializer.data)
            
        except WeightRecord.DoesNotExist:
            return Response(
                {'error': 'Weight record not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDenied as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )