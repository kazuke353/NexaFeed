#!/bin/bash
# Change the directory to the script's location
cd "$(dirname "$0")"

# Check if the repo is already cloned
if [ ! -d ".git" ]; then
    # If not empty, clone the repo into a new directory and cd into it
    git clone https://github.com/kazuke353/NexaFeed.git NexaFeed
    cd NexaFeed
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

env_variable_exists() {
  local var_name="$1"
  local env_file=".env"
  if grep -q "^$var_name=" "$env_file" 2>/dev/null; then
    return 0  # Return success if the variable exists
  else
    return 1  # Return failure if the variable does not exist
  fi
}

set_env_variable() {
  local var_name="$1"
  local prompt_message="$2"
  local already_set_message="${3-}"  # Default to unset if not provided.
  local default_value="${4-}"  # New argument for the default value.
  local env_file=".env"

  if ! env_variable_exists "$var_name"; then
    # If prompt_message is empty, set the variable silently using the default value.
    if [ -z "$prompt_message" ]; then
      var_value="$default_value"
    else
      # Include the default value in the prompt message.
      if [ -n "$default_value" ]; then
        prompt_message="${prompt_message} (default: $default_value): "
      else
        prompt_message="${prompt_message}: "
      fi

      read -p "$prompt_message" var_value

      # Use the default value if the input is empty.
      var_value="${var_value:-$default_value}"
    fi

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

# Function to kill process by PID
kill_process_by_pid_file() {
  if [ -f "$1" ]; then
    kill $(cat "$1")
    rm -f "$1"
  fi
}

# Function to check if a command exists
command_exists () {
  command -v "$1" >/dev/null 2>&1
}

# Function to install necessary packages based on the distro
install_python () {
  # If Python3 or pip3 doesn't exist, install necessary packages
  if ! command_exists python3 || ! command_exists pip3; then
    if [ -f "/etc/os-release" ]; then
      . /etc/os-release
      case $ID in
        ubuntu|debian|pop)
          sudo apt update
          sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib
          ;;
        fedora)
          sudo dnf update -y
          sudo dnf install -y python3 python3-pip python3-virtualenv postgresql postgresql-server
          ;;
        centos)
          sudo yum install -y python3 python3-pip python3-virtualenv postgresql-server postgresql-contrib
          ;;
        arch)
          sudo pacman -Syu python python-pip python-virtualenv postgresql
          ;;
        *)
          echo "Distro not recognized. Please install python3, python3-pip and python3-venv manually."
          exit 1
          ;;
      esac
    else
      echo "Distro not recognized. Please install python3, python3-pip and python3-venv manually."
      exit 1
    fi
  fi
}

install_postgresql () {
  if ! command_exists psql; then
    if [ -f "/etc/os-release" ]; then
      . /etc/os-release
      case $ID in
        ubuntu|debian|pop)
          sudo apt update
          sudo apt install -y postgresql postgresql-contrib
          ;;
        fedora)
          sudo dnf update -y
          sudo dnf install -y postgresql postgresql-server
          ;;
        centos)
          sudo yum install -y  postgresql-server postgresql-contrib
          ;;
        arch)
          sudo pacman -Syu postgresql
          ;;
        *)
          echo "Distro not recognized. Please install postgresql manually."
          exit 1
          ;;
      esac
    else
      echo "Distro not recognized. Please install postgresql manually."
      exit 1
    fi
  fi
}

install_python

# Kill existing processes
kill_process_by_pid_file "app_pid.txt"

if [ "$NGROK" = true ]; then
  set_env_variable "NGROK_TOKEN" "Enter your ngrok token: " "Ngrok token already set up you can remove the -n | --ngrok argument"
fi

if ! env_variable_exists "DB_USER" || ! env_variable_exists "DB_PASS" || ! env_variable_exists "DB_HOST" || ! env_variable_exists "DB_PORT" || ! env_variable_exists "DB_NAME"; then
  read -p "Is the PostgreSQL server on another PC? [y/n]: " remote_pc
  if [[ $remote_pc =~ ^[Yy]$ ]]; then
    set_env_variable "DB_USER" "Enter your database user" "" "root"
    echo
    set_env_variable "DB_PASS" "Enter your database password" "" "root"
    echo
    set_env_variable "DB_HOST" "Enter your database host" "" "localhost"
    echo
    set_env_variable "DB_PORT" "Enter your database port" "" "5432"
    echo
    set_env_variable "DB_NAME" "Enter your database name" "" "nexafeed"
  else
    set_env_variable "DB_USER" "" "" "postgres"
    echo
    set_env_variable "DB_PASS" "Enter your database password" "" "root"
    echo
    set_env_variable "DB_HOST" "" "" "localhost"
    echo
    set_env_variable "DB_PORT" "" "" "5432"
    echo
    set_env_variable "DB_NAME" "Enter your database name" "" "nexafeed"
    echo

    source .env
    install_postgresql

    if ! command_exists postgresql-setup; then
        sudo postgresql-setup --initdb
    fi
    sudo systemctl enable --now postgresql.service

    # Configure PostgreSQL with environment variables
    sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD '${DB_PASS}';" 2>/dev/null
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};" 2>/dev/null
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};" 2>/dev/null

    echo "PostgreSQL has been installed and configured."
    echo "The default PostgreSQL user 'postgres' has been modified and set with the provided password."
    echo "Please use these credentials to connect to the PostgreSQL database if you need."
  fi
fi

# Activate virtual environment if it exists, else create one
if [ -d "venv" ]; then
  source venv/bin/activate
else
  python3 -m venv venv
  source venv/bin/activate
fi

# Check if wheel package is installed, if not, install it
if ! pip show wheel > /dev/null; then
    pip install wheel
fi

# Check if FORCE_INSTALL is set or if requirements.txt was modified after last install
if [ "$FORCE_INSTALL" = true ] || [ -z "$LAST_INSTALLED" ] || [ "$REQUIREMENTS_MODIFIED" -gt "$LAST_INSTALLED" ]; then
  if [ "$FORCE_INSTALL" = true ]; then
    pip install -r requirements.txt --use-pep517 --force-reinstall
  else
    pip install -r requirements.txt --use-pep517
  fi
  echo $(date +%s) > .last_installed
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