import io
import json
import logging
import os
import tweepy
import tempfile

import discord
import requests
from bs4 import BeautifulSoup

from config import DISCORD_WEBHOOK_BOT_NAME, DISCORD_WEBHOOK_AVATAR_URL, DEALS_UPDATED_DISCORD_MESSAGE, \
    DEALS_IMAGE_EMBED_HEADER_MESSAGE
from secrets import API_CONSUMER_KEY, API_CONSUMER_KEY_SECRET, AUTHENTICATION_ACCESS_TOKEN, \
    AUTHENTICATION_ACCESS_TOKEN_SECRET, WEBHOOK_URL

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
    io_bytes = io.BytesIO(image)
    file = discord.File(fp=io_bytes, filename='image.png')
    webhook = discord.Webhook.from_url(WEBHOOK_URL, adapter=discord.RequestsWebhookAdapter())
    embed = discord.Embed(title=DEALS_IMAGE_EMBED_HEADER_MESSAGE)
    embed.set_image(url='attachment://image.png')
    webhook.send(username=DISCORD_WEBHOOK_BOT_NAME, avatar_url=DISCORD_WEBHOOK_AVATAR_URL, embed=embed, file=file)


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
    new_deals = list(set([d['image_name'] for d in current_deals]) - set(previous_deals))
    if new_deals:
        logging.info('New deals found')
        new_deals.reverse()
        save_deals([d['image_name'] for d in current_deals])
        send_webhook(DEALS_UPDATED_DISCORD_MESSAGE)
        auth = tweepy.OAuth1UserHandler(API_CONSUMER_KEY, API_CONSUMER_KEY_SECRET, AUTHENTICATION_ACCESS_TOKEN,
                                        AUTHENTICATION_ACCESS_TOKEN_SECRET)
        api = tweepy.API(auth)
        for new_deal in new_deals:
            new_deal = [d for d in current_deals if d['image_name'] == new_deal][0]
            logging.info(f'Downloading image from: {new_deal["url"]}')
            response = requests.get(url=new_deal['url'])
            if response.status_code != 200:
                logging.error(f'Response status code {response.status_code}')
                raise Exception(f'Response status code {response.status_code}')
            send_image(response.content)
            with tempfile.TemporaryFile() as temp:
                temp.write(response.content)
                temp.seek(0)
                try:
                    status = api.update_status_with_media(status='test', filename=new_deal['image_name'], file=temp)
                except:
                    logging.exception(f'Error when posting tweet for deal: {new_deal["image_name"]}')
    else:
        logging.info('No new deals found')


if __name__ == '__main__':
    main()
