import sys
import json
import pandas as pd
import requests
from bs4 import BeautifulSoup
from discord_webhook import DiscordWebhook
from dotenv import load_dotenv
import os
import time

load_dotenv()

def main(json_file: str) -> None:
    with open(json_file) as f:
        data = json.load(f)
    while True:
        search_ebay(data=data)
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
                time.sleep(1.5)


def make_soup(url: str) -> BeautifulSoup:
    r = requests.get(url)
    if r.status_code != 200:
        print('Failed to get data: ', r.status_code)
        sys.exit(1)
    return BeautifulSoup(r.text, 'html.parser')


def parse(soup: BeautifulSoup) -> list[list[str]]:
    result = []
    items = soup.select(".srp-main--isLarge .srp-grid .s-item")
    for item in items:
        title = item.select_one(".s-item__title").getText(strip=True)
        price = item.select_one(".s-item__price").getText(strip=True)
        link = item.select_one(".s-item__link")['href']
        result.append([title, price, link])
    return result



if __name__ == '__main__':
    main(sys.argv[1])
