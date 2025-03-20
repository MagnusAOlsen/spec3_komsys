import random
from stmpy import Machine, Driver
import logging

class CrashDetection:
    def __init__(self):
        pass  # Removed infinite loop; STM will handle state transitions

    def on_sense(self):
        while True:
            velocity = random.randint(1, 100)
            if 1 <= velocity <= 5:
                print('CRASH!!!!')
                self.crash_detected()
            else:
                print('Not a crash')

    def crash_detected(self):
        print('15 seconds before ambulance is called. Push button if safe')
        push = False

        if not push:
            
        
    def send_distress(self):
        print("Sending distress signal!")

    def alarm_on(self):
        print("Alarm activated!")

    def alarm_off(self):
        print("Alarm deactivated!")

    def stop_distress(self):
        print("Stopping distress signal!")


# Instantiate CrashDetection object
crash_detection = CrashDetection()

# Define state transitions
t0 = {'source': 'initial', 'target': 'standby'}

t1 = {'trigger': 'crash',
      'source': 'standby',
      'target': 'crash_detected',
      'effect': 'start_timer("timer", 15000)'}

t2 = {'trigger': 't',
      'source': 'crash_detected',
      'target': 'distress',
      'effect': 'send_distress; alarm_on'}

t3 = {'trigger': 'safe',
      'source': 'crash_detected',
      'target': 'standby',
      'effect': 'stop_timer'}

t4 = {'trigger': 'safe',
      'source': 'distress',  # Fixed typo
      'target': 'standby',
      'effect': 'alarm_off; stop_distress'}

transitions = [t0, t1, t2, t3, t4]

# Create state machine
stm_crash_detection = Machine(name='stm_crash_detection', transitions=transitions, obj=crash_detection)
crash_detection.stm = stm_crash_detection

# Configure logging
logger = logging.getLogger('stmpy.Driver')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

logger = logging.getLogger('stmpy.Machine')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

# Start the STM driver
driver = Driver()
driver.add_machine(stm_crash_detection)
driver.start()
crash_detection.on_sense()