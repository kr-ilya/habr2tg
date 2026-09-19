import requests
import logging

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10


class HabrAPI():
    def __init__(self):
        self.ENDPOINT = "https://habr.com/kek/v2/"

    def getArticles(self):
        return self._get('articles?fl=ru&hl=ru&sort=rating', 'getArticles')

    def getNews(self):
        return self._get('articles?fl=ru&hl=ru&news=true', 'getNews')

    def _get(self, path, label):
        try:
            r = requests.get(f'{self.ENDPOINT}{path}', timeout=REQUEST_TIMEOUT)

            if r.status_code != 200:
                logger.error(f'api.{label} returned {r.status_code}: {r.text[:200]}')
                return None

            return r.json()
        except Exception:
            logger.exception(f'api.{label} failed')
            return None
