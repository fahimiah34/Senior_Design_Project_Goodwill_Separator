# FINAL ULTRASONIC SENSOR CLASS
from gpiozero import DistanceSensor
import time
import asyncio


# Parameters
PARTITION_DISTANCE = 0.06              #Distance from sensor to partition
TOLERANCE = 0.04                       #Acceptable deviation from partition distance for detection
SPEED_TIMING_ACCURACY_THRESHOLD = 0.05  #Wait time used when finding motor speed, in seconds. CANNOT BE ZERO.
SAMPLES = 5                             #Number of samples used to find moving average of rotational speed
HISTORY_LENGTH = 15                     #Number of total speed entries to store for tracking moving average. Must be greater than SAMPLES

class UltrasonicSensor:
    def __init__(self, echo_pin, trigger_pin, sleep_time=0.05):
        """Initializes the ultrasonic sensor with the specified echo and trigger pins."""
        self.sensor = DistanceSensor(echo=echo_pin, trigger=trigger_pin)
        self.sleep_time = sleep_time
        self.distance = 1                       #Initialize distance variable to "far away". Start at 1
        self.count = 0                          #Initialize the counter at 0 to track how many partitions have gone by--useful for debugging
        self.state = 0                          #Initialize the state to 0 (i.e. no partition)
        self.last_partition_time = None         #Initialize as None--start with no partition detected
        self.before_last_partition_time = None  #Initialize the start of the interval for motor speed tracking
        self.elapsed_time = 0                   #Initialize time tracker for motor speed function
        self.new_elapsed_time = 0               #Initialize time tracker for motor speed function part 2
        self.time_between_partitions = None     #Initialize tracker variable for speed function
        self.motor_speed_rpm = None             #Initialize....ok you get the point
        self.speed_history = []                 #Initialize an object to track the speed over time -- use in case we need to average
        self.motor_speed_rpm_avg = None         #Initialize motor speed averaged over time

    async def get_distance(self):
        """Returns the current distance measured by the sensor in meters."""
        return self.sensor.distance

    async def continuously_measure_distance(self):
        """Continuously measures and prints the distance."""
        try:
            while True:
                self.distance = await self.get_distance()
                #print(f"Distance: {self.distance:.4f} m")
                await asyncio.sleep(self.sleep_time)
        except KeyboardInterrupt:
            print("Measurement stopped by user.")

    async def check_for_partition(self):
        """ Asynchronously checks whether there is a partition in front of the sensor """
        while True:
            current_distance = self.sensor.distance
            if (self.sensor.distance <= round((PARTITION_DISTANCE + TOLERANCE), 2)):
                #print("PARTITION FOUND")
                return True 
            await asyncio.sleep(0.01)
            return False
   
    async def track_partition_state(self):
        """ Function to track changes in partition state--i.e. when a partition passes"""
        while True:
            #print(self.count)
            #await self.continuously_measure_distance()
            await asyncio.sleep(0.01)                                                                               #JUST ADDED 7:36 pm
            if await self.check_for_partition() == True:
                if self.state == 0:
                    self.count += 1
                    self.state = 1 # keep at 1 for partition until detected clear
                
                    # For the motor speed function--this will leave us with two objects, one tracking the most recent partition pass, and one 
                    # tracking the partition pass right beore that
                    if self.last_partition_time != None:
                        self.before_last_partition_time = self.last_partition_time
                    self.last_partition_time = time.monotonic() #record the time, resetting the self.last_partition_time object

                    if self.before_last_partition_time != None: # Once we have two values, we can track the time between them!
                        self.time_between_partitions = self.last_partition_time - self.before_last_partition_time
                    print("Partition!")
                #else:
                    #print("Partition still there")
            else:
                if self.state == 1:
                    self.state = 0 # Once partition detected clear, switch back to "not-detected" state
                    print("Partition cleared")
                    #print("Moving")
                #else:
                    #print("Moving")

    async def get_time_since_last_partition(self):
        #"""returns the time since the last partition"""
        if self.last_partition_time is None:
            return None   # No partition has been detected yet
        return time.monotonic() - self.last_partition_time
    
    async def get_motor_speed(self):
        """returns the motor speed in RPM"""
        while True:
            self.motor_speed_rpm = (self.time_between_partitions * 6)/60

            # Save the speed to the tracker table so you can go back a bit and average if needed; save along with timestamp
            self.speed_history.append([self.motor_speed_rpm, time.monotonic()])

            # Calculate the average motor speed for the past number of samples--set using SAMPLES variable
            if len(self.speed_history) >= SAMPLES:
                recent_speeds = [entry[0] for entry in self.speed_history[-SAMPLES:]]
                self.motor_speed_rpm_avg = sum(recent_speeds) / len(recent_speeds)

            # Clear old entries to prevent the list from growing indefinitely
            if len(self.speed_history) > HISTORY_LENGTH * SAMPLES:
                self.speed_history = self.speed_history[-HISTORY_LENGTH * SAMPLES:]

            await asyncio.sleep(SPEED_TIMING_ACCURACY_THRESHOLD)