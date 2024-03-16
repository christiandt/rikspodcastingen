from datetime import datetime, timedelta

import requests
import rfeed


class Podcast:
    def __init__(self, podcast_name="loerdagsraadet", max_episodes=50, page_size=20, sort='desc', paginate=True):
        if int(max_episodes) > int(page_size) and not paginate:
            raise ValueError('when max_episodes is larger than page_size, pagination needs to be enabled')
        self.api_host = "https://psapi.nrk.no"
        self.podcast_name = podcast_name
        self.episodes = self._fetch_episodes(max_episodes=max_episodes, page_size=page_size, sort=sort, paginate=paginate)
        self._add_mp3_url_and_metadata()

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

    def _add_mp3_url_and_metadata(self):
        print(f"fetching files for {self.podcast_name}")

        for eps in self.episodes:
            manifest = requests.get(f"{self.api_host}/playback/manifest/podcast/{eps.get('episodeId')}?eea-portability=true")
            eps['mp3'] = manifest.json().get('playable').get('assets')[0].get('url')

            metadata = requests.get(f"{self.api_host}/playback/metadata/podcast/{eps.get('episodeId')}?eea-portability=true")
            eps['show_title'] = metadata.json().get('preplay').get('titles').get('title')
            eps['show_subtitle'] = metadata.json().get('preplay').get('titles').get('subtitle')
            eps['show_image'] = metadata.json().get('preplay').get('squarePoster').get('images')[-1].get('url')
            self.title = metadata.json().get('_embedded').get('podcast').get('titles').get('title')
            self.subtitle = metadata.json().get('_embedded').get('podcast').get('titles').get('subtitle')
            self.image = metadata.json().get('_embedded').get('podcast').get('imageUrl')
            print(".", end='')
        print("")

    def get_episodes(self):
        return self.episodes

    def rss_feed(self):
        items = []
        for eps in self.episodes:
            itunes_item = rfeed.iTunesItem(
                subtitle=eps.get('show_title'),
                summary=eps.get('show_subtitle'),
                duration=str(timedelta(seconds=eps.get('durationInSeconds'))),
                image=eps.get('show_image')
            )
            items.append(rfeed.Item(
                title=eps.get('titles').get('title'),
                description=eps.get('titles').get('subtitle'),
                pubDate=datetime.fromisoformat(eps.get('date')),
                link=eps.get('mp3'),
                enclosure=rfeed.Enclosure(url=eps.get('mp3'), length=eps.get('durationInSeconds'), type='audio/mpeg'),
                extensions=[itunes_item]
            ))
        itunes = rfeed.iTunes(
            subtitle=self.title,
            summary=self.subtitle,
            image=self.image
        )
        return rfeed.Feed(title=str(self.title),
                          link=f"https://radio.nrk.no/podkast/{self.podcast_name}",
                          description=self.subtitle,
                          items=items,
                          extensions=[itunes]
                          ).rss()


if __name__ == '__main__':
    podcasts = [
        "berrum_beyer_snakker_om_greier",
        "loerdagsraadet",
        "trygdekontoret",
        "abels_taarn"
    ]

    for pod_name in podcasts:
        pod = Podcast(
            podcast_name=pod_name,
            max_episodes=50,
            page_size=20,
            paginate=True
        )
        with open(f"{pod_name}.rss", 'w') as feed_file:
            feed_file.write(pod.rss_feed())

