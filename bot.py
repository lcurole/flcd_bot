import json
import logging
import os

import discord
import requests
from bs4 import BeautifulSoup

from config import DEALS_UPDATED_DISCORD_MESSAGE, DISCORD_WEBHOOK_BOT_NAME, DISCORD_WEBHOOK_AVATAR_URL
from secrets import WEBHOOK_URL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)


def load_deals():
    try:
        if os.path.exists('deals.json'):
            with open('deals.json', 'r') as f:
                return json.load(f)
        else:
            with open('deals.json', 'w') as f:
                f.write('[]')
            return []
    except json.decoder.JSONDecodeError:
        with open('deals.json', 'w') as f:
            f.write('[]')
        return []


def save_deals(deals):
    with open('deals.json', 'w') as f:
        f.write(json.dumps(deals))


def send_webhook(message):
    webhook = discord.Webhook.from_url(WEBHOOK_URL, adapter=discord.RequestsWebhookAdapter())
    webhook.send(message[:1999], username=DISCORD_WEBHOOK_BOT_NAME, avatar_url=DISCORD_WEBHOOK_AVATAR_URL)


def main():
    logging.info('Getting Short Code')
    response = requests.get(url='https://flcannabisdeals.org/todays-florida-dispensary-deals/')
    soup = BeautifulSoup(response.content, 'html.parser')
    short_code = soup.find('input')['data-photonic-shortcode']

    logging.info(f'Getting deals')
    data = {
        'action': 'photonic_lazy_load',
        'shortcode': short_code
    }
    response = requests.post(url='https://flcannabisdeals.org/wp-admin/admin-ajax.php', data=data)
    soup = BeautifulSoup(response.content, 'html.parser')
    deals_html = soup.find_all('figure', {'class': 'photonic-level-1'})
    current_deals = []
    for deal in deals_html:
        image = requests.get(deal.find('img')['src'])
        hashish = hashlib.md5(image.content)
        current_deals.append(hashish.hexdigest())
    previous_deals = load_deals()
    if collections.Counter(current_deals) != collections.Counter(previous_deals):
        logging.info('Deals have been updated')
        logging.info(f'Current Deals:\n{current_deals}')
        logging.info(f'Previous Deals:\n{previous_deals}')
        save_deals(current_deals)
        send_webhook(DEALS_UPDATED_DISCORD_MESSAGE)


if __name__ == '__main__':
    main()
