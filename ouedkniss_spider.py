import scrapy
import json
import time
import random


class OuedknissSpider(scrapy.Spider):
    name = "ouedkniss"
    allowed_domains = ["api.ouedkniss.com"]
    start_urls = ["https://api.ouedkniss.com/graphql"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_page = 1
        self.max_pages = 5  # Limit to prevent excessive scraping

    def start_requests(self):
        yield self.create_request(self.current_page)

    def create_request(self, page):
        # GraphQL request payload
        query_payload = {
            "operationName": "SearchQuery",
            "variables": {
                "mediaSize": "MEDIUM",
                "q": None,
                "filter": {
                    "categorySlug": "automobiles_vehicules",
                    "origin": None,
                    "connected": False,
                    "delivery": None,
                    "regionIds": [],
                    "cityIds": [],
                    "priceRange": [None, None],
                    "exchange": False,
                    "hasPictures": False,
                    "hasPrice": False,
                    "priceUnit": None,
                    "fields": [],
                    "page": page,
                    "count": 48
                }
            },
            "query": """query SearchQuery($q: String, $filter: SearchFilterInput, $mediaSize: MediaSize = MEDIUM) {
  search(q: $q, filter: $filter) {
    announcements {
      data {
        ...AnnouncementContent
        smallDescription {
          valueText
          __typename
        }
        noAdsense
        __typename
      }
      paginatorInfo {
        lastPage
        hasMorePages
        __typename
      }
      __typename
    }
    active {
      category {
        id
        name
        slug
        icon
        delivery
        deliveryType
        priceUnits
        children {
          id
          name
          slug
          icon
          __typename
        }
        specifications {
          isRequired
          specification {
            id
            codename
            label
            type
            class
            datasets {
              codename
              label
              __typename
            }
            dependsOn {
              id
              codename
              __typename
            }
            subSpecifications {
              id
              codename
              label
              type
              __typename
            }
            allSubSpecificationCodenames
            __typename
          }
          __typename
        }
        parentTree {
          id
          name
          slug
          icon
          children {
            id
            name
            slug
            icon
            __typename
          }
          __typename
        }
        parent {
          id
          name
          icon
          slug
          __typename
        }
        __typename
      }
      count
      filter {
        cities {
          id
          name
          __typename
        }
        regions {
          id
          name
          __typename
        }
        __typename
      }
      __typename
    }
    suggested {
      category {
        id
        name
        slug
        icon
        __typename
      }
      count
      __typename
    }
    __typename
  }
}

fragment AnnouncementContent on Announcement {
  id
  title
  slug
  createdAt: refreshedAt
  isFromStore
  isCommentEnabled
  userReaction {
    isBookmarked
    isLiked
    __typename
  }
  hasDelivery
  deliveryType
  likeCount
  description
  status
  cities {
    id
    name
    slug
    region {
      id
      name
      slug
      __typename
    }
    __typename
  }
  store {
    id
    name
    slug
    imageUrl
    isOfficial
    isVerified
    __typename
  }
  user {
    id
    __typename
  }
  defaultMedia(size: $mediaSize) {
    mediaUrl
    mimeType
    thumbnail
    __typename
  }
  price
  pricePreview
  priceUnit
  oldPrice
  oldPricePreview
  priceType
  exchangeType
  category {
    id
    slug
    __typename
  }
  __typename
}"""
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36",
        }

        # Add random delay between 1-3 seconds
        time.sleep(random.uniform(1, 3))

        return scrapy.Request(
            url=self.start_urls[0],
            method="POST",
            body=json.dumps(query_payload),
            callback=self.parse_results,
            headers=headers,
            meta={'page': page}
        )

    def parse_results(self, response):
        # Extract the current page from meta
        current_page = response.meta['page']

        try:
            data = json.loads(response.text)
            search_data = data.get("data", {}).get("search", {})

            # Extract pagination info
            paginator_info = search_data.get("announcements", {}).get("paginatorInfo", {})
            last_page = paginator_info.get("lastPage", 1)
            has_more_pages = paginator_info.get("hasMorePages", False)

            # Parse announcements
            announcements = search_data.get("announcements", {}).get("data", [])

            for announcement in announcements:
                yield {
                    "id": announcement.get("id"),
                    "title": announcement.get("title"),
                    "description": announcement.get("description"),
                    "price": announcement.get("price"),
                    "cities": [
                        {
                            "id": city.get("id") if city else None,
                            "name": city.get("name") if city else None,
                            "region": city.get("region", {}).get("name") if city and city.get("region") else None
                        } for city in announcement.get("cities", []) or []
                    ],
                    "store": {
                        "id": (announcement.get("store") or {}).get("id"),
                        "name": (announcement.get("store") or {}).get("name"),
                        "slug": (announcement.get("store") or {}).get("slug")
                    },
                    "default_media": (announcement.get("defaultMedia") or {}).get("mediaUrl"),
                    "created_at": announcement.get("createdAt"),
                    "price_preview": announcement.get("pricePreview"),
                    "price_unit": announcement.get("priceUnit"),
                    "page": current_page
                }

            # Pagination logic
            self.logger.info(f"Scraped page {current_page} of {last_page}")

            # Continue to next page if conditions are met
            if (has_more_pages and
                    current_page < self.max_pages and
                    current_page < last_page):
                next_page = current_page + 1
                yield self.create_request(next_page)

        except Exception as e:
            self.logger.error(f"Error parsing page {current_page}: {e}")
            self.logger.error(f"Response text: {response.text}")