import os
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fortura.settings")  # Change 'your_project' to your actual project name
django.setup()

from weight_billing.models import (
    Customer, Operator, Vehicle, WeighbridgeConfig, LiveWeightReading,
    CameraConfig, PrinterConfig, CompanyDetails, WeightRecord, WeightDrop,
    WeightRecordPhoto, Payment, QRCode, PaymentSlip, AuditLog
)

def print_separator(title=""):
    """Print a nice separator line"""
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}")
    else:
        print(f"{'-'*80}")

def show_customers():
    """Display all customers"""
    print_separator("CUSTOMERS")
    customers = Customer.objects.all()
    print(f"Total: {customers.count()}\n")
    
    for c in customers:
        print(f"ID: {c.id} | Name: {c.name} | Phone: {c.phone} | Email: {c.email}")
        print(f"  Address: {c.address}")
        print(f"  Created: {c.created_at.strftime('%Y-%m-%d %H:%M')}")
        print_separator()

def show_operators():
    """Display all operators"""
    print_separator("OPERATORS")
    operators = Operator.objects.all()
    print(f"Total: {operators.count()}\n")
    
    for o in operators:
        status = "Active" if o.is_active else "Inactive"
        print(f"ID: {o.id} | Name: {o.name} | Emp ID: {o.employee_id} | Status: {status}")
        print(f"  Phone: {o.phone}")
        print(f"  Created: {o.created_at.strftime('%Y-%m-%d %H:%M')}")
        print_separator()

def show_vehicles():
    """Display all vehicles"""
    print_separator("VEHICLES")
    vehicles = Vehicle.objects.all()
    print(f"Total: {vehicles.count()}\n")
    
    for v in vehicles:
        status = "Active" if v.is_active else "Inactive"
        print(f"ID: {v.id} | Number: {v.vehicle_number} | Type: {v.vehicle_type} | Status: {status}")
        print(f"  Capacity: {v.capacity} kg")
        print(f"  Created: {v.created_at.strftime('%Y-%m-%d %H:%M')}")
        print_separator()

def show_weighbridge_config():
    """Display weighbridge configurations"""
    print_separator("WEIGHBRIDGE CONFIGURATIONS")
    configs = WeighbridgeConfig.objects.all()
    print(f"Total: {configs.count()}\n")
    
    for w in configs:
        conn_status = "Connected" if w.is_connected else "Disconnected"
        print(f"ID: {w.id} | Name: {w.name} | Status: {conn_status}")
        print(f"  Port: {w.port} | Baud: {w.baud_rate} | Parity: {w.parity}")
        print(f"  Stability Threshold: {w.stability_threshold} kg | Duration: {w.stability_duration}s")
        print(f"  Auto-capture: {'Enabled' if w.auto_capture_enabled else 'Disabled'} | Delay: {w.auto_capture_delay}s")
        if w.last_connected:
            print(f"  Last Connected: {w.last_connected.strftime('%Y-%m-%d %H:%M:%S')}")
        print_separator()

def show_live_weight_readings():
    """Display recent live weight readings"""
    print_separator("LIVE WEIGHT READINGS")
    readings = LiveWeightReading.objects.all()
    print(f"Total: {readings.count()} | Showing: Last 20\n")
    
    for r in readings[:20]:
        stable = "STABLE" if r.is_stable else "UNSTABLE"
        print(f"Weight: {r.weight} kg | Status: {stable} | Duration: {r.stability_duration}s")
        print(f"  Timestamp: {r.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        if r.raw_data:
            print(f"  Raw Data: {r.raw_data[:100]}")
        print_separator()

def show_camera_config():
    """Display camera configurations"""
    print_separator("CAMERA CONFIGURATIONS")
    cameras = CameraConfig.objects.all()
    print(f"Total: {cameras.count()}\n")
    
    for c in cameras:
        conn_status = "Connected" if c.is_connected else "Disconnected"
        active = "Active" if c.is_active else "Inactive"
        print(f"ID: {c.id} | Name: {c.name} | Position: {c.get_position_display()} | Status: {active} | Connection: {conn_status}")
        print(f"  Type: {c.get_camera_type_display()} | Index: {c.camera_index}")
        if c.rtsp_url:
            print(f"  RTSP URL: {c.rtsp_url}")
        print(f"  Resolution: {c.resolution_width}x{c.resolution_height} | Quality: {c.jpeg_quality}%")
        print(f"  Auto-snapshot: {'Enabled' if c.auto_snapshot_enabled else 'Disabled'}")
        print_separator()

def show_printer_config():
    """Display printer configurations"""
    print_separator("PRINTER CONFIGURATIONS")
    printers = PrinterConfig.objects.all()
    print(f"Total: {printers.count()}\n")
    
    for p in printers:
        ready = "Ready" if p.is_ready else "Not Ready"
        conn_status = "Connected" if p.is_connected else "Disconnected"
        print(f"ID: {p.id} | Name: {p.name} | Type: {p.get_printer_type_display()} | Status: {ready} | Connection: {conn_status}")
        print(f"  Printer Name: {p.printer_name} | Paper: {p.get_paper_size_display()}")
        if p.ip_address:
            print(f"  IP: {p.ip_address}:{p.port}")
        print(f"  Auto-print: {'Enabled' if p.auto_print_enabled else 'Disabled'} | Copies: {p.auto_print_copies}")
        if p.last_printed:
            print(f"  Last Printed: {p.last_printed.strftime('%Y-%m-%d %H:%M:%S')}")
        print_separator()

def show_company_details():
    """Display company details"""
    print_separator("COMPANY DETAILS")
    companies = CompanyDetails.objects.all()
    print(f"Total: {companies.count()}\n")
    
    for c in companies:
        print(f"Company: {c.company_name}")
        print(f"Address: {c.company_address}")
        print(f"Phone: {c.company_phone} | Email: {c.company_email}")
        if c.gstin:
            print(f"GSTIN: {c.gstin} | PAN: {c.pan}")
        if c.upi_id:
            print(f"UPI ID: {c.upi_id} | UPI Name: {c.upi_name}")
        if c.bank_name:
            print(f"Bank: {c.bank_name} | Account: {c.account_number} | IFSC: {c.ifsc_code}")
        print_separator()

def show_weight_records():
    """Display weight records"""
    print_separator("WEIGHT RECORDS")
    records = WeightRecord.objects.all()
    print(f"Total: {records.count()} | Showing: Last 20\n")
    
    for wr in records[:20]:
        print(f"Slip: {wr.slip_number} | Status: {wr.get_status_display()}")
        print(f"  Customer: {wr.customer.name} | Vehicle: {wr.vehicle.vehicle_number}")
        print(f"  Date: {wr.date} | Shift: {wr.get_shift_display()} | Material: {wr.material_type}")
        
        if wr.first_weight:
            auto_1 = "Auto" if wr.first_weight_auto_captured else "Manual"
            print(f"  1st Weight: {wr.first_weight} kg | Capture: {auto_1} | Time: {wr.first_weight_time.strftime('%H:%M:%S') if wr.first_weight_time else 'N/A'}")
        
        if wr.second_weight:
            auto_2 = "Auto" if wr.second_weight_auto_captured else "Manual"
            print(f"  2nd Weight: {wr.second_weight} kg | Capture: {auto_2} | Time: {wr.second_weight_time.strftime('%H:%M:%S') if wr.second_weight_time else 'N/A'}")
        
        if wr.net_weight:
            print(f"  Gross: {wr.gross_weight} kg | Tare: {wr.tare_weight} kg | Net: {wr.net_weight} kg")
        
        if wr.total_amount:
            print(f"  Rate: Rs.{wr.rate_per_unit}/kg | Total: Rs.{wr.total_amount}")
        
        if wr.current_live_weight:
            print(f"  Live Weight: {wr.current_live_weight} kg")
        
        if wr.is_multi_drop:
            print(f"  Multi-Drop Record: Yes")
        
        print(f"  Created: {wr.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print_separator()

def show_weight_drops():
    """Display weight drops"""
    print_separator("WEIGHT DROPS")
    drops = WeightDrop.objects.all()
    print(f"Total: {drops.count()} | Showing: Last 20\n")
    
    for d in drops[:20]:
        print(f"Record: {d.weight_record.slip_number} | Drop Number: {d.drop_number}")
        print(f"  Gross: {d.gross_weight} kg | Tare: {d.tare_weight} kg | Net: {d.net_weight} kg")
        print(f"  Timestamp: {d.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        if d.remarks:
            print(f"  Remarks: {d.remarks}")
        print_separator()

def show_photos():
    """Display weight record photos"""
    print_separator("WEIGHT RECORD PHOTOS")
    photos = WeightRecordPhoto.objects.all()
    print(f"Total: {photos.count()} | Showing: Last 20\n")
    
    for p in photos[:20]:
        auto = "Auto-captured" if p.is_auto_captured else "Manual"
        print(f"Record: {p.weight_record.slip_number} | Type: {p.get_photo_type_display()} | Capture: {auto}")
        print(f"  Stage: {p.get_weight_stage_display()} | Photo: {p.photo.name}")
        if p.camera:
            print(f"  Camera: {p.camera.name} ({p.camera.get_position_display()})")
        if p.captured_weight:
            print(f"  Captured at Weight: {p.captured_weight} kg")
        if p.caption:
            print(f"  Caption: {p.caption}")
        print(f"  Uploaded: {p.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print_separator()

def show_payments():
    """Display payments"""
    print_separator("PAYMENTS")
    payments = Payment.objects.all()
    print(f"Total: {payments.count()} | Showing: Last 20\n")
    
    for p in payments[:20]:
        print(f"Payment ID: {p.payment_id} | Status: {p.get_payment_status_display()}")
        print(f"  Record: {p.weight_record.slip_number} | Amount: Rs.{p.amount}")
        print(f"  Method: {p.get_payment_method_display()}")
        
        if p.upi_transaction_id:
            print(f"  UPI Txn ID: {p.upi_transaction_id}")
        if p.transaction_date:
            print(f"  Transaction Date: {p.transaction_date.strftime('%Y-%m-%d %H:%M:%S')}")
        if p.remarks:
            print(f"  Remarks: {p.remarks}")
        
        print(f"  Created: {p.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print_separator()

def show_qr_codes():
    """Display QR codes"""
    print_separator("QR CODES")
    qr_codes = QRCode.objects.all()
    print(f"Total: {qr_codes.count()} | Showing: Last 20\n")
    
    for qr in qr_codes[:20]:
        active = "Active" if qr.is_active else "Inactive"
        print(f"QR ID: {qr.qr_id} | Payment: {qr.payment.payment_id} | Status: {active}")
        print(f"  Scan Count: {qr.scan_count}")
        print(f"  Generated: {qr.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if qr.expires_at:
            print(f"  Expires: {qr.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if qr.qr_string:
            print(f"  QR String: {qr.qr_string[:80]}...")
        print_separator()

def show_payment_slips():
    """Display payment slips"""
    print_separator("PAYMENT SLIPS")
    slips = PaymentSlip.objects.all()
    print(f"Total: {slips.count()} | Showing: Last 20\n")
    
    for s in slips[:20]:
        auto = "Auto-printed" if s.is_auto_printed else "Manual"
        print(f"Slip: {s.slip_number} | Status: {s.get_slip_status_display()} | Print Type: {auto}")
        print(f"  Payment: {s.payment.payment_id} | Print Count: {s.print_count}")
        
        if s.printer:
            print(f"  Printer: {s.printer.name}")
        
        if s.printed_at:
            print(f"  Printed: {s.printed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if s.auto_print_failed:
            print(f"  Auto-print Failed: {s.auto_print_error}")
        
        if s.pdf_file:
            print(f"  PDF: {s.pdf_file.name}")
        
        print(f"  Generated: {s.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print_separator()

def show_audit_logs():
    """Display audit logs"""
    print_separator("AUDIT LOGS")
    logs = AuditLog.objects.all()
    print(f"Total: {logs.count()} | Showing: Last 30\n")
    
    for log in logs[:30]:
        print(f"Action: {log.get_action_display()} | User: {log.user or 'System'}")
        
        if log.weight_record:
            print(f"  Record: {log.weight_record.slip_number}")
        
        if log.payment:
            print(f"  Payment: {log.payment.payment_id}")
        
        print(f"  Timestamp: {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if log.notes:
            print(f"  Notes: {log.notes}")
        
        if log.ip_address:
            print(f"  IP: {log.ip_address}")
        
        print_separator()

# Table menu mapping
TABLES = {
    '1': ('Customers', show_customers),
    '2': ('Operators', show_operators),
    '3': ('Vehicles', show_vehicles),
    '4': ('Weighbridge Config', show_weighbridge_config),
    '5': ('Live Weight Readings', show_live_weight_readings),
    '6': ('Camera Config', show_camera_config),
    '7': ('Printer Config', show_printer_config),
    '8': ('Company Details', show_company_details),
    '9': ('Weight Records', show_weight_records),
    '10': ('Weight Drops', show_weight_drops),
    '11': ('Photos', show_photos),
    '12': ('Payments', show_payments),
    '13': ('QR Codes', show_qr_codes),
    '14': ('Payment Slips', show_payment_slips),
    '15': ('Audit Logs', show_audit_logs),
}

def show_menu():
    """Display menu"""
    print("\n" + "="*80)
    print("                         SELECT TABLE TO VIEW")
    print("="*80 + "\n")
    
    print("MASTER DATA:")
    print("  1. Customers")
    print("  2. Operators")
    print("  3. Vehicles")
    
    print("\nHARDWARE CONFIGURATION:")
    print("  4. Weighbridge Config")
    print("  5. Live Weight Readings")
    print("  6. Camera Config")
    print("  7. Printer Config")
    print("  8. Company Details")
    
    print("\nOPERATIONAL DATA:")
    print("  9. Weight Records")
    print(" 10. Weight Drops")
    print(" 11. Photos")
    
    print("\nPAYMENT DATA:")
    print(" 12. Payments")
    print(" 13. QR Codes")
    print(" 14. Payment Slips")
    
    print("\nSYSTEM DATA:")
    print(" 15. Audit Logs")
    
    print("\n" + "="*80)

def main():
    """Main function"""
    try:
        show_menu()
        
        choice = input("\nEnter table number (1-15): ").strip()
        
        if choice in TABLES:
            table_name, table_function = TABLES[choice]
            print(f"\nLoading {table_name}...\n")
            table_function()
        else:
            print("\nInvalid choice! Please enter a number between 1 and 15.")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}\n")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()