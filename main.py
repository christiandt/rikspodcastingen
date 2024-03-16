from datetime import datetime

import requests
import rfeed


class Podcast:
    def __init__(self, podcast_name="loerdagsraadet", max_episodes=50, page_size=20, sort='desc', paginate=True):
        if int(max_episodes) > int(page_size) and not paginate:
            raise ValueError('when max_episodes is larger than page_size, pagination needs to be enabled')
        self.api_host = "https://psapi.nrk.no"
        self.podcast_name = podcast_name
        self.podcast_title = Podcast._convert_name_to_title(podcast_name)
        self.episodes = self._fetch_episodes(max_episodes=max_episodes, page_size=page_size, sort=sort, paginate=paginate)
        self._add_mp3_url()

    @staticmethod
    def _convert_name_to_title(name):
        return name.replace("_", " ").replace('ae', 'æ').replace('oe', 'ø').replace('aa', 'å').capitalize()

    def _fetch_episodes(self, max_episodes, page_size, sort, paginate):
        eps = []
        res = requests.get(f"{self.api_host}/radio/catalog/podcast/{self.podcast_name}/episodes?page=1&pageSize={page_size}&sort={sort}")
        eps.extend(res.json().get('_embedded').get('episodes'))
        fetched = 0
        if paginate:
            while 'next' in res.json().get('_links'):
                res = requests.get(f"{self.api_host}/{res.json().get('_links').get('next').get('href')}")
                eps.extend(res.json().get('_embedded').get('episodes'))
                fetched += page_size
                if fetched >= max_episodes:
                    return eps[0:max_episodes]
        return eps

    def _add_mp3_url(self):
        print(f"fetching files for {self.podcast_name}")
        for eps in self.episodes:
            res = requests.get(f"{self.api_host}/playback/manifest/podcast/{eps.get('episodeId')}?eea-portability=true")
            file_url = res.json().get('playable').get('assets')[0].get('url')
            eps['mp3'] = file_url
            print(".", end='')
        print("")

    def get_episodes(self):
        return self.episodes

    def rss_feed(self):
        items = []
        for eps in self.episodes:
            items.append(rfeed.Item(
                title=eps.get('titles').get('title'),
                description=eps.get('titles').get('subtitle'),
                pubDate=datetime.fromisoformat(eps.get('date')),
                link=eps.get('mp3')
            ))
        return rfeed.Feed(title=self.podcast_title,
                          link=f"https://radio.nrk.no/podkast/{self.podcast_name}",
                          description=self.podcast_title,
                          items=items
                          ).rss()


podcasts = [
    "berrum_beyer_snakker_om_greier",
    "loerdagsraadet",
    "trygdekontoret",
    "abels_taarn"
]

for pod_name in podcasts:
    pod = Podcast(
        podcast_name=pod_name,
        max_episodes=100,
        page_size=20,
        paginate=True
    )
    with open(f"{pod_name}.rss", 'w') as feed_file:
        feed_file.write(pod.rss_feed())

