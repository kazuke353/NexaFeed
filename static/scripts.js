function feedManager() {
    return feedManager_func;
}

const feedManager_func = {
    currentCategory: "main",
    searchQuery: "",
    feedCache: {},
    lastId: null,
    lastPd: null,
    loading: false,
    lastSearch: "",

    changeTheme: window.changeTheme,

    init(isSearch = false) {
        console.log('INIT');
        if (isSearch) {
            this.clearCacheAndFeeds();
        }
        this.fetchFeeds(this.currentCategory);
    },

    clearCacheAndFeeds() {
        this.lastId = null;
        this.lastPd = null;
        this.feedCache = {};
        document.querySelector(".feed-container").innerHTML = "";
    },

    search() {
        this.searchQuery = document.getElementById("search-box").value.trim();
        if (this.searchQuery.length > 0) {
            this.clearCacheAndFeeds();
            this.fetchFeeds(this.currentCategory);
        } else {
            this.init();
        }
    },

    async fetchFeeds(category) {
        try {
            console.log('CALLED');
            let url = `/api/fetch/${category}`;
            const queryParams = [];
            if (this.lastSearch && (this.searchQuery.length == 0 || this.searchQuery != this.lastSearch))
            {
                this.clearCacheAndFeeds();
            }
            if (this.searchQuery.length > 0) {
                queryParams.push(`q=${encodeURIComponent(this.searchQuery)}`);
            }
            if (this.lastId) {
                queryParams.push(`last_id=${encodeURIComponent(this.lastId)}`);
            }
            if (this.lastPd) {
                queryParams.push(`last_pd=${encodeURIComponent(this.lastPd)}`);
            }
            if (queryParams.length > 0) {
                url += "?"
            }
            url += queryParams.join('&');
            const response = await fetch(url);
            // Check if the response header is 'application/json'
            if (response.headers.get("content-type").includes("application/json")) {
                const data = await response.json();
                const html = data.html;
                const lastId = data.last_page[0];
                const lastPd = data.last_page[1];
                this.feedCache[category] = (this.feedCache[category] || "") + html;
                document.querySelector(".feed-container").innerHTML = this.feedCache[category];
                this.lastId = lastId;
                this.lastPd = lastPd;
            } else {
                // If response is not JSON, handle it here
                console.error('Response is not JSON:', await response.text());
            }
        } catch (error) {
            console.error(`Error fetching feeds for ${category}:`, error);
        }
    },

    handleScroll() {
      if (this.loading) return;
    
      let { scrollTop, scrollHeight, clientHeight } = document.documentElement;
      let atBottom = Math.ceil(scrollTop + clientHeight) >= scrollHeight;
    
      if (atBottom) {
        this.loading = true;
        this.fetchFeeds(this.currentCategory).then(() => {
            console.log('SCROLLING');
            this.loading = false;
        });
      }
    },

    highlightActiveCategory() {
        document.querySelectorAll("#nav-left a").forEach((link) => {
            link.classList.remove("active");
        });
        document.getElementById(this.currentCategory).classList.add("active");
    },

    goBack() {
        this.searchQuery = "";
        document.getElementById("search-box").value = this.searchQuery;
        this.init(true);
    },
};

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".nav-link").forEach((link) => {
        link.addEventListener("click", function () {
            document.querySelectorAll(".nav-link").forEach((innerLink) => {
                innerLink.classList.remove("active");
            });
            link.classList.add("active");
        });
    });
});

let autoFullscreen = true;
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
                content = `${initializeYouTubePlayer(
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

function initializeYouTubePlayer(videoId, originalLink) {
    const iframeContainer = createDivWithClass("iframe-container");
    const responsiveIframe = createDivWithClass("responsive-iframe");
    responsiveIframe.id = `youtubePlayer-${videoId}`;
    responsiveIframe.setAttribute("loading", "lazy");
    iframeContainer.appendChild(responsiveIframe);

    fetchSponsoredSegments(videoId, responsiveIframe).then(() => {
        const player = new YT.Player(responsiveIframe.id, {
            videoId: videoId,
            playerVars: {
                autoplay: 0,
                controls: 1,
                showinfo: 1,
            },
        });
    });

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

function fetchSponsoredSegments(videoId, youtubePlayer) {
    console.log(youtubePlayer);
    const apiUrl = `/api/sponsorblock/${videoId}`;

    return fetch(apiUrl)
        .then((response) => response.json())
        .then((data) => {
            const sponsoredSegments = data.segments;
            console.log("Segments: ", sponsoredSegments);

            if (sponsoredSegments && sponsoredSegments.length > 0) {
                const checkInterval = setInterval(() => {
                    const currentTime = youtubePlayer.getCurrentTime();

                    sponsoredSegments.forEach((segment) => {
                        if (
                            currentTime >= segment.start &&
                            currentTime <= segment.end
                        ) {
                            youtubePlayer.seekTo(segment.end);
                        }
                    });
                }, 1000);

                youtubePlayer.addEventListener("onStateChange", (event) => {
                    if (event.data === YT.PlayerState.ENDED) {
                        clearInterval(checkInterval);
                    }
                });

                return true; // There are sponsor segments
            } else {
                return false; // No sponsor segments
            }
        })
        .catch((error) => {
            console.error("Error fetching sponsored segments:", error);
            throw error;
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
    autoFullscreen = true;
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
