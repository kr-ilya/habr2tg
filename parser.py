# -*- coding: utf-8 -*-
import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import urlencode, quote_plus
import datetime as DT
import os
import ydb

#Переменные среды
#BOT_TOKEN - токен тг бота
#CHANNEL_ID - id канала с постами
#NEWS_CHANNEL_ID - id канала с новостями
#YDB_ENDPOINT
#YDB_DATABASE


# create driver in global space.
driver = ydb.Driver(endpoint=os.getenv('YDB_ENDPOINT'), database=os.getenv('YDB_DATABASE'))
# Wait for the driver to become active for requests.
driver.wait(fail_fast=True, timeout=10)
# Create the session pool instance to manage YDB sessions.
pool = ydb.SessionPool(driver)


botToken = os.environ['BOT_TOKEN'] #токен тг бота
channelId = os.environ['CHANNEL_ID'] #id канала с постами
news_channelId = os.environ['NEWS_CHANNEL_ID'] #id канала с новостями

apiUrl = 'https://api.telegram.org/bot{}'.format(botToken)

UPDQuery = 'UPDATE hb_info SET {} = {} WHERE id = 1;'
LTime = time.time()

def html_special_chars(text):
    return text \
    .replace(u"&", u"&amp;") \
    .replace(u'"', u"&quot;") \
    .replace(u"'", u"&#039;") \
    .replace(u"<", u"&lt;") \
    .replace(u">", u"&gt;")


def get_lasts(session):
    # create the transaction and execute query.
    result = session.transaction().execute(
        'select * FROM hb_info WHERE id = 1;',
        commit_tx=True,
        settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
    )
    return result[0].rows[0]


def set_last_nt(session):
    global UPDQuery
    global LTime
    session.transaction().execute(
        UPDQuery.format('LAST_NT', LTime),
        commit_tx=True,
        settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
    )

    return None

def set_last_at(session):
    global UPDQuery
    global LTime
    session.transaction().execute(
        UPDQuery.format('LAST_AT', LTime),
        commit_tx=True,
        settings=ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)
    )

    return None



def publish(url, cId):
    s = time.time()    
    article = False
    r = requests.get(url)
    if(r.status_code == 200):

        if(r.url.find('/article/') >= 0):
            article = True

        soup = BeautifulSoup(r.text, 'html.parser')
        title = soup.find("h1", {"class":'tm-article-snippet__title_h1'}).string

        try:
            tagsList = soup.find("ul", {"class": "tm-separated-list__list"}).findAll("a", {"class": "tm-tags-list__link"})
            tags = ''
            for tag in tagsList:
                tags += '#'+tag.contents[0].replace(" ", "_")+' '
        except AttributeError:
            print(f"ATTR ERROR URL {url}")

        if(not article):
            author = soup.find("span", {"class": "tm-article-snippet__author"}).find("a", {"class": "tm-user-info__username"}).string.strip()

        text = f"<b>{html_special_chars(title)}</b>\n"
        text += f"<b>Теги: </b>{html_special_chars(tags)}\n"

        if(not article):
            text += f"<b>Автор:</b> #{html_special_chars(author)}\n"

        text += "\n"+url

        query = {
            'chat_id': cId,
            'text': text,
            'parse_mode': 'HTML'
        }

        tgUrl = apiUrl + '/sendMessage?' + urlencode(query, quote_via=quote_plus)
        response = requests.get(tgUrl)
        res = response.json()

        print(f"url: {url} TG: {res}")
        te = time.time() - s
        if te < 1:
            time.sleep(1 - te)        

        return 1

def handler(event, context):
    global LTime
    ss = time.time()

    lasts = pool.retry_operation_sync(get_lasts)
    # Лента постов
    mainPage = requests.get('https://habr.com/ru/all/')
    if(mainPage.status_code == 200):
        soup = BeautifulSoup(mainPage.text, 'html.parser')
        articleBlocks = soup.findAll('article')
        for article in reversed(articleBlocks):
            articleTime = article.find('time').get('datetime')
            at = DT.datetime.strptime(articleTime, '%Y-%m-%dT%H:%M:%S.%fZ')
            at = at.replace(tzinfo=DT.timezone.utc).timestamp()

            if(float(at) > float(lasts.LAST_AT)):
                LTime = at
                pool.retry_operation_sync(set_last_at)
                articleId = article.get('id')
                aUrl = f"https://habr.com/ru/post/{articleId}/"
                publish(aUrl, channelId)

    #лента новостей
    mainPage = requests.get('https://habr.com/ru/news/')
    if(mainPage.status_code == 200):
        soup = BeautifulSoup(mainPage.text, 'html.parser')
        articleBlocks = soup.findAll('article')
        for article in reversed(articleBlocks):
            articleTime = article.find('time').get('datetime')
            at = DT.datetime.strptime(articleTime, '%Y-%m-%dT%H:%M:%S.%fZ')
            at = at.replace(tzinfo=DT.timezone.utc).timestamp()

            if(float(at) > float(lasts.LAST_NT)):
                LTime = at
                pool.retry_operation_sync(set_last_nt)
                articleId = article.get('id')
                aUrl = f"https://habr.com/ru/news/t/{articleId}/"
                publish(aUrl, news_channelId)


    print('TIME ', time.time() - ss)

    return {
            'statusCode': 200,
            'body': "ok"
        }