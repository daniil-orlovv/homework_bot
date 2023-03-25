import os
import requests
import time
import logging
import sys
from exeptions import MyException


import telegram

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    encoding='UTF-8'
)

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
    """Проверяем наличие переменных."""
    try:
        os.environ['PRACTICUM_TOKEN']
        os.environ['TELEGRAM_TOKEN']
        os.environ['TELEGRAM_CHAT_ID']
    except KeyError as e:
        logging.critical(f'Переменная {e.args[0]} не найдена.')
        sys.exit()


def send_message(bot, message):
    """Отправляем сообщение о статусе в телеграм."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('Сообщение о статусе отправлено.')
    except Exception as e:
        logging.error(f'Не удалось отправить сообщение: {str(e)}')


def get_api_answer(timestamp):
    """Получаем API с информацией о домашних работах."""

    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != 200:
            logging.error(f'Bad response: {response.status_code}')
            raise requests.exceptions.HTTPError
    except requests.exceptions.HTTPError:
        raise MyException('Это мое собственное исключение!')
    except requests.RequestException:
        logging.error('Ошибка запроса')


    return response.json()


def check_response(response):
    """Проверяем API на соответствие документации."""
    if not isinstance(response, dict):
        logging.error('API response is not a dictionary')
        raise TypeError('API response is not a dictionary')
    if not isinstance(response['current_date'], int):
        logging.error('current_date is not an integer')
        raise TypeError('current_date is not a dictionary')
    try:
        if not isinstance(response['homeworks'], list):
            logging.error('homeworks is not a list')
            raise TypeError('homeworks is not a dictionary')
    except KeyError:
        logging.error('homeworks not in a response')
        raise KeyError('homeworks not in a response')
    print(response)


def parse_status(homework):
    """Обрабатываем API и создаем ответ о статусе."""
    homework_name = homework['homeworks'][0]['homework_name']
    status = homework['homeworks'][0]['status']
    verdict = HOMEWORK_VERDICTS.get(status)
    print(homework_name, status, verdict)
    if homework_name and verdict:
        if status in HOMEWORK_VERDICTS:
            logging.info('Статус работы изменен.')
            return f'Изменился статус проверки работы "{homework_name}". {verdict}'
        else:
            logging.error(f'Неизвестный статус домашней работы: {verdict}')
            raise ValueError(f'Неизвестный статус домашней работы: {verdict}')

def main():
    """Основная логика работы бота."""
    check_tokens()
    timestamp = int(time.time()) - RETRY_PERIOD
    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    while True:
        try:
            response_json = get_api_answer(timestamp)
            check_response(response_json)
            message = parse_status(response_json)
            send_message(bot, message)
            timestamp = response_json['current_date']
        except Exception as error:
            print(f'Сбой в работе программы: {error}')
        time.sleep(RETRY_PERIOD)

if __name__ == '__main__':
    main()
