"""
Django management command to start the serial port reader for weighbridge integration.

Place this file in: weight_billing/management/commands/start_serial_reader.py

Usage:
    python manage.py start_serial_reader
    python manage.py start_serial_reader --port COM6  # Override COM port
    python manage.py start_serial_reader --test-mode  # Use test data
"""

import os
import django
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
import serial
import re
import time
import threading
from datetime import datetime, timedelta

# Import models
from weight_billing.models import (
    WeighbridgeConfig,
    LiveWeightReading,
    WeightRecord,
    AuditLog
)


class Command(BaseCommand):
    help = 'Start the serial port reader for weighbridge integration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=str,
            help='Override COM port (e.g., COM6)',
        )
        parser.add_argument(
            '--test-mode',
            action='store_true',
            help='Run in test mode (fake data)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting Weighbridge Serial Reader...'))
        
        port = options.get('port')
        test_mode = options.get('test_mode', False)
        
        reader = WeighbridgeSerialReader(
            port_override=port,
            test_mode=test_mode,
            stdout=self.stdout
        )
        
        try:
            reader.start()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n⚠️  Shutting down...'))
            reader.stop()
            self.stdout.write(self.style.SUCCESS('✅ Serial reader stopped'))


class WeighbridgeSerialReader:
    """
    Production serial reader for weighbridge integration.
    
    Features:
    - Reads from configured COM port
    - Stores live readings in LiveWeightReading table
    - Detects weight stability
    - Auto-captures weights when stable
    - Updates WeightRecord workflow status
    - Handles reconnection
    - Full audit logging
    """
    
    def __init__(self, port_override=None, test_mode=False, stdout=None):
        self.port_override = port_override
        self.test_mode = test_mode
        self.stdout = stdout
        self.serial_port = None
        self.is_running = False
        self.config = None
        
        # Stability tracking
        self.stability_buffer = []
        self.stability_start_time = None
        self.last_stable_weight = None
        
    def log(self, message, style='SUCCESS'):
        """Log message to console"""
        if self.stdout and hasattr(self.stdout, 'style'):
            if style == 'SUCCESS':
                self.stdout.write(self.stdout.style.SUCCESS(message))
            elif style == 'WARNING':
                self.stdout.write(self.stdout.style.WARNING(message))
            elif style == 'ERROR':
                self.stdout.write(self.stdout.style.ERROR(message))
            else:
                self.stdout.write(message)
        else:
            # Fallback to simple print with emojis
            print(message)
    
    def load_config(self):
        """Load weighbridge configuration from database"""
        try:
            self.config = WeighbridgeConfig.objects.filter(is_active=True).first()
            
            if not self.config:
                self.log('⚠️  No active WeighbridgeConfig found. Creating default...', 'WARNING')
                self.config = WeighbridgeConfig.objects.create(
                    name="Main Weighbridge",
                    port=self.port_override or 'COM6',
                    baud_rate=9600,
                    is_active=True
                )
            
            # Override port if specified
            if self.port_override:
                self.config.port = self.port_override
            
            self.log(f'✅ Config loaded: {self.config.port} @ {self.config.baud_rate} baud')
            return True
            
        except Exception as e:
            self.log(f'❌ Error loading config: {e}', 'ERROR')
            return False
    
    def connect_serial(self):
        """Connect to serial port"""
        try:
            if self.test_mode:
                self.log('🧪 TEST MODE: Using simulated data', 'WARNING')
                return True
            
            self.serial_port = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baud_rate,
                bytesize=self.config.data_bits,
                stopbits=self.config.stop_bits,
                timeout=1
            )
            
            self.config.is_connected = True
            self.config.last_connected = timezone.now()
            self.config.connection_status_message = 'Connected successfully'
            self.config.save()
            
            self.log(f'✅ Connected to {self.config.port}')
            
            # Log connection
            AuditLog.objects.create(
                action='WEIGHBRIDGE_CONNECTED',
                user='System',
                notes=f'Connected to {self.config.port}'
            )
            
            return True
            
        except serial.SerialException as e:
            error_msg = f'Failed to connect to {self.config.port}: {str(e)}'
            self.log(f'❌ {error_msg}', 'ERROR')
            
            self.config.is_connected = False
            self.config.connection_status_message = error_msg
            self.config.save()
            
            return False
        except Exception as e:
            self.log(f'❌ Unexpected error: {e}', 'ERROR')
            return False
    
    def parse_weight(self, data):
        """
        Extract weight from serial data.
        
        Handles formats like:
        - "WT: 25148 KG"
        - "+25148 kg"
        - "WEIGHT=25148"
        - "25148"
        """
        try:
            # Find first number in the string
            match = re.search(r'(\d+(?:\.\d+)?)', data)
            if match:
                return Decimal(match.group(1))
        except Exception as e:
            self.log(f'⚠️  Error parsing weight from "{data}": {e}', 'WARNING')
        
        return None
    
    def is_weight_stable(self, weight):
        """
        Check if weight is stable based on configured threshold and duration.
        
        Returns: (is_stable, duration_seconds)
        """
        threshold = self.config.stability_threshold
        required_duration = self.config.stability_duration
        
        # Add to buffer
        self.stability_buffer.append({
            'weight': weight,
            'time': timezone.now()
        })
        
        # Keep only last 10 seconds of readings
        cutoff = timezone.now() - timedelta(seconds=10)
        self.stability_buffer = [
            r for r in self.stability_buffer 
            if r['time'] > cutoff
        ]
        
        # Need at least 3 readings
        if len(self.stability_buffer) < 3:
            return False, 0
        
        # Check if all recent weights are within threshold
        weights = [float(r['weight']) for r in self.stability_buffer]
        weight_range = max(weights) - min(weights)
        
        if weight_range <= float(threshold):
            # Weight is stable
            if self.stability_start_time is None:
                self.stability_start_time = self.stability_buffer[0]['time']
            
            duration = (timezone.now() - self.stability_start_time).total_seconds()
            
            if duration >= required_duration:
                return True, duration
            else:
                return False, duration
        else:
            # Weight not stable, reset
            self.stability_start_time = None
            return False, 0
    
    def save_live_reading(self, weight, is_stable, stability_duration):
        """Save reading to LiveWeightReading table"""
        try:
            reading = LiveWeightReading.objects.create(
                weighbridge_config=self.config,
                weight=weight,
                is_stable=is_stable,
                stability_duration=Decimal(str(stability_duration)),
                stability_started_at=self.stability_start_time if is_stable else None,
                raw_data=f"Weight: {weight} kg"
            )
            return reading
        except Exception as e:
            self.log(f'⚠️  Error saving live reading: {e}', 'WARNING')
            return None
    
    def handle_stable_weight(self, weight, stability_duration):
        """
        Handle stable weight detection.
        Auto-capture if enabled and there's a pending weight record.
        """
        # Check if we already handled this stable weight
        if self.last_stable_weight == weight:
            return
        
        self.last_stable_weight = weight
        
        self.log(f'🎯 STABLE WEIGHT DETECTED: {weight} kg (stable for {stability_duration:.1f}s)')
        
        # Find pending weight records
        pending_records = WeightRecord.objects.filter(
            status__in=['FIRST_WEIGHT_PENDING', 'SECOND_WEIGHT_PENDING'],
            is_deleted=False
        ).order_by('-created_at')
        
        if not pending_records.exists():
            self.log('   No pending weight records found')
            return
        
        record = pending_records.first()
        
        # Determine if this is first or second weight
        if record.status == 'FIRST_WEIGHT_PENDING':
            # Mark as stable
            record.detect_first_weight_stable(stability_duration=Decimal(str(stability_duration)))
            self.log(f'   ✅ First weight stable detected for record {record.slip_number}')
            
            # Auto-capture if enabled
            if self.config.auto_capture_enabled:
                time.sleep(self.config.auto_capture_delay)
                record.capture_first_weight(
                    weight=weight,
                    operator=record.operator_first_weight,
                    auto_captured=True
                )
                self.log(f'   🤖 First weight AUTO-CAPTURED: {weight} kg')
                
                # Log audit
                AuditLog.objects.create(
                    weight_record=record,
                    action='FIRST_WEIGHT_AUTO_CAPTURED',
                    user='System (Auto-capture)',
                    new_values={'first_weight': float(weight)},
                    notes=f'Auto-captured after {stability_duration:.1f}s of stability'
                )
        
        elif record.status == 'SECOND_WEIGHT_PENDING':
            # Mark as stable
            record.detect_second_weight_stable(stability_duration=Decimal(str(stability_duration)))
            self.log(f'   ✅ Second weight stable detected for record {record.slip_number}')
            
            # Auto-capture if enabled
            if self.config.auto_capture_enabled:
                time.sleep(self.config.auto_capture_delay)
                record.capture_second_weight(
                    weight=weight,
                    operator=record.operator_second_weight or record.operator_first_weight,
                    auto_captured=True
                )
                self.log(f'   🤖 Second weight AUTO-CAPTURED: {weight} kg')
                
                # Log audit
                AuditLog.objects.create(
                    weight_record=record,
                    action='SECOND_WEIGHT_AUTO_CAPTURED',
                    user='System (Auto-capture)',
                    new_values={'second_weight': float(weight)},
                    notes=f'Auto-captured after {stability_duration:.1f}s of stability'
                )
                
                # Weights will auto-calculate via WeightRecord.save()
                self.log(f'   📊 Weights calculated: Gross={record.gross_weight} Tare={record.tare_weight} Net={record.net_weight}')
    
    def read_loop(self):
        """Main reading loop"""
        self.log('🔄 Starting read loop...')
        
        while self.is_running:
            try:
                if self.test_mode:
                    # Generate test data
                    import random
                    weight = Decimal(str(random.randint(10000, 40000)))
                    line = f"WT: {weight} KG"
                    time.sleep(2)
                else:
                    # Read from serial port
                    if not self.serial_port or not self.serial_port.is_open:
                        self.log('⚠️  Serial port not open, reconnecting...', 'WARNING')
                        if not self.connect_serial():
                            time.sleep(5)
                            continue
                    
                    line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    
                    if not line:
                        continue
                
                # Parse weight
                weight = self.parse_weight(line)
                
                if weight is None:
                    continue
                
                # Check stability
                is_stable, stability_duration = self.is_weight_stable(weight)
                
                # Save live reading
                self.save_live_reading(weight, is_stable, stability_duration)
                
                # Display
                stability_indicator = '🟢 STABLE' if is_stable else '🔵 READING'
                self.log(f'{stability_indicator} {weight} kg {f"({stability_duration:.1f}s)" if is_stable else ""}')
                
                # Update current live weight in pending records
                pending = WeightRecord.objects.filter(
                    status__in=['FIRST_WEIGHT_PENDING', 'SECOND_WEIGHT_PENDING'],
                    is_deleted=False
                ).first()
                
                if pending:
                    pending.update_live_weight(weight)
                
                # Handle stable weight
                if is_stable:
                    self.handle_stable_weight(weight, stability_duration)
                else:
                    # Reset last stable weight if weight becomes unstable
                    if self.last_stable_weight is not None:
                        self.last_stable_weight = None
                        self.log('   Weight no longer stable, reset')
                
            except serial.SerialException as e:
                self.log(f'❌ Serial error: {e}', 'ERROR')
                self.config.is_connected = False
                self.config.save()
                time.sleep(5)  # Wait before reconnecting
                
            except KeyboardInterrupt:
                break
                
            except Exception as e:
                self.log(f'❌ Error in read loop: {e}', 'ERROR')
                import traceback
                traceback.print_exc()
                time.sleep(1)
    
    def start(self):
        """Start the serial reader"""
        if not self.load_config():
            return False
        
        if not self.connect_serial():
            if not self.test_mode:
                return False
        
        self.is_running = True
        self.read_loop()
    
    def stop(self):
        """Stop the serial reader"""
        self.is_running = False
        
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        
        if self.config:
            self.config.is_connected = False
            self.config.save()
            
            AuditLog.objects.create(
                action='WEIGHBRIDGE_DISCONNECTED',
                user='System',
                notes=f'Disconnected from {self.config.port}'
            )  