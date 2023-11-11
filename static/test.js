function truncateTagsBasedOnWidth(tagsContainerSelector) {
    const tagsContainers = document.querySelectorAll(tagsContainerSelector);

    tagsContainers.forEach((container) => {
        let containerWidth = container.offsetWidth;
        let currentWidth = 0;
        let tags = container.querySelectorAll(".badge");
        let ellipsisExists = container.querySelector(".badge-truncate");

        // Remove existing ellipsis to recalculate width correctly
        if (ellipsisExists) {
            container.removeChild(ellipsisExists);
        }

        tags.forEach((tag, index) => {
            currentWidth += tag.offsetWidth;
            if (currentWidth > containerWidth && index !== tags.length - 1) {
                // Hide all tags beyond this point
                for (let j = index; j < tags.length; j++) {
                    tags[j].style.display = "none";
                }
                // Create and append ellipsis span if it doesn't exist
                if (!ellipsisExists) {
                    let ellipsisSpan = document.createElement("span");
                    ellipsisSpan.className = "badge badge-truncate";
                    ellipsisSpan.textContent = "...";
                    container.appendChild(ellipsisSpan);
                }
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
        // Set the card height to the max row height or max card height, whichever is smaller
        card.style.height = `${maxCardHeight}px`;

        const cardContentElements = card.querySelectorAll(
            ".card-title, .card-creator, .card-pd, .card-footer" // Include .card-footer if that's the class for your footer
        );
        let usedHeight = 0;

        cardContentElements.forEach((el) => {
            if (el !== card.querySelector(".card-text")) {
                usedHeight += el.offsetHeight;
            }
        });

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
    let cardsPerRow = 4;
    let rowsInView = 2;
    if (window.innerWidth < 1200 && window.innerWidth >= 768) {
        cardsPerRow = 2;
        rowsInView = 1; // Adjust rows in view if the screen is medium size
    } else {
        cardsPerRow = 1;
        rowsInView = 1;
    }

    truncateTagsBasedOnWidth(".card-info");
    adjustCardSizesAndTruncateText(cardsPerRow, rowsInView);
}

document.addEventListener("DOMContentLoaded", () => handleResize());
window.addEventListener("load", () => handleResize());
window.addEventListener("resize", () => handleResize());