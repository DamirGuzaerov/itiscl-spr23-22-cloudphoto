# itiscl-spr23-22-cloudphoto
ITIS Cloud lab practice. CloudPhoto application

## Программа, которая загружает фотографии в Yandex Object Storage соблюдая определенную структуру и для каждого фотоальбома генерирует HTML страницу для просмотра фотографий, а так же генерирует главную страницу со списком фотоальбомов.

## Предварительные действия
- 'python -m venv venv' - создание виртуального окружения
- 'venv/Scripts/activate.bat' - активация виртуального окружения
- 'pip install -r requirements.txt' - установка зависимостей
- Убедитесь что в домашнем каталоге пользователя есть файл ".config\cloudphoto\cloudphotorc" Он необходим для дальнейшей работы программы
  
## Доступные команды:
- list — вывод списка альбомов.
- upload — отправка фотографий в облачное хранилище.
- delete — удаление альбома и фотографий в нем.
- mksite — формирование и публикация веб-страниц фотоархива.
- init — инициализация программы.
