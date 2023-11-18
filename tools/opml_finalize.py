import feedparser
import xml.etree.ElementTree as ET

def update_opml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    for outline in root.findall(".//outline"):
        xml_url = outline.get('xmlUrl')
        if xml_url:
            feed = feedparser.parse(xml_url)
            if 'title' not in outline.attrib and feed.feed.get('title'):
                outline.set('title', feed.feed.title)
            if 'description' not in outline.attrib and feed.feed.get('subtitle'):
                outline.set('description', feed.feed.subtitle)
    tree.write('updated_opml.xml', encoding="UTF-8", xml_declaration=True)

update_opml('feeds.opml')
