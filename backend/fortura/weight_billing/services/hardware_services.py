import base64
import time
from datetime import datetime

from django.core.files.base import ContentFile


class HardwareIntegrationError(Exception):
    """Raised when hardware integration fails."""

    def __init__(self, message, code="HARDWARE_ERROR"):
        super().__init__(message)
        self.code = code


def _with_retries(func, retries=1, retry_delay=0.5):
    last_error = None
    for attempt in range(max(0, int(retries)) + 1):
        try:
            return func()
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(float(retry_delay))
    if isinstance(last_error, Exception):
        raise last_error
    raise HardwareIntegrationError("Unknown retry failure", code="RETRY_FAILED")


def decode_base64_image(image_data, prefix="snapshot"):
    """Decode base64 image data into Django ContentFile."""
    if not image_data:
        raise HardwareIntegrationError("Image data is empty")

    try:
        fmt = "jpg"
        payload = image_data
        if ";base64," in image_data:
            header, payload = image_data.split(";base64,", 1)
            if "/" in header:
                fmt = header.split("/")[-1]
        binary = base64.b64decode(payload)
    except Exception as exc:
        raise HardwareIntegrationError(f"Invalid base64 image data: {exc}") from exc

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{prefix}_{timestamp}.{fmt}"
    return ContentFile(binary, name=filename)


class CameraHardwareService:
    """Camera integration helpers backed by OpenCV."""

    def __init__(self, retries=1, retry_delay=0.5):
        try:
            import cv2  # type: ignore
        except ImportError as exc:
            raise HardwareIntegrationError(
                "OpenCV is not installed. Install opencv-python to use camera integration.",
                code="CAMERA_DEPENDENCY_MISSING",
            ) from exc
        self.cv2 = cv2
        self.retries = retries
        self.retry_delay = retry_delay

    def _get_source(self, camera):
        if camera.camera_type == "USB":
            return int(camera.camera_index)
        if camera.rtsp_url:
            return camera.rtsp_url
        raise HardwareIntegrationError("Camera source is not configured")

    def test_connection(self, camera):
        def _probe():
            source = self._get_source(camera)
            cap = self.cv2.VideoCapture(source)
            try:
                if not cap.isOpened():
                    raise HardwareIntegrationError(
                        f"Unable to open camera source: {source}",
                        code="CAMERA_OPEN_FAILED",
                    )

                ok, frame = cap.read()
                if not ok or frame is None:
                    raise HardwareIntegrationError(
                        "Camera opened but no frame received",
                        code="CAMERA_NO_FRAME",
                    )

                height, width = frame.shape[:2]
                return {
                    "source": str(source),
                    "resolution": f"{width}x{height}",
                }
            finally:
                cap.release()

        return _with_retries(
            _probe,
            retries=self.retries,
            retry_delay=self.retry_delay,
        )

    def capture_snapshot(self, camera, quality=90):
        def _capture():
            source = self._get_source(camera)
            cap = self.cv2.VideoCapture(source)
            try:
                if not cap.isOpened():
                    raise HardwareIntegrationError(
                        f"Unable to open camera source: {source}",
                        code="CAMERA_OPEN_FAILED",
                    )

                ok, frame = cap.read()
                if not ok or frame is None:
                    raise HardwareIntegrationError(
                        "Could not capture frame from camera",
                        code="CAMERA_NO_FRAME",
                    )

                encode_ok, buffer = self.cv2.imencode(
                    ".jpg",
                    frame,
                    [int(self.cv2.IMWRITE_JPEG_QUALITY), int(quality)],
                )
                if not encode_ok:
                    raise HardwareIntegrationError(
                        "Failed to encode captured frame",
                        code="CAMERA_ENCODE_FAILED",
                    )

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filename = f"cam_{camera.id}_{timestamp}.jpg"
                return ContentFile(buffer.tobytes(), name=filename)
            finally:
                cap.release()

        return _with_retries(
            _capture,
            retries=self.retries,
            retry_delay=self.retry_delay,
        )


class PrinterHardwareService:
    """Printer integration helpers for Windows spooler."""

    def __init__(self, retries=1, retry_delay=0.5):
        try:
            import win32print  # type: ignore
        except ImportError as exc:
            raise HardwareIntegrationError(
                "pywin32 is not installed. Install pywin32 to use printer integration.",
                code="PRINTER_DEPENDENCY_MISSING",
            ) from exc
        self.win32print = win32print
        self.retries = retries
        self.retry_delay = retry_delay

    def _resolve_printer_name(self, printer):
        configured = (printer.printer_name or "").strip()
        if not configured:
            raise HardwareIntegrationError(
                "Printer name is empty in configuration",
                code="PRINTER_NAME_MISSING",
            )
        return configured

    def test_connection(self, printer):
        printer_name = self._resolve_printer_name(printer)
        def _probe():
            handle = self.win32print.OpenPrinter(printer_name)
            self.win32print.ClosePrinter(handle)
            return {"printer_name": printer_name, "status": "ready"}

        try:
            return _with_retries(
                _probe,
                retries=self.retries,
                retry_delay=self.retry_delay,
            )
        except Exception as exc:
            raise HardwareIntegrationError(
                f"Printer '{printer_name}' is not reachable: {exc}",
                code="PRINTER_UNREACHABLE",
            ) from exc

    def print_test_page(self, printer, content=None):
        printer_name = self._resolve_printer_name(printer)
        text = content or (
            "WEIGHBRIDGE TEST PAGE\r\n"
            f"Printer: {printer_name}\r\n"
            f"Generated: {datetime.now().isoformat()}\r\n"
        )
        data = text.encode("utf-8", errors="ignore")

        handle = None
        try:
            handle = self.win32print.OpenPrinter(printer_name)
            job = self.win32print.StartDocPrinter(handle, 1, ("Test Page", None, "RAW"))
            self.win32print.StartPagePrinter(handle)
            self.win32print.WritePrinter(handle, data)
            self.win32print.EndPagePrinter(handle)
            self.win32print.EndDocPrinter(handle)
            return {"printer_name": printer_name, "job_id": job}
        except Exception as exc:
            raise HardwareIntegrationError(
                f"Failed to send test page to '{printer_name}': {exc}",
                code="PRINTER_PRINT_FAILED",
            ) from exc
        finally:
            if handle:
                self.win32print.ClosePrinter(handle)


class WeighbridgeHardwareService:
    """Weighbridge integration helpers for serial communication."""

    PARITY_MAP = {
        "NONE": "PARITY_NONE",
        "EVEN": "PARITY_EVEN",
        "ODD": "PARITY_ODD",
    }
    BYTESIZE_MAP = {
        5: "FIVEBITS",
        6: "SIXBITS",
        7: "SEVENBITS",
        8: "EIGHTBITS",
    }
    STOPBITS_MAP = {
        1: "STOPBITS_ONE",
        2: "STOPBITS_TWO",
    }

    def __init__(self, retries=1, retry_delay=0.5):
        self.retries = retries
        self.retry_delay = retry_delay
        try:
            import serial  # type: ignore
        except ImportError as exc:
            raise HardwareIntegrationError(
                "pyserial is not installed. Install pyserial to use weighbridge integration.",
                code="WEIGHBRIDGE_DEPENDENCY_MISSING",
            ) from exc
        self.serial = serial

    def _serial_kwargs(self, config):
        parity_name = self.PARITY_MAP.get((config.parity or "NONE").upper(), "PARITY_NONE")
        bytesize_name = self.BYTESIZE_MAP.get(int(config.data_bits), "EIGHTBITS")
        stopbits_name = self.STOPBITS_MAP.get(int(config.stop_bits), "STOPBITS_ONE")
        return {
            "port": config.port,
            "baudrate": int(config.baud_rate),
            "bytesize": getattr(self.serial, bytesize_name),
            "stopbits": getattr(self.serial, stopbits_name),
            "parity": getattr(self.serial, parity_name),
            "timeout": 2,
            "write_timeout": 2,
        }

    def test_connection(self, config):
        kwargs = self._serial_kwargs(config)

        def _probe():
            ser = self.serial.Serial(**kwargs)
            try:
                return {
                    "port": kwargs["port"],
                    "baud_rate": kwargs["baudrate"],
                    "is_open": bool(ser.is_open),
                }
            finally:
                if ser and ser.is_open:
                    ser.close()

        try:
            return _with_retries(
                _probe,
                retries=self.retries,
                retry_delay=self.retry_delay,
            )
        except self.serial.SerialException as exc:
            raise HardwareIntegrationError(
                f"Weighbridge serial connection failed on {kwargs['port']}: {exc}",
                code="WEIGHBRIDGE_SERIAL_FAILED",
            ) from exc
        except Exception as exc:
            raise HardwareIntegrationError(
                f"Weighbridge test failed: {exc}",
                code="WEIGHBRIDGE_TEST_FAILED",
            ) from exc
