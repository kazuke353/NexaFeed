document.addEventListener('alpine:init', () => {
    Alpine.data('feedManager', () => ({
        feedCache: {},
        feedUpdateTimer: null,
        lastId: null,
        lastPd: null,
        fetching: false,
        loading: false,
        searchQuery: "",
        lastSearch: "",


        shouldClearCache: function (isInit, feed) {
            // Check if cache needs to be cleared based on search query changes
            return isInit || feed ||
                (this.lastSearch.length === 0 && this.searchQuery.length > 0) ||
                (this.lastSearch && this.searchQuery.length === 0) ||
                (this.searchQuery !== this.lastSearch);
        },

        paginateFetchedFeed: async function (category, isInit = false, feed = null) {
            if (this.fetching || this.loading)
            {
                console.log("Already fetching! Skipping this call...", this.fetching, this.loading)
                return;
            }
            this.loading = true;
            try {
                if (this.shouldClearCache(isInit, feed)) {
                    this.clearCacheAndFeeds();
                }
                if (feed) {
                    this.clearCacheAndFeeds();
                    const feed_items = feed;

                    this.updateUI(feed_items, category, true);
                } else {
                    let url = `/api/fetch/${category}`;
                    const queryParams = [];
                    if (this.searchQuery.length > 0) {
                        queryParams.push(
                            `q=${encodeURIComponent(this.searchQuery)}`
                        );
                        this.lastSearch = this.searchQuery
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

                    this.lastSearch = this.searchQuery;
                    const response = await this.callFetch(url);
                    if (response.isJson) {
                        const data = response.data;
                        console.log("Data:", data);
                        console.log("Feed Items:", data.feed_items);

                        if (
                            (!data || !data.feed_items) &&
                            !isInit &&
                            (!(category in this.feedCache) || (category in this.feedCache && this.feedCache[category].length == 0)) &&
                            this.lastSearch.length === 0
                        ) {
                            console.log("Fetching feeds again");
                            this.loading = false;
                            this.paginateFetchedFeed(category, true);
                        } else {
                            this.updateUI(data.feed_items, category, isInit);
                        }
                    } else {
                        console.error(
                            "Response is not JSON:",
                            response.data
                        );
                    }
                }
            } catch (error) {
                console.error(`Error fetching feeds for ${category}:`, error);
            } finally {
                this.loading = false;
            }
        },

        clearCacheAndFeeds: function () {
            this.updateUI(null, null, true);
            this.updateLastEntry(null, null);
        },

        updateUI: function (feed_items, category = null, isInit = false) {
          if (!category) {
            category = Alpine.store("sharedState").getCurrentCategory();
          }
          if (isInit || !(category in this.feedCache)) {
            this.feedCache[category] = [];
          }
        
          // Add the new feed items to the feed_cache
          if (feed_items)
          {
            this.feedCache[category] = this.feedCache[category].concat(feed_items);
          }
          // Update the feed_items array in the sharedState store
          Alpine.store("sharedState").feed_items = this.feedCache[category];
        
          // Update the last_id and last_pd for pagination if we have entries
          if (feed_items && feed_items.length > 0) {
            // Assuming feed_items is an array and each item is an object
            const last_entry = feed_items[feed_items.length - 1];
            this.updateLastEntry(last_entry.id, last_entry.published_date);
          }
        },

        updateLastEntry: function (newLastId, newLastPd) {
            console.log("Last Entry: ", newLastId, newLastPd)
            this.lastId = newLastId;
            this.lastPd = newLastPd;
        },

        handleScroll: function () {
            // Get the feed container element
            const feedContainer = document.getElementById("feed-container");
            if (!feedContainer) return;
        
            // Get the scroll position and height properties
            const { scrollTop, scrollHeight, clientHeight } = feedContainer;
        
            // Check if the bottom of the feed container is reached
            const atBottom = Math.ceil(scrollTop + clientHeight) >= scrollHeight - 100;
        
            if (atBottom) {
                this.paginateFetchedFeed(Alpine.store("sharedState").getCurrentCategory())
            }
        },

        goBack: function (category_id = null) {
            this.searchQuery = "";
            document.getElementById("search-box").value = this.searchQuery;
            this.clearCacheAndFeeds();
            this.paginateFetchedFeed((category_id || Alpine.store("sharedState").getCurrentCategory()));
        },

        startFeedUpdates: function () {
            this.stopFeedUpdates();

            const checkForUpdates = async () => {
                let timer = 300000
                if (this.fetching || this.loading) {
                    timer = 60000
                } else {
                    const url = `/api/fetch/${Alpine.store("sharedState").getCurrentCategory()}?force_init=True`;
                    const response = await this.callFetch(url);

                    if (response.isJson) {
                        const data = response.data;
                        console.log("Data:", data);
                        console.log("Feed Items:", data.feed_items);

                        if (data && data.feed_items) {
                            const newContentExists = this.checkForNewContent(data.feed_items);
                    
                            if (newContentExists) {
                                this.showNotification();
                                this.fetchedFeed = data.feed_items;
                            }
                        }
                    } else {
                        console.error(
                            "Response is not JSON:",
                            response.data
                        );
                    }
                } 

                setTimeout(checkForUpdates, timer);
            };

            setTimeout(checkForUpdates, 600000);
        },

        checkForNewContent: function (fetchedEntries) {
            if (!fetchedEntries) {
                return false;
            }

            const currentEntries = this.feedCache[Alpine.store("sharedState").getCurrentCategory()];
            if (!currentEntries) {
                return true;
            }

            return currentEntries[0].id !== fetchedEntries[0].id;
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

        /**
         * Fetches data from a URL and handles JSON and text responses.
         * @param {string} url The URL to fetch data from.
         * @returns {Promise<{data: any, isJson: boolean}>} An object containing the fetched data and its type.
         */
        callFetch: async function (url) {
            if (this.fetching) {
                return { data: "Fetching in progress, please wait.", isJson: false };
            }
        
            this.fetching = true;
            let result = { data: null, isJson: false };
        
            try {
                const response = await fetch(url);
                const isJson = response.headers.get("content-type")?.includes("application/json");
                const data = isJson ? await response.json() : await response.text();
                result = { data, isJson };
            } catch (error) {
                console.error(`Error while fetching data from ${url}:`, error);
                result = { data: `Error: ${error.message}`, isJson: false };
            } finally {
                this.fetching = false;
                return result;
            }
        },

        initFeed: function (isInit = false) {
            this.waitForCurrentCategory(() => {
                this.paginateFetchedFeed(Alpine.store("sharedState").getCurrentCategory(), isInit);
                this.startFeedUpdates();
            });

            const notification = document.getElementById("notification");
            notification.addEventListener("click", () => {
                this.hideNotification();
                this.paginateFetchedFeed(Alpine.store("sharedState").getCurrentCategory(), true, this.fetchedFeed);
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
            if (query && query != null) {
                this.searchQuery = query;
            } else {
                this.searchQuery = document.getElementById("search-box").value.trim()
            }
            // Convert query to string if it's not already
            if (typeof this.searchQuery !== 'string') {
                this.searchQuery = String(this.searchQuery);
            }
        
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
            this.paginateFetchedFeed(categoryValue, false);
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

        changeTheme: window.changeTheme
    }));
});