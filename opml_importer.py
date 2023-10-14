import os
import yaml
from xml.etree import ElementTree as ET
from config_manager import ConfigManager

class OPMLImporter:
    def __init__(self, folder_path="opml", config_manager=None):
        self.folder_path = folder_path
        self.config_manager = config_manager or ConfigManager()

    def import_opml(self):
        try:
            # Fetch the existing URLs from config
            existing_feed_urls = set(self.config_manager.get("rss_urls", []))
            
            # To store new URLs fetched from OPML files
            new_feed_urls = set()
            
            for filename in os.listdir(self.folder_path):
                if filename.endswith('.opml'):
                    tree = ET.parse(os.path.join(self.folder_path, filename))
                    root = tree.getroot()
                    for elem in root.iterfind('.//outline'):
                        xml_url = elem.attrib.get('xmlUrl')
                        if xml_url:
                            new_feed_urls.add(xml_url)
            
            # Merge new URLs with existing ones, while eliminating duplicates
            updated_feed_urls = list(existing_feed_urls.union(new_feed_urls))
            
            self.config_manager.config_data["rss_urls"] = updated_feed_urls
            
            # Save the updated config back to the YAML file
            with open(self.config_manager.config_path, 'w') as file:
                yaml.safe_dump(self.config_manager.config_data, file)
                
        except Exception as e:
            raise Exception("Failed to import OPML: " + str(e))