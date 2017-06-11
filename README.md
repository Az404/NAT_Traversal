# NAT_Traversal

Утилита для установления UDP-соединения между двумя хостами за NAT.

Использует алгоритм [UDP Hole Punching](https://en.wikipedia.org/wiki/UDP_hole_punching) с некоторыми модификациями.

## Запуск
### Вспомогательный сервер
Для работы требуется сервер с публичным IP-адресом, который будет участвовать на этапе установки соединения.
```bash
python3 traversal_server.py
```

### Клиенты
На каждом из хостов, между которыми нужно установить соединение (A и B), нужно запустить `traversal_client.py`.

Для идентификации при запуске нужно указать строковый идентификатор данного клиента и удалённого клиента (`--id`, `--remote`).

Чтобы использовать установленное соединение в прикладных программах, скрипт может выступать как в роли клиента (`--connect 127.0.0.1:53`), так и в роли сервера (`--listen 5300`).

Пример запуска:

Хост A:
```bash
python3 traversal_client.py --server <server_ip> --id host_a -r host_b --listen 5300
```

Хост B:
```bash
python3 traversal_client.py --server <server_ip> --id host_b -r host_a --connect 127.0.0.1:53
```

После установки соединения все пакеты, которые приходят на 5300 UDP порт на хосте A будут переданы на 53 порт на хосте B (и обратно).

## Краткий алгоритм работы

Каждый из хостов подключается к серверу по TCP и по командам с сервера выполняет следующие действия:

1. Создаёт UDP-сокет, который будет использоваться при всех соединениях в п. 2-6.
2. Запрашивает с сервера по UDP IP адрес и порт противоположной стороны (используя идентификаторы). Этот запрос также позволяет серверу определить внешний IP и порт данного хоста.
3. Сервер отдаёт хосту A внешний IP адрес и порт хоста B (Addr_B), а хосту B - внешний IP адрес и порт хоста A (Addr_A).
4. Хост A отправляет UDP пакет "HELLO" на Addr_B.
5. Хост B отправляет UDP пакет "HELLO" на Addr_A.
6. Хост A повторно отправляет UDP пакет "HELLO" на Addr_B.

Если после выполнения п. 6 хост B получает пакет "HELLO", то соединение считается установленным. Если пакет не получен, то сервер повторно инициирует установку соединения, но меняет местами A и B (т.е. первый пакет в п. 4 отправляется хостом B на Addr_A и т.д.).
