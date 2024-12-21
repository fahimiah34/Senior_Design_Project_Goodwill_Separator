import asyncio
from Proximity_Sensor import ProximitySensor
from IR_Sensor import IRSensorArray
from IR_Camera import ThermalCamera
from Ultrasonic_Sensor import UltrasonicSensor
from updated_motor import TrapDoorMotor

class SharedState:
    def __init__(self):
        self.metal_detect = False
        self.partition_list = [0] * 6
        self.part = 0
        self.lock = asyncio.Lock()

    async def update_state(self, metal_detect=False, partition=None, part=0):
        async with self.lock:
            if metal_detect is not None:
                self.metal_detect = metal_detect
            await asyncio.sleep(0)
            if partition is not None:
                self.partition_list = partition
            await asyncio.sleep(0)
            if part is not None:
                self.part = part
            await asyncio.sleep(0)
    async def get_state(self):
        async with self.lock:
            return self.metal_detect, self.partition_list, self.part

async def monitor_sensors(prox_sensors, ir_sensor_array, ir_camera_array, shared_state):
    try:
        while True:
            # Check proximity sensors
            for sensor in prox_sensors:
                try:
                    detected = await asyncio.wait_for(sensor.is_object_detected(), timeout=0.5)
                    if detected:
                        print('Detected metal! (Proximity Sensor)')
                        await shared_state.update_state(metal_detect=True, partition=None, part=None)
                        print("Updated shared state: METALDETECT = True")
                        break
                    await asyncio.sleep(0)
                except asyncio.TimeoutError:
                    continue

            # Check IR sensors
            if await ir_sensor_array.detect_object():
                print("Detected metal! (IR Sensors)")
                await shared_state.update_state(metal_detect=True, partition=None, part=None)
            await asyncio.sleep(0)

            # Check IR camera
            if await ir_camera_array.detect_object():
                print("Detected metal! (IR Cameras)")
                await shared_state.update_state(metal_detect=True, partition=None, part=None)
            await asyncio.sleep(0)
    except asyncio.CancelledError:
        print("Sensor monitoring cancelled.")

async def motor_control(shared_state, ultrasonic_sensor):
    trap_door_motor = TrapDoorMotor(forward_pin=21, backward_pin=20)
    try:
        while True:
            metal_detect, partition_list, part = await shared_state.get_state()
            if partition_list[part] == 0 and trap_door_motor.trap_door_state:
                print("Closing trap door...")
                await trap_door_motor.lift_trapdoor(ultrasonic_sensor)
                trap_door_motor.trap_door_state = False  # Update state
            
            elif partition_list[part] == 1 and not trap_door_motor.trap_door_state:
                print("Opening trap door...")
                await trap_door_motor.run(ultrasonic_sensor)
                trap_door_motor.trap_door_state = True  # Update state
            await asyncio.sleep(0)
    except asyncio.CancelledError:
        print("Motor control task cancelled.")

async def monitor_ultrasonic(ultrasonic_sensor, shared_state):
    try:
        while True:
            await ultrasonic_sensor.track_partition_state()
            metal_detect, partition_list, part = await shared_state.get_state()
            if metal_detect:
                print(f"Ultrasonic sensor: Metal detected, partition {part} active.")
            await asyncio.sleep(0)
    except asyncio.CancelledError:
        print("Ultrasonic sensor monitoring cancelled.")

async def listy_things(ultrasonic_sensor, shared_state):
    while True:

        # Ensure `part` stays within the valid range
        if shared_state.part > 5:
            shared_state.part = 0
            shared_state.partition_list = [0,0,0,0,0,0]
        await asyncio.sleep(0)
        if ultrasonic_sensor.state == 1 and shared_state.metal_detect == True:
            shared_state.partition_list[shared_state.part] = 1                       #AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
            #await asyncio.sleep(0.03) 

            # Reset metal_detect after it has been handled
            shared_state.metal_detect = False

        else:
            shared_state.partition_list[shared_state.part] = 0
        await asyncio.sleep(0) 

        if ultrasonic_sensor.state == 0:
            shared_state.part += 1
            if shared_state.part > 5:
                shared_state.part = 0  # Reset part to prevent out of range access
            await asyncio.sleep(0) 
            
        await asyncio.sleep(0)  

        #print(shared_state.partition_list) 
        #print("ultrasonic_sensor.state is ", ultrasonic_sensor.state)

async def main():
    shared_state = SharedState()
    prox_sensors = [ProximitySensor(pin) for pin in [14, 15, 18, 23, 24, 25, 8, 7, 1, 12, 16]]
    ir_sensor_array = IRSensorArray()
    ir_camera_array = ThermalCamera()
    ultrasonic_sensor = UltrasonicSensor(10, 22)

    tasks = [
        monitor_sensors(prox_sensors, ir_sensor_array, ir_camera_array, shared_state),
        motor_control(shared_state, ultrasonic_sensor),
        monitor_ultrasonic(ultrasonic_sensor, shared_state),
        listy_things(ultrasonic_sensor, shared_state)
    ]

    try:
        print("Starting tasks...")
        await asyncio.gather(*tasks)
    except Exception as e:
        print(f"Unhandled exception in tasks: {e}")
    except asyncio.CancelledError:
        print("Tasks cancelled.")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program terminated by user.")
