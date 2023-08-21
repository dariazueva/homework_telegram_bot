import os
import logging
import telegram
from dotenv import load_dotenv
import time
import requests
from logging import StreamHandler


load_dotenv()


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler()
formatter=logging.Formatter('%(asctime)s, %(levelname)s, %(message)s')
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
    try:
        if not PRACTICUM_TOKEN or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
            raise ValueError('Отсуствуют переменные окружения.')
    except ValueError:
        logger.critical('Отсуствуют переменные окружения.')
        exit()

def send_message(bot, message):
    """Отправка сообщения в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Удачная отправка сообщения в Telegram.')
    except telegram.TelegramError:
        logger.error('Сбой при отправке сообщения в Telegram.')
    return message

def get_api_answer(timestamp):
    """Создание запроса к эндпоинту."""
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params={'from_date': timestamp})
        if response.status_code != 200:
            logger.error('Неожиданный статус домашней работы, обнаруженный в ответе API.')
            raise requests.RequestException(f'Получен ответ с кодом состояние {response.status_code}')
        response = response.json()
    except Exception as error:
        logger.error(error)
        raise Exception(error)
    return response

def check_response(response):
    """Проверка ответа API."""
    if type(response) != dict:
        logger.error('Ответ API не соответствует ожидаемому типу данных dict.')
        raise TypeError('Тип данных {type(response)} не соответсвует ожидаемому типу dict.')
    elif ('homeworks' in response) and ('current_date' in response):
        if type(response['homeworks']) != list:
            logger.error('Ответ API с ключом словаря homeworks не соответствует ожидаемому типу данных list.')
            raise TypeError('Тип данных {type("homeworks")} не соответсвует ожидаемому типу list.')
        return response.get('homeworks')
    logger.error('Отсутствуют ожидаемые ключи в ответе API.')
    raise KeyError('Подходящих ключей нет в ответе API.')

def parse_status(homework):
    """Извлечение информации из ответа API."""
    if homework['status'] not in HOMEWORK_VERDICTS:
        logger.error('Неизвестный статус.')
        raise KeyError('Статус не найден.')
    elif 'homework_name' not in homework:
        logger.error('Отсуствует ключ "homework_name".')
        raise KeyError('Ключ "homework_name" не найден.')
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[homework['status']]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
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
