import os
from xml.etree import ElementTree as ET
from config_manager import ConfigManager

class OPMLImporter:
    def __init__(self, folder_path="opml", config_manager=None):
        self.folder_path = folder_path
        self.config_manager = config_manager or ConfigManager()

    def load(self):
        try:
            # Load the entire configuration
            self.config_manager.config_data = self.config_manager.load_config()

            # Extract existing feed URLs or set to empty if not present
            category = "main_feed_urls"
            new_feed_urls = set()

            for filename in os.listdir(self.folder_path):
                if filename.endswith('.opml') and not filename.endswith('_processed.opml'):
                    full_path = os.path.join(self.folder_path, filename)
                    tree = ET.parse(full_path)
                    root = tree.getroot()

                    for elem in root.iterfind('.//outline'):
                        xml_url = elem.attrib.get('xmlUrl')
                        if xml_url:
                            new_feed_urls.add(xml_url)
                    
                    # Rename processed files to avoid reprocessing
                    new_filename = filename.replace('.opml', '_processed.opml')
                    os.rename(full_path, os.path.join(self.folder_path, new_filename))

            # Update and save the config using the new method
            self.config_manager.update_category_data(category, list(new_feed_urls))

        except Exception as e:
            print("Failed to import OPML: " + str(e))
