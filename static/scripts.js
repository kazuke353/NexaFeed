function formatContent(item) {
  let content = item.content;
  const originalLink = item.original_link;
  const videoId = item.video_id;

  if (!content) {
    content = "No content available";
  } else {
    const tempDiv = document.createElement("div");
    tempDiv.innerHTML = content;

    // Convert URLs to clickable links
    convertURLsToLinks(tempDiv);

    content = tempDiv.innerHTML;

    // Check if videoId is present
    if (videoId) {
      // Check if originalLink contains 'youtube'
      if (originalLink.includes("youtube")) {
        content = `${initializePipedPlayer(videoId, originalLink)}${content}`;
      } else if (originalLink.includes("reddit")) {
        handleRedditMedia(originalLink)
          .then((redditMedia) => {
            if (redditMedia) {
              // Reddit video
              if (
                redditMedia.includes(".png") ||
                redditMedia.includes(".gif")
              ) {
                const img = document.createElement("img");
                img.src = redditMedia;
                img.setAttribute("loading", "lazy");
                content = `${img.outerHTML}${content}`;
              } else if (redditMedia["reddit_video"]) {
                const video = document.createElement("video");
                video.src = redditMedia["reddit_video"]["fallback_url"];
                video.controls = true;
                video.setAttribute("loading", "lazy");
                content = `${video.outerHTML}${content}`;
              } else if (redditMedia["oembed"]) {
                const redditHTML = redditMedia["oembed"]["html"];
                content = `${redditHTML}${content}`;
              } else {
                const video = document.createElement("video");
                video.src = redditMedia;
                video.controls = true;
                video.setAttribute("loading", "lazy");
                content = `${video.outerHTML}${content}`;
              }
            }
          })
          .catch((err) => {
            console.error("Error:", err);
          });
      }
    }

    // Append a link to the original page, if available and not already present
    content = `${content}<br><br><a href="${originalLink}" target="_blank">[link]</a>`;
  }

  return content;
}

function convertURLsToLinks(tempDiv) {
  const textNodes = Array.from(tempDiv.childNodes).filter(
    (node) => node.nodeType === 3
  ); // Text nodes

  textNodes.forEach((textNode) => {
    const parent = textNode.parentNode;
    const textContent = textNode.nodeValue;
    const newTextContent = textContent.replace(
      /(https?:\/\/[^\s]+)/g,
      '<a href="$1" target="_blank">$1</a>'
    );
    const newHTML = document.createElement("span");
    newHTML.innerHTML = newTextContent.replace(/\n/g, "<br>"); // Preserve line breaks
    parent.replaceChild(newHTML, textNode);
  });
}

function initializePipedPlayer(videoId, originalLink) {
  const iframeContainer = createDivWithClass("iframe-container");
  const responsiveIframe = createDivWithClass("responsive-iframe");
  responsiveIframe.id = `pipedPlayer-${videoId}`;

  // Construct the Piped embed URL
  const pipedEmbedUrl = `https://piped.kavin.rocks/embed/${videoId}`;

  // Set up the iframe element
  const iframe = document.createElement("iframe");
  iframe.setAttribute("src", pipedEmbedUrl);
  iframe.setAttribute("width", "560"); // Set the width as needed
  iframe.setAttribute("height", "315"); // Set the height as needed
  iframe.setAttribute("frameborder", "0");
  iframe.setAttribute(
    "allow",
    "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
  );
  iframe.setAttribute("allowfullscreen", true);
  iframe.setAttribute("loading", "lazy");

  responsiveIframe.appendChild(iframe);
  iframeContainer.appendChild(responsiveIframe);

  return iframeContainer.outerHTML;
}

function createDivWithClass(className) {
  const div = document.createElement("div");
  div.className = className;
  return div;
}

function handleRedditMedia(originalLink) {
  const apiUrl = `/api/reddit/${btoa(originalLink)}`;
  return fetch(apiUrl)
    .then((response) => response.json())
    .then((data) => {
      console.log("Data: ", data);
      return data.media;
    })
    .catch((error) => {
      console.error("Error fetching:", error);
    });
}

function isMobileDevice() {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent
  );
}

function exitFullscreen() {
  const exitFullscreen =
    document.exitFullscreen ||
    document.mozCancelFullScreen ||
    document.webkitExitFullscreen ||
    document.msExitFullscreen;
  exitFullscreen.call(document);
}

// Function to stop the video in the modal
function stopVideo() {
  exitFullscreen();
  const iframe = document.querySelector(".modal-body iframe");
  if (iframe) {
    const iframeSrc = iframe.src;
    iframe.src = iframeSrc; // This will effectively reload the iframe, stopping the video
  }
}

window.changeTheme = function (themeName) {
  const themes = {
    latte: {
      "--bs-primary": "#dd7878", // Red
      "--bs-secondary": "#8839ef", // Lavender
      "--bs-success": "#a3be8c", // Green
      "--bs-info": "#81a1c1", // Blue
      "--bs-warning": "#e5c07b", // Yellow
      "--bs-danger": "#d20f39", // Red (more intense)
      "--bs-light": "#f5e0dc", // Surface 2
      "--bs-dark": "#495057", // Crust
      "--bs-blue": "#0d6efd", // Blue
      "--bs-indigo": "#6610f2", // Lavender (for lack of a closer match)
      "--bs-purple": "#6f42c1", // Lavender
      "--bs-pink": "#d63384", // Rosewater
      "--bs-red": "#dc3545", // Red
      "--bs-orange": "#fd7e14", // Peach
      "--bs-yellow": "#ffc107", // Yellow
      "--bs-green": "#198754", // Green
      "--bs-teal": "#20c997", // Teal
      "--bs-cyan": "#0dcaf0", // Teal (for lack of a closer match)
      "--bs-black": "#000", // Base
      "--bs-white": "#fff", // Surface 2
      "--bs-gray": "#6c757d", // Subtext 1
      "--bs-gray-dark": "#343a40", // Crust
      "--bs-gray-100": "#f8f9fa", // Surface 2 (lighter)
      "--bs-gray-200": "#e9ecef", // Surface 1
      "--bs-gray-300": "#dee2e6", // Surface 0
      "--bs-gray-400": "#ced4da", // Subtext 1 (lighter)
      "--bs-gray-500": "#adb5bd", // Subtext 0
      "--bs-gray-600": "#6c757d", // Subtext 1
      "--bs-gray-700": "#495057", // Mantle
      "--bs-gray-800": "#343a40", // Crust
      "--bs-gray-900": "#212529", // Base
      "--bs-primary-rgb": "221,120,120", // Red (RGB)
      "--bs-secondary-rgb": "114,92,108", // Mauve (RGB)
      "--bs-success-rgb": "163,190,140", // Green (RGB)
      "--bs-info-rgb": "129,161,193", // Blue (RGB)
      "--bs-warning-rgb": "229,192,123", // Yellow (RGB)
      "--bs-danger-rgb": "210,15,57", // Red (more intense, RGB)
      "--bs-light-rgb": "245,224,220", // Surface 2 (RGB)
      "--bs-dark-rgb": "73,80,87", // Crust (RGB)
      "--bs-primary-text": "#dd7878", // Red
      "--bs-secondary-text": "#b4be82", // Green (for lack of a closer match)
      "--bs-success-text": "#a3be8c", // Green
      "--bs-info-text": "#81a1c1", // Blue
      "--bs-warning-text": "#e5c07b", // Yellow
      "--bs-danger-text": "#e27878", // Red
      "--bs-light-text": "#d8dee9", // Surface 1 (for lack of a closer match)
      "--bs-dark-text": "#cdd6e3", // Surface 0 (for lack of a closer match)
      "--bs-primary-bg-subtle": "#f5e0dc", // Surface 2 (lighter)
      "--bs-secondary-bg-subtle": "#faf4ed", // Surface 2 (lightest)
      "--bs-success-bg-subtle": "#d1e7dd", // Green (lighter)
      "--bs-info-bg-subtle": "#cff4fc", // Blue (lighter)
      "--bs-warning-bg-subtle": "#fff3cd", // Yellow (lighter)
      "--bs-danger-bg-subtle": "#f8d7da", // Red (lighter)
      "--bs-light-bg-subtle": "#fcfcfd", // Surface 2 (lightest)
      "--bs-dark-bg-subtle": "#ced4da", // Subtext 1 (lighter)
      "--bs-primary-border-subtle": "#dd7878", // Red
      "--bs-secondary-border-subtle": "#a3be8c", // Green
      "--bs-success-border-subtle": "#a3be8c", // Green
      "--bs-info-border-subtle": "#81a1c1", // Blue
      "--bs-warning-border-subtle": "#e5c07b", // Yellow
      "--bs-danger-border-subtle": "#e27878", // Red
      "--bs-light-border-subtle": "#d8dee9", // Surface 1 (for lack of a closer match)
      "--bs-dark-border-subtle": "#cdd6e3", // Surface 0 (for lack of a closer match)
      "--bs-white-rgb": "255,255,255", // Surface 2 (RGB)
      "--bs-black-rgb": "48,52,63", // Base (RGB)
      "--bs-body-color-rgb": "48,52,63", // Base (RGB)
      "--bs-body-bg-rgb": "245,224,220", // Surface 2 (RGB)
      "--bs-body-color": "#30343f", // Base
      "--bs-emphasis-color": "#000", // Base
      "--bs-emphasis-color-rgb": "48,52,63", // Base (RGB)
      "--bs-secondary-color": "rgba(48, 52, 63, 0.75)", // Base with opacity
      "--bs-secondary-color-rgb": "114,92,108", // Mauve (RGB)
      "--bs-secondary-bg": "#b4be82", // Green (for lack of a closer match)
      "--bs-secondary-bg-rgb": "180,190,130", // Green (RGB, for lack of a closer match)
      "--bs-tertiary-color": "rgba(114, 92, 108, 0.5)", // Mauve with opacity
      "--bs-tertiary-color-rgb": "114, 92, 108", // Mauve (RGB)
      "--bs-tertiary-bg": "#d8dee9", // Surface 1 (for lack of a closer match)
      "--bs-tertiary-bg-rgb": "216, 222, 233", // Surface 1 (RGB, for lack of a closer match)
      "--bs-body-bg": "#f5e0dc", // Surface 2
      "--bs-body-bg-rgb": "245, 224, 220", // Surface 2 (RGB)
      "--bs-link-color": "#81a1c1", // Blue
      "--bs-link-color-rgb": "129, 161, 193", // Blue (RGB)
      "--bs-link-hover-color": "#7190b0", // Blue (slightly darker, for lack of a closer match)
      "--bs-link-hover-color-rgb": "113, 144, 176", // Blue (slightly darker, RGB)
      "--bs-code-color": "#d63384", // Rosewater
      "--bs-highlight-bg": "#fff3cd", // Yellow (lighter)
      "--bs-border-color": "#ced4da", // Subtext 1 (lighter)
      "--bs-border-color-translucent": "rgba(48, 52, 63, 0.175)", // Base with opacity
      "--bs-box-shadow": "0 0.5rem 1rem rgba(48, 52, 63, 0.15)", // Base (RGB) with opacity for shadow
      "--bs-box-shadow-sm": "0 0.125rem 0.25rem rgba(48, 52, 63, 0.075)", // Base (RGB) with lower opacity
      "--bs-box-shadow-lg": "0 1rem 3rem rgba(48, 52, 63, 0.175)", // Base (RGB) with opacity for large shadow
      "--bs-box-shadow-inset": "inset 0 1px 2px rgba(48, 52, 63, 0.075)", // Base (RGB) with lower opacity for inset
      "--bs-emphasis-color": "#30343f", // Base
      "--bs-form-control-bg": "var(--bs-body-bg)", // Using the same as body background
      "--bs-form-control-disabled-bg": "var(--bs-secondary-bg)", // Using the same as secondary background
      "--bs-highlight-bg": "#fff3cd", // Yellow (lighter)
    },
    frappe: {
      "--bs-primary": "#eebebe", // Example value for Flamingo (Frappe palette)
      "--bs-secondary": "#ca9ee6", // Example value for Mauve (Frappe palette)
      "--bs-success": "#a6d189", // Example value for Green (Frappe palette)
      "--bs-info": "#99d1db", // Example value for Sky (Frappe palette)
      "--bs-warning": "#f5a97f", // Example value for Peach (Frappe palette)
      "--bs-danger": "#e78284", // Example value for Red (Frappe palette)
      "--bs-light": "#f4dbd6", // Example value for Rosewater (Frappe palette)
      // Add more custom properties as needed
    },
    macchiato: {
      "--bs-primary": "#DDB6F2",
      "--bs-secondary": "#ABE9B3",
      "--bs-success": "#B8FA68",
      "--bs-info": "#8AADF4",
      "--bs-warning": "#FAE3B0",
      "--bs-danger": "#F2CDCD",
      "--bs-light": "#C6D0F5",
      "--bs-black": "#6E6C7E",
    },
    mocha: {
      "--bs-primary": "#f5c2e7", // Example value for Pink (Mocha palette)
      "--bs-secondary": "#89dceb", // Example value for Sky (Mocha palette)
      "--bs-success": "#a6e3a1", // Example value for Green (Mocha palette)
      "--bs-info": "#94e2d5", // Example value for Teal (Mocha palette)
      "--bs-warning": "#fab387", // Example value for Peach (Mocha palette)
      "--bs-danger": "#f38ba8", // Example value for Red (Mocha palette)
      "--bs-light": "#f5e0dc", // Example value for Rosewater (Mocha palette)
      // Add more custom properties as needed
    },
    // Additional themes can be defined here
  };

  const root = document.documentElement;
  const themeElements = document.querySelectorAll('[data-bs-theme="light"]');

  if (themeName in themes) {
    // Apply each color in the theme to the root style and theme elements
    Object.entries(themes[themeName]).forEach(([key, value]) => {
      // Set property on root
      root.style.setProperty(key, value, "!important");

      // Set property on all elements with the data-bs-theme attribute
      themeElements.forEach(element => {
        element.style.setProperty(key, value, "!important");
      });
    });

    localStorage.setItem("selectedTheme", themeName);
  } else {
    console.warn(
      `The theme "${themeName}" is not defined. Falling back to "latte".`
    );
    changeTheme("latte");
  }
};

window.onload = function () {
  const savedTheme = localStorage.getItem("selectedTheme") || "latte";
  changeTheme(String(savedTheme));
};

function formatToLocalTime(dateString) {
  const date = new Date(dateString);
  if (!date) return dateString;
  return new Intl.DateTimeFormat("default", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

function truncateTagsBasedOnWidth(tagsContainerSelector) {
  const tagsContainers = document.querySelectorAll(tagsContainerSelector);

  tagsContainers.forEach((container) => {
    let containerWidth = container.offsetWidth;
    let currentWidth = 0;
    let tags = container.querySelectorAll(".badge");

    tags.forEach((tag, index) => {
      currentWidth += tag.offsetWidth;
      if (currentWidth > containerWidth && index !== tags.length - 1) {
        // Create and append ellipsis span
        let ellipsisSpan = document.createElement("span");
        ellipsisSpan.className = "badge badge-truncate";
        ellipsisSpan.textContent = "...";
        container.appendChild(ellipsisSpan);
        return; // Exit the loop
      }
    });
  });
}

function truncateText(textElement, maxHeight) {
  let text = textElement.innerText;
  let currentHeight = textElement.offsetHeight;

  if (currentHeight <= maxHeight) {
    return; // No truncation needed
  }

  // Estimate the average character height and calculate the approximate overage
  const avgCharHeight = currentHeight / text.length;
  const overage = Math.ceil((currentHeight - maxHeight) / avgCharHeight);

  // Remove the estimated overage in characters
  text = text.slice(0, -overage);

  // Apply the rough truncation
  textElement.innerText = text.trim() + "...";
  currentHeight = textElement.offsetHeight;

  // Fine-tune the truncation one character at a time
  while (currentHeight > maxHeight && text.length > 0) {
    text = text.slice(0, -1);
    textElement.innerText = text.trim() + "...";
    currentHeight = textElement.offsetHeight;
  }
}

function calculateBadgesHeight(card) {
  const badges = card.querySelectorAll(".badge"); // Replace with your actual badge selector
  let totalHeight = 0;
  let currentTopOffset = 0;
  badges.forEach((badge, index) => {
    if (index === 0 || badge.offsetTop > currentTopOffset) {
      totalHeight += badge.offsetHeight;
      currentTopOffset = badge.offsetTop;
    }
    const style = window.getComputedStyle(badge);
    totalHeight += parseInt(style.marginTop) + parseInt(style.marginBottom);
  });
  return totalHeight;
}

function adjustCardSizesAndTruncateText(cardsPerRow, rowsInView) {
  const cards = Array.from(document.querySelectorAll(".card"));
  const availableHeightForRows = window.innerHeight;
  const maxCardHeight = Math.min(650, availableHeightForRows / rowsInView);

  cards.forEach((card) => {
    const cardContentElements = card.querySelectorAll(
      ".card-title, .card-creator, .card-pd, .card-footer" // Include .card-footer if that's the class for your footer
    );
    let usedHeight = 0;

    cardContentElements.forEach((el) => {
      usedHeight += el.offsetHeight;
    });

    const elDate = card.querySelector(".card-pd");
    const utcDate = elDate.textContent;
    const localDate = formatToLocalTime(utcDate);
    elDate.textContent = localDate;

    const imageElement = card.querySelector("img");
    const imageHeight = imageElement ? imageElement.offsetHeight : 0;
    usedHeight += imageHeight;

    usedHeight += calculateBadgesHeight(card);

    // Assuming .card-footer is the class for your "View More" footer
    const footerElement = card.querySelector(".card-footer");
    const footerHeight = footerElement ? footerElement.offsetHeight : 0;
    usedHeight += footerHeight;

    const cardTextElement = card.querySelector(".card-text");
    if (cardTextElement) {
      const padding =
        parseInt(getComputedStyle(cardTextElement).paddingTop) +
        parseInt(getComputedStyle(cardTextElement).paddingBottom);
      const textMaxHeight = maxCardHeight - usedHeight - padding - 20; // Adjust the 20px if more or less space is needed
      truncateText(cardTextElement, textMaxHeight);
    }
  });
}

function handleResize() {
  const navbarHeight = document.getElementById("navbar").offsetHeight;
  document.documentElement.style.setProperty(
    "--navbar-height",
    `${navbarHeight}px`
  );

  let cardsPerRow = 4;
  let rowsInView = 2;
  if (window.innerWidth < 1200 && window.innerWidth >= 768) {
    cardsPerRow = 2;
    rowsInView = 1; // Adjust rows in view if the screen is medium size
  } else {
    cardsPerRow = 1;
    rowsInView = 1;
  }

  adjustCardSizesAndTruncateText(cardsPerRow, rowsInView);
}

document.addEventListener("DOMContentLoaded", () => handleResize());
window.addEventListener("load", () => handleResize());
window.addEventListener("resize", () => handleResize());
