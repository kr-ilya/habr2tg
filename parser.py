# -*- coding: utf-8 -*-
import datetime as DT
import logging
import os
import time

import requests
import ydb
from dateutil.parser import parse

import habrapi

# Переменные среды
# BOT_TOKEN - токен тг бота
# CHANNEL_ID - id канала с постами
# NEWS_CHANNEL_ID - id канала с новостями
# TG_PROXY - прокси для api.telegram.org, используется только для него
# YDB_ENDPOINT
# YDB_DATABASE

# Обработчик и форматтер для корневого логгера настраивает сам Cloud Functions,
# его уровень по умолчанию - WARNING. Уровень задаётся этому логгеру, а не
# корневому, чтобы настройка не зависела от порядка инициализации рантайма.
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

API = habrapi.HabrAPI()

# Драйвер и пул переживают вызов функции, пока переиспользуется контейнер.
driver = ydb.Driver(
    endpoint=os.getenv('YDB_ENDPOINT'),
    database=os.getenv('YDB_DATABASE'),
    credentials=ydb.iam.MetadataUrlCredentials(),
)
driver.wait(fail_fast=True, timeout=5)
pool = ydb.SessionPool(driver)


class HabrParser():
    def __init__(self):
        botToken = os.environ['BOT_TOKEN']
        self.channelId = os.environ['CHANNEL_ID']
        self.news_channelId = os.environ['NEWS_CHANNEL_ID']
        self.tgProxy = os.getenv('TG_PROXY')

        self.tgApiUrl = f'https://api.telegram.org/bot{botToken}'

    def articles(self, last_dt):
        articles = API.getArticles()
        if articles is None:
            logger.info("not found articles")
            return None

        self._publish_feed(
            feed=articles,
            last_dt=last_dt,
            column='LAST_AT',
            channelId=self.channelId,
            linkPrefix='https://habr.com/ru/post',
            label='article',
        )
        return 1

    def news(self, last_dt):
        news = API.getNews()
        if news is None:
            logger.info("not found news")
            return None

        self._publish_feed(
            feed=news,
            last_dt=last_dt,
            column='LAST_NT',
            channelId=self.news_channelId,
            linkPrefix='https://habr.com/ru/news/t',
            label='news',
        )
        return 1

    def _publish_feed(self, feed, last_dt, column, channelId, linkPrefix, label):
        """Публикует записи новее last_dt и один раз сдвигает курсор в БД."""

        published_at = last_dt

        for publicationId in reversed(feed['publicationIds']):
            ref = feed['publicationRefs'][publicationId]

            timePublished = parse(ref['timePublished'])
            at = int(timePublished.replace(tzinfo=DT.timezone.utc).timestamp())

            if at <= last_dt:
                continue

            aid = ref['id']
            logger.info(f'found {label} to publish id={aid}')

            try:
                self.publish(
                    title=ref['titleHtml'],
                    author=ref['author']['alias'],
                    tagsList=ref['tags'],
                    link=f'{linkPrefix}/{aid}/',
                    channelId=channelId,
                )
            except Exception:
                # Курсор не сдвигаем дальше упавшей записи, чтобы она ушла
                # в канал на следующем запуске.
                logger.exception(f'failed to publish {label} id={aid}')
                break

            published_at = max(published_at, at)

        if published_at > last_dt:
            self.set_last_datetime(column, published_at)

    def get_last_datetime(self):

        result = [None]

        def getit(session):
            # create the transaction and execute query.
            res = session.transaction().execute(
                'SELECT * FROM hb_info WHERE id = 1;',
                commit_tx=True,
                settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
            )

            result[0] = res[0].rows[0]

        pool.retry_operation_sync(getit)

        return result[0]

    def set_last_datetime(self, column, data):

        def setit(session):
            session.transaction().execute(
                f'UPDATE hb_info SET {column} = {int(data)} WHERE id = 1;',
                commit_tx=True,
                settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
            )

        pool.retry_operation_sync(setit)

    def publish(self, title, author, tagsList, link, channelId):

        tags = ''
        for tag in tagsList:
            tags += '#'+tag['titleHtml'].replace(" ", "_")+' '

        text = f"<b>{html_special_chars(title)}</b>\n"
        text += f"<b>Теги: </b>{html_special_chars(tags)}\n"
        text += f"<b>Автор:</b> #{html_special_chars(author)}\n\n"
        text += link

        query = {
            'chat_id': channelId,
            'text': text,
            'parse_mode': 'HTML'
        }

        # Прокси нужен только для Telegram, поэтому задаётся явно,
        # а не через переменные HTTP_PROXY/HTTPS_PROXY.
        proxies = {'http': self.tgProxy, 'https': self.tgProxy} if self.tgProxy else None

        response = requests.post(
            f'{self.tgApiUrl}/sendMessage',
            data=query,
            proxies=proxies,
            timeout=30
        )

        try:
            tgres = response.json()
        except ValueError:
            raise RuntimeError(
                f'telegram sendMessage returned {response.status_code}: {response.text[:200]}'
            )

        if not tgres.get('ok'):
            raise RuntimeError(f"telegram sendMessage failed: {tgres.get('description')}")

        logger.debug(tgres)

        time.sleep(1)


def html_special_chars(text):
    return text \
    .replace(u"&", u"&amp;") \
    .replace(u'"', u"&quot;") \
    .replace(u"'", u"&#039;") \
    .replace(u"<", u"&lt;") \
    .replace(u">", u"&gt;")

def handler(event, context):

    habrParser = HabrParser()

    last_datetime = habrParser.get_last_datetime()

    # Лента постов
    articlesRes = habrParser.articles(int(last_datetime.LAST_AT))
    if articlesRes is None:
        return {
            'statusCode': 200,
            'body': "error get articles"
        }

    # лента новостей
    newsRes = habrParser.news(int(last_datetime.LAST_NT))
    if newsRes is None:
        return {
            'statusCode': 200,
            'body': "error get news"
        }

    return {
            'statusCode': 200,
            'body': "ok"
        }
