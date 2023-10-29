# NexaFeed 📰🔍

![License](https://img.shields.io/badge/license-MIT-blue)
![Python Version](https://img.shields.io/badge/python-3.x-blue)

> **Your one-stop solution for staying updated with the world.**

## Table of Contents
- [Why I Started NexaFeed](#why-i-started-nexafeed)
- [Introduction](#introduction)
- [Features](#features)
- [Tech Stack](#tech-stack-)
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

## Features

- **YouTube videos**: Supports watching YouTube videos.
- **Multiple Categories**: Organize your feeds into various categories for easier navigation.
- **Cache Management**: Speed up feed loading times with built-in caching.
- **OPML Import**: Easily import your existing subscriptions.
- **Responsive Design**: Works seamlessly on various screen sizes.
- **Cross-Platform**: Being a web-based application, NexaFeed is accessible on any device with a web browser, offering you the ultimate flexibility in how and where you consume your content.

## Tech Stack 🛠

This project is built with a variety of technologies to make it robust, scalable, and easy to use. Here's a rundown of the tech stack:

- **Backend**
  - [Python](https://www.python.org/): The programming language used for server-side logic.
  - [Quart](https://pgjones.gitlab.io/quart/): A Python web microframework based on Asyncio.
  - Python and Quart. Python for its versatility and Quart for its asyncio capabilities, which make it really fast.

- **Frontend**
  - [Bootstrap](https://getbootstrap.com/): A popular CSS framework for responsive design.
  - [Alpine.js](https://alpinejs.dev/): A minimal JavaScript framework for composing JavaScript behavior in HTML.
  - Bootstrap and Alpine.js. Bootstrap to ensure the app is responsive and works well on any device. Alpine.js to manage frontend logic without making things too complicated.

- **Templating**
  - [Jinja2](https://jinja.palletsprojects.com/): A modern and designer-friendly templating engine for Python.
  - Jinja2. It's straightforward, powerful, and integrates really well with Python.

The idea was to create a self-hosted solution that you could customize as per your needs, without any compromises.
Feel free to explore the project to see how these technologies are used!

## Prerequisites

- Python 3.9 or higher

## Installation

1. **Clone the Repository**: Start by cloning the GitHub repository to your local machine.

    ```bash
    git clone https://github.com/kazuke353/NexaFeed.git
    ```

2. **Navigate to the Project Directory**: Change your current directory to the NexaFeed directory.

    ```bash
    cd NexaFeed
    ```

3. **Configure RSS Feeds**: Open the `config.yaml` file to add or remove the RSS feeds you wish to include. The file includes some default feeds to get you started.

    ```yaml
    # config.yaml example snippet
    rss_feeds:
      - https://example1.com/rss
      - https://example2.com/rss
    ```

4. **Optional: Add ngrok Token**: If you want to expose your local server to the Internet using ngrok, you can add your ngrok token in the `config.yaml` file.

    ```yaml
    # config.yaml example snippet
    ngrok_token: "your-ngrok-token-here"
    ```

5. **Run the Application**: Use the `run.sh` script to install necessary packages and run the application. This script will take care of installing dependencies and booting up the server.

    ```bash
    chmod +x run.sh && ./run.sh
    ```

> **Note**: The `run.sh` script automates several tasks like installing dependencies and starting the Python app, making the setup process smoother.

## Usage

1. **Access NexaFeed**: Open your web browser and navigate to `http://127.0.0.1:5000/` to access the NexaFeed UI.

2. **Interact with UI**: Use the User Interface to read your RSS articles, watch YouTube videos, and manage your content categories.

3. **Optional: Access via ngrok**: If you've set up ngrok, you can also access NexaFeed via the ngrok URL, which will be displayed in the console when the app starts.

## Configuration

Configuration settings can be modified in `config.yaml`. Here, you can configure cache duration, database settings, RSS feeds, and more.

## Caching

NexaFeed employs a straightforward caching mechanism to accelerate feed loading times.

## Roadmap

Here are some upcoming features and improvements planned for NexaFeed:

### Planned Features

- **Reddit Video Embed**: Support for embedding Reddit videos directly into the feed.
- **Add/Remove RSS Feeds**: The ability to add and remove RSS feeds directly within the web app.
- **Category Management**: Create, edit, and remove categories for better feed organization.
- **RSS Feed Names**: Display the names of the RSS feeds alongside the tags, maintaining a consistent style.
- **Mark as Read**: Functionality to mark articles as read.
- **Video Watch Time**: Save the watched time of videos and restore it when revisiting.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
