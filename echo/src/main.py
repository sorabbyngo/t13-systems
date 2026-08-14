#!/usr/bin/env python3
"""
T13-Echo: RF Interception & IMSI Catcher Module
Classification: T13 Proprietary / ITAR Restricted
WARNING: This tool is for authorized penetration testing and sovereign agency use only.
"""

import os
import sys
import signal
import json
import time
import threading
from datetime import datetime

# --- Dependency Check & Imports ---
try:
    import numpy as np
    from scipy import signal as scipy_signal
except ImportError:
    print("[!] Installing required dependencies: numpy, scipy")
    os.system("pip3 install numpy scipy")

try:
    from rtlsdr import RtlSdr
    HAS_SDR = True
except ImportError:
    HAS_SDR = False
    print("[!] WARNING: rtlsdr library not found.")
    print("    Install with: pip3 install pyrtlsdr")
    print("    T13-Echo will run in SIMULATION MODE for testing logic.")

# --- T13 Core Configuration ---
CONFIG = {
    "frequency_mhz": 935.0,          # Typical GSM downlink (US/Europe). Adjust for your region.
    "sample_rate": 2.4e6,            # 2.4 MHz bandwidth
    "gain": "auto",                  # Auto-gain for the SDR
    "output_format": "json",         # Store intercepted metadata as JSON
    "log_file": "./logs/t13_echo.log"
}

class T13EchoEngine:
    def __init__(self, config):
        self.config = config
        self.sdr = None
        self.running = False
        self.captured_imsis = {}
        self.signal_buffer = []
        
        # Ensure logs directory exists
        os.makedirs("./logs", exist_ok=True)

    def initialize_sdr(self):
        """Connect to the Software Defined Radio (or simulate if missing)."""
        if HAS_SDR:
            try:
                self.sdr = RtlSdr()
                self.sdr.sample_rate = self.config["sample_rate"]
                self.sdr.center_freq = self.config["frequency_mhz"] * 1e6
                self.sdr.gain = self.config["gain"]
                print(f"[+] T13-Echo initialized on {self.config['frequency_mhz']} MHz")
                return True
            except Exception as e:
                print(f"[-] SDR Init Error: {e}")
                return False
        else:
            print("[*] Running in SIMULATION MODE (No hardware found).")
            return True

    def process_signal(self, samples):
        """
        Analyze raw IQ samples to detect cellular activity.
        In a real deployment, this would demodulate GSM bursts and extract TMSI/IMSI.
        """
        # SIMULATION: Fake signal detection
        if not HAS_SDR:
            fake_freq = np.random.uniform(0.8, 1.2)
            if fake_freq > 1.0:
                return {"type": "GSM_BURST", "strength": np.random.randint(-80, -50)}
            return None

        # REAL LOGIC: FFT to detect energy spikes
        try:
            fft_data = np.fft.fft(samples)
            power = np.abs(fft_data) ** 2
            avg_power = np.mean(power)
            if avg_power > 1e6:  # Arbitrary threshold for demo
                return {"type": "ACTIVE_SIGNAL", "power_db": 10 * np.log10(avg_power)}
        except Exception:
            pass
        return None

    def capture_loop(self):
        """Main loop to sniff RF and extract metadata."""
        self.running = True
        print("[*] T13-Echo listening for cellular signals...")

        while self.running:
            try:
                # Read samples from SDR
                if HAS_SDR and self.sdr:
                    samples = self.sdr.read_samples(256 * 1024)
                else:
                    # Simulation: generate white noise
                    samples = np.random.randn(256 * 1024) + 1j * np.random.randn(256 * 1024)

                # Process for activity
                result = self.process_signal(samples)
                if result:
                    timestamp = datetime.utcnow().isoformat()
                    log_entry = {
                        "timestamp": timestamp,
                        "frequency": self.config["frequency_mhz"],
                        "data": result
                    }
                    
                    # Write to log
                    with open(self.config["log_file"], "a") as f:
                        f.write(json.dumps(log_entry) + "\n")
                    
                    # Print to console (sanitized)
                    print(f"[{timestamp}] [+] Signal Detected: {result}")
                    
                    # SIM: Simulate IMSI capture (real logic would parse GSM Layer 3)
                    if "GSM_BURST" in str(result):
                        fake_imsi = f"310-150-{np.random.randint(100000000, 999999999)}"
                        if fake_imsi not in self.captured_imsis:
                            self.captured_imsis[fake_imsi] = timestamp
                            print(f"    🎯 TARGET ACQUIRED: IMSI {fake_imsi}")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[-] Capture error: {e}")
                time.sleep(0.1)

    def shutdown(self):
        """Gracefully close SDR connection."""
        self.running = False
        if HAS_SDR and self.sdr:
            self.sdr.close()
        print("\n[*] T13-Echo shutdown complete.")

def main():
    print("\n" + "="*50)
    print(" T13-Echo Systems | RF Intrusion Module v1.0")
    print("="*50)
    
    engine = T13EchoEngine(CONFIG)
    
    # Signal handler for clean exit
    def signal_handler(sig, frame):
        engine.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    if engine.initialize_sdr():
        engine.capture_loop()

if __name__ == "__main__":
    main()
