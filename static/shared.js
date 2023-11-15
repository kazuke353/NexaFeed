document.addEventListener("alpine:init", () => {
    const sharedState = {
        categories: [],
        feed_items: [],
        currentCategory: null,
        initCategories() {
            this.fetchCategories().then(() => {
                if (this.categories.length > 0) {
                    this.setCurrentCategory(this.categories[0].id);
                }
            });
        },
        async fetchCategories() {
            try {
                const response = await fetch("/api/categories");
                const data = await response.json();
                this.categories = data.categories;
                console.log("Categories:", this.categories);
            } catch (error) {
                console.error("Error fetching categories:", error);
            }
            return true
        },
        setCurrentCategory(categoryId) {
            this.currentCategory = categoryId;
        },
        getCurrentCategory() {
            if (!this.currentCategory && this.categories.length > 0) {
                this.setCurrentCategory(this.categories[0].id);
            } else if (!this.currentCategory) {
                this.setCurrentCategory(1);
            }
            return this.currentCategory;
        },
    };

    Alpine.store("sharedState", sharedState);

    Alpine.data("sharedData", () => ({
        fetch() {
            Alpine.store("sharedState").initCategories();
        },
        fetchCategories() {
            return Alpine.store("sharedState").fetchCategories();
        },
        get currentCategory() {
            return Alpine.store("sharedState").getCurrentCategory();
        },
        set currentCategory(value) {
            Alpine.store("sharedState").setCurrentCategory(value);
        },
        categories: Alpine.store("sharedState").categories,
        feed_items: Alpine.store("sharedState").feed_items,
        currentCategory: Alpine.store("sharedState").currentCategory,
    }));
});
