import asyncio
from gpiozero import Motor
import time

class TrapDoorMotor:
    def __init__(self, forward_pin, backward_pin):
        """Initializes the TrapDoorMotor class."""
        self.motor = Motor(forward=forward_pin, backward=backward_pin)

    async def run(self):
        """Handles the motor control asynchronously for opening and closing the trap door."""
        try:
            print("Detected, Waiting 4 seconds")
            await asyncio.sleep(2)

            print("Opening trap door...")
            self.motor.forward()  # Move motor forward to open the trap door
            await asyncio.sleep(.5)  # Wait for 2 seconds while the motor is running

            print("Pausing motor...")
            self.motor.stop()  # Stop motor
            await asyncio.sleep(1.25)  # Wait for 3 seconds (pause)

            print("Closing trap door...")
            self.motor.backward()  # Move motor backward to close the trap door
            await asyncio.sleep(1)  # Wait for 2 seconds while the motor is running

        finally:
            print("Stopping motor...")
            self.motor.stop()  # Ensure motor is stopped after operation
