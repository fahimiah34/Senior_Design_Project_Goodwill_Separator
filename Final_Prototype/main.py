# FINAL MAIN FILE
import asyncio
from Proximity_Sensor import ProximitySensor
from IR_Sensor import IRSensorArray
from IR_Camera import ThermalCamera
from Ultrasonic_Sensor import UltrasonicSensor
from Motor import TrapDoorMotor

# debugging
import board
import busio

async def monitor_proximity(sensor, motor_event):
    """Monitor proximity sensor asynchronously."""
    while True:
        if await sensor.is_object_detected():
            print('Object detected!')
            motor_event.set()  # Trigger motor event
        await asyncio.sleep(0.1)  # Add a sleep time to avoid rapid polling

async def monitor_ir_sensors(ir_sensor_array, motor_event):       # Temporarily commented out
    """Monitor IR sensor array asynchronously."""
    while True:
        if await ir_sensor_array.detect_object():
            print("Detected metal!")
            motor_event.set()  # Trigger motor event
        await asyncio.sleep(0.5)  # Add a sleep time to avoid rapid polling
        print("the IR SENSOR async wait just happened")

async def monitor_ir_camera(ir_camera_array, motor_event):
    """Monitor IR camera array asynchronously"""
    while True:
        if await ir_camera_array.detect_object():
            print("Detected metal!")
            motor_event.set() # Trigger motor event
        await asyncio.sleep(0.5) # sleep time to avoid rapid polling
        print("IR CAM async wait just happened")

async def motor_control(motor_event):
    """Control the motor to open and close the trap door."""
    trap_door_motor = TrapDoorMotor(forward_pin=21, backward_pin=20)  # Initialize motor once

    while True:
        await motor_event.wait()  # Wait for the event to be set
        await trap_door_motor.run()  # Run motor control asynchronously
        motor_event.clear()  # Reset the event

async def main():
    """Main async entry point for running the program."""
    motor_event = asyncio.Event()

    # Initialize sensors
    prox_sensors = [
        ProximitySensor(pin) for pin in [14, 15, 18, 23, 24, 25, 8, 7, 1, 12, 16]
    ]
    ir_sensor_array = IRSensorArray()       #Bring in IR sensor class
    ir_camera_array = ThermalCamera()       #Bring in IR camera 
    ultrasonic_sensor = UltrasonicSensor()  #Bring in Ultrasonic class


    # Create tasks for monitoring sensors
    tasks = [
        *[monitor_proximity(sensor, motor_event) for sensor in prox_sensors],
        monitor_ir_sensors(ir_sensor_array, motor_event),
        monitor_ir_camera(ir_camera_array, motor_event), 
        motor_control(motor_event) 
    ]
    # Monitor each proximity sensor
    # Monitor IR sensors asynchronously
    # Monitor IR camera asynchronously
    # Handle motor control asynchronously

    # Run all tasks concurrently
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    try:
        asyncio.run(main())  # Run the main async function
    except KeyboardInterrupt:
        print("\nCode stopped")
