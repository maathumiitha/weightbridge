import time
from decimal import Decimal

from django.db import DatabaseError, transaction
from django.utils import timezone

from ..models import AuditLog, CameraConfig, PrinterConfig, WeightRecord, WeightRecordPhoto
from .hardware_services import CameraHardwareService, HardwareIntegrationError


class WeighmentAutomationOrchestrator:
    """
    Handles real-time orchestration of stable-weight events into
    end-to-end weighment workflow transitions.
    """

    FIRST_PHASE_STATUSES = ("RECORD_SAVED", "FIRST_WEIGHT_PENDING", "FIRST_WEIGHT_STABLE")
    SECOND_PHASE_STATUSES = ("VEHICLE_RETURNED", "SECOND_WEIGHT_PENDING", "SECOND_WEIGHT_STABLE")
    RECOVERY_STATUSES = ("SECOND_WEIGHT_CAPTURED", "WEIGHTS_CALCULATED", "CHARGES_CALCULATED", "QR_GENERATED", "SLIP_PRINTED")

    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger
        self.max_retries = 3
        self.retry_delay_seconds = 0.5

    def _log(self, message):
        if self.logger:
            self.logger(message)

    def _audit(self, record, action, notes, new_values=None, calc=None):
        AuditLog.objects.create(
            weight_record=record,
            action=action,
            user="System (Automation)",
            notes=notes,
            new_values=new_values,
            calculation_details=calc,
        )

    def _mark_retry_pending(self, record, step, error):
        self._audit(
            record,
            "UPDATE",
            f"[AUTOMATION_RETRY_PENDING] step={step}; error={error}",
            new_values={"retry_step": step, "error": str(error)},
        )

    def _retry(self, fn, op_name):
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return fn()
            except Exception as exc:
                last_error = exc
                self._log(f"   {op_name} failed (attempt {attempt}/{self.max_retries}): {exc}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay_seconds)
        raise last_error

    def _get_next_record(self):
        statuses = self.FIRST_PHASE_STATUSES + self.SECOND_PHASE_STATUSES + self.RECOVERY_STATUSES
        base_qs = WeightRecord.objects.filter(is_deleted=False, status__in=statuses).order_by("created_at")
        try:
            return base_qs.select_for_update(skip_locked=True).first()
        except DatabaseError:
            return base_qs.first()

    def _capture_auto_snapshots(self, record, stage, captured_weight):
        if stage == "FIRST":
            cameras = CameraConfig.objects.filter(
                auto_snapshot_enabled=True,
                snapshot_on_first_weight=True,
                is_active=True,
                is_connected=True,
            )
            photo_type = "FIRST_WEIGHT"
        else:
            cameras = CameraConfig.objects.filter(
                auto_snapshot_enabled=True,
                snapshot_on_second_weight=True,
                is_active=True,
                is_connected=True,
            )
            photo_type = "SECOND_WEIGHT"

        captured_count = 0
        for camera in cameras:
            try:
                image_file = CameraHardwareService(retries=2, retry_delay=0.3).capture_snapshot(
                    camera,
                    quality=camera.jpeg_quality,
                )
                WeightRecordPhoto.objects.create(
                    weight_record=record,
                    camera=camera,
                    photo=image_file,
                    photo_type=photo_type,
                    weight_stage=stage,
                    is_auto_captured=True,
                    captured_weight=captured_weight,
                    timestamp_added=True,
                    caption=f"Auto-captured by automation from {camera.name}",
                )
                captured_count += 1
            except (HardwareIntegrationError, Exception) as exc:
                self._mark_retry_pending(record, f"camera_snapshot_{stage.lower()}", exc)
        if captured_count:
            self._audit(
                record,
                "PHOTO_AUTO_CAPTURED",
                f"{captured_count} auto snapshots captured for {stage.lower()} stage",
                new_values={"stage": stage, "count": captured_count},
            )

    def _auto_print_on_completion(self, record):
        if record.slip_printed_time:
            return None

        printer = PrinterConfig.objects.filter(
            is_active=True,
            is_ready=True,
            slip_engine_ready=True,
            auto_print_enabled=True,
            auto_print_on_completion=True,
        ).first()
        if not printer:
            return None

        self._retry(lambda: record.mark_slip_printed(auto_printed=True), "auto-print mark_slip_printed")
        printer.last_printed = timezone.now()
        self._retry(lambda: printer.save(update_fields=["last_printed", "updated_at"]), "auto-print printer save")
        self._audit(
            record,
            "SLIP_AUTO_PRINTED",
            f"Auto-printed by automation on {printer.name}",
            new_values={"printer": printer.name, "auto_printed": True},
        )
        return printer.name

    def _finalize_after_second_capture(self, record):
        if not record.net_weight and record.first_weight and record.second_weight:
            self._retry(lambda: record.calculate_weights(), "calculate_weights")
            self._retry(lambda: record.save(), "save weights")
            if not AuditLog.objects.filter(weight_record=record, action="WEIGHTS_CALCULATED").exists():
                self._audit(
                    record,
                    "WEIGHTS_CALCULATED",
                    f"Weights auto-calculated. Net={record.net_weight}",
                    calc={
                        "first_weight": str(record.first_weight),
                        "second_weight": str(record.second_weight),
                        "gross_weight": str(record.gross_weight),
                        "tare_weight": str(record.tare_weight),
                        "net_weight": str(record.net_weight),
                    },
                )

        # Ensure charges are calculated even for zero rate records.
        if record.net_weight is not None and record.rate_per_unit is not None and not record.charges_calculated_time:
            def _calc_charges():
                record.total_amount = record.net_weight * record.rate_per_unit
                record.charges_calculated_time = timezone.now()
                record.status = "CHARGES_CALCULATED"
                record.save()

            self._retry(_calc_charges, "calculate_charges")
            if not AuditLog.objects.filter(weight_record=record, action="CHARGES_CALCULATED").exists():
                self._audit(
                    record,
                    "CHARGES_CALCULATED",
                    f"Charges auto-calculated. Amount={record.total_amount}",
                    calc={
                        "net_weight": str(record.net_weight),
                        "rate_per_unit": str(record.rate_per_unit),
                        "total_amount": str(record.total_amount),
                    },
                )

        if record.net_weight is not None and record.status != "COMPLETED":
            self._retry(lambda: record.mark_completed(), "mark_completed")
            printer_name = self._auto_print_on_completion(record)
            notes = f"Weighment auto-completed for {record.slip_number}"
            if printer_name:
                notes += f" (auto-printed via {printer_name})"
            if not AuditLog.objects.filter(weight_record=record, action="WEIGHMENT_COMPLETE").exists():
                self._audit(
                    record,
                    "WEIGHMENT_COMPLETE",
                    notes,
                    new_values={
                        "slip_number": record.slip_number,
                        "net_weight": str(record.net_weight),
                        "total_amount": str(record.total_amount) if record.total_amount is not None else None,
                        "completed_at": record.completed_at.isoformat() if record.completed_at else None,
                        "printer": printer_name,
                    },
                )

    def process_stable_weight(self, weight, stability_duration):
        with transaction.atomic():
            record = self._get_next_record()
            if not record:
                self._log("   No pending records for automation")
                return None

            duration = Decimal(str(stability_duration))

            if record.status in self.RECOVERY_STATUSES:
                try:
                    self._finalize_after_second_capture(record)
                except Exception as exc:
                    self._mark_retry_pending(record, "recovery_finalize", exc)
                return record

            if record.status in self.FIRST_PHASE_STATUSES:
                already_logged_stable = AuditLog.objects.filter(
                    weight_record=record, action="FIRST_WEIGHT_STABLE_DETECTED"
                ).exists()
                record.detect_first_weight_stable(stability_duration=duration)
                if not already_logged_stable:
                    self._audit(
                        record,
                        "FIRST_WEIGHT_STABLE_DETECTED",
                        f"First weight stable: {weight}",
                        new_values={"stable_weight": float(weight), "stability_duration": float(duration)},
                    )
                self._log(f"   First stable detected for {record.slip_number}")

                if self.config.auto_capture_enabled and not record.first_weight:
                    time.sleep(self.config.auto_capture_delay)
                    record.capture_first_weight(
                        weight=weight,
                        operator=record.operator_first_weight,
                        auto_captured=True,
                    )
                    self._capture_auto_snapshots(record, "FIRST", weight)
                    if not AuditLog.objects.filter(weight_record=record, action="FIRST_WEIGHT_AUTO_CAPTURED").exists():
                        self._audit(
                            record,
                            "FIRST_WEIGHT_AUTO_CAPTURED",
                            f"First weight auto-captured: {weight}",
                            new_values={"first_weight": float(weight)},
                        )
                    self._log(f"   First weight auto-captured for {record.slip_number}")
                return record

            if record.status in self.SECOND_PHASE_STATUSES:
                already_logged_stable = AuditLog.objects.filter(
                    weight_record=record, action="SECOND_WEIGHT_STABLE_DETECTED"
                ).exists()
                record.detect_second_weight_stable(stability_duration=duration)
                if not already_logged_stable:
                    self._audit(
                        record,
                        "SECOND_WEIGHT_STABLE_DETECTED",
                        f"Second weight stable: {weight}",
                        new_values={"stable_weight": float(weight), "stability_duration": float(duration)},
                    )
                self._log(f"   Second stable detected for {record.slip_number}")

                if self.config.auto_capture_enabled and not record.second_weight:
                    time.sleep(self.config.auto_capture_delay)
                    record.capture_second_weight(
                        weight=weight,
                        operator=record.operator_second_weight or record.operator_first_weight,
                        auto_captured=True,
                    )
                    self._capture_auto_snapshots(record, "SECOND", weight)
                    if not AuditLog.objects.filter(weight_record=record, action="SECOND_WEIGHT_AUTO_CAPTURED").exists():
                        self._audit(
                            record,
                            "SECOND_WEIGHT_AUTO_CAPTURED",
                            f"Second weight auto-captured: {weight}",
                            new_values={"second_weight": float(weight)},
                        )
                    self._log(f"   Second weight auto-captured for {record.slip_number}")
                    try:
                        self._finalize_after_second_capture(record)
                    except Exception as exc:
                        self._mark_retry_pending(record, "second_phase_finalize", exc)
                return record

            self._log(f"   Record {record.slip_number} has unsupported status {record.status}")
            return record
