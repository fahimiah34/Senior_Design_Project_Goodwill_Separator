# FINAL PROXIMITY SENSOR CLASS
import asyncio
from gpiozero import InputDevice

class ProximitySensor:
    def __init__(self, sensor_pin):
        """Initializes the proximity sensor with the given GPIO pin."""
        self.sensor = InputDevice(sensor_pin, pull_up=False)

    async def is_object_detected(self):
        """Check if an object is detected asynchronously."""
        # Since GPIO reading is typically fast, we'll simulate async behavior here
        await asyncio.sleep(0)  # Yield control to the event loop to avoid blocking
        return self.sensor.value == 1

    async def monitor(self, motor_event):
        """Monitor the sensor asynchronously and trigger motor_event when an object is detected."""
        while True:
            if await self.is_object_detected():
                print("Object detected!")
                motor_event.set()  # Trigger motor event
            await asyncio.sleep(0.1)  # Poll every 100ms
         
    def cleanup(self):
        """Clean up the sensor by closing it."""
        self.sensor.close()
