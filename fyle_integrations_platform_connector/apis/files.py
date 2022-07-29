from typing import List
import base64
import requests

from .base import Base

class Files(Base):
    """
    Class for File API
    """

    def get_as_base64(self, url):
        return base64.b64encode(requests.get(url).content).decode('ascii')

    def bulk_generate_file_urls(self, data: List[dict]) ->  List[dict]:
        """
        Bulk generate download and upload URLs
        """

        payload = {
            'data': data
        }

        attachments = self.connection.bulk_generate_file_urls(payload=payload)['data']

        for attachment in attachments:
            attachment['download_url'] = self.get_as_base64(attachment['download_url'])
        
        return attachments
        

