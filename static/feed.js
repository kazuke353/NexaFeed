function shouldClearCache(isInit, lastSearch, searchQuery) {
    return isInit ||
        (lastSearch.length === 0 && searchQuery.length > 0) ||
        (lastSearch && searchQuery.length === 0) ||
        (searchQuery !== lastSearch);
}

document.addEventListener("alpine:init", () => {
    Alpine.data("feedManager", () => ({
        feedCache: {},
        fetchedFeed: {},
        fetching: false,
        loading: false,
        searchQuery: "",
        lastSearch: "",

        paginateFetchedFeed: async function (category, isInit = false, feed = null) {
            if (this.fetching || this.loading)
            {
                console.log("Already fetching! Skipping this call...", this.fetching, this.loading)
                return;
            }
            this.loading = true;
            try {
                if (feed) {
                    isInit = true
                } else {
                    let url = `/api/fetch/${category}`;
                    const queryParams = [];
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
                        if (data && data.feed_items) {
                            feed = data.feed_items
                        }
                    } else {
                        console.error("Response is not JSON:", response.data);
                    }
                }
                this.updateUI(feed, category, isInit);
            } catch (error) {
                console.error(`Error fetching feeds for ${category}:`, error);
            } finally {
                this.loading = false;
            }
        },

        updateUI: function (feedItems, category = null, isInit = false) {
            category = category || Alpine.store("sharedState").getCurrentCategory();

            if (shouldClearCache(isInit, this.lastSearch, this.searchQuery)) {
                this.feedCache[category] = [];
                this.fetchedFeed = {}
                this.updateLastEntry(null, null);
            }
            this.feedCache[category] = this.feedCache[category] || [];
            if (feedItems) {
                this.feedCache[category] = this.feedCache[category].concat(feedItems);
            }

            Alpine.store("sharedState").feed_items = this.feedCache[category];

            if (feedItems && feedItems.length > 0) {
                const lastEntry = feedItems[feedItems.length - 1];
                this.updateLastEntry(lastEntry.id, lastEntry.published_date);
            }
            this.lastSearch = this.searchQuery;
        },

        updateLastEntry: function (newLastId, newLastPd) {
            this.lastId = newLastId;
            this.lastPd = newLastPd;
        },

        handleScroll: function () {
            const feedContainer = this.$refs.feedContainer;
            if (!feedContainer) return;

            const { scrollTop, scrollHeight, clientHeight } = feedContainer;
            const atBottom = Math.ceil(scrollTop + clientHeight) >= Math.ceil(scrollHeight - 50);

            if (atBottom) {
                this.paginateFetchedFeed(Alpine.store("sharedState").getCurrentCategory());
            }
        },

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
            this.paginateFetchedFeed(Alpine.store("sharedState").getCurrentCategory(), isInit);
            this.startFeedUpdates();
        },

        search: function (query = null, category = null) {
            if (query) this.$refs.searchBox.value = query;
            this.searchQuery = this.$refs.searchBox.value.trim();
            let categoryValue = category && category.id !== undefined ? category.id :
                Alpine.store("sharedState").getCurrentCategory();

            this.paginateFetchedFeed(categoryValue, false);
        },

        goBack: function (category_id = null) {
            this.searchQuery = "";
            this.$refs.searchBox.value = this.searchQuery;
            this.updateUI(null, null, true);
            this.paginateFetchedFeed(category_id || Alpine.store("sharedState").getCurrentCategory());
        },

        startFeedUpdates: function () {
            this.stopFeedUpdates();

            const checkForUpdates = async () => {
                let timer = this.fetching || this.loading ? 60000 : 300000;

                const url = `/api/fetch/${Alpine.store("sharedState").getCurrentCategory()}?force_init=True`;
                const response = await this.callFetch(url);

                if (response.isJson) {
                    const data = response.data;
                    console.log("Data:", data);
                    console.log("Feed Items:", data.feed_items);

                    if (data && data.feed_items) {
                        const newContentExists = this.checkForNewContent(data.feed_items);

                        if (newContentExists) {
                            this.fetchedFeed = data.feed_items;
                        }
                    }
                } else {
                    console.error(
                        "Response is not JSON:",
                        response.data
                    );
                }

                setTimeout(checkForUpdates, timer);
            };

            setTimeout(checkForUpdates, 1000);
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
    }));
});
