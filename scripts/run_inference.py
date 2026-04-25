#!/usr/bin/env python3
"""
Launch script for the Bird Tracker inference pipeline.
Loads config and starts the real-time system.
"""

import yaml

from bird_tracker.infer import InferencePipeline

def main():
    with open('configs/config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    pipeline = InferencePipeline(config)
    pipeline.run()

if __name__ == '__main__':
    main()