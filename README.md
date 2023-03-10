![Foodgram workflow](https://github.com/agsharapov/foodgram-project-react/actions/workflows/foodgram_workflow.yml/badge.svg?branch=main)

# Описание

**Foodgram** — ресурс для публикации, чтения и добавления в избранное рецептов.

Также на нём можно подписаться на авторов рецептов, создать список покупок и скачать его в виде файла.

# Используемые технологии
 
[Python](https://www.python.org/)
 
[Django](https://www.djangoproject.com/)
 
[Django REST Framework](https://www.django-rest-framework.org/)

[PostgreSQL](https://www.postgresql.org/)

[nginx](https://nginx.org/)

[Gunicorn](https://gunicorn.org/)

[Docker](https://www.docker.com/)

# Работа с проектом на Linux
 
## 1) Клонировать репозиторий и перейти в него:
 
git@github.com:agsharapov/foodgram-project-react.git
 
cd foodgram-project-react
 
## 2) Cоздать и активировать виртуальное окружение:
 
python3 -m venv venv
 
source venv/bin/activate
 
## 3) Установить зависимости из файла requirements.txt:

cd backend

pip install -r requirements.txt
 
## 4) Развернуть контейнеры:
 
cd infra
 
docker-compose up -d --build
 
## 5) Выполнить миграции, создать суперюзера, собрать статику:
 
docker-compose exec web python manage.py migrate
 
docker-compose exec web python manage.py createsuperuser
 
docker-compose exec web python manage.py collectstatic --no-input
 
## Шаблон наполнения файла infra/.env
 
DB_ENGINE=django.db.backends.postgresql
 
DB_NAME=postgres
 
POSTGRES_USER=postgres
 
POSTGRES_PASSWORD=postgres
 
DB_HOST=db
 
DB_PORT=5432

# IP проекта:

158.160.28.12

# Документация:

158.160.28.12/api/docs/

# Данные суперпользователя:

Почта: sashasharapov1999@yandex.ru

Пароль: admin

# Об авторах:

* Шарапов Александр (agsharapov) — бэкенд, деплой

* Яндекс Практикум — фронтенд, данные для БД