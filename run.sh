#!/bin/bash
# Change the directory to the script's location
cd "$(dirname "$0")"

# Check if the repo is already cloned
if [ ! -d ".git" ]; then
    # Check if the current directory is empty
    if [ -z "$(ls -A .)" ]; then
        # If empty, clone the repository into the current directory
        git clone https://github.com/kazuke353/NexaFeed.git .
    else
        # If not empty, clone the repo into a new directory and cd into it
        git clone https://github.com/kazuke353/NexaFeed.git NexaFeed
        cd NexaFeed
        # Remove the original run.sh from the parent directory
        rm ../run.sh
    fi
fi

# Parse command line arguments
FORCE_INSTALL=false
USE_SSL=false
HEADLESS=false

# Get the modification time of requirements.txt
REQUIREMENTS_MODIFIED=$(stat -c %Y requirements.txt 2>/dev/null)
# Get the last installed time from a marker file
LAST_INSTALLED=$(cat .last_installed 2>/dev/null)

while [ "$1" != "" ]; do
    case $1 in
        -f | --force )    FORCE_INSTALL=true
                          ;;
        -s | --ssl )      USE_SSL=true
                          ;;
        --headless )      HEADLESS=true
                          ;;
        -n | --ngrok )    NGROK=true
                          ;;
        -d | --dry-run )  DRYRUN=true
                          ;;
    esac
    shift
done

set_env_variable() {
  local var_name="$1"
  local prompt_message="$2"
  local already_set_message="${3-}"  # Default to unset if not provided.
  local env_file=".env"

  if ! grep -q "^$var_name=" "$env_file" 2>/dev/null; then
    read -p "$prompt_message" var_value
    echo
    echo "$var_name=$var_value" >> "$env_file"
    chmod 600 "$env_file"
  else
    # Check if the message is not an empty string.
    if [ -n "$already_set_message" ]; then
      # Use the provided message or default if not provided.
      echo "${already_set_message:-"$var_name already set."}"
    fi
  fi
}

# Function to check if a command exists
command_exists () {
  type "$1" &> /dev/null ;
}

# Function to check if a process with a given name is running
is_process_running() {
  pgrep -x "$1" > /dev/null
}

# Function to kill a process by name
kill_process_by_name() {
  if is_process_running "$1"; then
    killall "$1"
  fi
}

# Function to kill process by PID
kill_process_by_pid_file() {
  if [ -f "$1" ]; then
    kill -9 $(cat "$1")
    rm -f "$1"
  fi
}

# Kill existing processes
kill_process_by_pid_file "app_pid.txt"
kill_process_by_name "python3"
kill_process_by_name "ngrok"


if [ "$NGROK" = true ]; then
  set_env_variable "NGROK_TOKEN" "Enter your ngrok token: " "Ngrok token already set up you can remove the -n | --ngrok argument"
fi

set_env_variable "DB_USER" "Enter your database user: " ""
set_env_variable "DB_PASS" "Enter your database password: " ""

# Function to install necessary packages based on the distro
install_packages () {
  if [ -f "/etc/os-release" ]; then
    . /etc/os-release
    case $ID in
      ubuntu|debian|pop)
        sudo apt update
        sudo apt install -y python3 python3-pip python3-venv openssl
        ;;
      fedora)
        sudo dnf install -y python3 python3-pip python3-virtualenv openssl
        ;;
      centos)
        sudo yum install -y python3 python3-pip python3-virtualenv openssl
        ;;
      arch)
        sudo pacman -Syu python python-pip python-virtualenv openssl
        ;;
      *)
        echo "Distro not recognized. Please install python3, python3-pip, python3-venv, and openssl manually."
        exit 1
        ;;
    esac
  else
    echo "Distro not recognized. Please install python3, python3-pip, python3-venv, and openssl manually."
    exit 1
  fi
}

# Check for Python3 and pip3, install if not exists
if ! command_exists python3 || ! command_exists pip3; then
  install_packages
fi

# Activate virtual environment if it exists, else create one
if [ -d "venv" ]; then
  source venv/bin/activate
else
  python3 -m venv venv
  source venv/bin/activate
fi

# Check if FORCE_INSTALL is set or if requirements.txt was modified after last install
if [ "$FORCE_INSTALL" = true ] || [ -z "$LAST_INSTALLED" ] || [ "$REQUIREMENTS_MODIFIED" -gt "$LAST_INSTALLED" ]; then
  if [ "$FORCE_INSTALL" = true ]; then
    pip install -r requirements.txt --force-reinstall
  else
    pip install -r requirements.txt
  fi
  echo $(date +%s) > .last_installed
fi

# Check for SSL certificates and create if not exists
if [ "$USE_SSL" = true ]; then
  [ ! -f "cert.pem" ] && openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"
fi

# Create a runner script in the home directory if it doesn't exist
if [ ! -f "$HOME/run_rss.sh" ]; then
  echo "#!/bin/bash" > "$HOME/run_rss.sh"
  # Use the absolute path for cd command
  echo "cd \"$(pwd)\"" >> "$HOME/run_rss.sh"
  # Assuming run.sh is in the current directory at the time of this script execution
  echo "\"$(pwd)/run.sh\" \"\$@\"" >> "$HOME/run_rss.sh"
  chmod +x "$HOME/run_rss.sh"
fi

if [ "$DRYRUN" != "true" ]; then
  # Run the application based on the arguments
  if [ "$HEADLESS" = true ]; then
    if [ "$USE_SSL" = "true" ]; then
      nohup python3 main_ssl.py --certfile=cert.pem --keyfile=key.pem > app.log 2>&1 &
    else
      nohup python3 main.py > app.log 2>&1 &
    fi
    echo $! > "app_pid.txt"
  else
    if [ "$USE_SSL" = "true" ]; then
      python3 main_ssl.py --certfile=cert.pem --keyfile=key.pem
    else
      python3 main.py
    fi
  fi
fi
