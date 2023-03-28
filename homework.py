import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exeptions import MyRequestsException, MyBotHTTPError
from config import PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from config import RETRY_PERIOD, ENDPOINT, HEADERS

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    encoding='UTF-8'
)


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяем наличие переменных."""
    if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        logging.critical('Отсутствуют обязательные переменные.')
        sys.exit(1)


def send_message(bot, message):
    """Отправляем сообщение о статусе в телеграм."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('Сообщение о статусе отправлено.')
    except telegram.error.TelegramError as e:
        logging.error(f'Не удалось отправить сообщение: {str(e)}')
        raise MyRequestsException('Ошибка отправки сообщения в Telegram') from e


def get_api_answer(timestamp):
    """Получаем API с информацией о домашних работах."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            logging.error(f'Bad response: {response.status_code}')
            raise MyBotHTTPError("Bad response:", response.status_code)
    except requests.exceptions.HTTPError:
        raise MyRequestsException(f'Bad response: {response.status_code}')
    except requests.RequestException:
        logging.error('Ошибка связанная с запросом')
    return response.json()


def check_response(response):
    """Проверяем API на соответствие документации."""
    if not isinstance(response, dict):
        logging.error('API response is not a dictionary')
        raise TypeError('API response is not a dictionary')
    if not isinstance(response['current_date'], int):
        logging.error('current_date is not an integer')
        raise TypeError('current_date is not a dictionary')
    if 'homeworks' not in response:
        logging.error('homeworks is not in a response')
        raise IndexError('homeworks is not in a response')
    if not isinstance(response['homeworks'], list):
        logging.error('homeworks is not a list')
        raise TypeError('homeworks is not a list')
    print(response)
    if response['homeworks']:
        logging.info('homeworks key value found')
        return response['homeworks'][0]
    else:
        logging.error('homeworks key value NOT FOUND')
        raise IndexError('homeworks key value NOT FOUND')


def parse_status(homework):
    """Обрабатываем API и создаем ответ о статусе."""
    print(homework)
    if 'homework_name' in homework:
        logging.info('Значение ключа homework_name найдено')
    else:
        logging.error('Значение ключа homework_name не найдено')
        raise IndexError('Значение ключа homework_name не найдено')
    homework_name = homework['homework_name']
    print(homework_name)
    status = homework['status']
    if status in HOMEWORK_VERDICTS:
        logging.info('Значение статуса соответствует HOMEWORK_VERDICTS')
        verdict = HOMEWORK_VERDICTS.get(status)
        print(verdict)
        logging.info('Статус работы изменился')
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
            homeworks = check_response(response_json)
            message = parse_status(homeworks)
            send_message(bot, message)
            timestamp = response_json['current_date']
        except Exception as error:
            logging.error(f'Ошибка в работе программы: {error}')
            print(f'Сбой в работе программы: {error}')
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
