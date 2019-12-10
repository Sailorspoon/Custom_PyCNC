# check which module to import
try:
    from cnc.hal_raspberry.hal import *
except ImportError:
    print("----- Hardware not detected, using virtual environment -----")
    print("----- Use M111 command to enable more detailed debug -----")
    from cnc.hal_virtual import *

# check if all methods that is needed is implemented
if 'init' not in locals():
    raise NotImplementedError("hal.init() not implemented")
if 'fan_control' not in locals():
    raise NotImplementedError("hal.fan_control() not implemented")
if 'extruder_heater_control' not in locals():
    raise NotImplementedError("hal.extruder_heater_control() not implemented")
if 'bed_heater_control' not in locals():
    raise NotImplementedError("hal.bed_heater_control() not implemented")
if 'get_extruder_temperature' not in locals():
    raise NotImplementedError("hal.get_extruder_temperature() not implemented")
if 'get_bed_temperature' not in locals():
    raise NotImplementedError("hal.get_bed_temperature() not implemented")
if 'disable_steppers' not in locals():
    raise NotImplementedError("hal.disable_steppers() not implemented")
if 'calibrate' not in locals():
    raise NotImplementedError("hal.calibrate() not implemented")
if 'move' not in locals():
    raise NotImplementedError("hal.move() not implemented")
if 'join' not in locals():
    raise NotImplementedError("hal.join() not implemented")
if 'deinit' not in locals():
    raise NotImplementedError("hal.deinit() not implemented")
if 'watchdog_feed' not in locals():
    raise NotImplementedError("hal.watchdog_feed() not implemented")
