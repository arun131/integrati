"""Google Search API wrapper for common tools."""

import os
import logging
from typing import List, Dict, Any, Optional
import httpx
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleSearchAPI:
    """Google Search API wrapper for web and local search operations."""

    def __init__(self):
        """Initialize Google Search API with credentials from environment."""
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID")
        self.google_places_api_key = os.getenv("GOOGLE_PLACES_API_KEY")

        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")

        if not self.google_cse_id:
            raise ValueError("GOOGLE_CSE_ID environment variable is required")

        if not self.google_places_api_key:
            raise ValueError("GOOGLE_PLACES_API_KEY environment variable is required")

        self.google_directions_api_key = os.getenv(
            "GOOGLE_DIRECTIONS_API_KEY", self.google_api_key
        )

        self.custom_search_service = None

    def _get_custom_search_service(self):
        """Get or create Google Custom Search service instance."""
        if self.custom_search_service is None:
            try:
                self.custom_search_service = build(
                    "customsearch", "v1", developerKey=self.google_api_key
                )
            except Exception as e:
                logger.error(f"Failed to create Google Custom Search service: {e}")
                raise
        return self.custom_search_service

    async def web_search(
        self, query: str, num_results: int = 10, location: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Perform web search using Google Custom Search API.

        Args:
            query: The search query
            num_results: Number of results to return (max 10)
            location: Optional location to refine search results

        Returns:
            List of dictionaries with title, url, snippet
        """
        try:
            service = self._get_custom_search_service()

            # Build search query with simple location handling
            search_query = query
            if location:
                # Simply combine query with location using "in"
                clean_location = location.strip()
                search_query = f"{query} in {clean_location}"
                logger.info(f"Search query with location: {search_query}")

            # Build search parameters
            search_params = {
                "q": search_query,
                "cx": self.google_cse_id,
                "num": min(num_results, 10),  # Google API limit is 10
            }

            # Add country restriction if location is provided
            if location:
                # Map common locations to country codes for better results
                country_mapping = {
                    "united states": "countryUS",
                    "usa": "countryUS",
                    "us": "countryUS",
                    "canada": "countryCA",
                    "united kingdom": "countryGB",
                    "uk": "countryGB",
                    "australia": "countryAU",
                    "germany": "countryDE",
                    "france": "countryFR",
                    "japan": "countryJP",
                    "china": "countryCN",
                    "india": "countryIN",
                    "brazil": "countryBR",
                    "mexico": "countryMX",
                }

                location_lower = location.lower()
                for country_key, country_code in country_mapping.items():
                    if country_key in location_lower:
                        search_params["cr"] = country_code
                        logger.info(f"Added country restriction: {country_code}")
                        break

            # Execute search
            result = service.cse().list(**search_params).execute()

            items = result.get("items", [])

            # Format results
            formatted_results = []
            for item in items:
                formatted_results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "display_link": item.get("displayLink", ""),
                        "formatted_url": item.get("formattedUrl", ""),
                    }
                )

            logger.info(
                f"Web search completed: {len(formatted_results)} results for query '{query}'"
            )
            return formatted_results

        except HttpError as e:
            logger.error(f"Google Custom Search API error: {e}")
            raise Exception(f"Google Search API error: {e}")
        except Exception as e:
            logger.error(f"Error performing web search: {e}")
            raise Exception(f"Web search failed: {str(e)}")

    async def local_search(
        self, query: str, location: Optional[str] = None, num_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Perform local business search using Google Places API.

        Args:
            query: Search query (e.g., "home services near me")
            location: Optional location override
            num_results: Number of results to return

        Returns:
            List with name, rating, price, reviews, address, etc.
        """
        try:
            # Build Places API URL
            base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"

            # Build search query with simple location handling
            search_query = query
            if location:
                # Simply combine query with location using "in"
                clean_location = location.strip()
                search_query = f"{query} in {clean_location}"
                logger.info(f"Local search query with location: {search_query}")

            params = {
                "query": search_query,
                "key": self.google_places_api_key,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(base_url, params=params)
                response.raise_for_status()

                data = response.json()

                if data.get("status") != "OK":
                    logger.warning(f"Places API returned status: {data.get('status')}")
                    return []

                results = data.get("results", [])[:num_results]

                # Format results
                formatted_results = []
                for place in results:
                    formatted_result = {
                        "name": place.get("name", ""),
                        "address": place.get("formatted_address", ""),
                        "rating": place.get("rating"),
                        "price_level": place.get("price_level"),
                        "user_ratings_total": place.get("user_ratings_total"),
                        "business_status": place.get("business_status"),
                        "types": place.get("types", []),
                        "location": {
                            "lat": place.get("geometry", {})
                            .get("location", {})
                            .get("lat"),
                            "lng": place.get("geometry", {})
                            .get("location", {})
                            .get("lng"),
                        },
                        "place_id": place.get("place_id"),
                        "photos": [],
                    }

                    # Add photo references if available
                    if "photos" in place:
                        for photo in place["photos"][:3]:  # Limit to 3 photos
                            formatted_result["photos"].append(
                                {
                                    "photo_reference": photo.get("photo_reference"),
                                    "width": photo.get("width"),
                                    "height": photo.get("height"),
                                }
                            )

                    formatted_results.append(formatted_result)

                logger.info(
                    f"Local search completed: {len(formatted_results)} results for query '{query}'"
                )
                return formatted_results

        except httpx.TimeoutException:
            logger.error("Places API request timed out")
            raise Exception("Local search request timed out")
        except httpx.HTTPStatusError as e:
            logger.error(f"Places API HTTP error: {e}")
            raise Exception(f"Places API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error performing local search: {e}")
            raise Exception(f"Local search failed: {str(e)}")

    async def get_directions(
        self, start_location: str, end_location: str, mode: str = "driving"
    ) -> Dict[str, Any]:
        """Get directions using Google Directions API.

        Args:
            start_location: Starting location (address or coordinates)
            end_location: Destination location (address or coordinates)
            mode: Travel mode (driving, walking, bicycling, transit)

        Returns:
            Directions data including routes, legs, steps
        """
        try:
            base_url = "https://maps.googleapis.com/maps/api/directions/json"

            params = {
                "origin": start_location,
                "destination": end_location,
                "mode": mode,
                "key": self.google_directions_api_key,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(base_url, params=params)
                response.raise_for_status()

                data = response.json()

                if data.get("status") != "OK":
                    logger.warning(
                        f"Directions API returned status: {data.get('status')}"
                    )
                    return {"status": data.get("status"), "routes": []}

                logger.info(
                    f"Directions retrieved from '{start_location}' to '{end_location}' via {mode}"
                )
                return data

        except httpx.TimeoutException:
            logger.error("Directions API request timed out")
            raise Exception("Directions request timed out")
        except httpx.HTTPStatusError as e:
            logger.error(f"Directions API HTTP error: {e}")
            raise Exception(f"Directions API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error getting directions: {e}")
            raise Exception(f"Directions request failed: {str(e)}")
