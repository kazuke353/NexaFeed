import subprocess
import json
import requests
from time import sleep

class NgrokManager:
    def __init__(self, token: str, port: int):
        self.token = token
        self.port = port
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

    def start_ngrok(self) -> str:
        command = f"ngrok authtoken {self.token} && ngrok http {self.port}"
        subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        sleep(3)  # Give ngrok time to initialize
        running, public_url = self.is_ngrok_running()
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
