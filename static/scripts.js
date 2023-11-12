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
                content = `${initializePipedPlayer(
                    videoId,
                    originalLink
                )}${content}`;
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
                                video.src =
                                    redditMedia["reddit_video"]["fallback_url"];
                                video.controls = true;
                                video.setAttribute("loading", "lazy");
                                content = `${video.outerHTML}${content}`;
                            } else if (redditMedia["oembed"]) {
                                const redditHTML =
                                    redditMedia["oembed"]["html"];
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
    const iframe = document.createElement('iframe');
    iframe.setAttribute('src', pipedEmbedUrl);
    iframe.setAttribute('width', '560'); // Set the width as needed
    iframe.setAttribute('height', '315'); // Set the height as needed
    iframe.setAttribute('frameborder', '0');
    iframe.setAttribute('allow', 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture');
    iframe.setAttribute('allowfullscreen', true);
    iframe.setAttribute('loading', 'lazy');

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

window.changeTheme = function (theme) {
    const root = document.documentElement;
    localStorage.setItem("selectedTheme", theme);

    // Define a helper function to clear existing styles
    function clearThemeStyles() {
        root.style.removeProperty("--primary-color");
        root.style.removeProperty("--secondary-color");
        root.style.removeProperty("--background-color");
        root.style.removeProperty("--text-color");
        root.style.removeProperty("--secondary-bg-color");
        root.style.removeProperty("--title-color");
        root.style.removeProperty("--accent-color");
        root.style.removeProperty("--highlight-color");
        root.style.removeProperty("--link-color");
    }

    switch (theme) {
        case "light":
            clearThemeStyles(); // Clear any existing theme styles
            root.style.setProperty("--primary-color", "#0066ff");
            root.style.setProperty("--secondary-color", "#ffcc00");
            root.style.setProperty("--background-color", "#f3f3f3");
            root.style.setProperty("--text-color", "#333333");
            root.style.setProperty("--secondary-bg-color", "#dddddd");
            root.style.setProperty("--title-color", "#000000");
            root.style.setProperty("--border-color-1", "#cccccc"); // Light grey for borders
            root.style.setProperty("--border-color-2", "#e6e6e6"); // Even lighter grey for secondary borders
            break;
        case "dark":
            clearThemeStyles();
            root.style.setProperty("--primary-color", "#ffffff");
            root.style.setProperty("--secondary-color", "#5e5e5e");
            root.style.setProperty("--background-color", "#333333");
            root.style.setProperty("--text-color", "#f3f3f3");
            root.style.setProperty("--secondary-bg-color", "#242424");
            root.style.setProperty("--title-color", "#ffffff");
            root.style.setProperty("--border-color-1", "#4c4c4c"); // Dark grey for borders
            root.style.setProperty("--border-color-2", "#666666"); // Medium grey for secondary borders
            break;
        case "latte":
            clearThemeStyles();
            root.style.setProperty("--primary-color", "#E5C07B"); // Soft Brown
            root.style.setProperty("--secondary-color", "#7E9CD8"); // Soft Blue
            root.style.setProperty("--background-color", "#FDF0ED"); // Cream White
            root.style.setProperty("--text-color", "#4C4F69"); // Deep Lavender
            root.style.setProperty("--secondary-bg-color", "#F0EDE3"); // Light Cream
            root.style.setProperty("--title-color", "#4C4F69"); // Deep Lavender
            root.style.setProperty("--border-color-1", "#DDBB99"); // A light brown for borders
            root.style.setProperty("--border-color-2", "#CDAF91"); // A darker shade of light brown for secondary borders
            break;
        case "frappe":
            clearThemeStyles();
            root.style.setProperty("--primary-color", "#A6E3A1"); // Soft Green
            root.style.setProperty("--secondary-color", "#F28FAD"); // Soft Pink
            root.style.setProperty("--background-color", "#303446"); // Dark Slate
            root.style.setProperty("--text-color", "#F2D5CF"); // Light Rose
            root.style.setProperty("--secondary-bg-color", "#3C415E"); // Dark Lavender
            root.style.setProperty("--title-color", "#F2D5CF"); // Light Rose
            root.style.setProperty("--border-color-1", "#B4A5A5"); // A muted pink for borders
            root.style.setProperty("--border-color-2", "#9E9494"); // A darker shade for secondary borders
            break;
        case "macchiato":
            clearThemeStyles();
            root.style.setProperty("--primary-color", "#EB6F92"); // Soft Red
            root.style.setProperty("--secondary-color", "#F9C2A2"); // Soft Orange
            root.style.setProperty("--background-color", "#24273A"); // Deep Blue
            root.style.setProperty("--text-color", "#CAD3F5"); // Light Periwinkle
            root.style.setProperty("--secondary-bg-color", "#2D2F41"); // Dark Periwinkle
            root.style.setProperty("--title-color", "#CAD3F5"); // Light Periwinkle
            root.style.setProperty("--border-color-1", "#F3C1D3"); // A light red/pink for borders
            root.style.setProperty("--border-color-2", "#F7DAD1"); // A lighter shade for secondary borders
            break;
        case "mocha":
            clearThemeStyles();
            root.style.setProperty("--primary-color", "#AB9DF2"); // Soft Purple
            root.style.setProperty("--secondary-color", "#F8BD96"); // Soft Peach
            root.style.setProperty("--background-color", "#1E1E2E"); // Very Dark Blue
            root.style.setProperty("--text-color", "#CDD6F4"); // Light Lavender
            root.style.setProperty("--secondary-bg-color", "#282A3A"); // Dark Lavender
            root.style.setProperty("--title-color", "#CDD6F4"); // Light Lavender
            root.style.setProperty("--border-color-1", "#9D8DD0"); // A light purple for borders
            root.style.setProperty("--border-color-2", "#EFBBA6"); // A light peach for secondary borders
            break;
        default:
            clearThemeStyles();
            // Fallback to light theme
            root.style.setProperty("--primary-color", "#0066ff");
            root.style.setProperty("--secondary-color", "#ffcc00");
            root.style.setProperty("--background-color", "#f3f3f3");
            root.style.setProperty("--text-color", "#333333");
            root.style.setProperty("--secondary-bg-color", "#dddddd");
            root.style.setProperty("--title-color", "#000000");
            root.style.setProperty("--border-color-1", "#cccccc"); // Light grey for borders
            root.style.setProperty("--border-color-2", "#e6e6e6"); // Even lighter grey for secondary borders
    }
};

window.onload = function () {
    const savedTheme = localStorage.getItem("selectedTheme");
    if (savedTheme) {
        changeTheme(savedTheme); // Apply the saved theme
    }
};

function formatToLocalTime(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('default', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
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
    const badges = card.querySelectorAll('.badge'); // Replace with your actual badge selector
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

        const elDate = card.querySelector('.card-pd');
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
            const textMaxHeight =
                maxCardHeight - usedHeight - padding - 20; // Adjust the 20px if more or less space is needed
            truncateText(cardTextElement, textMaxHeight);
        }
    });
}

function handleResize() {
    const navbarHeight = document.getElementById('navbar').offsetHeight;
    document.documentElement.style.setProperty('--navbar-height', `${navbarHeight}px`);

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