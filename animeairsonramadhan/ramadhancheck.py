import requests as req
from typing import Tuple, List, TypedDict
from typing import Literal as Lit
from datetime import datetime, timedelta
from time import sleep

ANILIST_API_URL = "https://graphql.anilist.co"
ANIME_TAG_TO_FIND = "food"


FORMATS = Lit["TV", "TV_SHORT", "MOVIE", "SPECIAL", "OVA", "ONA", "MUSIC",
              "MANGA", "NOVEL", "ONE_SHOT"]
STATUS = Lit["FINISHED", "RELEASING", "NOT_YET_RELEASED", "CANCELLED", "HIATUS"]
MEDIA_TYPE = Lit["ANIME", "MANGA"]
SORT = Lit["ID", "ID_DESC", "TITLE_ROMAJI", "TITLE_ROMAJI_DESC", "TITLE_ENGLISH",
            "TITLE_ENGLISH_DESC", "TITLE_NATIVE", "TITLE_NATIVE_DESC", "TYPE",
            "TYPE_DESC", "FORMAT", "FORMAT_DESC", "START_DATE", "START_DATE_DESC",
            "END_DATE", "END_DATE_DESC", "SCORE", "SCORE_DESC", "POPULARITY",
            "POPULARITY_DESC", "TRENDING", "TRENDING_DESC", "EPISODES",
            "EPISODES_DESC", "DURATION", "DURATION_DESC", "STATUS", "STATUS_DESC",
            "CHAPTERS", "CHAPTERS_DESC", "VOLUMES", "VOLUMES_DESC", "UPDATED_AT",
            "UPDATED_AT_DESC", "SEARCH_MATCH", "FAVOURITES", "FAVOURITES_DESC"]

class Variables(TypedDict):
    page: int
    """The page to search on"""
    perPage: int
    """The number of results per page"""
    format_not_in: List[FORMATS]
    """The formats to exclude"""
    status_not_in: List[STATUS]
    """The statuses to exclude"""
    tag: str
    """The tag to search for"""
    sort: SORT
    """The sort order"""
    type: MEDIA_TYPE
    """The media type"""


def create_query(mediatype: MEDIA_TYPE = "ANIME",
                 tag: str = ANIME_TAG_TO_FIND,
                 sort: SORT = "START_DATE_DESC",
                 status_not_in: List[STATUS] = ["HIATUS", "NOT_YET_RELEASED", "CANCELLED"],
                 format_not_in: List[FORMATS] = ["MUSIC", "OVA", "SPECIAL"],
                 page: int = 1,
                 perpage: int = 50) -> Tuple[str, Variables]:
    """
    Create a query for the Anilist API
    :param tag: The tag to search for
    :param page: The page to search on
    :return: A tuple containing the page and the query
    :rtype: Tuple[str, Variables]
    """
    query = """
    query ($page: Int, $perPage: Int, $format_not_in: [MediaFormat], $status_not_in: [MediaStatus], $tag: String, $sort: [MediaSort], $type: MediaType) {
      Page (page: $page, perPage: $perPage) {
        pageInfo {
          total
          currentPage
          lastPage
          hasNextPage
          perPage
        }
        media (type: $type, sort: $sort, format_not_in: $format_not_in, status_not_in: $status_not_in, tag: $tag) {
          id
          title {
            romaji
            english
            native
          }
          episodes
          startDate {
            day
            month
            year
          }
          endDate {
            day
            month
            year
          }
          format
          status
          tags {
            name
            rank
          }
        }
      }
    }
    """
    variables: Variables = {
        "page": page,
        "perPage": perpage,
        "format_not_in": format_not_in,
        "status_not_in": status_not_in,
        "tag": tag,
        "sort": sort,
        "type": mediatype
    }

    return query, variables


def post_query(query: str, variables: Variables) -> dict:
    """
    Post a query to the Anilist API
    :param query: The query to post
    :param variables: The variables to use
    :return: The response from the API
    :rtype: dict
    """
    response = req.post(ANILIST_API_URL, json={"query": query, "variables": variables})
    return response.json()

HIJRI_MONTH_LIST = ["Muharram", "Ṣafar", "Rabīʿ al-awwal", "Rabīʿ al-thānī",
                  "Jumādá al-ūlá", "Jumādá al-ākhirah", "Rajab", "Shaʿbān",
                  "Ramaḍān", "Shawwāl", "Dhū al-Qaʿdah", "Dhū al-Ḥijjah"]
HIJRI_MONTH = Lit["Muharram", "Ṣafar", "Rabīʿ al-awwal", "Rabīʿ al-thānī",
                  "Jumādá al-ūlá", "Jumādá al-ākhirah", "Rajab", "Shaʿbān",
                  "Ramaḍān", "Shawwāl", "Dhū al-Qaʿdah", "Dhū al-Ḥijjah"]

def guess_first_hijri_months(h_year: int, month: HIJRI_MONTH = "Ramaḍān") -> Tuple[datetime, datetime]:
    """
    Guess the first day of a month in the Hijri calendar
    :param hyear: The year to guess the month for
    :type year: int
    :param month: The month to guess
    :type month: HIJRI_MONTH
    :return: The guessed date
    :rtype: tuple[datetime, datetime], the first and last day of the month
    """
    # convert the month to a number
    month = HIJRI_MONTH_LIST.index(month) + 1
    # convert to DD-MM-YYYY
    response = req.get(f"https://api.aladhan.com/v1/hToGCalendar/{month}/{h_year}")
    json = response.json()
    # get the first day of the month
    first_day = json["data"][0]["gregorian"]["date"]
    # get the last day of the month
    last_day = json["data"][-1]["gregorian"]["date"]
    # convert to datetime
    first_day = datetime.strptime(first_day, "%d-%m-%Y")
    last_day = datetime.strptime(last_day, "%d-%m-%Y")
    return first_day, last_day

def get_gregorian_to_hijri(date: datetime) -> Tuple[int, int, int]:
    """
    Get the Hijri date for a given Gregorian date
    :param date: The date to convert
    :type date: datetime
    :return: The Hijri date
    :rtype: tuple[int, int, int]
    """
    # convert to DD-MM-YYYY
    date = date.strftime("%d-%m-%Y")
    # get the Hijri date
    response = req.get(f"https://api.aladhan.com/v1/gToH?date={date}")
    json = response.json()
    # get the Hijri date
    hijri = json["data"]["hijri"]
    return int(hijri["day"]), int(hijri["month"]["number"]), int(hijri["year"])


start_date = None
start_hijri = None
end_date = None
end_hijri = None

def check_anime_airs_on_ramadhan(anime: dict) -> bool:
    """
    Check if an anime airs on Ramadan
    :param anime: The anime to check
    :type anime: dict
    :return: Whether the anime airs on Ramadan
    :rtype: bool
    """
    # get the start date
    start_date = anime["startDate"]
    if start_date is None:
        return False
    elif start_date["year"] is None or start_date["month"] is None or start_date["day"] is None:
        return False
    # get the end date
    end_date = anime["endDate"]
    if end_date is None:
        return False
    ey = end_date["year"]
    em = end_date["month"]
    ed = end_date["day"]
    # convert to datetime
    start_date = datetime(start_date["year"], start_date["month"], start_date["day"])
    if ey is None or em is None or ed is None:
        # check from total episodes to add to start date
        if anime["format"] == "MOVIE":
            end_date = start_date
        else:
            end_date = start_date
            ep = anime["episodes"] or 12
            if ep != 1:
                end_date += timedelta(days=7 * ep)
    else:
        end_date = datetime(ey, em, ed)
    # get the Hijri date
    start_hijri = get_gregorian_to_hijri(start_date)
    # get the first day of Ramadan
    ramadhan_start, ramadhan_end = guess_first_hijri_months(start_hijri[2])
    # check if the anime airs on Ramadan by checking gregorian dates
    return start_date <= ramadhan_end and end_date >= ramadhan_start


def main():
    # create the query
    query, variables = create_query(perpage=1)
    # post the query
    response = post_query(query, variables)
    init_info = response["data"]["Page"]["pageInfo"]
    # get the total number of pages
    total_pages = init_info["total"] // 50
    total = 0
    print(f"Total: {init_info['total']} anime")
    print(f"Total pages: {total_pages}")
    print(f"Estimated time: {total_pages * 2} seconds, or {total_pages * 2 / 60} minutes")
    print("")
    # loop over the pages
    for page in range(1, total_pages + 1):
        # create the query
        query, variables = create_query(page=page)
        # post the query
        response = post_query(query, variables)
        # get the anime
        animes = response["data"]["Page"]["media"]
        # loop over the anime
        for anime in animes:
            title = anime["title"]["english"]
            if title is None:
                title = anime["title"]["romaji"]
            romaji = anime["title"]["romaji"]
            id = anime["id"]
            year = anime["startDate"]["year"]
            stop = False
            #if "food" tag rank is less than 50, skip
            for tag in anime["tags"]:
                if tag["name"] == "food" and tag["rank"] < 50:
                    stop = True
            if stop:
                continue
            term_url = f"\033]8;;https://anilist.co/anime/{anime['id']}\a{title}\033]8;;\a"
            # check if the anime airs on Ramadan
            try:
                if check_anime_airs_on_ramadhan(anime):
                    # print the anime
                    print(f"{term_url} ({romaji}, {year}, {id}) airs on Ramadan.")
                    total += 1
            except Exception as e:
                print(f"{term_url} ({romaji}, {year}, {id}) error: {e}")
            sleep(1)
        sleep(1)
    print(f"Total: {total} from {init_info['total']} anime")


if __name__ == "__main__":
    main()
