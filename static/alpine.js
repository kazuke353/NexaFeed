class CardHandler {
    constructor() {
      this.open = false;
      this.embed = null;
      this.content = null;
      this.originalLink = null;
    }
  
    initCard(embed, content, originalLink) {
        if (embed === null || content === null || originalLink === null) {
          console.error('Invalid parameters passed to initCard');
          return;
        }
        this.embed = embed;
        this.content = content;
        this.originalLink = originalLink;
        console.log('Initialized:', this.embed, this.content, this.originalLink);
    }
  
    toggleScroll(status) {
      // Toggle background scrolling
      if (status) {
        document.body.classList.add('no-scroll');
      } else {
        document.body.classList.remove('no-scroll');
      }
    }
  
    formatContent() {
      console.log('Formatting Content:', content); // Debugging
      if (!content) return 'No content available';
        
      // Safely convert URLs to clickable links
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = this.content;
      const textNodes = Array.from(tempDiv.childNodes).filter(node => node.nodeType === 3); // Text nodes
    
      textNodes.forEach(textNode => {
        const parent = textNode.parentNode;
        const textContent = textNode.nodeValue;
        const newTextContent = textContent.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
        const newHTML = document.createElement('span');
        newHTML.innerHTML = newTextContent.replace(/\n/g, '<br>'); // Preserve line breaks
        parent.replaceChild(newHTML, textNode);
      });
    
      // Append a link to the original page, if available and not already present
      if (originalLink && !tempDiv.innerHTML.includes(originalLink)) {
        tempDiv.innerHTML = `${this.embed}<br>${tempDiv.innerHTML}<br><br><a href="${this.originalLink}" target="_blank">[link]</a>`;
      }
    
      return tempDiv.innerHTML;
    }
  }
  
  Alpine.data('cardHandler', () => new CardHandler());