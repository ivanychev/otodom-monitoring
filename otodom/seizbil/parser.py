import pathlib
import time
from operator import itemgetter

from furl import furl
from selenium import webdriver
from selenium.common import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
import tenacity
import json

import pandas as pd

Html = str
COLUMNS = ('announcement_date',
           'district',
           'type',
           'number',
           'offer_mode',
           'submission_start_date',
           'submission_deadline_date',
           'description')
BASE_URL = 'https://seizbil.zgnpragapld.pl'

class SeizbilSeleniumParser:
    def __init__(self):
        pass

    @classmethod
    def from_webdriver(cls):
        pass

@tenacity.retry(
    wait=tenacity.wait_fixed(2),
    retry=tenacity.retry_if_exception_type(StaleElementReferenceException),
    stop=tenacity.stop_after_attempt(5)
)
def click_page_idx(driver: WebDriver, idx: int) -> bool:
    try:
        time.sleep(2)  # Wait until the browser renders the page.
        driver.find_element(By.CSS_SELECTOR, f"[aria-label='Page {idx}']").click()
        return True
    except NoSuchElementException:
        return False

@tenacity.retry(
    wait=tenacity.wait_fixed(2),
    retry=tenacity.retry_if_exception_type(StaleElementReferenceException),
    stop=tenacity.stop_after_attempt(5)
)
def get_raw_table(d: WebDriver) -> str:
    return d.find_element(By.CLASS_NAME, "xspDataTable").get_attribute('outerHTML')

def parse_raw_tables(driver: WebDriver) -> dict[int, Html]:
    raw_pages: dict[int, str] = {}
    driver.get(f"{BASE_URL}/seizbil/projekt_konkursy.nsf/konkursyUM.xsp")

    current_page = 1
    while True:
        print(f"Processing page {current_page}")
        clicked = click_page_idx(driver, current_page)
        if not clicked:
            print(f"Not clicked on {current_page}")
            break
        raw_pages[current_page] = get_raw_table(driver)
        current_page += 1
    return raw_pages

def parse_table(table_html: str) -> pd.DataFrame:
    df = pd.read_html(table_html, extract_links="body")[0]
    df = df.set_axis(COLUMNS, axis='columns')
    df['document_url'] = df['number'].apply(lambda item: BASE_URL + item[1])
    df['document_id'] = df['document_url'].apply(lambda url: furl(url).query.params.get('documentId'))
    for col in COLUMNS:
        df[col] = df[col].apply(itemgetter(0))
    for col in ('announcement_date', 'submission_start_date', 'submission_deadline_date'):
        df[col] = pd.to_datetime(df[col], format='%b %d, %Y')
    return df

def main():
    with webdriver.Remote(
        command_executor='http://127.0.0.1:4444',
        options=webdriver.ChromeOptions()
    ) as driver:
        page_index_to_tables = parse_raw_tables(driver)
        pathlib.Path("/Users/iv/Desktop/temp.json").write_text(json.dumps(page_index_to_tables, indent=2))
        page_index_to_tables = json.loads(pathlib.Path("/Users/iv/Desktop/temp.json").read_text())
        df = pd.concat([
            parse_table(table)
            for table in page_index_to_tables.values()
        ], axis=0)
        df = df.reset_index(drop=True)
        print(df)


if __name__ == "__main__":
    main()
