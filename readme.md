# Habr2Tg

Habr2Tg - Парсинг постов и новостей с habr.com в телеграм
Предназначен для запуска на [Yandex Cloud Functions](https://cloud.yandex.ru/services/functions)

## Tech

- python 3.7+
- [YDB](https://cloud.yandex.ru/services/ydb)

## Installation

Переменные окружения

```sh
BOT_TOKEN=токен тг бота
CHANNEL_ID=id канала с постами
NEWS_CHANNEL_ID=id канала с новостями
YDB_ENDPOINT
YDB_DATABASE
```

## License

MIT