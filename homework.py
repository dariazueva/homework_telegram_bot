import os
import telegram
from dotenv import load_dotenv
import time
import requests


load_dotenv()


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
        exit()

def send_message(bot, message):
    """Отправка сообщения в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError as error:
        raise telegram.TelegramError(error)
    return message

def get_api_answer(timestamp):
    """Создание запроса к эндпоинту."""
    response = requests.get(ENDPOINT, headers=HEADERS, params={'from_date': timestamp})
    if response.status_code != 200:
        raise requests.RequestException('Полученный статус ответа отличается от 200.')
    response = response.json()
    return response

def check_response(response):
    """Проверка ответа API."""
    if type(response) != dict:
        raise TypeError('Тип данных {type(response)} не соответсвует ожидаемому типу dict.')
    elif ('homeworks' in response) and ('current-time in response'):
        if type(response['homeworks']) != list:
            raise TypeError('Тип данных {type("homeworks")} не соответсвует ожидаемому типу list.')
        return response.get('homeworks')
    raise KeyError('Подходящего ключа нет в ответе.')

def parse_status(homework):
    """Извлечение информации из ответа API."""
    if homework['status'] not in HOMEWORK_VERDICTS:
        raise KeyError('Статус не найден.')
    elif 'homework_name' not in homework:
        raise KeyError('Ключ "homework_name" не найден.')
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[homework['status']]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            for homework in response['homeworks']:
                message = parse_status(homework)
                send_message(bot, message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            ...
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
