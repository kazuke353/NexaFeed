import os
import signal
import subprocess
import json
import aiohttp
import asyncio

class NgrokManager:
    pid_file = 'ngrok.pid'

    def __init__(self, token: str, port: int):
        self.token = token
        self.port = port
        self.process = None
        self.api_url = "http://localhost:4040/api/tunnels"

    async def is_ngrok_running(self) -> (bool, str):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(self.api_url) as response:
                    if response.status == 200:
                        tunnels = json.loads(await response.text())["tunnels"]
                        for tunnel in tunnels:
                            if tunnel['proto'] == 'https':
                                return True, tunnel['public_url']
            except aiohttp.ClientError:
                pass
        return False, ""

    async def start_ngrok(self):
        os.system(f"ngrok authtoken {self.token}")  # Separate command execution
        command = f"ngrok http {self.port}"
        self.process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, preexec_fn=os.setsid)

        await asyncio.sleep(3)  # Non-blocking sleep

        running, public_url = await self.is_ngrok_running()
        if running:
            with open(self.pid_file, 'w') as f:
                f.write(str(self.process.pid))
            return public_url
        else:
            raise Exception("Failed to start ngrok")

    async def manage_ngrok(self) -> str:
        running, public_url = await self.is_ngrok_running()
        if running:
            return public_url
        else:
            return await self.start_ngrok()

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
