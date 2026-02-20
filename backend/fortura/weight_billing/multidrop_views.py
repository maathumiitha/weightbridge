# multidrop_views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.core.exceptions import PermissionDenied
from .models import WeightRecord, WeightDrop
from .serializers import (
    MultiDropCreateSerializer, WeightDropSerializer, 
    MultiDropSummarySerializer
)
from .utils import create_audit_log

# ==================== SECURITY IMPORTS ====================
from .models_security_data_management import (
    check_date_lock,
    log_security_action
)


class MultiDropViewSet(viewsets.ViewSet):
    """
    ViewSet for handling multi-drop weight records.
    Enhanced with security features: date lock checking and audit logging.
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def create_drops(self, request):
        """
        Create multiple drops for a weight record.
        
        Security:
        - Checks date lock before creating drops
        - Logs all drop creation actions
        """
        serializer = MultiDropCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        weight_record_id = serializer.validated_data['weight_record_id']
        drops_data = serializer.validated_data['drops']
        
        try:
            weight_record = WeightRecord.objects.get(id=weight_record_id)
            
            # ==================== SECURITY: DATE LOCK CHECK ====================
            # Check if the weight record's date is locked
            if check_date_lock(weight_record.date, request.user):
                log_security_action(
                    action='DATE_LOCK_ATTEMPT_BLOCKED',
                    user=request.user,
                    weight_record=weight_record,
                    affected_model='WeightDrop',
                    notes=f'Attempt to create drops for locked date: {weight_record.date}',
                    request=request
                )
                raise PermissionDenied(
                    f"Cannot create drops for record from {weight_record.date}. Date is locked."
                )
            
            with transaction.atomic():
                # Mark as multi-drop
                weight_record.is_multi_drop = True
                weight_record.save()
                
                # Create drops
                created_drops = []
                for idx, drop_data in enumerate(drops_data, 1):
                    drop = WeightDrop.objects.create(
                        weight_record=weight_record,
                        drop_number=idx,
                        gross_weight=drop_data['gross_weight'],
                        tare_weight=drop_data['tare_weight'],
                        remarks=drop_data.get('remarks', '')
                    )
                    created_drops.append(drop)
                
                # Recalculate total
                weight_record.calculate_from_drops()
                
                # Create regular audit log
                create_audit_log(
                    weight_record=weight_record,
                    action='MULTI_DROP_ADD',
                    request=request,
                    calculation_details={
                        'total_drops': len(created_drops),
                        'drops': [
                            {
                                'drop_number': d.drop_number,
                                'gross': str(d.gross_weight),
                                'tare': str(d.tare_weight),
                                'net': str(d.net_weight)
                            } for d in created_drops
                        ]
                    },
                    notes=f'Created {len(created_drops)} drops'
                )
                
                # ==================== SECURITY: AUDIT LOG ====================
                # Log the multi-drop creation in security audit
                log_security_action(
                    action='CREATE',
                    user=request.user,
                    weight_record=weight_record,
                    affected_model='WeightDrop',
                    new_values={
                        'total_drops': len(created_drops),
                        'total_net_weight': str(weight_record.net_weight),
                        'total_amount': str(weight_record.total_amount)
                    },
                    notes=f'Created {len(created_drops)} drops for weight record {weight_record.slip_number}',
                    request=request
                )
                
                # Prepare response
                drops_serializer = WeightDropSerializer(created_drops, many=True)
                return Response({
                    'weight_record_id': weight_record.id,
                    'drops': drops_serializer.data,
                    'total_net_weight': weight_record.net_weight,
                    'total_amount': weight_record.total_amount
                }, status=status.HTTP_201_CREATED)
                
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
    
    @action(detail=False, methods=['post'])
    def add_drop(self, request):
        """
        Add a single drop to existing multi-drop record.
        
        Security:
        - Checks date lock before adding drop
        - Logs drop addition action
        """
        weight_record_id = request.data.get('weight_record_id')
        gross_weight = request.data.get('gross_weight')
        tare_weight = request.data.get('tare_weight')
        remarks = request.data.get('remarks', '')
        
        try:
            weight_record = WeightRecord.objects.get(id=weight_record_id)
            
            # ==================== SECURITY: DATE LOCK CHECK ====================
            if check_date_lock(weight_record.date, request.user):
                log_security_action(
                    action='DATE_LOCK_ATTEMPT_BLOCKED',
                    user=request.user,
                    weight_record=weight_record,
                    affected_model='WeightDrop',
                    notes=f'Attempt to add drop for locked date: {weight_record.date}',
                    request=request
                )
                raise PermissionDenied(
                    f"Cannot add drop for record from {weight_record.date}. Date is locked."
                )
            
            # Get next drop number
            last_drop = weight_record.drops.order_by('-drop_number').first()
            next_drop_number = (last_drop.drop_number + 1) if last_drop else 1
            
            with transaction.atomic():
                # Create new drop
                drop = WeightDrop.objects.create(
                    weight_record=weight_record,
                    drop_number=next_drop_number,
                    gross_weight=gross_weight,
                    tare_weight=tare_weight,
                    remarks=remarks
                )
                
                # Mark as multi-drop if not already
                if not weight_record.is_multi_drop:
                    weight_record.is_multi_drop = True
                    weight_record.save()
                
                # Recalculate total
                weight_record.calculate_from_drops()
                
                # Create regular audit log
                create_audit_log(
                    weight_record=weight_record,
                    action='MULTI_DROP_ADD',
                    request=request,
                    calculation_details={
                        'drop_number': drop.drop_number,
                        'gross': str(drop.gross_weight),
                        'tare': str(drop.tare_weight),
                        'net': str(drop.net_weight)
                    },
                    notes=f'Added drop #{drop.drop_number}'
                )
                
                # ==================== SECURITY: AUDIT LOG ====================
                log_security_action(
                    action='CREATE',
                    user=request.user,
                    weight_record=weight_record,
                    affected_model='WeightDrop',
                    affected_object_id=drop.id,
                    new_values={
                        'drop_number': drop.drop_number,
                        'gross_weight': str(drop.gross_weight),
                        'tare_weight': str(drop.tare_weight),
                        'net_weight': str(drop.net_weight)
                    },
                    notes=f'Added drop #{drop.drop_number} to weight record {weight_record.slip_number}',
                    request=request
                )
                
                serializer = WeightDropSerializer(drop)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
                
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
    
    @action(detail=True, methods=['get'])
    def get_drops(self, request, pk=None):
        """
        Get all drops for a weight record.
        No security restrictions for reading.
        """
        try:
            weight_record = WeightRecord.objects.get(id=pk)
            drops = weight_record.drops.all()
            
            # Calculate summary
            total_gross = sum(drop.gross_weight for drop in drops)
            total_tare = sum(drop.tare_weight for drop in drops)
            total_net = sum(drop.net_weight for drop in drops)
            
            summary_data = {
                'weight_record_id': weight_record.id,
                'total_drops': drops.count(),
                'drops': WeightDropSerializer(drops, many=True).data,
                'total_gross_weight': total_gross,
                'total_tare_weight': total_tare,
                'total_net_weight': total_net,
                'final_amount': weight_record.total_amount
            }
            
            serializer = MultiDropSummarySerializer(data=summary_data)
            serializer.is_valid(raise_exception=True)
            
            return Response(serializer.data)
            
        except WeightRecord.DoesNotExist:
            return Response(
                {'error': 'Weight record not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def calculate_total(self, request):
        """
        Calculate total from all drops.
        
        Security:
        - Checks date lock before recalculation
        - Logs recalculation action
        """
        weight_record_id = request.data.get('weight_record_id')
        
        try:
            weight_record = WeightRecord.objects.get(id=weight_record_id)
            
            if not weight_record.is_multi_drop:
                return Response(
                    {'error': 'This is not a multi-drop record'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # ==================== SECURITY: DATE LOCK CHECK ====================
            if check_date_lock(weight_record.date, request.user):
                log_security_action(
                    action='DATE_LOCK_ATTEMPT_BLOCKED',
                    user=request.user,
                    weight_record=weight_record,
                    affected_model='WeightDrop',
                    notes=f'Attempt to recalculate drops for locked date: {weight_record.date}',
                    request=request
                )
                raise PermissionDenied(
                    f"Cannot recalculate drops for record from {weight_record.date}. Date is locked."
                )
            
            # Store old values for audit
            old_net_weight = weight_record.net_weight
            old_total_amount = weight_record.total_amount
            
            # Recalculate from drops
            total_net = weight_record.calculate_from_drops()
            
            # Create regular audit log
            create_audit_log(
                weight_record=weight_record,
                action='MULTI_DROP_CALCULATE',
                request=request,
                calculation_details={
                    'total_drops': weight_record.drops.count(),
                    'calculated_net_weight': str(total_net),
                    'total_amount': str(weight_record.total_amount)
                },
                notes='Multi-drop total recalculated'
            )
            
            # ==================== SECURITY: AUDIT LOG ====================
            log_security_action(
                action='UPDATE',
                user=request.user,
                weight_record=weight_record,
                affected_model='WeightRecord',
                affected_object_id=weight_record.id,
                old_values={
                    'net_weight': str(old_net_weight),
                    'total_amount': str(old_total_amount)
                },
                new_values={
                    'net_weight': str(weight_record.net_weight),
                    'total_amount': str(weight_record.total_amount)
                },
                notes=f'Recalculated multi-drop totals for {weight_record.slip_number}',
                request=request
            )
            
            return Response({
                'weight_record_id': weight_record.id,
                'total_drops': weight_record.drops.count(),
                'total_net_weight': weight_record.net_weight,
                'total_amount': weight_record.total_amount
            })
            
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
    
    @action(detail=False, methods=['delete'])
    def delete_drop(self, request):
        """
        Delete a specific drop.
        
        Security:
        - Checks date lock before deletion
        - Requires super admin for deletion (via soft delete check)
        - Logs deletion action
        """
        drop_id = request.data.get('drop_id')
        
        try:
            drop = WeightDrop.objects.get(id=drop_id)
            weight_record = drop.weight_record
            drop_number = drop.drop_number
            
            # ==================== SECURITY: DATE LOCK CHECK ====================
            if check_date_lock(weight_record.date, request.user):
                log_security_action(
                    action='DATE_LOCK_ATTEMPT_BLOCKED',
                    user=request.user,
                    weight_record=weight_record,
                    affected_model='WeightDrop',
                    affected_object_id=drop.id,
                    notes=f'Attempt to delete drop #{drop_number} for locked date: {weight_record.date}',
                    request=request
                )
                raise PermissionDenied(
                    f"Cannot delete drop for record from {weight_record.date}. Date is locked."
                )
            
            # ==================== SECURITY: PERMISSION CHECK ====================
            # Only super admins can delete drops
            if not request.user.is_superuser:
                log_security_action(
                    action='PERMISSION_DENIED',
                    user=request.user,
                    weight_record=weight_record,
                    affected_model='WeightDrop',
                    affected_object_id=drop.id,
                    notes=f'Non-superuser attempted to delete drop #{drop_number}',
                    request=request
                )
                raise PermissionDenied("Only super admins can delete drops")
            
            # Store drop info for audit
            drop_info = {
                'drop_number': drop.drop_number,
                'gross_weight': str(drop.gross_weight),
                'tare_weight': str(drop.tare_weight),
                'net_weight': str(drop.net_weight)
            }
            
            with transaction.atomic():
                drop.delete()
                
                # Recalculate total
                weight_record.calculate_from_drops()
                
                # Renumber remaining drops
                remaining_drops = weight_record.drops.order_by('drop_number')
                for idx, remaining_drop in enumerate(remaining_drops, 1):
                    if remaining_drop.drop_number != idx:
                        remaining_drop.drop_number = idx
                        remaining_drop.save()
                
                # Create regular audit log
                create_audit_log(
                    weight_record=weight_record,
                    action='DELETE',
                    request=request,
                    notes=f'Deleted drop #{drop_number}'
                )
                
                # ==================== SECURITY: AUDIT LOG ====================
                log_security_action(
                    action='DELETE',
                    user=request.user,
                    weight_record=weight_record,
                    affected_model='WeightDrop',
                    affected_object_id=drop_id,
                    old_values=drop_info,
                    notes=f'Deleted drop #{drop_number} from weight record {weight_record.slip_number}',
                    request=request
                )
                
                return Response({
                    'message': f'Drop #{drop_number} deleted successfully',
                    'remaining_drops': weight_record.drops.count(),
                    'new_total_net_weight': weight_record.net_weight
                })
                
        except WeightDrop.DoesNotExist:
            return Response(
                {'error': 'Drop not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDenied as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )