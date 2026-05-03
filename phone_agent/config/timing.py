"""Minimal timing config for ADB operations (no env var loading)."""

import os
from dataclasses import dataclass


@dataclass
class ActionTimingConfig:
    keyboard_switch_delay: float = 1.0
    text_clear_delay: float = 1.0
    text_input_delay: float = 1.0
    keyboard_restore_delay: float = 1.0


@dataclass
class DeviceTimingConfig:
    default_tap_delay: float = 1.0
    default_double_tap_delay: float = 1.0
    double_tap_interval: float = 0.1
    default_long_press_delay: float = 1.0
    default_swipe_delay: float = 1.0
    default_back_delay: float = 1.0
    default_home_delay: float = 1.0
    default_launch_delay: float = 1.0


@dataclass
class ConnectionTimingConfig:
    adb_restart_delay: float = 2.0
    server_restart_delay: float = 1.0


@dataclass
class TimingConfig:
    action: ActionTimingConfig
    device: DeviceTimingConfig
    connection: ConnectionTimingConfig

    def __init__(self):
        self.action = ActionTimingConfig()
        self.device = DeviceTimingConfig()
        self.connection = ConnectionTimingConfig()


TIMING_CONFIG = TimingConfig()
