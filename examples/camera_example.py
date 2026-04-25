#!/usr/bin/env python3
"""
Simple example demonstrating LowResCamera usage on Raspberry Pi.

This script:
1. Initializes the camera from config
2. Captures frames in a loop
3. Displays frame dimensions and timing info
4. Exits on 'q' keypress

Usage:
    python examples/camera_example.py
"""

import time
import cv2
import yaml

from bird_tracker.camera import LowResCamera


def main():
    # Load configuration
    with open('/home/jrswanbe/Documents/Bird-Tracker/configs/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize camera
    print("Initializing camera...")
    camera = LowResCamera(config['low_res_camera'])
    
    print("Capturing frames... (press 'q' to quit)")
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            # Capture frame
            frame = camera.capture_frame()
            frame_count += 1
            
            # Calculate FPS
            elapsed = time.time() - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0
            
            # Display frame with info overlay
            info_text = f"Frame {frame_count} | FPS: {fps:.1f} | Shape: {frame.shape}"
            cv2.putText(frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.7, (0, 255, 0), 2)
            
            cv2.imshow('Bird Tracker - Camera Test', frame)
            
            # Check for exit
            key = cv2.waitKey(1)
            if key & 0xFF == ord('q'):
                break
    
    finally:
        # Cleanup
        cv2.destroyAllWindows()
        camera.release()
        
        total_time = time.time() - start_time
        avg_fps = frame_count / total_time if total_time > 0 else 0
        print(f"\nCaptured {frame_count} frames in {total_time:.1f}s (avg FPS: {avg_fps:.1f})")


if __name__ == '__main__':
    main()
