# -*- coding: utf-8 -*-
import requests
import time
from urllib.parse import urlencode, quote_plus
import datetime as DT
from dateutil.parser import parse
import os
import ydb
import habrapi
import logging

#Переменные среды
#BOT_TOKEN - токен тг бота
#CHANNEL_ID - id канала с постами
#NEWS_CHANNEL_ID - id канала с новостями
#YDB_ENDPOINT
#YDB_DATABASE

API = habrapi.HabrAPI()
logger = logging.getLogger()
logger.setLevel(logging.WARNING)

class HabrParser():
    def __init__(self):

        # create driver in global space.
        driver = ydb.Driver(endpoint=os.getenv('YDB_ENDPOINT'), database=os.getenv('YDB_DATABASE'))
        # Wait for the driver to become active for requests.
        driver.wait(fail_fast=True, timeout=5)
        # Create the session pool instance to manage YDB sessions.
        self.pool = ydb.SessionPool(driver)

        botToken = os.environ['BOT_TOKEN'] #токен тг бота
        self.channelId = os.environ['CHANNEL_ID'] #id канала с постами
        self.news_channelId = os.environ['NEWS_CHANNEL_ID'] #id канала с новостями

        self.tgApiUrl = f'https://api.telegram.org/bot{botToken}'

    def articles(self, last_dt):
        articles = API.getArticles()
        if articles == None:
            return None

        logger.info(f"articlesIds {articles['articleIds']}")
        
        for article in reversed(articles['articleIds']):
            timePublished = parse(articles['articleRefs'][article]['timePublished'])
            timePublished.replace(tzinfo=DT.timezone.utc).timestamp()
            at = int(timePublished.replace(tzinfo=DT.timezone.utc).timestamp())
            
            if(at > last_dt):

                self.set_last_datetime('LAST_AT', at)

                title = articles['articleRefs'][article]['titleHtml']
                author = articles['articleRefs'][article]['author']['alias']
                tags = articles['articleRefs'][article]['tags']
                aid = articles['articleRefs'][article]['id']

                link = f'https://habr.com/ru/post/{aid}/'
                self.publish(title, author, tags, link, self.channelId)
        return 1


    def news(self, last_dt):
        articles = API.getNews()
        if articles == None:
            return None
        
        logger.info(f"newsIds {articles['articleIds']}")

        for article in reversed(articles['articleIds']):

            timePublished = parse(articles['articleRefs'][article]['timePublished'])
            timePublished.replace(tzinfo=DT.timezone.utc).timestamp()
            at = int(timePublished.replace(tzinfo=DT.timezone.utc).timestamp())
            
            if(at > last_dt):

                self.set_last_datetime('LAST_NT', at)

                title = articles['articleRefs'][article]['titleHtml']
                author = articles['articleRefs'][article]['author']['alias']
                tags = articles['articleRefs'][article]['tags']
                aid = articles['articleRefs'][article]['id']

                link = f'https://habr.com/ru/news/t/{aid}/'
                self.publish(title, author, tags, link, self.news_channelId)

        return 1

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

        self.pool.retry_operation_sync(getit)

        return result[0]

    def set_last_datetime(self, column, data):

        def setit(session):
            session.transaction().execute(
                f'UPDATE hb_info SET {column} = {data} WHERE id = 1;',
                commit_tx=True,
                settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
            )

        self.pool.retry_operation_sync(setit)

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

        tgUrl = f'{self.tgApiUrl}/sendMessage?{urlencode(query, quote_via=quote_plus)}'
        response = requests.get(tgUrl)
        tgres = response.json()
        
        logger.info(tgres)

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
    if articlesRes == None:
        return {
            'statusCode': 200,
            'body': "error get articles"
        }

    # лента новостей
    newsRes = habrParser.news(int(last_datetime.LAST_NT))
    if newsRes == None:
        return {
            'statusCode': 200,
            'body': "error get news"
        }

    return {
            'statusCode': 200,
            'body': "ok"
        }