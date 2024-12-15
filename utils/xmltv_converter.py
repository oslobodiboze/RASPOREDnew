import os
import logging
from lxml import etree
import requests
import pandas as pd  # Ensure pandas is imported
from zoneinfo import ZoneInfo

def download_dtd(dtd_path):
    """Downloads the XMLTV DTD and saves it to the specified path.

    Args:
        dtd_path: The absolute path where the DTD should be saved.
    """
    try:
        dtd_url = 'https://raw.githubusercontent.com/XMLTV/xmltv/master/xmltv.dtd'  # Use HTTPS for security.
        response = requests.get(dtd_url, timeout=10)  # Add timeout for robustness.
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx).

        dtd_dir = os.path.dirname(dtd_path)
        os.makedirs(dtd_dir, exist_ok=True)  # Ensure directory exists.

        with open(dtd_path, 'wb') as f:
            f.write(response.content)

        logging.info(f"DTD downloaded successfully to {dtd_path}")
        return True

    except requests.exceptions.RequestException as e:  # More specific HTTP error handling.
        logging.error(f"Error downloading DTD: {e}")
        return False
    except OSError as e:  # Catch file system errors.
        logging.error(f"Error saving DTD to {dtd_path}: {e}")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred downloading DTD: {e}")
        return False

def dataframe_to_xmltv(display_df, internal_df, timezone): # timezone added as parameter
    try:
        required_columns = ['start', 'stop', 'title', 'desc', 'Category', 'episode-num']
        for column in required_columns:
            if column not in internal_df.columns:
                raise ValueError(f"Missing required column: {column}")

        tv = etree.Element('tv', {
            'generator-info-name': 'DiadoraXMLTV/2.0.0.3',
            'source-info-url': 'https://www.diadora.tv/',
            'source-info-name': 'DiadoraTV XMLTV',
            'source-data-url': 'https://diadora.tv/xmltv/diadora-pregled-programa-xmltv.xml'
        })


        channel = etree.SubElement(tv, 'channel', {'id': 'diadora-tv'})
        display_name = etree.SubElement(channel, 'display-name')
        display_name.text = 'DiadoraTV'
        url = etree.SubElement(channel, 'url')
        url.text = 'https://www.diadora.tv/'

        for idx, row in internal_df.iterrows():
            if pd.isna(row['start']) or pd.isna(row['stop']):
                logging.warning(f"Row {idx} skipped due to missing start/stop times: {row.to_dict()}")
                continue

            # CORRECTED CODE: Localize datetime objects, not the timezone object
            start_aware = row['start'].replace(tzinfo=timezone) # Correct method
            stop_aware = row['stop'].replace(tzinfo=timezone)   # Correct method


            programme = etree.SubElement(tv, 'programme', {
                'channel': 'diadora-tv',
                'start': start_aware.strftime("%Y%m%d%H%M%S %z"),
                'stop': stop_aware.strftime("%Y%m%d%H%M%S %z")
            })

            title = etree.SubElement(programme, 'title', {'lang': 'hr'})
            title.text = row['title']

            desc = etree.SubElement(programme, 'desc', {'lang': 'hr'})
            desc.text = row['desc']

            category = etree.SubElement(programme, 'category', {'lang': 'hr'})
            category.text = str(row['Category']) if not pd.isna(row['Category']) else 'Unknown'

            if isinstance(row['episode-num'], str) and row['episode-num'].strip():  # Check if episode-num is a string and not empty
                episode_num = etree.SubElement(programme, 'episode-num', {'system': 'onscreen'})
                episode_num.text = row['episode-num']

        return etree.ElementTree(tv)
    except (KeyError, ValueError) as e:
        logging.error("Error during DataFrame to XMLTV conversion:", exc_info=True)
        raise e
    
def validate_xmltv(xml_tree, dtd_path):
    try:
        with open(dtd_path, 'rb') as f:
            dtd = etree.DTD(f)

        xml_doc = xml_tree.getroot()
        if not dtd.validate(xml_doc):
            error_messages = "\n".join([str(error) for error in dtd.error_log])
            raise ValueError(f"XMLTV datoteka nije validna:\n{error_messages}")
        
        logging.info("XMLTV datoteka uspješno validirana prema DTD-u.")
        return True
    except (etree.DTDParseError, ValueError) as e:
        logging.error("Validacija XMLTV datoteke nije uspjela:", exc_info=True)
        raise e
    except Exception as e:
        logging.error("Nepoznata greška tijekom validacije XMLTV datoteke:", exc_info=True)
        raise e
