# FINAL IR CAMERA CLASS
import time
import asyncio
import board
import busio
import adafruit_mlx90640
import numpy as np
from ultrasonic_final import UltrasonicSensor  #Used for the ul

class ThermalCamera:
    # Define class attributes for the fixed resolution of MLX90640
    WIDTH = 32
    HEIGHT = 24
    CALIBRATION_DURATION = 6                  # Duration in seconds for the calibration period
    THRESHOLD = 0.5                           # Temperature threshold for detecting metal
    MIN_POINTS = 12                           # Minimum number of points that have to be above threshold for metal detection to trigger
    BINARY_ARRAY = np.zeros((HEIGHT, WIDTH))  # Initialize the array of zeroes that will track where metal is detected

    def __init__(self, refresh_rate=adafruit_mlx90640.RefreshRate.REFRESH_2_HZ, i2c_frequency=800000):
        """ Initializes the ThermalCamera object.
        :param refresh_rate: The refresh rate for the thermal camera.
        :param i2c_frequency: The frequency for the I2C communication."""
        try:
            self.i2c = busio.I2C(board.SCL, board.SDA, frequency=i2c_frequency) # Initialize I2C connection
            self.mlx = adafruit_mlx90640.MLX90640(self.i2c) # Initialize MLX90640 sensor
            print("MLX90640 detected with serial number:", self.mlx.serial_number)
            self.mlx.refresh_rate = refresh_rate             # Set the refresh rate
            print(f"Refresh rate set to {self.mlx.refresh_rate}")
            self.frame = [0] * (ThermalCamera.WIDTH * ThermalCamera.HEIGHT)             # Initialize the frame buffer based on sensor resolution\

        except Exception as e:
            print("Failed to initialize ThermalCamera:", e)
            raise

        self.frame_matrix = [] # initialize frame_matrix object
        self.calibrate() # Automatically calibrate the camera on startup
    
    async def read_frame(self):
        """ Reads a frame from the thermal camera.
        :return: A 2D numpy array representing the temperature values."""
        try:
            self.mlx.getFrame(self.frame)
            self.frame_matrix = np.array(self.frame).reshape((24, 32))

        except ValueError as ve:
            print("ValueError:", ve)
            return None
        
    async def display_frame(self, matrix, decimals):
        """ Displays the temperature frame in a readable format with aligned columns.
        decimals is the number of decimal points to display
        :param frame_matrix: A 2D numpy array of temperature values. """
        if matrix is None:
            print("No frame to display.")
            return

        # Determine the column width, accommodating the longest value (with sign)
        col_width = 0
        if decimals >=1:
            col_width = 4  # For example, enough for "-999.9" 
        for row in matrix:
            print(" ".join(f"{temp:>{col_width}.{decimals}f}" for temp in row))
        print()  # Add an extra newline for better readability

    def calibrate(self):
        """
        Calibrates the thermal camera by calculating the average temperature
        matrix over a specified time duration.
        """
        print("Starting calibration...")
        start_time = time.time()
        accum_matrix = np.zeros((ThermalCamera.HEIGHT, ThermalCamera.WIDTH))
        count = 0

        # Try-except lines to make sure the self.frame_matrix is properly sized
        try:
            self.mlx.getFrame(self.frame)
            self.frame_matrix = np.array(self.frame).reshape((24, 32))
        except ValueError as ve:
            print("ValueError:", ve)

        while (time.time() - start_time) < ThermalCamera.CALIBRATION_DURATION:
            if self.frame_matrix is not None:
                accum_matrix += self.frame_matrix
                count += 1
            time.sleep(1 / self.mlx.refresh_rate)  # Wait for the next refresh cycle
        
        if count > 0:
            self.calibration_matrix = accum_matrix / count
            self.calibration_matrix = np.round(self.calibration_matrix, decimals=1) # ROUNDING HAPPENS HERE
            print(self.calibration_matrix)
            print("Calibration completed.")
            time.sleep(2)
        else:
            print("Calibration failed: no frames captured.")

    async def detect_object(self):
        """Detect if any sensor reads a temperature above the baseline plus threshold."""
        await self.read_frame() # update the frame matrix with the newest sample
        differences_from_baseline = np.subtract(self.frame_matrix, self.calibration_matrix)
        await self.display_frame(differences_from_baseline, 1)  # this line prints out the actual difference from baseline array

        # If any values are above the threshold:
        if differences_from_baseline is not None:
            binary_array = (differences_from_baseline > self.THRESHOLD).astype(int) # make a binary array to visualize where metal is detected
            count = np.sum(binary_array)            # Count the total points where metal is detected
            print(f"TOTAL POINTS ABOTE THRESHOLD: {count}")
            
            if count >= self.MIN_POINTS:
                await self.display_frame(binary_array, 0)        # Print the differences from baseline to show where metal is detected
                return True
        
        #print(binary_array)
        return False

    async def monitor(self, motor_event):
        """Monitor the camera array asynchronously and trigger the motor event if an object is detected."""
        ultrasonic_sensor = UltrasonicSensor()
        while True:
            # wait to sense until the IR camera is in the middle of the partition
            if ultrasonic_sensor.motor_speed_rpm_avg is not None: #Using the simple discrete motor speed for now, but can change to average
                expected_position = (time.monotonic() - ultrasonic_sensor.last_partition_time)* 60 * (1/6) * ultrasonic_sensor.motor_speed_rpm
                
                time_to_wait = ultrasonic_sensor.last_partition_time


                if await self.detect_object():
                    print("Object detected!")
                    motor_event.set()  # Trigger motor event

                else:
                    #await self.display_frame()
                    pass

            await asyncio.sleep(0.1)  # Sleep to avoid busy-waiting
