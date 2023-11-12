import yaml
import xml.etree.ElementTree as ET

def convert_yaml_to_opml(yaml_file, opml_file):
    # Load YAML file
    with open(yaml_file, 'r') as file:
        data = yaml.safe_load(file)

    # Create the base of the OPML file
    opml = ET.Element('opml', version='2.0')
    body = ET.SubElement(opml, 'body')
    outline = ET.SubElement(body, 'outline', text='Feeds', title='Feeds')

    # Add feeds from YAML to OPML
    for feed_url in data['urls']:
        ET.SubElement(outline, 'outline', type='rss', xmlUrl=feed_url)

    # Create a tree and write the OPML file
    tree = ET.ElementTree(opml)
    tree.write(opml_file, encoding='utf-8', xml_declaration=True)

# Example usage
convert_yaml_to_opml('config.yaml', 'feeds.opml')
