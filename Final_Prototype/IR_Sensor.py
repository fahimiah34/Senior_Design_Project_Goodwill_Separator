# FINAL IR SENSOR CLASS
import asyncio
import board
import adafruit_mlx90614
import adafruit_tca9548a
import time as time

# Replace threshold with measured value
# Ideally there is a large difference between wood/glass temperature and
# metal temperature so this can catch all cases of metal accurately

# Testing threshold of 0.07 is very low and within the accuracy of the sensors themselves (0.5C).
"""
Pardon the yapping, the code and hardware adjustments will happen and will be based on this.

Preliminary testing indicates that using the floor of the sensing bay for calibration has the potential to not work,
likely for one of several reasons:
    1) The distance between the IR sensors and the table is too far outside the sensors' range (5 cm) for it to actually 
    figure out what's going on
    2) The emissivity of the wooden table top is lower than expected. This could be because the surface is rough,
    because it is unpolished and therefore not reflective, because the plywood material used is of poorer quality and 
    made of multiple grains/pulp, or because it is textured.

To address problem 1:
    still working on this

To address problem 2:
    Emissivity coefficients:
        PVC cover sheet has an emissivity (0.91 - 0.93) much closer to glass (0.92 - 0.94)
        Other plastics: 0.90 - 0.97 (prox sensor tips!)
        Wood has an emissivity anywhere from 0.75 (Sawdust) and 0.84 (Pine) to planed beech (0.935)
        Metal emissivity is far lower: Tin (0.04), Aluminum (0.04 - 0.09), Steel (0.07 - 0.79) (ignoring weathered stainless
            and old galvanized steel since we're detecting mason jar lids and not old bridges), zinc (0.045 - 0.25)

        In general, the more polished the metal, the lower the emissivity.

    NB: If metal is present in the glass, the effect of the metal will not be the same as completely lowering the 
    emissivity, making the IR sensors less sensitive.

    Calibration:
        Original plan: use a PVC sheet cover on the top of the table, so that the difference between PVC and glass
            was very minimal.   
        Option A: Set up calibration differently--use ambient temperature (second reading from the same sensors)
        Option B: Continue with physically-based calibration--put thin strips of PVC on the top of the 2020 partitions,
            time calibration with the ultrasonic
        Option C: Make empty partition cover out of PVC sheet, calibrate over empty partitions
        Option D: Calibrate at the same time as material passes through the trapdoor

    EMISSIVITY INFO SOURCE: Engineering Toolbox https://www.engineeringtoolbox.com/emissivity-coefficients-d_447.html

"""

""" Threshold numbers used:
    0.4 works for initialization over an empty bay
    0.8 appears to work for initialization over PVC either on top of the bay or on the table"""
# SETTING THRESHOLD
THRESHOLD = 0.8

class IRSensorArray:
    def __init__(self):
        """Initialize the IRSensorArray and set up the I2C bus and sensors."""
        self.i2c = board.I2C()  # I2C initialization
        self.tca = adafruit_tca9548a.TCA9548A(self.i2c)
        self.sensors = []
        self.baselines = [] # to store the baseline object temps for each sensor

        # checks if sensors are connected through I2C and to the Pi 5 
        for i in range(8):
            try:
                print(f"Initializing sensor on channel {i}...")
                sensor = adafruit_mlx90614.MLX90614(self.tca[i])
                self.sensors.append(sensor)
                print(f"Sensor on channel {i} initialized successfully.")
            except Exception as e:
                print(f"Failed to initialize sensor on channel {i}: {e}")

        print("Sensors initialized. Run calculate_baselines asynchronously to calibrate sensors.")
        self._calculate_baselines()

    async def _get_object_temperature_async(self, sensor):
        """Fetch the OBJECT temperature from a sensor asynchronously."""
        # Run the blocking call in a separate thread to avoid blocking the event loop
        return await asyncio.to_thread(lambda: sensor.object_temperature)
    
    async def _get_ambient_temperature_async(self, sensor):
        """Fetch the AMBIENT temperature from a sensor asynchronously.
            Careful to use the right function here"""
        # Run the blocking call in a separate thread to avoid blocking the event loop
        return await asyncio.to_thread(lambda: sensor.ambient_temperature)

    def _calculate_baselines(self, sampling_time=1.6, samples=10):
        """Synchronous function to calculate the baseline temps
        for each sensor. It calculates the average temperature of each sensor over a set period of time.
        THIS IS THE AUTO CALIBRATION FUNCTION.
        sampling_time = time to run the calibration for each sensor
        samples = the number of samples to take within that calibration time"""
        
        print("Starting baseline calculation for all sensors...")
        for sensor in self.sensors:
            readings = []
            for _ in range(samples):  # number of readings per each sensor
                try:
                    temp = round(sensor.object_temperature, 2)  # Blocking call
                    readings.append(temp)
                except Exception as e:
                    print(f"Error reading temperature: {e}")
                print(temp)
                time.sleep(sampling_time/samples)

            if readings:
                average_temp = round(sum(readings) / len(readings), 2)
                self.baselines.append(average_temp)
                print(f"Baseline for sensor: {average_temp}")
            else:
                self.baselines.append(None)
                print("Baseline calculation failed for this sensor.")

        print("Baseline calibration completed.")

    async def detect_object(self):
        """Detect if any sensor reads a temperature above the baseline plus threshold."""
        # Check if any sensor detects an object above a certain temperature
        # Check if any sensor detects an object above its baseline temperature
        for sensor, baseline in zip(self.sensors, self.baselines):
            if baseline is None:
                continue  # Skip sensors with invalid baselines

            current_temp = await self._get_object_temperature_async(sensor)             # Read the temperature asynchronously
            current_temp = round(current_temp, 2)
            #print(f"Current temperature: {current_temp}")

            # for debugging and testing the effect of metal vs pure glass:
            difference_from_baseline = round(current_temp - baseline, 2)
            print(f"difference from baseline: {difference_from_baseline}")

            if current_temp >= baseline + THRESHOLD:
                print(f"TEMPERATURE DIFFERENCE: {(current_temp - baseline), 2}")
                return True
        return False

    async def monitor(self, motor_event):
        """Monitor the sensor array asynchronously and trigger the motor event if an object is detected."""
        while True:
            if await self.detect_object():
                print("Object detected!")
                motor_event.set()  # Trigger motor event
            await asyncio.sleep(0.1)  # Sleep to avoid busy-waiting
