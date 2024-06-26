import logging
import os
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
import telegram
from dotenv import load_dotenv

from exceptions import ResponseException

load_dotenv()


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler()
formatter = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Отправка сообщения в Telegram чат."""
    try:
        logger.debug('Начало отправки сообщения в Telegram.')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Удачная отправка сообщения в Telegram.')
    except telegram.TelegramError:
        logger.error('Сбой при отправке сообщения в Telegram.')
    return message


def get_api_answer(timestamp):
    """Создание запроса к эндпоинту."""
    try:
        logger.debug('Начало запроса к API.')
        response = requests.get(ENDPOINT, headers=HEADERS,
                                params={'from_date': timestamp})
    except Exception as error:
        raise ResponseException(error)
    if response.status_code != HTTPStatus.OK:
        raise requests.RequestException(f'Получен ответ с кодом состояние'
                                        f'{response.status_code}')
    return response.json()


def check_response(response):
    """Проверка ответа API."""
    if isinstance(response, dict) is False:
        raise TypeError(f'Тип данных {type(response)}'
                        f'не соответсвует ожидаемому типу dict.')
    if 'homeworks' not in response:
        raise KeyError('Ключа "homeworks" нет в ответе API.')
    if 'current_date' not in response:
        raise KeyError('Ключа "current_date" нет в ответе API.')
    homeworks = response.get('homeworks')
    if isinstance(homeworks, list) is False:
        raise TypeError(f'Тип данных {type("homeworks")} не'
                        f'соответсвует ожидаемому типу list.')
    return homeworks


def parse_status(homework):
    """Извлечение информации из ответа API."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if 'homework_name' not in homework:
        raise KeyError('Ключа "homework_name" нет в ответе API.')
    if 'status' not in homework:
        raise KeyError('Ключа "status" нет в ответе API.')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(f'Статуса {homework_status}'
                       f'нет в словаре HOMEWORK_VERDICTS.')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсуствуют переменные окружения.')
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    previous_message = None
    previous_error = None
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                new_message = parse_status(homework[0])
                if new_message != previous_message:
                    send_message(bot, new_message)
                    previous_message = new_message
                else:
                    logger.debug('Нет новых домашек в "homeworks".')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if error != previous_error:
                send_message(bot, message)
                previous_error = error
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
