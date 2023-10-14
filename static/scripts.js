function feedManager() {
  return {
    currentCategory: 'main',
    feedCache: {},
    page: 1,
    loading: false,

    init() {
      this.fetchFeeds(this.currentCategory);
      this.setupCategoryListeners();
    },

    setupCategoryListeners() {
      document.querySelectorAll("#nav-left a").forEach(link => {
        link.addEventListener("click", (e) => {
          e.preventDefault();
          this.currentCategory = e.target.getAttribute("data-category");
          this.page = 1;  // Reset page number
          this.feedCache = {};  // Clear cache
          this.fetchFeeds(this.currentCategory);
          this.highlightActiveCategory();
        });
      });
    },

    async fetchFeeds(category) {
      console.log("fetchFeeds called", category, this.page);  // Debug log
    
      try {
        const response = await fetch(`/${category}/page/${this.page}`);
        const html = await response.text();
        this.feedCache[category] = (this.feedCache[category] || "") + html;
        document.querySelector('.feed-container').innerHTML = this.feedCache[category];
      } catch (error) {
        console.error(`Error fetching feeds for ${category}:`, error);
      }
    },

    highlightActiveCategory() {
      document.querySelectorAll("#nav-left a").forEach(link => {
        link.classList.remove("active");
      });
      document.getElementById(this.currentCategory).classList.add("active");
    },

    handleScroll() {
      console.log("Scroll event fired", this.loading);  // Debug log
      if (this.loading) return;

      let { scrollTop, scrollHeight, clientHeight } = document.documentElement;
      let atBottom = Math.ceil(scrollTop + clientHeight) >= scrollHeight - 200;

      if (atBottom) {
        this.loading = true;
        this.page++;
        console.log("Incremented page to", this.page);  // Debug log
        this.fetchFeeds(this.currentCategory).then(() => {
          this.loading = false;
          console.log("Feeds loaded, setting loading to false");  // Debug log
        });
      }
    }
  };
}

function formatContent(item) {
  let content = item.content;
  let originalLink = item.original_link;
  let videoId = item.video_id;

  if (!content) {
    content = 'No content available';
  } else {
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = content;

    // Safely convert URLs to clickable links
    const textNodes = Array.from(tempDiv.childNodes).filter(node => node.nodeType === 3); // Text nodes

    textNodes.forEach(textNode => {
      const parent = textNode.parentNode;
      const textContent = textNode.nodeValue;
      const newTextContent = textContent.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
      const newHTML = document.createElement('span');
      newHTML.innerHTML = newTextContent.replace(/\n/g, '<br>'); // Preserve line breaks
      parent.replaceChild(newHTML, textNode);
    });

    content = tempDiv.innerHTML;

    // Check if originalLink contains 'youtube' and videoId is present
    if (originalLink.includes('youtube') && videoId) {
      // Create a div for the iframe-container
      const iframeContainer = document.createElement('div');
      iframeContainer.className = 'iframe-container';
      const responsiveIframe = document.createElement('div');
      responsiveIframe.className = 'responsive-iframe';
      responsiveIframe.id = `youtubePlayer-${videoId}`;
      responsiveIframe.setAttribute('loading', 'lazy');
      iframeContainer.appendChild(responsiveIframe);

      // Initialize YouTube player after appending to DOM
      setTimeout(() => {
        const player = new YT.Player(responsiveIframe.id, {
          videoId: videoId,
          playerVars: {
            "controls": 1,
            "showinfo": 1,
          },
          events: {
            "onReady": (event) => {
              const url = new URL(originalLink);
              const vId = new URLSearchParams(url.search).get("v");
              fetchSponsoredSegments(vId, event.target);
            },
            "onStateChange": (event) => {
              if (event.data === YT.PlayerState.PLAYING) {
                // Video is playing, go fullscreen
                const iframe = event.target.getIframe();
                if (iframe.requestFullscreen) {
                  iframe.requestFullscreen();
                } else if (iframe.mozRequestFullScreen) { // Firefox
                  iframe.mozRequestFullScreen();
                } else if (iframe.webkitRequestFullscreen) { // Chrome, Safari and Opera
                  iframe.webkitRequestFullscreen();
                } else if (iframe.msRequestFullscreen) { // IE/Edge
                  iframe.msRequestFullscreen();
                }
              }
              if (event.data === YT.PlayerState.ENDED || event.data === YT.PlayerState.PAUSED) {
                // Video ended or paused, exit fullscreen
                if (document.exitFullscreen) {
                  document.exitFullscreen();
                } else if (document.mozCancelFullScreen) { // Firefox
                  document.mozCancelFullScreen();
                } else if (document.webkitExitFullscreen) { // Chrome, Safari and Opera
                  document.webkitExitFullscreen();
                } else if (document.msExitFullscreen) { // IE/Edge
                  document.msExitFullscreen();
                }
              }
            }
          }
        });
      }, 0);

      // Prepend iframe-container to the content
      content = `${iframeContainer.outerHTML}${content}`;
    }

    // Append a link to the original page, if available and not already present
    if (originalLink && !tempDiv.innerHTML.includes(originalLink)) {
      content = `${content}<br><br><a href="${originalLink}" target="_blank">[link]</a>`;
    }
  }

  return content;
}

function fetchSponsoredSegments(videoId, youtubePlayer) {
  const apiUrl = `/api/sponsorblock/${videoId}`;

  fetch(apiUrl)
    .then(response => response.json())
    .then(data => {
      const sponsoredSegments = data.segments;
      console.log("Segments: ", sponsoredSegments);

      // Initialize an interval to continuously check the video time
      const checkInterval = setInterval(() => {
        const currentTime = youtubePlayer.getCurrentTime();
        
        sponsoredSegments.forEach(segment => {
          if (currentTime >= segment.start && currentTime <= segment.end) {
            youtubePlayer.seekTo(segment.end);
          }
        });
      }, 1000); // Check every second

      youtubePlayer.addEventListener('onStateChange', (event) => {
        if (event.data === YT.PlayerState.ENDED) {
          clearInterval(checkInterval); // Clear the interval when the video ends
        }
      });
    })
    .catch(error => {
      console.error('Error fetching sponsored segments:', error);
    });
}

// Function to exit fullscreen mode
function exitFullscreen() {
  if (document.exitFullscreen) {
    document.exitFullscreen();
  } else if (document.mozCancelFullScreen) { /* Firefox */
    document.mozCancelFullScreen();
  } else if (document.webkitExitFullscreen) { /* Chrome, Safari and Opera */
    document.webkitExitFullscreen();
  } else if (document.msExitFullscreen) { /* IE/Edge */
    document.msExitFullscreen();
  }
}

// Function to stop the video in the modal
function stopVideo() {
  const iframe = document.querySelector('.modal-body iframe');
  if (iframe) {
    const iframeSrc = iframe.src;
    iframe.src = iframeSrc;  // This will effectively reload the iframe, stopping the video
  }
}