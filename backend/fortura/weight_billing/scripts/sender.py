"""
Realistic weighbridge simulator
Simulates a vehicle driving onto scale and weight settling

Place this file in: weight_billing/scripts/sender.py
"""

import serial
import time
import random

PORT = 'COM5'
BAUD_RATE = 9600

class RealisticWeighbridge:
    """Simulates realistic weighbridge behavior"""
    
    def __init__(self):
        self.state = 'EMPTY'  # EMPTY → LOADING → STABLE → UNLOADING
        self.target_weight = 0
        self.current_weight = 0
        self.stable_count = 0
        
    def get_next_weight(self):
        """Generate next weight reading based on current state"""
        
        if self.state == 'EMPTY':
            # Scale is empty, show near-zero with small noise
            self.current_weight = random.uniform(0, 5)
            
            # Randomly decide to start loading
            if random.random() < 0.1:  # 10% chance per reading
                self.state = 'LOADING'
                self.target_weight = random.randint(15000, 35000)
                print(f"\n🚛 Vehicle driving onto scale...")
                print(f"   Target weight: {self.target_weight} kg\n")
        
        elif self.state == 'LOADING':
            # Weight increasing as vehicle drives on
            difference = self.target_weight - self.current_weight
            
            if difference > 100:
                # Big jumps while vehicle moving
                self.current_weight += random.uniform(500, 2000)
                self.current_weight = min(self.current_weight, self.target_weight)
            elif difference > 10:
                # Smaller changes as vehicle slows
                self.current_weight += random.uniform(50, 200)
            else:
                # Close to target, transition to stable
                self.state = 'STABLE'
                self.stable_count = 0
                print(f"🎯 Vehicle stopped, weight settling...\n")
        
        elif self.state == 'STABLE':
            # Weight settled, small fluctuations only
            # ± 0.3 kg variance (within stability threshold of 0.5 kg)
            self.current_weight = self.target_weight + random.uniform(-0.3, 0.3)
            self.stable_count += 1
            
            # After 10 stable readings (20 seconds), start unloading
            if self.stable_count > 10:
                self.state = 'UNLOADING'
                print(f"🚛 Vehicle leaving scale...\n")
        
        elif self.state == 'UNLOADING':
            # Weight decreasing as vehicle drives off
            self.current_weight -= random.uniform(500, 2000)
            
            if self.current_weight < 100:
                self.state = 'EMPTY'
                self.current_weight = 0
                print(f"✅ Scale empty again\n")
        
        return round(self.current_weight, 2)


def main():
    print("=" * 60)
    print("🏭 REALISTIC WEIGHBRIDGE SIMULATOR")
    print("=" * 60)
    print(f"Port: {PORT}")
    print(f"Baud Rate: {BAUD_RATE}")
    print()
    print("This simulates:")
    print("  1. Empty scale (near 0 kg)")
    print("  2. Vehicle drives on (weight increases)")
    print("  3. Vehicle stops (weight becomes STABLE)")
    print("  4. Vehicle drives off (weight decreases)")
    print()
    
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
        print(f"✅ Connected to {PORT}")
        print()
        
        weighbridge = RealisticWeighbridge()
        
        print("📤 Starting simulation...")
        print("   (Press Ctrl+C to stop)")
        print()
        
        while True:
            # Get next weight
            weight = weighbridge.get_next_weight()
            
            # Format data
            data = f"WT: {weight} KG\r\n"
            
            # Send to serial port
            ser.write(data.encode())
            
            # Display with state indicator
            state_emoji = {
                'EMPTY': '⚪',
                'LOADING': '🔵',
                'STABLE': '🟢',
                'UNLOADING': '🟡'
            }
            emoji = state_emoji.get(weighbridge.state, '⚪')
            
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] {emoji} {weighbridge.state:12} │ {weight:8.2f} kg")
            
            # Wait 2 seconds
            time.sleep(2)
            
    except serial.SerialException as e:
        print(f"❌ Error: {e}")
        print()
        print("💡 Make sure:")
        print(f"   1. COM port {PORT} exists (check com0com setup)")
        print("   2. Port is not already in use")
        print("   3. com0com is properly installed")
        
    except KeyboardInterrupt:
        print()
        print("⚠️  Stopped by user")
        
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print(f"✅ Disconnected from {PORT}")


if __name__ == "__main__":
    main()