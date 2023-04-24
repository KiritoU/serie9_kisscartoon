import logging
from time import sleep

from bs4 import BeautifulSoup

from helper import helper
from kisscartoon import Kisscartoon
from settings import CONFIG

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


class Crawler:
    def crawl_soup(self, url):
        logging.info(f"Crawling {url}")

        html = helper.download_url(url)
        soup = BeautifulSoup(html.content, "html.parser")

        return soup

    def get_episodes_data(self, watching_href: str) -> dict:
        if "http" not in watching_href:
            watching_href = CONFIG.SERIES9_HOMEPAGE + watching_href

        res = {}
        try:
            soup = self.crawl_soup(watching_href)

            main_detail = soup.find("div", class_="main-detail")
            mv_info = main_detail.find("div", {"id": "mv-info"})
            list_eps = mv_info.find("div", {"id": "list-eps"})
            servers = list_eps.find_all("div", class_="le-server")
            for server in servers:
                les_content = server.find("div", class_="les-content")
                episodes = les_content.find_all("a")
                for episode in episodes:
                    title = episode.get("title")
                    player_data = episode.get("player-data")
                    episode_data = episode.get("episode-data")

                    res.setdefault(episode_data, {})
                    res[episode_data].setdefault("title", "")
                    res[episode_data].setdefault("links", [])

                    if res[episode_data]["title"] != title:
                        res[episode_data]["title"] = title
                    res[episode_data]["links"].append(player_data)

        except Exception as e:
            helper.error_log(
                f"Failed to get episode information--{watching_href}",
                log_file="episodes.log",
            )

        return res

    def crawl_film(self, href: str, post_type: str = "series"):
        soup = self.crawl_soup(href)

        title, description = helper.get_title_and_description(soup)
        watching_href, fondo_player = helper.get_watching_href_and_fondo(soup)
        if not watching_href:
            watching_href += "/watching.html"

        poster_url = helper.get_poster_url(soup)

        fondo_player = helper.add_https_to(fondo_player)
        poster_url = helper.add_https_to(poster_url)

        trailer_id = helper.get_trailer_id(soup)
        extra_info = helper.get_extra_info(soup)

        if not title:
            helper.error_log(
                log_msg=f"No title was found--{href}", log_file="base.no_title.log"
            )
            return

        film_data = {
            "title": title,
            "description": description,
            "post_type": post_type,
            "trailer_id": trailer_id,
            "fondo_player": fondo_player,
            "poster_url": poster_url,
            "extra_info": extra_info,
        }

        episodes_data = self.get_episodes_data(watching_href)

        return [film_data, episodes_data]

    def crawl_page(self, url, post_type: str = "series"):
        soup = self.crawl_soup(url)

        movies_list = soup.find("div", class_="movies-list")
        if not movies_list:
            return 0

        ml_items = movies_list.find_all("div", class_="ml-item")
        if not ml_items:
            return 0

        for item in ml_items:
            try:
                href = item.find("a").get("href")

                if "http" not in href:
                    href = CONFIG.SERIES9_HOMEPAGE + href

                film_data, episodes_data = self.crawl_film(
                    href=href, post_type=post_type
                )

                Kisscartoon(film_data, episodes_data).insert_film()

                sleep(CONFIG.WAIT_BETWEEN_MOVIE)
            except Exception as e:
                helper.error_log(f"Failed for item in--{url}", "page.log")

        return 1


if __name__ == "__main__":
    Crawler().crawl_page(
        "https://series9.la/movie/filter/movie/all/all/all/all/latest/?page=599",
        "movie",
    )
    # Crawler_Site().crawl_episodes(
    #     1, "https://series9.la/film/country-queen-season-1/watching.html", "", "", ""
    # )

    # Crawler_Site().crawl_film("https://series9.la/film/the-masked-dancer-season-2-uk")
    # Crawler_Site().crawl_film(
    #     "https://series9.la/film/the-curse-of-oak-island-season-10"
    # )
    # Crawler_Site().crawl_film("https://series9.la//film/crossing-lines-season-3-wds")

    # Crawler_Site().crawl_film(
    #     "https://series9.la//film/ghost-adventures-bwm", post_type="post"
    # )

    # Crawler_Site().crawl_film("https://series9.la//film/ghost-adventures-season-1-utc")
