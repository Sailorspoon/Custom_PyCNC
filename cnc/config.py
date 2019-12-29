# -----------------------------------------------------------------------------
# Hardware config.

import math

# new parameter for newly developed printer head
distance_pivot_FFF_nozzle = 0

# new parameter for delta-Logic
distance_pivot_carriage_mm = {'a': 0, 'b': 0, 'c': 0}
radius_heatbed = 263  # distance middle heatbed to carriage on xy-level
height_pivot_tool_mm = 22
height_carriage_mm = {'a': 0, 'b': 0, 'c': 0}
length_arm = {'a': 400, 'b': 400, 'c': 400}
distance_pivot_tool_mm = 40
tu = {'x': 0, 'y': 0, 'z': 455}  # starting position for tool --> home

# Workplace physical size.
# TABLE_SIZE_X_MM = 100
# TABLE_SIZE_Y_MM = 100
TABLE_SIZE_Z_MM = 455
TABLE_SIZE_RADIUS_MM = 180
MAX_ROTATION_N_MM = 360
MAX_TILT_ANGLE = 90
# no maximum for rotatory degree of freedom of the heating bed

# start values of the carriage high:
# height_carriage_mm is a function of distance_pivot_carriage_mm
# height carriage calculated with pythagoras of distance_pivot_carriage and the arm lenght. This is added to the height.
# distance_pivot_carriage calculated with tx, ty, tz = 0
# x-axes and carriage(a) are in alignment.
height_carriage_mm['a'] = TABLE_SIZE_Z_MM + height_pivot_tool_mm\
                          + math.sqrt(length_arm['a'] ** 2 - ((radius_heatbed - distance_pivot_tool_mm) ** 2))
height_carriage_mm['b'] = TABLE_SIZE_Z_MM + height_pivot_tool_mm\
                          + math.sqrt(length_arm['b'] ** 2
                                      - ((radius_heatbed * math.cos(math.radians(120))
                                          - (distance_pivot_tool_mm * math.cos(math.radians(120)))) ** 2
                                         + (radius_heatbed * math.sin(math.radians(120))
                                            - (distance_pivot_tool_mm * math.sin(math.radians(120)))) ** 2))
height_carriage_mm['c'] = TABLE_SIZE_Z_MM + height_pivot_tool_mm\
                          + math.sqrt(length_arm['c'] ** 2
                                      - ((radius_heatbed * math.cos(math.radians(240))
                                          - (distance_pivot_tool_mm * math.cos(math.radians(240)))) ** 2
                                         + (radius_heatbed * math.sin(math.radians(240))
                                            - (distance_pivot_tool_mm * math.sin(math.radians(240)))) ** 2))

distance_mm = dict()
height_carriage_mm_old = dict()

# Maximum velocity for each axis in millimeter per minute.
MAX_VELOCITY_MM_PER_MIN_X = 6000
MAX_VELOCITY_MM_PER_MIN_Y = 6000
MAX_VELOCITY_MM_PER_MIN_Z = 6000
MAX_VELOCITY_MM_PER_MIN_E = 1500
MAX_VELOCITY_MM_PER_MIN_Q = 3000
MAX_VELOCITY_MM_PER_MIN_N = 600
MAX_VELOCITY_MM_PER_MIN_A = 800
MAX_VELOCITY_MM_PER_MIN_B = 800
MIN_VELOCITY_MM_PER_MIN = 1
# Average velocity for endstop calibration procedure
CALIBRATION_VELOCITY_MM_PER_MIN = 300

# Stepper motors steps per millimeter for each axis.
STEPPER_PULSES_PER_MM_X = 100
STEPPER_PULSES_PER_MM_Y = 100
STEPPER_PULSES_PER_MM_Z = 100
STEPPER_PULSES_PER_MM_E = 150
STEPPER_PULSES_PER_MM_Q = 100
STEPPER_PULSES_PER_MM_N = 80
STEPPER_PULSES_PER_MM_A = 444  # 1/16 microstepping, 1:50 Getriebe, 1.8° 
STEPPER_PULSES_PER_MM_B = 356 # 1/16 microstepping, 1:10 Getriebe, 1.8°, 1:4 Zahnriemen

# Invert axises direction, by default(False) high level means increase of
# position. For inverted(True) axis, high level means decrease of position.
STEPPER_INVERTED_X = False
STEPPER_INVERTED_Y = False
STEPPER_INVERTED_Z = False
STEPPER_INVERTED_E = True
STEPPER_INVERTED_Q = False
STEPPER_INVERTED_N = False
STEPPER_INVERTED_A = False
STEPPER_INVERTED_B = False

# Invert zero end stops switches. By default(False) low level on input pin
# means that axis in zero position. For inverted(True) end stops, high level
# means zero position.
ENDSTOP_INVERTED_X = False
ENDSTOP_INVERTED_Y = False
ENDSTOP_INVERTED_Z = False  # Auto leveler
ENDSTOP_INVERTED_A = False

# Mixed settings.
STEPPER_PULSE_LENGTH_US = 2
STEPPER_MAX_ACCELERATION_MM_PER_S2 = 3000  # for all axis, mm per sec^2
SPINDLE_MAX_RPM = 10000    # value can be ignored - can be deleted, if corresponding function is deleted
EXTRUDER_MAX_TEMPERATURE = 250
BED_MAX_TEMPERATURE = 100
MIN_TEMPERATURE = 40
EXTRUDER_PID = {"P": 0.059161177519,
                "I": 0.00206217171374,
                "D": 0.206217171374}
BED_PID = {"P": 0.226740848076,
           "I": 0.00323956215053,
           "D": 0.323956215053}

# -----------------------------------------------------------------------------
# Pins configuration.

# Enable pin for all steppers, low level is enabled.
STEPPERS_ENABLE_PIN = 26
STEPPER_STEP_PIN_X = 21
STEPPER_STEP_PIN_Y = 16
STEPPER_STEP_PIN_Z = 12
STEPPER_STEP_PIN_E = 8
# new degrees of freedom
STEPPER_STEP_PIN_Q = 15
STEPPER_STEP_PIN_N = 6
STEPPER_STEP_PIN_A = 25
STEPPER_STEP_PIN_B = 17

STEPPER_DIR_PIN_X = 20
STEPPER_DIR_PIN_Y = 19
STEPPER_DIR_PIN_Z = 13
STEPPER_DIR_PIN_E = 7
# new degrees of freedom
STEPPER_DIR_PIN_Q = 14
STEPPER_DIR_PIN_N = 5
STEPPER_DIR_PIN_A = 23
STEPPER_DIR_PIN_B = 4

#FAN_PIN = 27
EXTRUDER_HEATER_PIN = 18
BED_HEATER_PIN = 22
EXTRUDER_TEMPERATURE_SENSOR_CHANNEL = 2
BED_TEMPERATURE_SENSOR_CHANNEL = 1

ENDSTOP_PIN_X = 24
ENDSTOP_PIN_Y = 9
ENDSTOP_PIN_Z = 11
ENDSTOP_PIN_A = 27 #Alter Pin von fan 

# -----------------------------------------------------------------------------
#  Behavior config

# Run command immediately after receiving and stream new pulses, otherwise
# buffer will be prepared firstly and then command will run.
# Before enabling this feature, please make sure that board performance is
# enough for streaming pulses(faster then real time).
INSTANT_RUN = True

# If this parameter is False, error will be raised on command with velocity
# more than maximum velocity specified here. If this parameter is True,
# velocity would be decreased(proportional for all axises) to fit the maximum
# velocity.
AUTO_VELOCITY_ADJUSTMENT = True

# Automatically turn on fan when extruder is heating, boolean value.
AUTO_FAN_ON = True
