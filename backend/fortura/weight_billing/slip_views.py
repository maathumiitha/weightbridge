# slip_views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from django.http import HttpResponse, FileResponse
from django.conf import settings
import qrcode
import io
import base64
from decimal import Decimal

from .models import (
    Payment, QRCode, PaymentSlip, WeightRecord, 
    CompanyDetails, WeightRecordPhoto, Operator
)
from .serializers import (
    PaymentSerializer, QRCodeSerializer, PaymentSlipSerializer,
    WeightRecordPhotoSerializer, CompanyDetailsSerializer
)
from .utils import create_audit_log
from .slip_generator import SlipGenerator  # We'll create this utility


class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing payments"""
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    lookup_field = 'payment_id'
    
    def get_queryset(self):
        queryset = Payment.objects.select_related(
            'weight_record',
            'weight_record__customer',
            'weight_record__vehicle',
            'weight_record__operator_first_weight',
            'weight_record__operator_second_weight'
        ).prefetch_related('qr_codes', 'slips').all()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(payment_status=status_filter)
        
        # Filter by weight record
        weight_record_id = self.request.query_params.get('weight_record_id')
        if weight_record_id:
            queryset = queryset.filter(weight_record_id=weight_record_id)
        
        # Filter by payment method
        payment_method = self.request.query_params.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        
        return queryset
    
    def perform_create(self, serializer):
        """Create payment and log action"""
        payment = serializer.save()
        create_audit_log(
            weight_record=payment.weight_record,
            payment=payment,
            action='PAYMENT_INITIATED',
            request=self.request,
            new_values=serializer.data,
            notes=f'Payment initiated for amount {payment.amount}'
        )
    
    @action(detail=True, methods=['post'])
    def mark_success(self, request, payment_id=None):
        """Mark payment as successful"""
        payment = self.get_object()
        transaction_id = request.data.get('transaction_id', '')
        transaction_ref = request.data.get('transaction_ref', '')
        
        payment.mark_success(transaction_id, transaction_ref)
        
        create_audit_log(
            weight_record=payment.weight_record,
            payment=payment,
            action='PAYMENT_SUCCESS',
            request=request,
            notes=f'Payment marked as successful. Transaction ID: {transaction_id}'
        )
        
        return Response({
            'status': 'success',
            'message': 'Payment marked as successful',
            'payment': PaymentSerializer(payment).data
        })
    
    @action(detail=True, methods=['post'])
    def mark_failed(self, request, payment_id=None):
        """Mark payment as failed"""
        payment = self.get_object()
        reason = request.data.get('reason', 'Payment failed')
        
        payment.mark_failed(reason)
        
        create_audit_log(
            weight_record=payment.weight_record,
            payment=payment,
            action='PAYMENT_FAILED',
            request=request,
            notes=f'Payment marked as failed. Reason: {reason}'
        )
        
        return Response({
            'status': 'success',
            'message': 'Payment marked as failed',
            'payment': PaymentSerializer(payment).data
        })


class QRCodeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing QR codes"""
    queryset = QRCode.objects.all()
    serializer_class = QRCodeSerializer
    lookup_field = 'qr_id'
    
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
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate QR code for a payment"""
        payment_id = request.data.get('payment_id')
        
        try:
            payment = Payment.objects.get(payment_id=payment_id)
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get company details for UPI
        company = CompanyDetails.objects.filter(is_active=True).first()
        if not company or not company.upi_id:
            return Response(
                {'error': 'Company UPI details not configured'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate UPI deep link
        upi_string = self._generate_upi_string(payment, company)
        
        # Generate QR code image
        qr_image_base64 = self._generate_qr_image(upi_string)
        
        # Create QR code record
        qr_code = QRCode.objects.create(
            payment=payment,
            qr_string=upi_string,
            qr_image=qr_image_base64,
            is_active=True
        )
        
        # Update payment with QR data
        payment.upi_qr_data = upi_string
        payment.save()
        
        # Create audit log
        create_audit_log(
            weight_record=payment.weight_record,
            payment=payment,
            action='QR_GENERATED',
            request=request,
            notes=f'QR code generated for payment {payment.payment_id}'
        )
        
        return Response({
            'status': 'success',
            'message': 'QR code generated successfully',
            'qr_code': QRCodeSerializer(qr_code).data
        }, status=status.HTTP_201_CREATED)
    
    def _generate_upi_string(self, payment, company):
        """Generate UPI deep link string"""
        # UPI format: upi://pay?pa=UPI_ID&pn=NAME&am=AMOUNT&tn=NOTE&cu=INR
        upi_id = company.upi_id
        upi_name = company.upi_name or company.company_name
        amount = str(payment.amount)
        note = f"Payment for Weight Record {payment.weight_record.id}"
        
        upi_string = (
            f"upi://pay?"
            f"pa={upi_id}&"
            f"pn={upi_name}&"
            f"am={amount}&"
            f"tn={note}&"
            f"cu=INR"
        )
        
        return upi_string
    
    def _generate_qr_image(self, data):
        """Generate QR code image and return as base64"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return img_str
    
    @action(detail=True, methods=['post'])
    def mark_scanned(self, request, qr_id=None):
        """Mark QR code as scanned"""
        qr_code = self.get_object()
        qr_code.mark_scanned()
        
        create_audit_log(
            weight_record=qr_code.payment.weight_record,
            payment=qr_code.payment,
            action='PAYMENT_SCANNED',
            request=request,
            notes=f'QR code scanned. Scan count: {qr_code.scan_count}'
        )
        
        return Response({
            'status': 'success',
            'message': 'QR code marked as scanned',
            'scan_count': qr_code.scan_count
        })


class PaymentSlipViewSet(viewsets.ModelViewSet):
    """ViewSet for managing payment slips"""
    queryset = PaymentSlip.objects.all()
    serializer_class = PaymentSlipSerializer
    lookup_field = 'slip_id'
    
    def get_queryset(self):
        queryset = PaymentSlip.objects.select_related(
            'payment',
            'payment__weight_record',
            'printed_by',
            'generated_by'
        ).all()
        
        # Filter by payment
        payment_id = self.request.query_params.get('payment_id')
        if payment_id:
            queryset = queryset.filter(payment__payment_id=payment_id)
        
        # Filter by status
        slip_status = self.request.query_params.get('status')
        if slip_status:
            queryset = queryset.filter(slip_status=slip_status)
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Generate a complete payment slip following the workflow:
        1. Pull Data From Database
        2. Fetch Images
        3. Create QR Payment Code
        4. Build Slip Layout
        5. Add Company Details
        6. Add All Weights
        7. Add Time
        8. Add Operator
        9. Add Photos
        10. Generate PDF
        """
        payment_id = request.data.get('payment_id')
        operator_id = request.data.get('operator_id')
        
        try:
            payment = Payment.objects.select_related(
                'weight_record',
                'weight_record__customer',
                'weight_record__vehicle',
                'weight_record__operator_first_weight',
                'weight_record__operator_second_weight'
            ).prefetch_related(
                'weight_record__photos',
                'weight_record__drops'
            ).get(payment_id=payment_id)
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get operator
        operator = None
        if operator_id:
            try:
                operator = Operator.objects.get(id=operator_id)
            except Operator.DoesNotExist:
                pass
        
        try:
            with transaction.atomic():
                # Step 1: Pull Data From Database (already done above)
                weight_record = payment.weight_record
                
                # Step 2: Fetch Images (company logo and weight record photos)
                company = CompanyDetails.objects.filter(is_active=True).first()
                photos = weight_record.photos.all()
                
                # Step 3: Create QR Payment Code (if not exists)
                qr_code = payment.qr_codes.filter(is_active=True).first()
                if not qr_code and company and company.upi_id:
                    # Generate QR code
                    upi_string = self._generate_upi_string(payment, company)
                    qr_image_base64 = self._generate_qr_image(upi_string)
                    
                    qr_code = QRCode.objects.create(
                        payment=payment,
                        qr_string=upi_string,
                        qr_image=qr_image_base64,
                        is_active=True
                    )
                    
                    create_audit_log(
                        weight_record=weight_record,
                        payment=payment,
                        action='QR_GENERATED',
                        request=request,
                        notes='QR code generated during slip generation'
                    )
                
                # Generate unique slip number
                slip_number = self._generate_slip_number(payment)
                
                # Prepare slip data
                slip_data = {
                    'payment': payment,
                    'weight_record': weight_record,
                    'company': company,
                    'qr_code': qr_code,
                    'photos': photos,
                    'operator': operator,
                    'slip_number': slip_number,
                    'generated_at': timezone.now()
                }
                
                # Steps 4-9: Build slip layout with all components
                # This is handled by SlipGenerator utility
                slip_generator = SlipGenerator()
                pdf_content = slip_generator.generate_pdf(slip_data)
                
                # Step 10: Generate PDF and save
                slip = PaymentSlip.objects.create(
                    payment=payment,
                    slip_number=slip_number,
                    slip_status='GENERATED',
                    slip_content=self._create_slip_content_json(slip_data),
                    generated_by=operator
                )
                
                # Save PDF file
                from django.core.files.base import ContentFile
                pdf_filename = f"slip_{slip_number}_{payment.payment_id}.pdf"
                slip.pdf_file.save(pdf_filename, ContentFile(pdf_content))
                
                # Create audit log
                create_audit_log(
                    weight_record=weight_record,
                    payment=payment,
                    action='SLIP_GENERATED',
                    request=request,
                    notes=f'Payment slip generated: {slip_number}'
                )
                
                return Response({
                    'status': 'success',
                    'message': 'Payment slip generated successfully',
                    'slip': PaymentSlipSerializer(slip).data,
                    'pdf_url': slip.pdf_file.url if slip.pdf_file else None
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response(
                {'error': f'Failed to generate slip: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_slip_number(self, payment):
        """Generate unique slip number"""
        now = timezone.now()
        prefix = f"SLP{now.strftime('%Y%m%d')}"
        
        # Get last slip number for today
        last_slip = PaymentSlip.objects.filter(
            slip_number__startswith=prefix
        ).order_by('-slip_number').first()
        
        if last_slip:
            # Extract sequence number and increment
            last_seq = int(last_slip.slip_number.split('-')[-1])
            new_seq = last_seq + 1
        else:
            new_seq = 1
        
        return f"{prefix}-{new_seq:04d}"
    
    def _generate_upi_string(self, payment, company):
        """Generate UPI deep link string"""
        upi_id = company.upi_id
        upi_name = company.upi_name or company.company_name
        amount = str(payment.amount)
        note = f"Payment for Weight Record {payment.weight_record.id}"
        
        upi_string = (
            f"upi://pay?"
            f"pa={upi_id}&"
            f"pn={upi_name}&"
            f"am={amount}&"
            f"tn={note}&"
            f"cu=INR"
        )
        
        return upi_string
    
    def _generate_qr_image(self, data):
        """Generate QR code image and return as base64"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return img_str
    
    def _create_slip_content_json(self, slip_data):
        """Create JSON content for slip"""
        weight_record = slip_data['weight_record']
        payment = slip_data['payment']
        
        content = {
            'slip_number': slip_data['slip_number'],
            'generated_at': slip_data['generated_at'].isoformat(),
            'weight_record': {
                'id': weight_record.id,
                'date': str(weight_record.date),
                'shift': weight_record.shift,
                'gross_weight': str(weight_record.gross_weight),
                'tare_weight': str(weight_record.tare_weight),
                'net_weight': str(weight_record.net_weight),
                'material_type': weight_record.material_type,
                'rate_per_unit': str(weight_record.rate_per_unit),
                'total_amount': str(weight_record.total_amount),
            },
            'customer': {
                'driver_name': weight_record.customer.driver_name,
                'driver_phone': weight_record.customer.driver_phone,
                'address': weight_record.customer.address,
            },
            'vehicle': {
                'number': weight_record.vehicle.vehicle_number,
                'type': weight_record.vehicle.vehicle_type,
            },
            'operators': {
                'first_weight': {
                    'employee_name': weight_record.operator_first_weight.employee_name if weight_record.operator_first_weight else None,
                    'employee_id': weight_record.operator_first_weight.employee_id if weight_record.operator_first_weight else None,
                },
                'second_weight': {
                    'employee_name': weight_record.operator_second_weight.employee_name if weight_record.operator_second_weight else None,
                    'employee_id': weight_record.operator_second_weight.employee_id if weight_record.operator_second_weight else None,
                }
            },
            'payment': {
                'payment_id': str(payment.payment_id),
                'amount': str(payment.amount),
                'payment_method': payment.payment_method,
                'payment_status': payment.payment_status,
            }
        }
        
        return content
    
    @action(detail=True, methods=['post'])
    def print_slip(self, request, slip_id=None):
        """Mark slip as printed"""
        slip = self.get_object()
        
        operator_id = request.data.get('operator_id')
        printer_name = request.data.get('printer_name', '')
        
        operator = None
        if operator_id:
            try:
                operator = Operator.objects.get(id=operator_id)
            except Operator.DoesNotExist:
                pass
        
        slip.mark_printed(operator=operator, printer_name=printer_name)
        
        create_audit_log(
            weight_record=slip.payment.weight_record,
            payment=slip.payment,
            action='SLIP_PRINTED',
            request=request,
            notes=f'Slip {slip.slip_number} printed. Print count: {slip.print_count}'
        )
        
        return Response({
            'status': 'success',
            'message': 'Slip marked as printed',
            'slip': PaymentSlipSerializer(slip).data
        })
    
    @action(detail=True, methods=['get'])
    def download_pdf(self, request, slip_id=None):
        """Download slip PDF"""
        slip = self.get_object()
        
        if not slip.pdf_file:
            return Response(
                {'error': 'PDF file not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        response = FileResponse(slip.pdf_file.open('rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{slip.slip_number}.pdf"'
        
        return response


class WeightRecordPhotoViewSet(viewsets.ModelViewSet):
    """ViewSet for managing weight record photos"""
    queryset = WeightRecordPhoto.objects.all()
    serializer_class = WeightRecordPhotoSerializer
    
    def get_queryset(self):
        queryset = WeightRecordPhoto.objects.select_related('weight_record', 'uploaded_by').all()
        
        # Filter by weight record
        weight_record_id = self.request.query_params.get('weight_record_id')
        if weight_record_id:
            queryset = queryset.filter(weight_record_id=weight_record_id)
        
        # Filter by photo type
        photo_type = self.request.query_params.get('photo_type')
        if photo_type:
            queryset = queryset.filter(photo_type=photo_type)
        
        return queryset
    
    def perform_create(self, serializer):
        """Create photo and log action"""
        photo = serializer.save()
        
        create_audit_log(
            weight_record=photo.weight_record,
            action='PHOTO_UPLOADED',
            request=self.request,
            notes=f'Photo uploaded: {photo.get_photo_type_display()}'
        )
    
    def perform_destroy(self, instance):
        """Delete photo and log action"""
        create_audit_log(
            weight_record=instance.weight_record,
            action='PHOTO_DELETED',
            request=self.request,
            notes=f'Photo deleted: {instance.get_photo_type_display()}'
        )
        instance.delete()


class CompanyDetailsViewSet(viewsets.ModelViewSet):
    """ViewSet for managing company details"""
    queryset = CompanyDetails.objects.all()
    serializer_class = CompanyDetailsSerializer
    
    def get_queryset(self):
        # Return only active company
        return CompanyDetails.objects.filter(is_active=True)