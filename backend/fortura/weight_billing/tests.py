from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (
    AuditLog,
    CameraConfig,
    CompanyDetails,
    Customer,
    Operator,
    Payment,
    PaymentSlip,
    PrinterConfig,
    Vehicle,
    WeighbridgeConfig,
    WeightRecord,
)
from .services.automation_orchestrator import WeighmentAutomationOrchestrator


class PhaseTwoAutomationTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(driver_name="T Driver", driver_phone="9000000001", address="Yard")
        self.operator = Operator.objects.create(employee_name="T Operator", employee_id="OP-T-1", phone="9000000002")
        self.vehicle = Vehicle.objects.create(vehicle_number="TN00TEST0001", vehicle_type="Truck", capacity=Decimal("40000.00"))
        self.config = WeighbridgeConfig.objects.create(
            name="Test WB",
            port="COM6",
            auto_capture_enabled=True,
            auto_capture_delay=0,
            is_active=True,
        )

    def test_second_phase_auto_finalize_to_completed(self):
        record = WeightRecord.objects.create(
            customer=self.customer,
            vehicle=self.vehicle,
            date=timezone.now().date(),
            shift="MORNING",
            material_type="Sand",
            rate_per_unit=Decimal("10.50"),
            status="VEHICLE_RETURNED",
            first_weight=Decimal("40000.00"),
            first_weight_time=timezone.now(),
            operator_first_weight=self.operator,
        )

        orchestrator = WeighmentAutomationOrchestrator(config=self.config)
        orchestrator.process_stable_weight(Decimal("12000.00"), Decimal("3.2"))

        record.refresh_from_db()
        self.assertEqual(record.status, "COMPLETED")
        self.assertEqual(record.net_weight, Decimal("28000.00"))
        self.assertIsNotNone(record.charges_calculated_time)
        self.assertIsNotNone(record.completed_at)
        self.assertEqual(record.total_amount, Decimal("294000.00"))

    def test_first_phase_idempotent_autocapture_log(self):
        record = WeightRecord.objects.create(
            customer=self.customer,
            vehicle=self.vehicle,
            date=timezone.now().date(),
            shift="MORNING",
            material_type="Blue metal",
            rate_per_unit=Decimal("8.00"),
            status="FIRST_WEIGHT_PENDING",
            operator_first_weight=self.operator,
        )

        orchestrator = WeighmentAutomationOrchestrator(config=self.config)
        orchestrator.process_stable_weight(Decimal("25000.00"), Decimal("3.1"))
        orchestrator.process_stable_weight(Decimal("25000.00"), Decimal("3.1"))

        record.refresh_from_db()
        self.assertEqual(record.first_weight, Decimal("25000.00"))
        self.assertEqual(
            AuditLog.objects.filter(weight_record=record, action="FIRST_WEIGHT_AUTO_CAPTURED").count(),
            1,
        )


class PhaseThreeWhatsAppTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(driver_name="WA Driver", driver_phone="9000000111", address="Yard")
        self.operator = Operator.objects.create(employee_name="WA Operator", employee_id="OP-WA-1", phone="9000000222")
        self.vehicle = Vehicle.objects.create(vehicle_number="TN00WA0001", vehicle_type="Truck", capacity=Decimal("40000.00"))
        self.record = WeightRecord.objects.create(
            customer=self.customer,
            vehicle=self.vehicle,
            date=timezone.now().date(),
            shift="MORNING",
            material_type="Sand",
            rate_per_unit=Decimal("10.00"),
            total_amount=Decimal("25000.00"),
            operator_first_weight=self.operator,
            status="COMPLETED",
        )
        self.payment = Payment.objects.create(
            weight_record=self.record,
            amount=Decimal("25000.00"),
            payment_method="UPI",
            payment_status="PENDING",
        )
        self.slip = PaymentSlip.objects.create(
            payment=self.payment,
            slip_number="SLP-TEST-0001",
            slip_status="GENERATED",
            pdf_file="slips/test.pdf",
        )

    def test_send_whatsapp_virtual_queue_and_status(self):
        send_url = f"/api/payment-slips/{self.slip.slip_id}/send_whatsapp/"
        send_response = self.client.post(send_url, data={}, format="json")
        self.assertEqual(send_response.status_code, 200)
        self.assertEqual(send_response.data["status"], "QUEUED_VIRTUAL")

        status_url = f"/api/payment-slips/{self.slip.slip_id}/whatsapp_status/"
        status_response = self.client.get(status_url)
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.data["status"], "QUEUED_VIRTUAL")

    def test_retry_whatsapp_virtual_queue(self):
        retry_url = f"/api/payment-slips/{self.slip.slip_id}/retry_whatsapp/"
        retry_response = self.client.post(retry_url, data={}, format="json")
        self.assertEqual(retry_response.status_code, 200)
        self.assertEqual(retry_response.data["status"], "QUEUED_VIRTUAL")


class PhaseThreeReportExportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(username="reportuser", password="pass1234")
        self.client.force_authenticate(self.user)

        self.customer = Customer.objects.create(driver_name="R Driver", driver_phone="9000000999", address="Yard")
        self.operator = Operator.objects.create(employee_name="R Operator", employee_id="OP-R-1", phone="9000000888")
        self.vehicle = Vehicle.objects.create(vehicle_number="TN00RP0001", vehicle_type="Truck", capacity=Decimal("40000.00"))
        self.record = WeightRecord.objects.create(
            customer=self.customer,
            vehicle=self.vehicle,
            date=timezone.now().date(),
            shift="MORNING",
            material_type="Blue metal",
            rate_per_unit=Decimal("10.00"),
            total_amount=Decimal("280000.00"),
            gross_weight=Decimal("40000.00"),
            tare_weight=Decimal("12000.00"),
            net_weight=Decimal("28000.00"),
            operator_first_weight=self.operator,
            operator_second_weight=self.operator,
            status="COMPLETED",
        )

    def test_export_excel_success(self):
        response = self.client.post("/api/reports/export_excel/", data={}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_export_pdf_success(self):
        response = self.client.post("/api/reports/export_pdf/", data={}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_operator_filter_works_for_weight_record_operator_fields(self):
        response = self.client.post(
            "/api/reports/fetch_records/",
            data={"operator": self.operator.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)


class PhaseFourReadinessTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_deployment_readiness_reports_blockers_by_default(self):
        response = self.client.get("/api/weighbridge-configs/deployment_readiness/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["ready_for_production"])
        self.assertGreater(response.data["blocker_count"], 0)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["127.0.0.1", "localhost", "testserver"], CORS_ALLOW_ALL_ORIGINS=False)
    def test_deployment_readiness_reports_ready_when_core_config_present(self):
        WeighbridgeConfig.objects.create(name="Main WB", port="COM6", is_active=True)
        CameraConfig.objects.create(name="Camera 1", position="FRONT", is_active=True)
        PrinterConfig.objects.create(name="Printer 1", printer_name="Microsoft Print to PDF", is_active=True)
        CompanyDetails.objects.create(
            company_name="Weighbridge Tech",
            company_address="Industrial Zone",
            upi_id="weighbridge@upi",
            is_active=True,
        )
        Customer.objects.create(driver_name="D1", driver_phone="9000001000", address="Yard")
        Vehicle.objects.create(vehicle_number="TN00RD1001", vehicle_type="Truck", capacity=Decimal("40000.00"))
        Operator.objects.create(employee_name="OP1", employee_id="OP-READY-1", phone="9000001001")

        response = self.client.get("/api/weighbridge-configs/deployment_readiness/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["ready_for_production"])
        self.assertEqual(response.data["blocker_count"], 0)
