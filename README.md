# NexaFeed 📰🔍

![License](https://img.shields.io/badge/license-MIT-blue)
![Python Version](https://img.shields.io/badge/python-3.x-blue)

> **Your one-stop solution for staying updated with the world.**

## Table of Contents
- [Why I Started NexaFeed](#why-i-started-nexafeed)
- [Introduction](#introduction)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Caching](#caching)
- [Roadmap](#roadmap)
- [License](#license)

## Why I Started NexaFeed

Hey, glad you're here! Let me tell you a bit about why I felt the need to build NexaFeed.

### The Struggle Is Real
You know how it goes, right? We're living in an information-rich era, but finding a single platform that bundles everything up just the way you want it is a real challenge. I was on the same boat, struggling to keep up with things like the latest security breaches, privacy news, and much more.

### Unlimited Access
So, the first thing I wanted was more than what platforms like Feedly could offer. Those 100 RSS feed caps for the free plan weren't cutting it for me. I needed a platform that could grow as my interests and needs did.

### YouTube, Anytime, Anywhere
Switching platforms to stay updated with YouTube was a hassle. I wanted that integrated right into NexaFeed.

### Any Device, Any Time
One of the best things about NexaFeed being a web app is that you can use it on any device that has a web browser. Your content will always be within reach.

## Introduction

NexaFeed is a web-based RSS feed aggregator that allows you to stay updated with your favorite websites, all in one place. Built with Quart, Jinja2, Bootstrap, and Alpine.js, it offers a clean UI and various features to enhance your feed reading experience.

![Screenshot](screenshot.png)

## NexaFeed: Streamlined and Powerful Web-based RSS Feed Reader

### Key Features

- **YouTube Integration**: Effortlessly watch YouTube videos directly within NexaFeed.
- **Categorical Organization**: Streamline your browsing experience with customizable categories, making feed navigation intuitive and efficient.
- **Advanced Cache Management**: Experience faster feed loading with our sophisticated caching system, ensuring a seamless and quick content retrieval.
- **Simple OPML Import**: Seamlessly transition to NexaFeed by importing your existing subscriptions. Just drop any .opml file into the designated folder, and you're set!
- **Responsive Design for Modern Users**: Enjoy a consistent and fluid experience across all devices, thanks to our adaptive design that looks great on any screen size.
- **High-Efficiency Infinite Scroll**: Powered by Alpine.js, NexaFeed's lightweight infinite scroll feature enhances your browsing without compromising on performance.
- **Smart Autoclean Functionality**: Keep your feed clean and efficient. Autoclean automatically removes inaccessible or non-responsive feeds, ensuring a streamlined experience.
- **Truly Cross-Platform**: NexaFeed's web-based nature means you can stay informed and entertained on any device with a web browser. From desktops to smartphones, your content is always within reach, further enhanced by the freedom to use your favorite browser extensions.

Experience the future of feed reading with NexaFeed – Your gateway to organized, efficient, and enjoyable content consumption.

<h2 id="tech-stack">Tech Stack 🛠️</h2>

### Backend
- Python: The core programming language for server-side logic.
- Quart: Asynchronous Python web microframework.
- feedparser: Library for parsing RSS/Atom feeds.
- pyngrok: Tool to expose local servers to the public internet securely.
- cachetools: Caching mechanisms for Python functions.
- python-dateutil: Library for parsing and manipulating dates and times.
- requests: Library for making HTTP requests.
- user_agent: Library for parsing and generating user agent strings.
- lxml: Library for XML and HTML parsing.
- aiohttp: Library for asynchronous HTTP requests in Python.
- ruamel.yaml: Library for YAML parsing and manipulation.

### Frontend
- Bootstrap: Frontend framework for responsive design.
- Alpine.js: Minimal JavaScript framework for reactive components.

### Templating
- Jinja2: Templating engine for Python.

### Database
- PostgreSQL: Object-relational database system for secure and scalable storage.

Our mission with NexaFeed was to craft a self-hosted solution that doesn't just meet but exceeds your expectations. Customizable, robust, and user-friendly - NexaFeed is more than an RSS reader; it's a testament to what modern web technologies can achieve.

Dive into the project and explore how these technologies harmonize to deliver an unparalleled content consumption experience.

---

## Prerequisites

Before you begin, ensure you have **Python 3.9 or higher** installed on your system. You can check your Python version using:

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

## Caching

NexaFeed employs a straightforward caching mechanism to accelerate feed loading times.

## Roadmap

Here are some upcoming features and improvements planned for NexaFeed:

### Planned Features

- &#10006; **Reddit Video Embed**: Support for embedding Reddit videos directly into the feed.
- &#10006; **Add/Remove RSS Feeds**: The ability to add and remove RSS feeds directly within the web app.
- &#10006; **Category Management**: Create, edit, and remove categories for better feed organization.
- &#10004; **RSS Feed Names**: Display the names of the RSS feeds alongside the tags, maintaining a consistent style.
- &#10006; **Mark as Read**: Functionality to mark articles as read.
- &#10006; **Video Watch Time**: Save the watched time of videos and restore it when revisiting.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
