import asyncio
import json
import os
import time
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup


def load_posted_ids():
    if os.path.exists('posted_items.json'):
        with open('posted_items.json') as f:
            return set(json.load(f))
    return set()


def save_posted_ids(posted_ids):
    with open('posted_items.json', 'w') as f:
        json.dump(sorted(list(posted_ids)), f, indent=2)


def scrape_items():
    url = 'https://arco.trasparenza-valutazione-merito.it/web/trasparenza/albo-pretorio-informatico'
    params = {
        'p_p_id': 'jcitygovalbopubblicazioni_WAR_jcitygovalbiportlet',
        'p_p_lifecycle': '1',
        'p_p_state': 'pop_up',
        'p_p_mode': 'view',
        '_jcitygovalbopubblicazioni_WAR_jcitygovalbiportlet_action': 'eseguiPaginazione'
    }
    data = {
        'hidden_page_size': '50',
        'hidden_page_to': ''
    }

    response = requests.post(url, params=params, data=data, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    items = []
    for row in soup.find_all('tr', {'data-id': True}):
        item_id = row['data-id']

        # Extract basic fields
        registration = row.find('td', class_='annonumeroregistrazione').text.strip()
        document = row.find('td', class_='annonumero').text.strip()

        # Document type: combine categoria + subcategoria
        cat_elem = row.find('span', class_='categoria_categoria')
        subcat_elem = row.find('span', class_='categoria_sottocategoria')

        if cat_elem and subcat_elem:
            doc_type = f"{cat_elem.text.strip()}/{subcat_elem.text.strip()}"
        else:
            doc_type = "N/A"

        subject = row.find('td', class_='oggetto').text.strip()

        # Dates: get text with separator
        dates_elem = row.find('td', class_='periodo-pubblicazione')
        dates = dates_elem.get_text(' - ', strip=True) if dates_elem else "N/A"

        # Attachments: get badge number or 0
        badge = row.find('span', class_='badge')
        attachments = int(badge.text.strip()) if badge else 0

        # URL: extract from actions link
        link_elem = row.find('td', class_='actions')
        item_url = None
        if link_elem:
            link = link_elem.find('a')
            if link and 'href' in link.attrs:
                item_url = link['href']

        items.append({
            'id': item_id,
            'registration': registration,
            'document': document,
            'type': doc_type,
            'subject': subject,
            'dates': dates,
            'attachments': attachments,
            'url': item_url
        })

    return items


async def post_to_telegram(item):
    bot = Bot(token=os.getenv('BOT_TOKEN'))
    channel_id = os.getenv('CHANNEL_ID')

    # Escape markdown special characters in text fields
    def escape_markdown(text):
        """Escape special characters for Telegram MarkdownV2."""
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text

    # Format message with Markdown
    message = f"""📋 *{escape_markdown(item['type'])}*

🔢 Registro: {escape_markdown(item['registration'])}
📄 Atto: {escape_markdown(item['document'])}

📝 *Oggetto:*
{escape_markdown(item['subject'])}

📅 Pubblicazione: {escape_markdown(item['dates'])}
📎 Allegati: {item['attachments']}"""

    # Create inline keyboard with button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Visualizza dettagli", url=item['url'])]
    ])

    await bot.send_message(
        chat_id=channel_id,
        text=message,
        parse_mode='MarkdownV2',
        reply_markup=keyboard,
        disable_web_page_preview=True
    )


def main():
    # Load environment variables
    load_dotenv()

    # Check required env vars
    if not os.getenv('BOT_TOKEN') or not os.getenv('CHANNEL_ID'):
        print("Error: BOT_TOKEN and CHANNEL_ID must be set in .env file")
        return 1

    # Check if this is the first run
    is_first_run = not os.path.exists('posted_items.json')

    # Load posted IDs
    posted_ids = load_posted_ids()
    print(f"Loaded {len(posted_ids)} posted items")

    # Scrape items
    items = scrape_items()
    print(f"Scraped list of {len(items)} items")

    if not items:
        print("Error: no items scraped")
        return 1

    # First run: just save all IDs without posting
    if is_first_run:
        for item in items:
            posted_ids.add(item['id'])
        save_posted_ids(posted_ids)
        print(f"✓ Saved {len(items)} item IDs as this is the first run, future runs will only post new items")
        return 0

    # Filter new items
    new_items = [item for item in items if item['id'] not in posted_ids]
    print(f"Found {len(new_items)} new items")

    if not new_items:
        print("No new items to post")
        return 0

    # Sort by registration number (oldest first)
    new_items.sort(key=lambda x: x['registration'])

    # Post each new item
    posted_count = 0
    for item in new_items:
        try:
            asyncio.run(post_to_telegram(item))
            posted_ids.add(item['id'])
            save_posted_ids(posted_ids)
            print(f"✓ Posted: {item['registration']}")
            posted_count += 1
            time.sleep(1)  # Rate limiting
        except Exception as e:
            print(f"✗ Failed to post {item['registration']}: {e}")

    print(f"Done! Posted {posted_count}/{len(new_items)} items")
    return 0


if __name__ == '__main__':
    exit(main())
