import sys, time
p = r'c:\Users\helde\Documents\Engenharia\products\configurador'
if p not in sys.path:
    sys.path.insert(0,p)
from services.serial_service import SerialService

class DummyLog:
    def log_message(self, m):
        print('LOG>', m.strip())

class DummyApp:
    def __init__(self):
        self.log_frame = DummyLog()

class DummySerial:
    def __init__(self):
        self.writes = []
        self.in_waiting = 0
    def write(self, b):
        print('DUMMY_SERIAL_WRITE:', b)
        self.writes.append(b)

app = DummyApp()
svc = SerialService(app)
# mark connected and provide dummy serial port
svc.is_connected = True
svc.serial_port = DummySerial()

commands = [
    'ATSMS:APN,allcom.br,allcom,allcom#',
    'ATSMS:SERVER,0,201.72.200.130,7012,0#'
]

# queue and start processing
svc.queue_commands(commands, command_types=[None, None], delay=0.2)

# wait for processing to finish with timeout
timeout = 10
start = time.time()
while svc.queue_processing and (time.time() - start) < timeout:
    time.sleep(0.1)

print('DONE. queued processing:', svc.queue_processing)
print('Writes captured:', len(svc.serial_port.writes))
for w in svc.serial_port.writes:
    print('->', w)
