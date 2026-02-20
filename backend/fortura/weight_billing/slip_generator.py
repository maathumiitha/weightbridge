# slip_generator.py
"""
Utility for generating payment slips as PDFs
Implements the slip generation workflow from the diagram
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, 
    Spacer, Image, PageBreak, KeepTogether
)
from reportlab.pdfgen import canvas
from django.conf import settings
import io
import os
from datetime import datetime
from decimal import Decimal
import base64


class SlipGenerator:
    """
    Generates payment slips with the following components:
    - Company Details (logo, name, address)
    - Weight Information (all weights)
    - Payment QR Code
    - Time/Date Information
    - Operator Information
    - Photos (vehicle and material)
    """
    
    def __init__(self):
        self.width, self.height = A4
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#666666'),
            spaceAfter=10,
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))
        
        # Header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            spaceAfter=6,
            spaceBefore=10,
            fontName='Helvetica-Bold'
        ))
        
        # Normal text
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#333333'),
            spaceAfter=3,
            fontName='Helvetica'
        ))
        
        # Small text
        self.styles.add(ParagraphStyle(
            name='SmallText',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#666666'),
            spaceAfter=2,
            fontName='Helvetica'
        ))
    
    def generate_pdf(self, slip_data):
        """
        Generate PDF for payment slip
        
        Args:
            slip_data: Dictionary containing all slip information
                - payment: Payment object
                - weight_record: WeightRecord object
                - company: CompanyDetails object
                - qr_code: QRCode object
                - photos: QuerySet of WeightRecordPhoto objects
                - operator: Operator object
                - slip_number: String
                - generated_at: DateTime
        
        Returns:
            bytes: PDF content as bytes
        """
        buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=15*mm,
            bottomMargin=15*mm,
            title=f"Payment Slip - {slip_data['slip_number']}"
        )
        
        # Build story (content)
        story = []
        
        # Step 1: Add Company Details
        story.extend(self._add_company_details(slip_data))
        story.append(Spacer(1, 10*mm))
        
        # Step 2: Add Slip Header
        story.extend(self._add_slip_header(slip_data))
        story.append(Spacer(1, 5*mm))
        
        # Step 3: Add Customer and Vehicle Details
        story.extend(self._add_customer_vehicle_details(slip_data))
        story.append(Spacer(1, 5*mm))
        
        # Step 4: Add All Weights
        story.extend(self._add_weight_details(slip_data))
        story.append(Spacer(1, 5*mm))
        
        # Step 5: Add Payment Details with QR Code
        story.extend(self._add_payment_details(slip_data))
        story.append(Spacer(1, 5*mm))
        
        # Step 6: Add Time and Operator Information
        story.extend(self._add_time_operator_info(slip_data))
        story.append(Spacer(1, 5*mm))
        
        # Step 7: Add Photos (if available)
        if slip_data.get('photos') and slip_data['photos'].exists():
            story.extend(self._add_photos(slip_data))
        
        # Step 8: Add Footer
        story.extend(self._add_footer(slip_data))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()
        
        return pdf_content
    
    def _add_company_details(self, slip_data):
        """Add company logo, name, and address"""
        elements = []
        company = slip_data.get('company')
        
        if not company:
            return elements
        
        # Company logo and header in table
        data = []
        
        # Logo
        logo_cell = None
        if company.company_logo:
            try:
                logo_path = company.company_logo.path
                if os.path.exists(logo_path):
                    logo = Image(logo_path, width=50*mm, height=20*mm)
                    logo_cell = logo
            except:
                logo_cell = Paragraph("", self.styles['CustomNormal'])
        else:
            logo_cell = Paragraph("", self.styles['CustomNormal'])
        
        # Company info
        company_info = f"""
        <b>{company.company_name}</b><br/>
        {company.company_address}<br/>
        """
        if company.company_phone:
            company_info += f"Phone: {company.company_phone}<br/>"
        if company.company_email:
            company_info += f"Email: {company.company_email}<br/>"
        if company.gstin:
            company_info += f"GSTIN: {company.gstin}"
        
        company_cell = Paragraph(company_info, self.styles['CustomNormal'])
        
        data = [[logo_cell, company_cell]]
        
        table = Table(data, colWidths=[60*mm, 110*mm])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        elements.append(table)
        
        # Divider line
        line_table = Table([['']], colWidths=[170*mm])
        line_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 2, colors.HexColor('#333333')),
        ]))
        elements.append(Spacer(1, 3*mm))
        elements.append(line_table)
        
        return elements
    
    def _add_slip_header(self, slip_data):
        """Add slip title and number"""
        elements = []
        
        # Title
        title = Paragraph("PAYMENT SLIP", self.styles['CustomTitle'])
        elements.append(title)
        
        # Slip number and date
        slip_info = f"""
        <b>Slip No:</b> {slip_data['slip_number']}<br/>
        <b>Generated:</b> {slip_data['generated_at'].strftime('%d-%b-%Y %I:%M %p')}
        """
        slip_para = Paragraph(slip_info, self.styles['CustomNormal'])
        elements.append(slip_para)
        
        return elements
    
    def _add_customer_vehicle_details(self, slip_data):
        """Add customer and vehicle information"""
        elements = []
        weight_record = slip_data['weight_record']
        
        # Section header
        header = Paragraph("CUSTOMER & VEHICLE DETAILS", self.styles['SectionHeader'])
        elements.append(header)
        
        # Details table
        data = [
            ['Driver Name:', weight_record.customer.driver_name],
            ['Driver Phone:', weight_record.customer.driver_phone or 'N/A'],
            ['Address:', weight_record.customer.address or 'N/A'],
            ['Vehicle Number:', weight_record.vehicle.vehicle_number],
            ['Vehicle Type:', weight_record.vehicle.vehicle_type],
            ['Material Type:', weight_record.material_type],
        ]
        
        table = Table(data, colWidths=[50*mm, 120*mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        elements.append(table)
        
        return elements
    
    def _add_weight_details(self, slip_data):
        """Add all weight measurements"""
        elements = []
        weight_record = slip_data['weight_record']
        
        # Section header
        header = Paragraph("WEIGHT DETAILS", self.styles['SectionHeader'])
        elements.append(header)
        
        # Check if multi-drop
        if weight_record.is_multi_drop and weight_record.drops.exists():
            # Multi-drop weight table
            drop_data = [['Drop #', 'Gross Weight (kg)', 'Tare Weight (kg)', 'Net Weight (kg)']]
            
            for drop in weight_record.drops.all():
                drop_data.append([
                    str(drop.drop_number),
                    f"{drop.gross_weight:,.2f}",
                    f"{drop.tare_weight:,.2f}",
                    f"{drop.net_weight:,.2f}"
                ])
            
            # Add totals row
            total_gross = sum(drop.gross_weight for drop in weight_record.drops.all())
            total_tare = sum(drop.tare_weight for drop in weight_record.drops.all())
            drop_data.append([
                'TOTAL',
                f"{total_gross:,.2f}",
                f"{total_tare:,.2f}",
                f"{weight_record.net_weight:,.2f}"
            ])
            
            drop_table = Table(drop_data, colWidths=[30*mm, 45*mm, 45*mm, 45*mm])
            drop_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e0e0e0')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5f5f5')),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            
            elements.append(drop_table)
        else:
            # Single weight measurement
            data = [
                ['Gross Weight:', f"{weight_record.gross_weight:,.2f} kg"],
                ['Tare Weight:', f"{weight_record.tare_weight:,.2f} kg"],
                ['Net Weight:', f"{weight_record.net_weight:,.2f} kg"],
            ]
            
            table = Table(data, colWidths=[50*mm, 120*mm])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, 1), 'Helvetica'),
                ('FONTNAME', (1, 2), (1, 2), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#f0f0f0')),
            ]))
            
            elements.append(table)
        
        return elements
    
    def _add_payment_details(self, slip_data):
        """Add payment information and QR code"""
        elements = []
        payment = slip_data['payment']
        weight_record = slip_data['weight_record']
        qr_code = slip_data.get('qr_code')
        
        # Section header
        header = Paragraph("PAYMENT DETAILS", self.styles['SectionHeader'])
        elements.append(header)
        
        # Create table with payment details and QR code
        payment_info_data = [
            ['Rate per Unit:', f"₹ {weight_record.rate_per_unit:,.2f}"],
            ['Net Weight:', f"{weight_record.net_weight:,.2f} kg"],
            ['Total Amount:', f"₹ {payment.amount:,.2f}"],
            ['Payment Method:', payment.get_payment_method_display()],
            ['Payment Status:', payment.get_payment_status_display()],
        ]
        
        payment_table = Table(payment_info_data, colWidths=[50*mm, 70*mm])
        payment_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, 1), 'Helvetica'),
            ('FONTNAME', (1, 2), (1, 2), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#fff8dc')),
        ]))
        
        # QR code (if available)
        qr_cell = None
        if qr_code and qr_code.qr_image:
            try:
                # Decode base64 QR image
                qr_image_data = base64.b64decode(qr_code.qr_image)
                qr_buffer = io.BytesIO(qr_image_data)
                qr_img = Image(qr_buffer, width=40*mm, height=40*mm)
                
                qr_text = Paragraph("<b>Scan to Pay</b><br/><font size=7>UPI Payment</font>", 
                                   self.styles['CustomNormal'])
                qr_cell = [[qr_img], [qr_text]]
            except:
                qr_cell = [[Paragraph("QR Code<br/>Not Available", self.styles['SmallText'])]]
        else:
            qr_cell = [[Paragraph("", self.styles['SmallText'])]]
        
        qr_table = Table(qr_cell)
        qr_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        # Combine payment details and QR code
        main_table = Table([[payment_table, qr_table]], colWidths=[120*mm, 50*mm])
        main_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ]))
        
        elements.append(main_table)
        
        return elements
    
    def _add_time_operator_info(self, slip_data):
        """Add time/date and operator information"""
        elements = []
        weight_record = slip_data['weight_record']
        operator = slip_data.get('operator')
        
        # Section header
        header = Paragraph("TRANSACTION DETAILS", self.styles['SectionHeader'])
        elements.append(header)
        
        # Details - show both first and second weight operators
        data = [
            ['Date:', weight_record.date.strftime('%d-%b-%Y')],
            ['Shift:', weight_record.get_shift_display()],
            ['Record Created:', weight_record.created_at.strftime('%d-%b-%Y %I:%M %p')],
        ]
        
        # Add first weight operator info
        if weight_record.operator_first_weight:
            data.append(['First Weight Operator:', weight_record.operator_first_weight.employee_name])
            data.append(['Employee ID:', weight_record.operator_first_weight.employee_id])
        
        # Add second weight operator info (if different)
        if weight_record.operator_second_weight:
            if weight_record.operator_first_weight != weight_record.operator_second_weight:
                data.append(['Second Weight Operator:', weight_record.operator_second_weight.employee_name])
                data.append(['Employee ID:', weight_record.operator_second_weight.employee_id])
        
        # Add slip generator operator if different
        if operator and operator != weight_record.operator_first_weight and operator != weight_record.operator_second_weight:
            data.append(['Slip Generated By:', operator.employee_name])
        
        table = Table(data, colWidths=[50*mm, 120*mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        elements.append(table)
        
        return elements
    
    def _add_photos(self, slip_data):
        """Add vehicle and material photos"""
        elements = []
        photos = slip_data.get('photos')
        
        if not photos or not photos.exists():
            return elements
        
        # Section header
        header = Paragraph("PHOTOS", self.styles['SectionHeader'])
        elements.append(header)
        elements.append(Spacer(1, 3*mm))
        
        # Add photos in grid (2 per row)
        photo_data = []
        photo_row = []
        
        for photo in photos[:6]:  # Limit to 6 photos
            try:
                img_path = photo.photo.path
                if os.path.exists(img_path):
                    img = Image(img_path, width=75*mm, height=50*mm)
                    
                    caption = Paragraph(
                        f"<b>{photo.get_photo_type_display()}</b>",
                        self.styles['SmallText']
                    )
                    
                    photo_cell = [[img], [caption]]
                    photo_cell_table = Table(photo_cell)
                    photo_cell_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ]))
                    
                    photo_row.append(photo_cell_table)
                    
                    if len(photo_row) == 2:
                        photo_data.append(photo_row)
                        photo_row = []
            except:
                continue
        
        # Add remaining photos
        if photo_row:
            # Fill empty cell if odd number
            while len(photo_row) < 2:
                photo_row.append(Paragraph("", self.styles['SmallText']))
            photo_data.append(photo_row)
        
        if photo_data:
            photo_table = Table(photo_data, colWidths=[85*mm, 85*mm])
            photo_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))
            
            elements.append(photo_table)
        
        return elements
    
    def _add_footer(self, slip_data):
        """Add footer with terms and signature"""
        elements = []
        company = slip_data.get('company')
        
        elements.append(Spacer(1, 10*mm))
        
        # Footer text
        if company and company.slip_footer_text:
            footer_text = Paragraph(company.slip_footer_text, self.styles['SmallText'])
            elements.append(footer_text)
        
        # Signature section
        elements.append(Spacer(1, 10*mm))
        
        sig_data = [
            ['_____________________', '_____________________'],
            ['Operator Signature', 'Driver Signature'],
        ]
        
        sig_table = Table(sig_data, colWidths=[85*mm, 85*mm])
        sig_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 1), (-1, 1), 5),
        ]))
        
        elements.append(sig_table)
        
        # Bottom line
        elements.append(Spacer(1, 5*mm))
        line_table = Table([['']], colWidths=[170*mm])
        line_table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        elements.append(line_table)
        
        # Final note
        note = Paragraph(
            "<i>This is a computer-generated document. No signature required.</i>",
            self.styles['SmallText']
        )
        elements.append(Spacer(1, 2*mm))
        elements.append(note)
        
        return elements