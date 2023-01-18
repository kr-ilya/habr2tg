import requests
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class HabrAPI():
    def __init__(self):
        self.ENDPOINT = "https://habr.com/kek/v2/"

    
    def getArticles(self):

        try:
            r = requests.get(f'{self.ENDPOINT}articles?fl=ru&hl=ru&sort=rating')
            response = r.json()

            if(r.status_code == 200):
                return response
            else:
                logger.error("api.getArticles.!200")
                return None
        except Exception as e:
            logger.error("api.getArticles")
            return None
    
    def getNews(self):

        try:
            r = requests.get(f'{self.ENDPOINT}articles?fl=ru&hl=ru&news=true')
            response = r.json()

            if(r.status_code == 200):
                return response
            else:
                logger.error("api.getNews.!200")
                return None
        except Exception as e:
            logger.error("api.getNews")
            return None