# NexaFeed 📰🔍

![License](https://img.shields.io/badge/license-MIT-blue)
![Python Version](https://img.shields.io/badge/python-3.9-blue)

> **Your one-stop solution for staying updated with the world.**

## Table of Contents
1. [Introduction](#introduction)
2. [Features](#features)
3. [Tech Stack](#tech-stack)
   - [Backend](#backend)
   - [Frontend](#frontend)
   - [Templating and Database](#database)
4. [Installation](#installation)
   - [Prerequisites](#prerequisites)
   - [Quick Start](#quick-start)
   - [Docker](#docker)
5. [Usage](#usage)
6. [Roadmap](#roadmap)
7. [Contributing](#contributing)
8. [License](#license)
9. [Acknowledgments](#acknowledgments)

## Introduction <a name="introduction"></a>
NexaFeed is a web-based RSS feed aggregator that consolidates your favorite websites into one intuitive interface. Designed with efficiency and user experience in mind, it's built using Quart, Jinja2, Bootstrap, and Alpine.js.

## Features <a name="features"></a>
- **YouTube Integration**: Watch YouTube videos without leaving NexaFeed.
- **Categorical Organization**: Customizable categories for efficient navigation.
- **Advanced Cache Management**: Quick content retrieval with sophisticated caching.
- **Simple OPML Import**: Import your subscriptions with a simple .opml file drop.
- **Responsive Design**: A seamless experience on all devices.
- **High-Efficiency Infinite Scroll**: Browse endlessly with minimal resource use.
- **Smart Autoclean**: Automated maintenance for a clean feed.
- **Cross-Platform**: Accessible on any device with a web browser.

## Tech Stack <a name="tech-stack"></a>
### Backend <a name="backend"></a>
- Python, Quart, feedparser, pyngrok, cachetools, python-dateutil, user_agent, lxml, aiohttp, ruamel.yaml

### Frontend <a name="frontend"></a>
- Bootstrap for responsive design
- Alpine.js for dynamic UI components
- FontAwesome for intuitive icons

### Database <a name="database"></a>
- PostgreSQL for data storage

## Installation <a name="installation"></a>
### Prerequisites <a name="prerequisites"></a>
Ensure you have **Python 3.9 or higher** installed on your system. You can check your Python version using:

  ```bash
  python --version
  ```

## Easy Installation Guide

Get NexaFeed up and running in no time with these simple steps:

1.  **Clone the Repository**: Grab the latest version of NexaFeed from GitHub.

    ```bash
    git clone https://github.com/kazuke353/NexaFeed.git
    ```

2.  **Enter the Nexus**: Dive into your new NexaFeed directory.

    ```bash
    cd NexaFeed
    ```

3.  **Tailor Your Experience**: Customize your RSS feeds in the `config.yaml` file. Start with our curated defaults or add your favorites.

    ```yaml
    # config.yaml example snippet
    main_feed_urls:
     - https://example1.com/rss
     - https://example2.com/rss
    ```

4.  **Enhance with ngrok** _(Optional)_: Want remote access? Add your ngrok token to `config.yaml` for anywhere-access.

    ```yaml
    # config.yaml example snippet
    ngrok:
      token: "your-ngrok-token-here"
    ```

5.  **Launch NexaFeed**: Run `run.sh` to install dependencies and start your journey. This script is your one-click gateway to NexaFeed.

    ```bash
    chmod +x run.sh && ./run.sh
    ```

> **Pro Tip**:
>
> Run the following command in your terminal for a hassle-free installation. This script will clone the repository, copy over opml files and config.yaml file if they exist, install needed Linux packages, handle python dependencies and kick-start NexaFeed for you:
>
> ```bash
> curl -s https://raw.githubusercontent.com/kazuke353/NexaFeed/main/run.sh | bash
> ```

## Docker Installation

For those who prefer using Docker, follow these steps:

1.  **Build with Docker**: Build your Docker image with:

    ```bash
    docker build -t my-nexafeed-app .
    ```

2.  **Run with Docker**: Start your container using:

    ```bash
    docker run -p 5000:5000 my-nexafeed-app
    ```

    Alternatively, you can use Docker Compose:

    ```bash
    docker-compose up
    ```

## How to Use

1. **Enter the Feed World**: Launch a web browser and navigate to `http://127.0.0.1:5000/`. Your personalized NexaFeed dashboard awaits.
2. **Explore and Enjoy**: Browse your RSS articles, catch up on YouTube, and customize categories through the intuitive UI.
3. **Go Global with ngrok** *(Optional)*: If you're using ngrok, your NexaFeed can be accessed anywhere via the ngrok URL displayed in your console.

## Tailoring NexaFeed

Dive into `config.yaml` to fine-tune settings to your liking. Adjust cache timings, manage database configurations, curate RSS feeds, and much more. NexaFeed is not just an RSS reader; it's your personal content haven, customizable to the core.

---

Start your NexaFeed adventure today and redefine how you interact with content online!

## Roadmap

Our ongoing commitment to improvement is outlined in our roadmap:

### Completed Features
- **Category Management**: Limitless creation and customization of feed categories.
- **Add/Remove RSS Feeds**: Manage your RSS feeds directly within the web app.
- **RSS Feed Names**: Consistent display of RSS feed names alongside their tags.

### Upcoming Features
- **Reddit Video Embed**: (30% complete) Integrating Reddit video embedding directly into feed entries.
- **Mark as Read**: (Planned) Easily mark articles as read.
- **Save for Later**: (Planned) Save articles to read at your convenience.
- **Video Watch Time**: (Planned) Save and restore the watch time for videos in your 'Read Later' list.
- **Custom Parser**: (Planned) A tailored parser built on LXML for optimized performance, with feedparser as a fallback.
- **Extensions**: (Planned) Enable community-driven extensions and modifications.
- **Strip Away**: (Planned) Refactor specific functionalities into extensions for a lean core experience.

## Contributing

As an open-source project, we welcome contributions of all forms. Please feel free to submit issues, pull requests, or suggest features.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Acknowledgments

Thanks to all the contributors who have helped shape NexaFeed into what it is today.

## Stay Updated

For the latest updates and feature releases, watch this repository or join our community.