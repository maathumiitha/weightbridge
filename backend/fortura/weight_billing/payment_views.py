# payment_views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from .models import WeightRecord, Payment, QRCode, PaymentSlip, Operator
from .serializers import PaymentSerializer, QRCodeSerializer, PaymentSlipSerializer
from .utils import create_audit_log, generate_upi_string, generate_qr_image

# ==================== SECURITY IMPORTS ====================
from .models_security_data_management import (
    check_date_lock,
    log_security_action
)

# Payment configuration
UPI_ID = "yourbusiness@upi"
MERCHANT_NAME = "Your Business Name"


class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for handling payment operations"""
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    lookup_field = 'payment_id'
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Payment.objects.select_related(
            'weight_record', 
            'weight_record__customer', 
            'weight_record__vehicle'
        ).all()
        
        # Filter by status
        payment_status = self.request.query_params.get('status')
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        
        # Filter by payment method
        payment_method = self.request.query_params.get('method')
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        
        # Filter by weight record
        weight_record_id = self.request.query_params.get('weight_record_id')
        if weight_record_id:
            queryset = queryset.filter(weight_record_id=weight_record_id)
        
        return queryset
    
    @action(detail=False, methods=['post'], url_path='generate-qr')
    def generate_qr(self, request):
        """
        Step 1: Generate UPI QR Code for a weight record
        POST /api/payments/generate-qr/
        Body: {
            "weight_record_id": 1
        }
        """
        try:
            weight_record_id = request.data.get('weight_record_id')
            if not weight_record_id:
                return Response({
                    'success': False,
                    'error': 'weight_record_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            weight_record = get_object_or_404(WeightRecord, id=weight_record_id)
            
            # ==================== SECURITY: DATE LOCK CHECK ====================
            if check_date_lock(weight_record.date, request.user):
                log_security_action(
                    action='DATE_LOCK_ATTEMPT_BLOCKED',
                    user=request.user,
                    weight_record=weight_record,
                    affected_model='Payment',
                    notes=f'Attempt to generate payment QR for locked date: {weight_record.date}',
                    request=request
                )
                raise PermissionDenied(
                    f"Cannot generate payment for record from {weight_record.date}. Date is locked."
                )
            
            # Check if payment already exists
            existing_payment = Payment.objects.filter(
                weight_record=weight_record,
                payment_status__in=['PENDING', 'PROCESSING']
            ).first()
            
            if existing_payment:
                # Return existing QR if available
                qr_code = existing_payment.qr_codes.filter(is_active=True).first()
                if qr_code:
                    return Response({
                        'success': True,
                        'payment_id': str(existing_payment.payment_id),
                        'qr_id': str(qr_code.qr_id),
                        'qr_string': qr_code.qr_string,
                        'qr_image': qr_code.qr_image,
                        'amount': str(existing_payment.amount),
                        'status': existing_payment.payment_status,
                        'customer': weight_record.customer.driver_name,
                        'vehicle': weight_record.vehicle.vehicle_number,
                        'weight_record_id': weight_record.id
                    })
            
            # Create new payment
            payment = Payment.objects.create(
                weight_record=weight_record,
                amount=weight_record.total_amount,
                payment_method='UPI',
                payment_status='PENDING'
            )
            
            # Generate UPI string
            transaction_note = f"Payment for {weight_record.customer.driver_name} - {weight_record.vehicle.vehicle_number}"
            upi_string = generate_upi_string(
                payment_id=str(payment.payment_id),
                amount=str(payment.amount),
                merchant_name=MERCHANT_NAME,
                upi_id=UPI_ID,
                transaction_note=transaction_note
            )
            
            # Generate QR image
            qr_image = generate_qr_image(upi_string)
            
            # Save QR code
            qr_code = QRCode.objects.create(
                payment=payment,
                qr_string=upi_string,
                qr_image=qr_image,
                expires_at=timezone.now() + timezone.timedelta(hours=24)
            )
            
            # Update payment with QR data
            payment.upi_qr_data = upi_string
            payment.save()
            
            # Create audit log
            create_audit_log(
                weight_record=weight_record,
                payment=payment,
                action='QR_GENERATED',
                request=request,
                notes=f"QR generated for payment {payment.payment_id}"
            )
            
            # ==================== SECURITY: AUDIT LOG ====================
            log_security_action(
                action='CREATE',
                user=request.user,
                weight_record=weight_record,
                affected_model='Payment',
                affected_object_id=payment.id,
                new_values={
                    'payment_id': str(payment.payment_id),
                    'amount': str(payment.amount),
                    'payment_method': payment.payment_method,
                    'payment_status': payment.payment_status
                },
                notes=f'Generated payment QR for weight record {weight_record.slip_number}',
                request=request
            )
            
            return Response({
                'success': True,
                'payment_id': str(payment.payment_id),
                'qr_id': str(qr_code.qr_id),
                'qr_string': upi_string,
                'qr_image': qr_image,
                'amount': str(payment.amount),
                'status': payment.payment_status,
                'customer': weight_record.customer.driver_name,
                'vehicle': weight_record.vehicle.vehicle_number,
                'weight_record_id': weight_record.id
            }, status=status.HTTP_201_CREATED)
            
        except WeightRecord.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Weight record not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except PermissionDenied as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='print-slip')
    def print_slip(self, request, payment_id=None):
        """
        Step 2: Print payment slip with QR code
        POST /api/payments/<payment_id>/print-slip/
        Body: {
            "operator_id": 1,
            "printer_name": "Thermal Printer"
        }
        """
        try:
            payment = get_object_or_404(Payment, payment_id=payment_id)
            
            # ==================== SECURITY: DATE LOCK CHECK ====================
            if check_date_lock(payment.weight_record.date, request.user):
                log_security_action(
                    action='DATE_LOCK_ATTEMPT_BLOCKED',
                    user=request.user,
                    weight_record=payment.weight_record,
                    affected_model='PaymentSlip',
                    notes=f'Attempt to print payment slip for locked date: {payment.weight_record.date}',
                    request=request
                )
                raise PermissionDenied(
                    f"Cannot print slip for record from {payment.weight_record.date}. Date is locked."
                )
            
            operator_id = request.data.get('operator_id')
            printer_name = request.data.get('printer_name', '')
            
            operator = None
            if operator_id:
                try:
                    operator = Operator.objects.get(id=operator_id)
                except Operator.DoesNotExist:
                    return Response({
                        'success': False,
                        'error': 'Operator not found'
                    }, status=status.HTTP_404_NOT_FOUND)
            
            # Get QR code
            qr_code = payment.qr_codes.filter(is_active=True).first()
            if not qr_code:
                return Response({
                    'success': False,
                    'error': 'No active QR code found for this payment'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Generate slip number
            slip_count = PaymentSlip.objects.count()
            slip_number = f"SLIP-{timezone.now().strftime('%Y%m%d')}-{slip_count + 1:05d}"
            
            # Create slip content
            slip_content = {
                'slip_number': slip_number,
                'payment_id': str(payment.payment_id),
                'amount': str(payment.amount),
                'customer_driver_name': payment.weight_record.customer.driver_name,
                'vehicle_number': payment.weight_record.vehicle.vehicle_number,
                'material_type': payment.weight_record.material_type,
                'net_weight': str(payment.weight_record.net_weight),
                'date': payment.weight_record.date.strftime('%Y-%m-%d'),
                'qr_image': qr_code.qr_image,
                'printed_at': timezone.now().isoformat()
            }
            
            # Create payment slip
            slip = PaymentSlip.objects.create(
                payment=payment,
                slip_number=slip_number,
                printed_by=operator,
                slip_content=slip_content,
                printer_name=printer_name
            )
            
            # Create audit log
            create_audit_log(
                weight_record=payment.weight_record,
                payment=payment,
                action='SLIP_PRINTED',
                request=request,
                notes=f"Slip {slip_number} printed"
            )
            
            # ==================== SECURITY: AUDIT LOG ====================
            log_security_action(
                action='CREATE',
                user=request.user,
                weight_record=payment.weight_record,
                affected_model='PaymentSlip',
                affected_object_id=slip.id,
                new_values={
                    'slip_id': str(slip.slip_id),
                    'slip_number': slip_number,
                    'payment_id': str(payment.payment_id)
                },
                notes=f'Printed payment slip {slip_number} for payment {payment.payment_id}',
                request=request
            )
            
            return Response({
                'success': True,
                'slip_id': str(slip.slip_id),
                'slip_number': slip_number,
                'slip_content': slip_content
            }, status=status.HTTP_201_CREATED)
            
        except Payment.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Payment not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except PermissionDenied as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='update-status')
    def update_status(self, request, payment_id=None):
        """
        Step 4: Update payment status (manual or webhook)
        POST /api/payments/<payment_id>/update-status/
        Body: {
            "status": "SUCCESS" | "FAILED" | "CANCELLED",
            "transaction_id": "UPI_TRANSACTION_ID",
            "transaction_ref": "BANK_REF",
            "remarks": "Optional remarks"
        }
        """
        try:
            payment = get_object_or_404(Payment, payment_id=payment_id)
            
            # ==================== SECURITY: DATE LOCK CHECK ====================
            if check_date_lock(payment.weight_record.date, request.user):
                log_security_action(
                    action='DATE_LOCK_ATTEMPT_BLOCKED',
                    user=request.user,
                    weight_record=payment.weight_record,
                    affected_model='Payment',
                    affected_object_id=payment.id,
                    notes=f'Attempt to update payment status for locked date: {payment.weight_record.date}',
                    request=request
                )
                raise PermissionDenied(
                    f"Cannot update payment for record from {payment.weight_record.date}. Date is locked."
                )
            
            new_status = request.data.get('status', '').upper()
            transaction_id = request.data.get('transaction_id', '')
            transaction_ref = request.data.get('transaction_ref', '')
            remarks = request.data.get('remarks', '')
            
            if new_status not in ['SUCCESS', 'FAILED', 'CANCELLED']:
                return Response({
                    'success': False,
                    'error': 'Invalid status. Must be SUCCESS, FAILED, or CANCELLED'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            old_status = payment.payment_status
            
            if new_status == 'SUCCESS':
                payment.mark_success(
                    transaction_id=transaction_id,
                    transaction_ref=transaction_ref
                )
                action = 'PAYMENT_SUCCESS'
            elif new_status == 'FAILED':
                payment.mark_failed(reason=remarks)
                action = 'PAYMENT_FAILED'
            else:  # CANCELLED
                payment.payment_status = 'CANCELLED'
                payment.remarks = remarks
                payment.save()
                action = 'PAYMENT_UPDATED'
            
            # Create audit log
            create_audit_log(
                weight_record=payment.weight_record,
                payment=payment,
                action=action,
                request=request,
                old_values={'status': old_status},
                new_values={'status': new_status, 'transaction_id': transaction_id},
                notes=remarks
            )
            
            # ==================== SECURITY: AUDIT LOG ====================
            log_security_action(
                action='UPDATE',
                user=request.user,
                weight_record=payment.weight_record,
                affected_model='Payment',
                affected_object_id=payment.id,
                old_values={
                    'payment_status': old_status
                },
                new_values={
                    'payment_status': new_status,
                    'transaction_id': transaction_id,
                    'transaction_ref': transaction_ref
                },
                notes=f'Updated payment status from {old_status} to {new_status}',
                request=request
            )
            
            return Response({
                'success': True,
                'payment_id': str(payment.payment_id),
                'old_status': old_status,
                'new_status': payment.payment_status,
                'transaction_id': payment.upi_transaction_id,
                'transaction_date': payment.transaction_date
            })
            
        except Payment.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Payment not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except PermissionDenied as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='status')
    def get_status(self, request, payment_id=None):
        """
        Get current payment status
        GET /api/payments/<payment_id>/status/
        """
        try:
            payment = get_object_or_404(Payment, payment_id=payment_id)
            
            return Response({
                'success': True,
                'payment_id': str(payment.payment_id),
                'status': payment.payment_status,
                'amount': str(payment.amount),
                'payment_method': payment.payment_method,
                'transaction_id': payment.upi_transaction_id,
                'transaction_date': payment.transaction_date,
                'created_at': payment.created_at,
                'weight_record': {
                    'id': payment.weight_record.id,
                    'customer': payment.weight_record.customer.driver_name,
                    'vehicle': payment.weight_record.vehicle.vehicle_number,
                    'total_amount': str(payment.weight_record.total_amount)
                }
            })
            
        except Payment.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Payment not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'], url_path='link-to-weighment')
    def link_to_weighment(self, request, payment_id=None):
        """
        Step 5: Link payment to weighment record (already linked during creation)
        POST /api/payments/<payment_id>/link-to-weighment/
        """
        try:
            payment = get_object_or_404(Payment, payment_id=payment_id)
            
            if payment.payment_status != 'SUCCESS':
                return Response({
                    'success': False,
                    'error': 'Payment must be successful before linking',
                    'current_status': payment.payment_status
                }, status=status.HTTP_400_BAD_REQUEST)
            
            weight_record = payment.weight_record
            
            return Response({
                'success': True,
                'payment_id': str(payment.payment_id),
                'weight_record_id': weight_record.id,
                'linked': True,
                'weight_record': {
                    'customer': weight_record.customer.driver_name,
                    'vehicle': weight_record.vehicle.vehicle_number,
                    'date': str(weight_record.date),
                    'total_amount': str(weight_record.total_amount),
                    'payment_status': payment.payment_status
                }
            })
            
        except Payment.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Payment not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class QRCodeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for QR Code operations"""
    queryset = QRCode.objects.all()
    serializer_class = QRCodeSerializer
    lookup_field = 'qr_id'
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = QRCode.objects.select_related('payment').all()
        
        # Filter by payment
        payment_id = self.request.query_params.get('payment_id')
        if payment_id:
            queryset = queryset.filter(payment__payment_id=payment_id)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset
    
    @action(detail=True, methods=['post'], url_path='scan')
    def scan(self, request, qr_id=None):
        """
        Step 3: Customer scans QR code (optional tracking)
        POST /api/qrcodes/<qr_id>/scan/
        """
        try:
            qr_code = get_object_or_404(QRCode, qr_id=qr_id)
            
            # Check if QR is still active
            if not qr_code.is_active:
                return Response({
                    'success': False,
                    'error': 'QR code is no longer active'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if expired
            if qr_code.expires_at and qr_code.expires_at < timezone.now():
                qr_code.is_active = False
                qr_code.save()
                return Response({
                    'success': False,
                    'error': 'QR code has expired'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Mark as scanned
            qr_code.mark_scanned()
            
            # Update payment status to processing
            payment = qr_code.payment
            if payment.payment_status == 'PENDING':
                payment.payment_status = 'PROCESSING'
                payment.save()
            
            # Create audit log
            create_audit_log(
                weight_record=payment.weight_record,
                payment=payment,
                action='PAYMENT_SCANNED',
                request=request,
                notes=f"QR {qr_id} scanned"
            )
            
            # ==================== SECURITY: AUDIT LOG ====================
            log_security_action(
                action='UPDATE',
                user=request.user,
                weight_record=payment.weight_record,
                affected_model='QRCode',
                affected_object_id=qr_code.id,
                new_values={
                    'scan_count': qr_code.scan_count,
                    'payment_status': payment.payment_status
                },
                notes=f'QR code scanned (scan #{qr_code.scan_count}) for payment {payment.payment_id}',
                request=request
            )
            
            return Response({
                'success': True,
                'payment_id': str(payment.payment_id),
                'amount': str(payment.amount),
                'status': payment.payment_status,
                'upi_string': qr_code.qr_string
            })
            
        except QRCode.DoesNotExist:
            return Response({
                'success': False,
                'error': 'QR code not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class PaymentSlipViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Payment Slip operations"""
    queryset = PaymentSlip.objects.all()
    serializer_class = PaymentSlipSerializer
    lookup_field = 'slip_id'
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = PaymentSlip.objects.select_related('payment', 'printed_by').all()
        
        # Filter by payment
        payment_id = self.request.query_params.get('payment_id')
        if payment_id:
            queryset = queryset.filter(payment__payment_id=payment_id)
        
        # Filter by operator
        operator_id = self.request.query_params.get('operator_id')
        if operator_id:
            queryset = queryset.filter(printed_by_id=operator_id)
        
        return queryset