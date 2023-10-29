function feedManager() {
  return feedManager_func;
}

const feedManager_func = {
  currentCategory: 'main',
  searchQuery: '',
  feedCache: {},
  page: 1,
  prevPage: 1,
  loading: false,

  init(isSearch = false) {
    if (isSearch) {
      this.clearCacheAndFeeds();
    }
    this.fetchFeeds(this.currentCategory);
    this.setupCategoryListeners();
  },

  clearCacheAndFeeds() {
    this.feedCache = {};
    document.querySelector('.feed-container').innerHTML = '';
  },

  search() {
    this.searchQuery = document.getElementById('search-box').value.trim();
    if (this.searchQuery.length > 0) {
      this.prevPage = this.page;
      this.page = 1;
      this.init(true);
    } else {
      this.page = this.prevPage;
      this.init(true);
    }
  },

  setupCategoryListeners() {
    document.querySelectorAll("#nav-left a").forEach(link => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        this.currentCategory = e.target.getAttribute("data-category");
        this.page = 1;
        this.clearCacheAndFeeds();
        this.fetchFeeds(this.currentCategory);
        this.highlightActiveCategory();
      });
    });
  },

  async fetchFeeds(category) {
    try {
      let url = `/${category}/page/${this.page}`;
      if (this.searchQuery.length > 0) {
        url += `?q=${encodeURIComponent(this.searchQuery)}`;
      }
      const response = await fetch(url);
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
    if (this.loading) return;

    let { scrollTop, scrollHeight, clientHeight } = document.documentElement;
    let atBottom = Math.ceil(scrollTop + clientHeight) >= scrollHeight - 200;

    if (atBottom) {
      this.loading = true;
      this.page++;
      this.fetchFeeds(this.currentCategory).then(() => {
        this.loading = false;
      });
    }
  },

  goBack() {
    this.searchQuery = '';
    document.getElementById('search-box').value = this.searchQuery;
    this.page = this.prevPage;
    this.init(true);
  }
};

document.addEventListener("DOMContentLoaded", function() {
  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', function() {
      document.querySelectorAll('.nav-link').forEach(innerLink => {
        innerLink.classList.remove('active');
      });
      link.classList.add('active');
    });
  });
});

let autoFullscreen = true;
function formatContent(item) {
  let content = item.content;
  const originalLink = item.original_link;
  const videoId = item.video_id;

  if (!content) {
    content = 'No content available';
  } else {
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = content;

    // Convert URLs to clickable links
    convertURLsToLinks(tempDiv);

    content = tempDiv.innerHTML;

    // Check if videoId is present
    if (videoId) {
      // Check if originalLink contains 'youtube'
      if (originalLink.includes('youtube')) {
        content = `${initializeYouTubePlayer(videoId, originalLink)}${content}`;
      } else if (originalLink.includes('reddit')) {
        handleRedditMedia(originalLink).then(redditMedia => {
          if (redditMedia) {
            // Reddit video
            if (redditMedia.includes('.png') || redditMedia.includes('.gif')) {
              const img = document.createElement('img');
              img.src = redditMedia;
              img.setAttribute('loading', 'lazy');
              content = `${img.outerHTML}${content}`;
            } else if (redditMedia['reddit_video']) {
              const video = document.createElement('video');
              video.src = redditMedia['reddit_video']['fallback_url'];
              video.controls = true;
              video.setAttribute('loading', 'lazy');
              content = `${video.outerHTML}${content}`;
            } else if (redditMedia['oembed']) {
              const redditHTML = redditMedia['oembed']['html'];
              content = `${redditHTML}${content}`;
            } else {
              const video = document.createElement('video');
              video.src = redditMedia;
              video.controls = true;
              video.setAttribute('loading', 'lazy');
              content = `${video.outerHTML}${content}`;
            }
          }
        }).catch(err => {
          console.error('Error:', err);
        });
      }
    }

    // Append a link to the original page, if available and not already present
    content = `${content}<br><br><a href="${originalLink}" target="_blank">[link]</a>`;
  }

  return content;
}

function convertURLsToLinks(tempDiv) {
  const textNodes = Array.from(tempDiv.childNodes).filter(node => node.nodeType === 3); // Text nodes

  textNodes.forEach(textNode => {
    const parent = textNode.parentNode;
    const textContent = textNode.nodeValue;
    const newTextContent = textContent.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
    const newHTML = document.createElement('span');
    newHTML.innerHTML = newTextContent.replace(/\n/g, '<br>'); // Preserve line breaks
    parent.replaceChild(newHTML, textNode);
  });
}

function initializeYouTubePlayer(videoId, originalLink) {
  const iframeContainer = createDivWithClass('iframe-container');
  const responsiveIframe = createDivWithClass('responsive-iframe');
  responsiveIframe.id = `youtubePlayer-${videoId}`;
  responsiveIframe.setAttribute('loading', 'lazy');
  iframeContainer.appendChild(responsiveIframe);

  fetchSponsoredSegments(videoId, responsiveIframe)
     .then(() => {
      const player = new YT.Player(responsiveIframe.id, {
        videoId: videoId,
        playerVars: {
            "autoplay": 0,
            "controls": 1,
            "showinfo": 1,
        }
      });
     });

  return iframeContainer.outerHTML;
}

function createDivWithClass(className) {
  const div = document.createElement('div');
  div.className = className;
  return div;
}

function handleRedditMedia(originalLink) {
  const apiUrl = `/api/reddit/${btoa(originalLink)}`;
  return fetch(apiUrl)
    .then(response => response.json())
    .then(data => {
      console.log("Data: ", data);
      return data.media;
    })
    .catch(error => {
      console.error('Error fetching:', error);
    });
}

function fetchSponsoredSegments(videoId, youtubePlayer) {
  console.log(youtubePlayer)
  const apiUrl = `/api/sponsorblock/${videoId}`;

  return fetch(apiUrl)
    .then(response => response.json())
    .then(data => {
      const sponsoredSegments = data.segments;
      console.log("Segments: ", sponsoredSegments);

      if (sponsoredSegments && sponsoredSegments.length > 0) {
        const checkInterval = setInterval(() => {
          const currentTime = youtubePlayer.getCurrentTime();

          sponsoredSegments.forEach(segment => {
            if (currentTime >= segment.start && currentTime <= segment.end) {
              youtubePlayer.seekTo(segment.end);
            }
          });
        }, 1000);

        youtubePlayer.addEventListener('onStateChange', (event) => {
          if (event.data === YT.PlayerState.ENDED) {
            clearInterval(checkInterval);
          }
        });

        return true; // There are sponsor segments
      } else {
        return false; // No sponsor segments
      }
    })
    .catch(error => {
      console.error('Error fetching sponsored segments:', error);
      throw error;
    });
}

function isMobileDevice() {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

function exitFullscreen() {
  const exitFullscreen = document.exitFullscreen || document.mozCancelFullScreen || document.webkitExitFullscreen || document.msExitFullscreen;
  exitFullscreen.call(document);
  autoFullscreen = true;
}

// Function to stop the video in the modal
function stopVideo() {
  exitFullscreen()
  const iframe = document.querySelector('.modal-body iframe');
  if (iframe) {
    const iframeSrc = iframe.src;
    iframe.src = iframeSrc;  // This will effectively reload the iframe, stopping the video
  }
}