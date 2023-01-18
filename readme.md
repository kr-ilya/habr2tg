# Habr2Tg

Habr2Tg - Парсинг постов и новостей с habr.com в телеграм

Предназначен для запуска на [Yandex Cloud Functions](https://cloud.yandex.ru/services/functions)

[Habr Feed](https://t.me/HabrFeed)  
[Habr News](https://t.me/HabrNewsFeed)

## Tech

- python 3.9+
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

Точка входа
```sh
parser.handler
```

[Создать](https://cloud.yandex.ru/docs/ydb/quickstart#create-db) базу YDB и таблицу с приведенной ниже схемой данных  
Настроить [триггер](https://cloud.yandex.ru/docs/functions/quickstart/create-trigger/) для запуска скрипта каждую минуту

#### Схема таблицы
| **#** |**Имя**| **Ключ** | **Тип** |
| :---- | :------ | :----- | :------ |
| 0 | id | PK | Uint64 |
| 1 | LAST_AT |  | Double |
| 2 | LAST_NT |  | Double |

## License

MIT
