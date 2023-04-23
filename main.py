import sys
import json
import pandas as pd
import requests
from bs4 import BeautifulSoup
from discord_webhook import DiscordWebhook
from dotenv import load_dotenv
import os
import time
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main(json_file: str) -> None:
    logger.info("starting main.py")
    with open(json_file) as f:
        data = json.load(f)
    while True:
        try:
            search_mercari(data)
            search_ebay(data)
        except Exception as e:
            logger.error(f"Failed to search: {e}")
        time.sleep(60)

def search_ebay(data):
    results = []
    for query in data["queries"]:
        url = f"https://www.ebay.com/sch/i.html?_from=R40&_trksid=p2380057.m570.l1313&_nkw={query['keyword']}&_sacat=0"
        print(url, file=sys.stderr)
        df = pd.DataFrame(parse(make_soup(url)), columns=['title', 'price', 'link'])
        df["query"] = query["keyword"]
        df["max_price"] = query["max_price"]
        results.append(df)

    df_all = pd.concat(results)
    df_all.to_csv("output.csv", sep="\t", index=False)
    alert_discord()
    print("Done!")

def search_mercari(data):
    results = []
    for query in data["queries"]:
        url = f"https://www.mercari.com/search/?keyword={query['keyword']}"
        print(url, file=sys.stderr)
        df = pd.DataFrame(parse(make_soup(url)), columns=['title', 'price', 'link'])
        df["query"] = query["keyword"]
        df["max_price"] = query["max_price"]
        results.append(df)

    df_all = pd.concat(results)
    df_all.to_csv("output.csv", sep="\t", index=False, mode='a', header=False)
    alert_discord()
    print("Done!")

def alert_discord():
    # reads output.csv and sends discord webhook
    urls_sent = []
    with open('output.csv', 'r') as file:
        for line in file:
            url = line.strip().split("\t")[2]
            if url not in urls_sent:
                urls_sent.append(url)
                webhook = DiscordWebhook(url=os.getenv('webhook_url'), content=url)
                response = webhook.execute()
                print(response)
                logger.info(f"Sent Discord alert for {url}")
                time.sleep(1.5)


def make_soup(url: str) -> BeautifulSoup:
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to get data: {e}", file=sys.stderr)
        return None
    return BeautifulSoup(r.text, 'html.parser')



def parse(soup: BeautifulSoup) -> list[list[str]]:
    result = []
    items = soup.select(".srp-main--isLarge .srp-grid .s-item")
    for item in items:
        title_elem = item.select_one(".s-item__title")
        if not title_elem:
            continue
        title = title_elem.get_text(strip=True)
        price_elem = item.select_one(".s-item__price")
        if not price_elem:
            continue
        price = price_elem.get_text(strip=True)
        link_elem = item.select_one(".s-item__link")
        if not link_elem:
            continue
        link = link_elem['href']
        result.append([title, price, link])
    return result



if __name__ == '__main__':
    main(sys.argv[1])
