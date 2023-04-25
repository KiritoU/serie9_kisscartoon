import json
import logging
import re
from datetime import datetime, timedelta

from slugify import slugify

from _db import database
from helper import helper
from settings import CONFIG

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


class Kisscartoon:
    def __init__(self, film: dict, episodes: dict):
        self.film = film
        self.film["quality"] = (
            "HD"
            if "Quality" not in self.film["extra_info"].keys()
            else self.film["extra_info"]["Quality"]
        )
        self.episodes = episodes

    def generate_film_data(
        self,
        title,
        description,
        post_type,
        trailer_id,
        quality,
        fondo_player,
        poster_url,
        extra_info,
    ):
        post_data = {
            "description": description,
            "title": title,
            "post_type": post_type,
            # "id": "202302",
            "youtube_id": trailer_id,
            "quality": quality,
            # "serie_vote_average": extra_info["IMDb"],
            # "episode_run_time": extra_info["Duration"],
            "fondo_player": fondo_player,
            "poster_url": poster_url,
            # "category": extra_info["Genre"],
            # "stars": extra_info["Actor"],
            # "director": extra_info["Director"],
            # "release-year": [extra_info["Release"]],
            # "country": extra_info["Country"],
        }

        key_mapping = {
            "IMDb": "imdb",
            "Duration": "duration",
            "Genre": "genre",
            "Actor": "cast",
            "Director": "director",
            "Country": "country",
            "Release": "year",
        }

        for info_key in key_mapping.keys():
            if info_key in extra_info.keys():
                post_data[key_mapping[info_key]] = extra_info[info_key]

        return post_data

    def get_timeupdate(self) -> datetime:
        timeupdate = datetime.now() - timedelta(hours=10)

        return timeupdate

    def get_slug_list_from(self, table: str, names: list) -> str:
        res = []
        for name in names:
            try:
                condition = f"slug='{slugify(name)}'"
                data = (name, slugify(name))
                be_data_with_slug = database.select_or_insert(
                    table=table, condition=condition, data=data
                )
                res.append(be_data_with_slug[0][-1])
            except:
                pass

        return json.dumps(res)

    def insert_movie(self, post_data: dict) -> int:
        try:
            timeupdate = self.get_timeupdate()
            genre_names = post_data.get("genre", [])
            country_names = post_data.get("country", [])
            cast_names = post_data.get("cast", [])
            for name in country_names:
                if name in genre_names:
                    genre_names = genre_names.remove(name)
                if name in cast_names:
                    cast_names.remove(name)
            duration = post_data.get("duration", "")
            movie = {
                "name": post_data.get("title", ""),
                "origin_name": post_data.get("title", ""),
                "thumb": post_data.get("poster_url", ""),
                "genres": self.get_slug_list_from(table="genres", names=genre_names),
                "year": post_data.get("year", 0),
                "view": 0,
                "hot": 0,
                "content": post_data.get("description", ""),
                "type": post_data.get("post_type", ""),
                "status": "Ongoing"
                if self.film["post_type"] != "single"
                else "Completed",
                "public": 1,
                "slug": slugify(post_data.get("title", "")),
                "time": timeupdate.strftime("%Y-%m-%d %H:%M:%S"),
                "creater": timeupdate.strftime("%Y-%m-%d"),
            }
            post_id = database.insert_into(table="movie", data=list(movie.values()))

            return post_id
        except Exception as e:
            print(e)
            return 0
            # helper.error_log(f"Failed to insert film")

    def insert_root_film(self) -> list:
        condition = f"""slug = '{slugify(self.film["post_title"])}' AND type='{self.film["post_type"]}'"""
        be_post = database.select_all_from(table=f"movie", condition=condition)
        if not be_post:
            logging.info(f'Inserting root film: {self.film["post_title"]}')
            post_data = self.generate_film_data(
                self.film["post_title"],
                self.film["description"],
                self.film["post_type"],
                self.film["trailer_id"],
                self.film["quality"],
                self.film["fondo_player"],
                self.film["poster_url"],
                self.film["extra_info"],
            )

            return self.insert_movie(post_data)
        else:
            return be_post[0][0]

    def validate_movie_episodes(self) -> None:
        res = []
        for ep_num, episode in self.episodes.items():
            episode_name = episode.get("title")
            episode_links = episode.get("links")
            # episodeName = episodeName.replace("Episoden", "").strip()
            episode_name = (
                episode_name.strip()
                .replace("\n", "")
                .replace("\t", " ")
                .replace("\r", " ")
            )
            if episode_links:
                episode_links = [
                    link if link.startswith("https:") else "https:" + link
                    for link in episode_links
                ]
                res.append([episode_name, ep_num, episode_links])
        res.sort(key=lambda x: float(x[1]), reverse=True)
        self.movie_episodes = res

    def get_server_name_from(self, link: str) -> str:
        x = re.search(r"//[^/]*", link)
        if x:
            return x.group().replace("//", "")

        return "Default"

    def get_episode_server_from(self, links: list) -> list:
        removeLinks = []
        for removeLink in removeLinks:
            if removeLink in links:
                links.remove(removeLink)
        res = [
            {
                "server_name": self.get_server_name_from(link),
                "server_type": "embed",
                "server_link": link,
            }
            for link in links
        ]

        return res

    def get_episode_data(self) -> list:
        res = []
        for episode in self.movie_episodes:
            episode_name, ep_num, episode_links = episode
            if episode_name.lower().startswith(self.film["post_title"].lower()):
                episode_name = (
                    episode_name.lower()
                    .replace(self.film["post_title"].lower(), "", 1)
                    .strip()
                    .title()
                )

            res.append(
                {
                    "ep_name": episode_name,
                    "ep_slug": slugify(episode_name),
                    "ep_time": self.get_timeupdate().strftime("%Y-%m-%d"),
                    "server_data": self.get_episode_server_from(episode_links),
                }
            )

        return res

    def insert_episodes(self, movie_id: int) -> None:
        logging.info(
            f"Updating episodes for movie {self.film['post_title']} with ID: {movie_id}"
        )

        self.validate_movie_episodes()

        data = self.get_episode_data()

        data = json.dumps(data)

        be_episode_data = database.select_or_insert(
            table="episode", condition=f"movieId={movie_id}", data=(movie_id, data)
        )

        episode_data = be_episode_data[0][-1]
        # print(episode_data)
        episode_data = (
            episode_data.decode() if isinstance(episode_data, bytes) else episode_data
        )
        # with open("json/diff.txt", "w") as f:
        #     print(data, file=f)
        #     print(episode_data, file=f)

        if episode_data != data:
            print("Diff")
            escape_data = data.replace("'", "''")
            database.update_table(
                table="episode",
                set_cond=f"""data='{escape_data}'""",
                where_cond=f"movieId={movie_id}",
            )

    def insert_film(self):
        self.film["post_title"] = self.film["title"]
        self.film["season_number"] = "1"

        if len(self.episodes) > 1:
            self.film["post_type"] = "series"

        post_id = self.insert_root_film()
        if post_id:
            self.insert_episodes(post_id)
