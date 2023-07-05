import argparse
import configparser
import os
import re

import boto3
import sys


def get_config_file_path():
    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, ".config", "cloudphoto")
    os.makedirs(config_dir, exist_ok=True)
    config_file = os.path.join(config_dir, "cloudphotorc")
    return config_file


def check_config_file():
    config_file = get_config_file_path()

    if not os.path.isfile(config_file):
        print("Configuration file not found. Use 'init' command to initialize.")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_file)
    if not config['DEFAULT']:
        print("Invalid configuration file. Use 'init' command to initialize.")
        sys.exit(1)

    required_params = ['bucket', 'aws_access_key_id', 'aws_secret_access_key', 'region', 'endpoint_url']

    for param in required_params:
        if not config['DEFAULT'].get(param):
            print(f"Missing {param} in the configuration file. Use 'init' command to initialize.")
            sys.exit(1)


def initialize_program():
    config_file = get_config_file_path()

    config = configparser.ConfigParser()
    config.read(config_file)

    if config.sections():
        print("CloudPhoto is already initialized.")
        return

    aws_access_key_id = input("Enter AWS Access Key ID: ")
    aws_secret_access_key = input("Enter AWS Secret Access Key: ")
    bucket = input("Enter bucket name: ")

    config['DEFAULT'] = {
        'bucket': bucket,
        'aws_access_key_id': aws_access_key_id,
        'aws_secret_access_key': aws_secret_access_key,
        'region': 'ru-central1',
        'endpoint_url': 'https://storage.yandexcloud.net'
    }

    with open(config_file, 'w') as configfile:
        config.write(configfile)

    # Создаем бакет в облачном хранилище
    s3 = boto3.resource('s3',
                        endpoint_url='https://storage.yandexcloud.net',
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key)
    s3.create_bucket(Bucket=bucket)

    print("Initialization completed successfully.")


def list_albums():
    check_config_file()

    config_file = get_config_file_path()

    config = configparser.ConfigParser()
    config.read(config_file)

    bucket = config['DEFAULT'].get('bucket')
    if not bucket:
        print("Bucket name is not defined in the configuration file.")
        sys.exit(1)

    s3 = boto3.client('s3',
                      endpoint_url='https://storage.yandexcloud.net',
                      aws_access_key_id=config['DEFAULT']['aws_access_key_id'],
                      aws_secret_access_key=config['DEFAULT']['aws_secret_access_key'])

    response = s3.list_objects(Bucket=bucket)

    if 'Contents' in response:
        albums = set()
        for item in response['Contents']:
            album = item['Key']
            if album.endswith('/'):
                albums.add(album)

        if albums:
            for album in sorted(albums):
                print(album)
        else:
            print("Photo not found")
    else:
        print("Photo albums not found")


def upload_photos(album, photos_dir):
    check_config_file()

    config_file = get_config_file_path()

    config = configparser.ConfigParser()
    config.read(config_file)

    bucket = config['DEFAULT'].get('bucket')
    if not bucket:
        print("Bucket name is not defined in the configuration file.")
        sys.exit(1)

    s3 = boto3.client('s3',
                      endpoint_url='https://storage.yandexcloud.net',
                      aws_access_key_id=config['DEFAULT']['aws_access_key_id'],
                      aws_secret_access_key=config['DEFAULT']['aws_secret_access_key'])

    # Проверяем наличие фотоальбома
    response = s3.list_objects(Bucket=bucket, Prefix=f"{album}/")
    album_exists = 'Contents' in response

    # Создаем фотоальбом, если он не существует
    if not album_exists:
        s3.put_object(Body='', Bucket=bucket, Key=f"{album}/")

    # Отправляем фотографии
    if os.path.isdir(photos_dir):
        files = [f for f in os.listdir(photos_dir) if os.path.isfile(os.path.join(photos_dir, f))]
        if files:
            photos_uploaded = False
            for file in files:
                file_path = os.path.join(photos_dir, file)
                if re.search(r"\.(jpe?g)$", file, re.IGNORECASE):
                    try:
                        with open(file_path, 'rb') as f:
                            s3.upload_fileobj(f, bucket, f"{album}/{file}")
                        photos_uploaded = True
                    except Exception as e:
                        print(f"Warning: Photo not sent {file}")
                else:
                    print(f"Warning: Invalid file format {file}")

            if not photos_uploaded:
                print(f"Warning: No valid photos found in directory {photos_dir}")
                sys.exit(1)
        else:
            print(f"Warning: Photos not found in directory {photos_dir}")
            sys.exit(1)
    else:
        print(f"Warning: No such directory {photos_dir}")
        sys.exit(1)

    print("Upload completed successfully.")


def delete_album(album):
    check_config_file()

    config_file = get_config_file_path()

    config = configparser.ConfigParser()
    config.read(config_file)

    bucket = config['DEFAULT'].get('bucket')
    if not bucket:
        print("Bucket name is not defined in the configuration file.")
        sys.exit(1)

    s3 = boto3.client('s3',
                      endpoint_url='https://storage.yandexcloud.net',
                      aws_access_key_id=config['DEFAULT']['aws_access_key_id'],
                      aws_secret_access_key=config['DEFAULT']['aws_secret_access_key'])

    # Проверяем наличие фотоальбома
    response = s3.list_objects(Bucket=bucket, Prefix=f"{album}/")
    album_exists = 'Contents' in response

    # Удаляем альбом, если он существует
    if album_exists:
        # Удаляем все фотографии из альбома
        objects = response['Contents']
        objects_to_delete = [{'Key': obj['Key']} for obj in objects]
        s3.delete_objects(Bucket=bucket, Delete={'Objects': objects_to_delete})

        # Удаляем определение фотоальбома
        s3.delete_object(Bucket=bucket, Key=f"{album}/")

        print(f"Album '{album}' deleted successfully.")
        sys.exit(0)
    else:
        print(f"Warning: Photo album not found {album}")
        sys.exit(1)


def set_bucket_public_access(bucket_name):
    # Чтение конфигурационного файла
    config_path = get_config_file_path()
    config = configparser.ConfigParser()
    config.read(config_path)

    s3 = boto3.client('s3',
                      endpoint_url='https://storage.yandexcloud.net',
                      aws_access_key_id=config['DEFAULT']['aws_access_key_id'],
                      aws_secret_access_key=config['DEFAULT']['aws_secret_access_key'])

    # Установка политики публичного доступа на чтение объектов бакета
    response = s3.put_bucket_acl(
        Bucket=bucket_name,
        ACL='public-read'
    )

    return True


def configure_bucket_website(bucket_name):
    # Чтение конфигурационного файла
    config_path = get_config_file_path()
    config = configparser.ConfigParser()
    config.read(config_path)

    s3 = boto3.client('s3',
                      endpoint_url='https://storage.yandexcloud.net',
                      aws_access_key_id=config['DEFAULT']['aws_access_key_id'],
                      aws_secret_access_key=config['DEFAULT']['aws_secret_access_key'])

    # Настройка веб-сайта бакета
    response = s3.put_bucket_website(
        Bucket=bucket_name,
        WebsiteConfiguration={
            'IndexDocument': {'Suffix': 'index.html'},
            'ErrorDocument': {'Key': 'error.html'}
        }
    )


def get_albums():
    # Чтение конфигурационного файла
    config_path = get_config_file_path()
    config = configparser.ConfigParser()
    config.read(config_path)

    s3 = boto3.client('s3',
                      endpoint_url='https://storage.yandexcloud.net',
                      aws_access_key_id=config['DEFAULT']['aws_access_key_id'],
                      aws_secret_access_key=config['DEFAULT']['aws_secret_access_key'])

    # Получение списка объектов в бакете
    response = s3.list_objects_v2(Bucket=config['DEFAULT']['bucket'])

    if not response.get('Contents'):
        print("Photo albums not found")
        sys.exit(1)

    # Извлечение имен альбомов из списка объектов
    albums = [obj for obj in response['Contents'] if obj['Key'].endswith('/')]

    return albums


def get_album_content(album_name):
    # Чтение конфигурационного файла
    config_path = get_config_file_path()
    config = configparser.ConfigParser()
    config.read(config_path)

    s3 = boto3.client('s3',
                      endpoint_url='https://storage.yandexcloud.net',
                      aws_access_key_id=config['DEFAULT']['aws_access_key_id'],
                      aws_secret_access_key=config['DEFAULT']['aws_secret_access_key'])

    # Получение списка объектов в альбоме
    response = s3.list_objects_v2(Bucket=config['DEFAULT']['bucket'], Prefix=album_name)

    # Извлечение имен фотографий из списка объектов
    album_content = [obj['Key'] for obj in response['Contents'] if obj['Key'] != album_name]

    return album_content


def generate_and_publish_website():
    # Чтение конфигурационного файла
    config = configparser.ConfigParser()
    config_path = get_config_file_path()
    config.read(config_path)

    s3 = boto3.client('s3',
                      endpoint_url='https://storage.yandexcloud.net',
                      aws_access_key_id=config['DEFAULT']['aws_access_key_id'],
                      aws_secret_access_key=config['DEFAULT']['aws_secret_access_key'])

    # Получение имени бакета из конфигурационного файла
    bucket_name = config.get('DEFAULT', 'bucket')

    # Установка публичного доступа на чтение объектов бакета
    set_bucket_public_access(bucket_name)

    # Настройка хостинга статического сайта
    configure_bucket_website(bucket_name)

    album_number = 1
    albums = get_albums()

    index_html = generate_index_html(albums)
    index_html_key = f"index.html"
    s3.put_object(Bucket=config['DEFAULT']['bucket'], Key=index_html_key, Body=index_html, ContentType='text/html')

    error_html = generate_error_html()
    error_html_key = f"error.html"
    s3.put_object(Bucket=config['DEFAULT']['bucket'], Key=error_html_key, Body=error_html, ContentType='text/html')

    for album in albums:
        html = generate_html_for_album(get_album_content(album['Key']))
        html_key = f"album{album_number}.html"
        s3.put_object(Bucket=config['DEFAULT']['bucket'], Key=html_key, Body=html, ContentType='text/html')
        album_number += 1

    print("Website generation and publishing completed.")
    print("https://itiscl-spr23-22-cloudphoto-test.website.yandexcloud.net")


def generate_html_for_album(photos):
    html_template = """
    <!doctype html>
    <html>
        <head>
            <meta charset=utf-8>
            <link rel="stylesheet" type="text/css" href="https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/themes/classic/galleria.classic.min.css" />
            <style>
                .galleria{ width: 960px; height: 540px; background: #000 }
            </style>
            <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/galleria.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/themes/classic/galleria.classic.min.js"></script>
        </head>
        <body>
            <div class="galleria">
    """

    for photo in photos:
        photo_filename = os.path.basename(photo)

        html_template += f"""
            <img src="{photo}" data-title="{photo_filename}">
        """

    html_template += """
            </div>
            <p>Вернуться на <a href="index.html">главную страницу</a> фотоархива</p>
            <script>
                (function() {
                    Galleria.run('.galleria');
                }());
            </script>
        </body>
    </html>
    """
    return html_template


def generate_index_html(albums):
    index_html = '''<html>
    <head>
        <meta charset=utf-8>
        <title>PhotoAlbum</title>
    </head>
    <body>
        <h1>PhotoAlbum</h1>
        <ul>\n'''

    album_number = 1
    for album in albums:
        album_name = album['Key']
        album_html = f'<li><a href="album{album_number}.html">{album_name}</a></li>\n'
        index_html += album_html
        album_number += 1

    index_html += '''        </ul>
    </body>
</html>'''

    return index_html


def generate_error_html():
    error_html = '''<html>
    <head>
        <meta charset=utf-8>
        <title>Фотоархив</title>
    </head>
    <body>
        <h1>Ошибка</h1>
        <p>Ошибка при доступе к фотоархиву. Вернитесь на <a href="index.html">главную страницу</a> фотоархива.</p>
    </body>
    </html>'''

    return error_html


def main():
    parser = argparse.ArgumentParser(prog='cloudphoto', description='Cloud Photo Program')
    subparsers = parser.add_subparsers(title='Commands', dest='command', metavar='COMMAND')

    # Команда init
    init_parser = subparsers.add_parser('init', help='Initialize the program')

    # Команда list
    list_parser = subparsers.add_parser('list', help='List albums')

    # Команда upload
    upload_parser = subparsers.add_parser('upload', help='Upload photos')
    upload_parser.add_argument('--album', required=True, help='Album name')
    upload_parser.add_argument('--path', default='.', help='Photos directory')

    # Команда delete
    delete_parser = subparsers.add_parser('delete', help='Delete album')
    delete_parser.add_argument('album', help='Album name')

    # Команда mksite
    mksite_parser = subparsers.add_parser('mksite', help='Generate and publish photo archive website')

    args = parser.parse_args()


    if args.command != 'init':
        check_config_file()


    if args.command == 'init':
        initialize_program()
    elif args.command == 'list':
        list_albums()
    elif args.command == 'upload':
        if args.album:
            album = args.album
            photos_dir = args.path if args.path else "."
            upload_photos(album, photos_dir)
        else:
            parser.print_help()
    elif args.command == 'delete':
        if args.album:
            album = args.album
            delete_album(album)
        else:
            parser.print_help()
    elif args.command == 'mksite':
        generate_and_publish_website()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
