document.addEventListener('alpine:init', () => {
    Alpine.data('feedManager', () => ({
        feedCache: {},
        feedUpdateTimer: null,
        lastId: null,
        lastPd: null,
        loading: false,
        searchQuery: "",
        lastSearch: "",

        paginateFetchedFeed: async function (category, isInit = false, feed = null) {
            this.loading = true;
            try {
                if (feed) {
                    this.clearCacheAndFeeds();
                    const feed_items = feed;

                    this.updateUI(feed_items, category, true);
                } else {
                    let url = `/api/fetch/${category}`;
                    const queryParams = [];
                    if (
                        isInit ||
                        (this.lastSearch &&
                            (this.searchQuery.length == 0 ||
                                this.searchQuery != this.lastSearch))
                    ) {
                        this.clearCacheAndFeeds();
                    }
                    if (this.searchQuery.length > 0) {
                        queryParams.push(
                            `q=${encodeURIComponent(this.searchQuery)}`
                        );
                    }
                    if (this.lastId) {
                        queryParams.push(
                            `last_id=${encodeURIComponent(this.lastId)}`
                        );
                    }
                    if (this.lastPd) {
                        queryParams.push(
                            `last_pd=${encodeURIComponent(this.lastPd)}`
                        );
                    }
                    if (isInit) {
                        queryParams.push(
                            `force_init=${encodeURIComponent(isInit)}`
                        );
                    }
                    if (queryParams.length > 0) {
                        url += "?";
                    }
                    url += queryParams.join("&");

                    const response = await this.callFetch(url);
                    if (response.isJson) {
                        const data = response.data;
                        console.log("Data:", data);
                    
                        this.updateUI(data.feed_items, category, isInit);
                    } else if (!isInit) {
                        console.log("Fetching feeds again");
                        this.paginateFetchedFeed(category, true);
                    } else {
                        console.error(
                            "Response is not JSON:",
                            response.data
                        );
                    }
                }
                handleResize();
            } catch (error) {
                console.error(`Error fetching feeds for ${category}:`, error);
            } finally {
                this.loading = false;
            }
        },

        clearCacheAndFeeds: function () {
            this.updateUI("", null, true);
            this.updateLastIds(null, null);
        },

        updateUI: function (feed_items, category = null, isInit = false) {
          if (!category) {
            category = Alpine.store("sharedState").getCurrentCategory();
          }
          if (isInit || !(category in this.feedCache)) {
            this.feedCache[category] = [];
          }
        
          // Add the new feed items to the feed_cache
          this.feedCache[category] = this.feedCache[category].concat(feed_items);
        
          // Update the feed_items array in the sharedState store
          Alpine.store("sharedState").feed_items = this.feedCache[category];
        
          // Update the last_id and last_pd for pagination if we have entries
          if (feed_items && feed_items.length > 0) {
            // Assuming feed_items is an array and each item is an object
            const last_entry = feed_items[feed_items.length - 1];
            const last_id = last_entry.id;
            const last_pd = last_entry.published_date;
            this.updateLastIds(last_id, last_pd);
          }
        },

        updateLastIds: function (newLastId, newLastPd) {
            this.lastId = newLastId;
            this.lastPd = newLastPd;
        },

        handleScroll: function () {
            if (this.loading) return;
        
            // Get the feed container element
            const feedContainer = document.getElementById("feed-container-inner");
            if (!feedContainer) return;
        
            // Get the scroll position and height properties
            const { scrollTop, scrollHeight, clientHeight } = feedContainer;
        
            // Check if the bottom of the feed container is reached
            const atBottom = Math.ceil(scrollTop + clientHeight) >= scrollHeight - 300;
        
            if (atBottom) {
                this.loading = true;
                this.paginateFetchedFeed(Alpine.store("sharedState").getCurrentCategory())
            }
        },        

        goBack: function (category_id = null) {
            this.searchQuery = "";
            document.getElementById("search-box").value = this.searchQuery;
            this.paginateFetchedFeed((category_id || Alpine.store("sharedState").getCurrentCategory()));
        },

        startFeedUpdates: function () {
            this.stopFeedUpdates();

            const checkForUpdates = async () => {
                const url = `/api/fetch/${Alpine.store("sharedState").getCurrentCategory()}?force_init=True`;
                const response = await this.callFetch(url);

                if (response.isJson) {
                    const data = response.data;
                    const html = data.html;
                    const newContentExists = this.checkForNewContent(html);
                
                    if (newContentExists && !this.feedCache[Alpine.store("sharedState").getCurrentCategory()]) {
                        this.paginateFetchedFeed(Alpine.store("sharedState").getCurrentCategory(), true, data);
                    } else if (newContentExists) {
                        this.showNotification();
                        fetchedFeed = data;
                    }
                } else {
                    console.error(
                        "Response is not JSON:",
                        response.data
                    );
                }

                setTimeout(checkForUpdates, 600000);
            };

            checkForUpdates();
        },

        checkForNewContent: function (html) {
            const currentFeedCache = this.feedCache[Alpine.store("sharedState").getCurrentCategory()];

            if (!currentFeedCache) {
                return true;
            }

            const currentEntries = currentFeedCache.split("</div>");
            const currentFirstEntry = currentEntries[0];
            const fetchedEntries = html.split("</div>");
            const fetchedFirstEntry = fetchedEntries[0];

            return fetchedFirstEntry !== currentFirstEntry;
        },

        stopFeedUpdates: function () {
            if (this.feedUpdateTimer) {
                clearInterval(this.feedUpdateTimer);
                this.feedUpdateTimer = null;
            }
        },

        showNotification: function () {
            const notification = document.getElementById("notification");
            notification.classList.remove("d-none");
        },

        hideNotification: function () {
            const notification = document.getElementById("notification");
            notification.classList.add("d-none");
        },

        callFetch: async function (url) {
            const response = await fetch(url);
            if (response.headers.get("content-type").includes("application/json")) {
                const data = await response.json();
                return { data: data, isJson: true };
            }
            const textData = await response.text();
            return { data: textData, isJson: false };
        },        

        initFeed: function (isInit = false) {
            this.waitForCurrentCategory(() => {
                this.paginateFetchedFeed(Alpine.store("sharedState").getCurrentCategory(), isInit);
                //this.startFeedUpdates();
            });

            const notification = document.getElementById("notification");
            notification.addEventListener("click", () => {
                this.hideNotification();
                this.paginateFetchedFeed(Alpine.store("sharedState").getCurrentCategory(), true, fetchedFeed);
            });
        },

        waitForCurrentCategory: function (callback) {
            if (Alpine.store("sharedState").getCurrentCategory()) {
                callback();
            } else {
                const intervalId = setInterval(() => {
                    if (Alpine.store("sharedState").getCurrentCategory()) {
                        clearInterval(intervalId);
                        callback();
                    }
                }, 1000);
            }
        },

        search: function (query = null, category = null) {
            // Convert query to string if it's not already
            if (typeof query !== 'string') {
                query = String(query);
            }
            this.searchQuery = (query || document.getElementById("search-box").value).trim();
        
            // Determine the category value
            let categoryValue;
            if (typeof category === 'number') {
                // Use the category directly if it's a number
                categoryValue = category;
            } else if (category && category.id !== undefined) {
                // If category contains an 'id', use that
                categoryValue = category.id;
            } else {
                // Otherwise, get the current category from the Alpine store
                categoryValue = Alpine.store("sharedState").getCurrentCategory();
            }
        
            // Paginate the fetched feed based on the determined values
            this.paginateFetchedFeed(categoryValue, this.searchQuery.length > 0);
        },

        openModal: function (item) {
            item.open = true;
            this.toggleScroll(false);
            if (!item.contentFormatted) {
                item.formattedContent = formatContent(item);
                item.contentFormatted = true;
            }
        },

        closeModal: function (item) {
            this.toggleScroll(true);
            stopVideo();
            item.open = false;
        },

        toggleScroll: function (status) {
            if (!status) {
                document.body.classList.add("no-scroll");
            } else {
                document.body.classList.remove("no-scroll");
            }
        },
    }));
});