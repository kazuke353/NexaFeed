document.addEventListener('alpine:init', () => {
    Alpine.data('sidebarManager', () => ({
        // Fetch the feeds for a given category
        fetchFeeds: async function (category) {
            // Check if feeds are already fetched
            if (category.feeds && category.feeds.length > 0) {
                return; // Feeds are already loaded, so do nothing
            }
        
            try {
                const response = await fetch(`/api/categories/feeds/${category.id}`);
                const data = await response.json();
                console.log("Category Feeds:", data);

                if (data.feeds) {
                    // Find the category in the store by ID
                    const storeCategory = Alpine.store('sharedState').categories.find(cat => cat.id === category.id);
                    
                    // Check if the category is found and update its feeds
                    if (storeCategory) {
                        storeCategory.feeds = data.feeds;
                    }
                }
            } catch (error) {
                console.error("Error fetching feeds:", error);
            }
        },        

        addCategory: async function () {
            // Show an input field to enter the category name
            const categoryName = prompt("Enter the category name:");
            if (categoryName) {
                // Add the new category to the list
                await fetch("/api/categories", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ name: categoryName }),
                });
                Alpine.store("sharedState").categories.push({
                    name: categoryName,
                    expanded: false,
                });
                // Add an id field for testing
                Alpine.store("sharedState").categories.forEach((category, index) => {
                    category.id = index + 1; // Assign a temporary unique id
                });
            }
        },

        // Remove a category
        removeCategory: async function (category) {
            // Confirm the removal
            const confirmRemove = confirm(
                `Are you sure you want to remove the category "${category.name}"?`
            );
            if (confirmRemove) {
                await fetch(`/api/categories/${category.id}`, {
                    method: "DELETE",
                });
                // Remove the category from the list
                const index = Alpine.store("sharedState").categories.indexOf(category);
                if (index !== -1) {
                    Alpine.store("sharedState").categories.splice(index, 1);
                }
                // Add an id field for testing
                Alpine.store("sharedState").categories.forEach((category, index) => {
                    category.id = index + 1; // Assign a temporary unique id
                });
                Alpine.store("sharedState").setCurrentCategory(Alpine.store("sharedState").categories[0].id);
            }
        },
    
        // Add a new feed to a category
        addFeed: async function (category) {
            // Show an input field to enter the feed URL
            const feedUrl = prompt("Enter the feed URL:");
            if (feedUrl) {
                // Add the new feed to the category
                await fetch(`/api/categories/feeds/${category.id}`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ url: feedUrl }),
                });
                Alpine.store("sharedState").categories[category.id].feeds.push({ name: feedUrl, url: feedUrl });
                // Add an id field for testing
                Alpine.store("sharedState").categories[category.id].feeds.forEach((feed, index) => {
                    feed.id = index + 1; // Assign a temporary unique id
                });
            }
        },
    
        // Remove a feed from a category
        removeFeed: async function (category, feed) {
            // Confirm the removal
            const confirmRemove = confirm(
                `Are you sure you want to remove the feed "${feed.name}"?`
            );
            if (confirmRemove) {
                await fetch(`/api/categories/feeds/${feed.id}`, {
                    method: "DELETE",
                });
                // Find the index of the feed in the category's feeds array
                const index = Alpine.store("sharedState").categories[category.id].feeds.indexOf(feed);
                if (index !== -1) {
                    // Remove the feed from the array
                    Alpine.store("sharedState").categories[category.id].feeds.splice(index, 1);
                }
                Alpine.store("sharedState").categories[category.id].feeds.forEach((feed, index) => {
                    feed.id = index + 1; // Assign a temporary unique id
                });
            }
        },
    
        // Import an OPML file to a category
        importOPML: async function (category) {
            const input = document.createElement("input");
            input.type = "file";
            input.accept = ".opml";
            input.addEventListener("change", async (event) => {
                const file = event.target.files[0];
                const formData = new FormData();
                formData.append("opml", file);
                try {
                    const response = await fetch(
                        `/api/categories/${category.id}/import`,
                        {
                            method: "POST",
                            body: formData,
                        }
                    );
                    const data = await response.json();
                    // Add an id field for testing
                    data.feeds.forEach((feed, index) => {
                        feed.id = index + 1; // Assign a temporary unique id
                    });
                    // Update the feeds for the selected category
                    category.feeds = data.feeds;
                    console.log("Feeds:", category.feeds);
                } catch (error) {
                    console.error("Error importing OPML file:", error);
                }
            });
            input.click();
        },
    }));
});