# Albo Pretorio Arco

This repository contains a script that scrapes albo pretorio items from the Arco municipality [transparency portal](https://arco.trasparenza-valutazione-merito.it/web/trasparenza/dettaglio-albo-pretorio?p_p_id=jcitygovmenutrasversaleleftcolumn_WAR_jcitygovalbiportlet&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&p_p_col_id=column-2&p_p_col_count=1&_jcitygovmenutrasversaleleftcolumn_WAR_jcitygovalbiportlet_current-page-parent=0&_jcitygovmenutrasversaleleftcolumn_WAR_jcitygovalbiportlet_current-page=14598) and posts new items to a Telegram channel, [https://t.me/ComuneArcoAlbo](https://t.me/ComuneArcoAlbo).

## Setup

Install dependencies:

```bash
uv sync
```

Create `.env` file with your Telegram credentials, starting from `.env.example`:

Run the project with:

```bash
uv run python main.py
```

## How it works

1. Loads previously posted item IDs from `posted_items.json`
2. Scrapes latest 50 items from the Albo Pretorio web page
3. **First run**: Saves all current item IDs without posting (initialization)
4. **Subsequent runs**: Filters out items that have already been posted
5. Posts new items to Telegram channel (oldest first)
6. Saves posted item IDs after each successful post
