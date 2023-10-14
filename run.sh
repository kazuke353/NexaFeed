#!/bin/bash

# Parse command line arguments
FORCE_INSTALL=false
USE_SSL=false
HEADLESS=false

while [ "$1" != "" ]; do
    case $1 in
        -f | --force )    FORCE_INSTALL=true
                          ;;
        -s | --ssl )      USE_SSL=true
                          ;;
        --headless )      HEADLESS=true
                          ;;
    esac
    shift
done

# Function to check if a command exists
command_exists () {
  type "$1" &> /dev/null ;
}

# Function to kill process by PID
kill_process() {
  if [ -f "$1" ]; then
    kill -9 $(cat "$1")
    rm -f "$1"
  fi
}

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

# Force install requirements if flag is set
if [ "$FORCE_INSTALL" = true ]; then
  pip install -r requirements.txt --force-reinstall
elif [ ! -f "requirements_installed" ]; then
  pip install -r requirements.txt
  touch requirements_installed
fi

# Check for SSL certificates and create if not exists
if [ "$USE_SSL" = true ]; then
  [ ! -f "cert.pem" ] && openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"
fi

# Kill existing processes
kill_process "app_pid.txt"


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

# Create a runner script in the home directory if it doesn't exist
if [ ! -f "~/run_rss.sh" ]; then
  echo "#!/bin/bash" > ~/run_rss.sh
  echo "cd $(pwd)" >> ~/run_rss.sh
  echo "./run.sh" >> ~/run_rss.sh
  chmod +x ~/run_rss.sh
fi
