import logging
import time

from base import Crawler
from settings import CONFIG

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


crawler = Crawler()

if __name__ == "__main__":
    while True:
        try:
            crawler.crawl_page(
                url=CONFIG.SERIES9_MOVIES_LATEST_PAGE, post_type="single"
            )
        except Exception as e:
            pass
        time.sleep(CONFIG.WAIT_BETWEEN_LATEST)
