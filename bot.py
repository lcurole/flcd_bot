import json
import logging
import os

import discord
import requests
from bs4 import BeautifulSoup

from config import DISCORD_WEBHOOK_BOT_NAME, DISCORD_WEBHOOK_AVATAR_URL, DEALS_UPDATED_DISCORD_MESSAGE
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


def send_image(image):
    webhook = discord.Webhook.from_url(WEBHOOK_URL, adapter=discord.RequestsWebhookAdapter())
    embed = discord.Embed(title='New Deal!')
    embed.set_image(url=image)
    webhook.send(username=DISCORD_WEBHOOK_BOT_NAME, avatar_url=DISCORD_WEBHOOK_AVATAR_URL, embed=embed)


def main():
    logging.info('Getting Short Code')
    response = requests.get(url='https://flcannabisdeals.org/todays-florida-dispensary-deals/')
    soup = BeautifulSoup(response.content, 'html.parser')
    short_code = soup.find('input', {'class': 'photonic-js-load-button'})
    if not short_code or not short_code['data-photonic-shortcode']:
        logging.error('No short code found')
        raise Exception('No short code found')
    short_code = short_code['data-photonic-shortcode']

    logging.info(f'Getting deals')
    data = {
        'action': 'photonic_lazy_load',
        'shortcode': short_code
    }
    response = requests.post(url='https://flcannabisdeals.org/wp-admin/admin-ajax.php', data=data)
    soup = BeautifulSoup(response.content, 'html.parser')
    deals_html = soup.find_all('figure', {'class': 'photonic-level-1'})
    if not deals_html:
        logging.error('No deals found')
        raise Exception('No deals found')

    current_deals = []
    for deal in deals_html:
        url = deal.find('img')['src']
        current_deals.append({
            'url': url,
            'image_name': url.split('/')[-1],
        })
    previous_deals = load_deals()
    new_deals = set([d['image_name'] for d in current_deals]) - set(previous_deals)
    if new_deals:
        logging.info('New deals found')
        save_deals([d['image_name'] for d in current_deals])
        send_webhook(DEALS_UPDATED_DISCORD_MESSAGE)
        for new_deal in new_deals:
            send_image([d for d in current_deals if d['image_name'] == new_deal][0]['url'])
    else:
        logging.info('No new deals found')


if __name__ == '__main__':
    main()
