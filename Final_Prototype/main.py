import asyncio
from Proximity_Sensor import ProximitySensor
from IR_Sensor import IRSensorArray
from IR_Camera import ThermalCamera
from motor_test import TrapDoorMotor

async def monitor_ir_sensors(ir_sensor_array, queue):
    """Monitor IR sensor array asynchronously."""
    while True:
        if await ir_sensor_array.detect_object():
            print("Detected metal! (IR Sensors)")
            await queue.put("metal_detected")
        await asyncio.sleep(0.3)

async def monitor_ir_camera(ir_camera_array, queue):
    """Monitor IR camera array asynchronously."""
    while True:
        if await ir_camera_array.detect_object():
            print("Detected metal! (IR Cameras)")
            await queue.put("metal_detected")
        await asyncio.sleep(1)

async def monitor_proximity(sensor, queue):
    """Monitor proximity sensor asynchronously."""
    while True:
        if await sensor.is_object_detected():
            print("Detected object!")
            await queue.put("metal_detected")
        await asyncio.sleep(0.1)

async def motor_control(queue):
    """Control the motor to open and close the trap door."""
    trap_door_motor = TrapDoorMotor(forward_pin=21, backward_pin=20)
    while True:
        event = await queue.get()  # Wait for detection event
        if event == "metal_detected":
            print("Opening trap door...")
            await trap_door_motor.run()
            
            while not queue.empty():
                await queue.get()
        await asyncio.sleep(0.1)

async def main():
    """Main async entry point for running the program."""
    # Create detection queue
    detection_queue = asyncio.Queue()

    # Initialize sensors
    prox_sensors = [ProximitySensor(pin) for pin in [14, 15, 18, 23, 24, 25, 8, 7, 1, 12, 16]]
    ir_sensor_array = IRSensorArray()
    ir_camera_array = ThermalCamera()

    # Create tasks for monitoring sensors and controlling the motor
    tasks = [
        *[monitor_proximity(sensor, detection_queue) for sensor in prox_sensors],
        monitor_ir_sensors(ir_sensor_array, detection_queue),
        monitor_ir_camera(ir_camera_array, detection_queue),
        motor_control(detection_queue),
    ]

    try:
        print("Starting tasks...")
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        print("Shutting down...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
