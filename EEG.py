#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 28 13:59:24 2026

@author: nicolas
"""

from Serial_class_test import serial_class

import threading
import time
import numpy as np
from collections import deque
from pythonosc.udp_client import SimpleUDPClient

FS = 250
TIME_WINDOW = 5
SAMPLES = FS * TIME_WINDOW
ACTIVE_CHANELS = 6
STEP_TIME = 8 / 250 # 32 ms

RELAX_SECONDS = 30
RELAX_SIZE = int(RELAX_SECONDS / STEP_TIME)

class EEG_signal_processing:
    
    def __init__(self):
        
        self.alpha = 0
        self.beta = 0
        self.ratio = 0
        self.n_ratio = 0
        self.smoothed_ratio = 0.5
        self.smoothing = 1
        
        self.osc = SimpleUDPClient("127.0.0.1", 9000)
        
        self.running = False
        
        self.serial_flux = serial_class(buffer=True, buffer_window = TIME_WINDOW)
        self.serial_flux.init_port()

        serial_thread = threading.Thread(target=self.serial_flux.reception, daemon=True)
        serial_thread.start()
        
        self.ref_buffer = deque(maxlen=RELAX_SIZE)
        self.data = []
        self.data.append(["alpha", "beta", "z ratio", "smooth ratio"])
        
    def start(self):
        
        self.ref_ready = False
        self.ref_buffer.clear()
        
        self.running = True
        fft_thread = threading.Thread(target=self.processing_loop, daemon=True)
        fft_thread.start()

    def stop(self):
        
        self.running = False
        self.osc.send_message("/reverb/crossfade", 1.0)
        
    def processing_loop(self):
        
        freqs = np.fft.rfftfreq(1250, d=1/250)
        alpha_mask = (freqs >= 8) & (freqs <= 12)
        beta_mask  = (freqs >= 12) & (freqs <= 20)
        
        hann_win = np.hanning(SAMPLES)
        
        while self.running:
            
            if len(self.serial_flux.data) < SAMPLES:
                time.sleep(0.05)
                continue
            
            X = np.array(self.serial_flux.data)[:, :ACTIVE_CHANELS]
            X = X * hann_win[:, None]
            
            FFT = np.fft.rfft(X, axis=0)
            power = np.abs(FFT) ** 2
            
            alpha_power = power[alpha_mask].mean()
            beta_power = power[beta_mask].mean()
            
            self.alpha = float(alpha_power)
            self.beta = float(beta_power)
            self.ratio = float(alpha_power / (beta_power + 1e-12))
            
            if (not self.ref_ready):
                if (len(self.ref_buffer) != RELAX_SIZE):
                    self.ref_buffer.append(self.ratio)
                
                else:
                    self.ref_ready = True
                    ref = np.array(self.ref_buffer)
                    r_mean = np.mean(ref)
                    r_std = np.std(ref)
                    
                    print("Reference ready")
                    print(f"Mean: {r_mean} |"
                          f"Dev: {r_std} |"
                    )
            else:
                z_ratio = (self.ratio - r_mean) / (r_std + 1e-12)
                self.n_ratio = np.clip((z_ratio + 2)/4, 0, 1)
                #print(self.n_ratio)
                
                # EMA smoothing
                self.smoothed_ratio = (self.smoothing * self.n_ratio + (1 - self.smoothing) * self.smoothed_ratio)
                self.osc.send_message("/reverb/crossfade", float(self.smoothed_ratio))
                self.data.append([self.alpha, self.beta, z_ratio, self.smoothed_ratio])
                #print(self.smoothed_ratio)

            time.sleep(STEP_TIME)
        
    def save_data(self):
        import csv
        with open("data/power_data.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(self.data)
        