import os
import signal
import subprocess
import time
import json
import requests

class NgrokManager:
    pid_file = 'ngrok.pid'

    def __init__(self, token: str, port: int):
        self.token = token
        self.port = port
        self.process = None
        self.api_url = "http://localhost:4040/api/tunnels"

    def is_ngrok_running(self) -> (bool, str):
        try:
            response = requests.get(self.api_url)
            if response.status_code == 200:
                tunnels = json.loads(response.text)["tunnels"]
                for tunnel in tunnels:
                    if tunnel['proto'] == 'https':
                        return True, tunnel['public_url']
        except requests.exceptions.RequestException:
            pass
        return False, ""

    def start_ngrok(self):
        command = f"ngrok authtoken {self.token} && ngrok http {self.port}"
        self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, preexec_fn=os.setsid)
        time.sleep(3)  # Give ngrok time to initialize
        running, public_url = self.is_ngrok_running()

        with open(self.pid_file, 'w') as f:
            f.write(str(self.process.pid))

        if running:
            return public_url
        else:
            raise Exception("Failed to start ngrok")

    def manage_ngrok(self) -> str:
        running, public_url = self.is_ngrok_running()
        if running:
            return public_url
        else:
            return self.start_ngrok()

    def terminate_ngrok(self):
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read())
            os.killpg(os.getpgid(pid), signal.SIGTERM)
            os.remove(self.pid_file)
            print("ngrok has been terminated successfully.")
        except FileNotFoundError:
            print("No ngrok process id file found.")
        except ProcessLookupError:
            print("ngrok process was not found.")
        except Exception as e:
            print(f"An error occurred: {e}")
