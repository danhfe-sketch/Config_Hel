import sys, time
p = r'c:\Users\helde\Documents\Engenharia\products\configurador'
if p not in sys.path:
    sys.path.insert(0,p)

from main import App
import threading

class DummyLog:
    def log_message(self, m):
        print('LOG>', m.strip())

class DummySerial:
    def __init__(self):
        self.writes = []
        self.in_waiting = 0
    def write(self, b):
        print('DUMMY_SERIAL_WRITE:', b)
        self.writes.append(b)

# Run the app in a thread so we can schedule actions
app = App()

# Replace app.serial_service.serial_port with dummy and mark connected
app.serial_service.serial_port = DummySerial()
app.serial_service.is_connected = True

# Schedule send_all_parameters after short delay once mainloop starts
def schedule_send():
    print('Scheduling bulk send in 1s')
    def do_send():
        print('Calling send_all_parameters()')
        app.serial_service.send_all_parameters()
    app.after(1000, do_send)

app.after(500, schedule_send)

# Run mainloop briefly to exercise the flow then stop
def run_app():
    # Let the GUI run for a few seconds to process the bulk send
    app.after(5000, app.destroy)
    app.mainloop()

run_app()
print('App run completed')
