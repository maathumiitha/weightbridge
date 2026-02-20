"""
Simple serial port reader for testing (no Django dependencies)

This is a simple test script to verify COM port communication works.
Use this BEFORE running the Django management command.

Place this file in: weight_billing/scripts/test_reader.py
"""

import serial
import re

# Configuration
PORT = 'COM6'  # Receiver side of virtual cable
BAUD_RATE = 9600

def parse_weight(data):
    """Extract weight number from data"""
    match = re.search(r'(\d+(?:\.\d+)?)', data)
    if match:
        return float(match.group(1))
    return None

def main():
    print("=" * 60)
    print("📥 SIMPLE SERIAL PORT READER (Test Mode)")
    print("=" * 60)
    print(f"Port: {PORT}")
    print(f"Baud Rate: {BAUD_RATE}")
    print()
    
    try:
        # Connect to COM port
        ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
        print(f"✅ Connected to {PORT}")
        print()
        print("📥 Listening for weight data...")
        print("   (Press Ctrl+C to stop)")
        print()
        
        while True:
            # Read line from serial port
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            
            if line:
                # Parse weight
                weight = parse_weight(line)
                
                # Display
                timestamp = time.strftime("%H:%M:%S")
                if weight:
                    print(f"[{timestamp}] 📥 Received: {line} → Weight: {weight:.2f} kg")
                else:
                    print(f"[{timestamp}] 📥 Received: {line} (could not parse weight)")
                    
    except serial.SerialException as e:
        print(f"❌ Error: {e}")
        print()
        print("💡 Make sure:")
        print(f"   1. COM port {PORT} exists (check com0com setup)")
        print("   2. Port is not already in use")
        print("   3. Sender is running (python sender.py)")
        
    except KeyboardInterrupt:
        print()
        print("⚠️  Stopped by user")
        
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print(f"✅ Disconnected from {PORT}")


if __name__ == "__main__":
    import time
    main()