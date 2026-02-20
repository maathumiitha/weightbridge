# utils.py
import qrcode
import base64
from io import BytesIO
from .models import AuditLog


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


def create_audit_log(weight_record, action, request, old_values=None, 
                     new_values=None, notes='', calculation_details=None, payment=None):
    """Create audit log entry"""
    AuditLog.objects.create(
        weight_record=weight_record,
        payment=payment,
        action=action,
        user=request.user.username if request.user.is_authenticated else 'Anonymous',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        old_values=old_values,
        new_values=new_values,
        notes=notes,
        calculation_details=calculation_details
    )


def generate_upi_string(payment_id, amount, merchant_name, upi_id, transaction_note=""):
    """Generate UPI deep link string"""
    upi_string = (
        f"upi://pay?"
        f"pa={upi_id}&"
        f"pn={merchant_name}&"
        f"am={amount}&"
        f"tr={payment_id}&"
        f"cu=INR"
    )
    if transaction_note:
        upi_string += f"&tn={transaction_note}"
    return upi_string


def generate_qr_image(upi_string):
    """Generate QR code image as base64"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_string)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"