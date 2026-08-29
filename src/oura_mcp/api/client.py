"""Oura API client."""

import asyncio
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx

from .auth import OuraAuth, OuraAuthError as _OuraAuthErrorOAuth
from ..utils.config import OuraAPIConfig
from ..utils.logging import get_logger


logger = get_logger(__name__)


class OuraAPIError(Exception):
    """Base exception for Oura API errors."""
    pass


class OuraAuthError(OuraAPIError):
    """Authentication error."""
    pass


class OuraRateLimitError(OuraAPIError):
    """Rate limit exceeded."""
    pass


class OuraClient:
    """
    Async client for Oura Ring API v2.
    
    Handles authentication, rate limiting, and data retrieval.
    """
    
    def __init__(self, config: OuraAPIConfig, auth: Optional[OuraAuth] = None):
        """
        Initialize Oura API client.
        
        Args:
            config: API configuration
        """
        self.config = config
        self.base_url = config.base_url
        self._client: Optional[httpx.AsyncClient] = None

        # OAuth2 (2026-08-29). The auth object owns the token lifecycle; the client
        # only asks it for headers. Injectable so tests can supply a fake.
        self.auth = auth or OuraAuth(
            client_id=getattr(config, "client_id", None),
            client_secret=getattr(config, "client_secret", None),
            redirect_uri=getattr(config, "redirect_uri", None),
        )
        if getattr(config, "access_token", None) and not self.auth.access_token:
            self.auth.access_token = config.access_token
        if getattr(config, "refresh_token", None) and not self.auth.refresh_token:
            self.auth.refresh_token = config.refresh_token
        
        # Rate limiting state
        self._request_times: List[float] = []
        self._daily_requests = 0
        self._daily_reset_time = datetime.now().date()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self._client is None:
            # No Authorization header here on purpose: with OAuth2 the token can be
            # rotated while the client lives, so it is attached per request instead
            # of being baked into the session at construction time.
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout_seconds,
                headers={"Content-Type": "application/json"},
            )
    
    async def close(self):
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    async def _rate_limit(self):
        """Apply rate limiting."""
        now = asyncio.get_event_loop().time()
        
        # Reset daily counter if needed
        today = datetime.now().date()
        if today > self._daily_reset_time:
            self._daily_requests = 0
            self._daily_reset_time = today
        
        # Check daily limit
        if self._daily_requests >= self.config.rate_limit.requests_per_day:
            raise OuraRateLimitError("Daily request limit exceeded")
        
        # Check per-minute limit
        minute_ago = now - 60
        self._request_times = [t for t in self._request_times if t > minute_ago]
        
        if len(self._request_times) >= self.config.rate_limit.requests_per_minute:
            sleep_time = 60 - (now - self._request_times[0])
            logger.warning(f"Rate limit reached, sleeping {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)
        
        # Record this request
        self._request_times.append(now)
        self._daily_requests += 1
    
    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Oura API.
        
        Args:
            method: HTTP method
            path: API path (e.g., '/v2/usercollection/daily_sleep')
            params: Query parameters
            
        Returns:
            JSON response data
            
        Raises:
            OuraAuthError: Authentication failed
            OuraRateLimitError: Rate limit exceeded
            OuraAPIError: Other API errors
        """
        await self._ensure_client()
        await self._rate_limit()
        
        url = urljoin(self.base_url, path)
        
        try:
            await self.auth.ensure_valid_token()
            response = await self._client.request(
                method, url, params=params, headers=self.auth.get_headers()
            )

            # A 401 is the normal way an expired token announces itself: tokens loaded
            # from .env carry no expiry, so this — not the clock — is what drives the
            # refresh. Retried exactly once; a second 401 means the credentials are
            # dead, not stale, and only re-authorization helps.
            if response.status_code == 401:
                await self.auth.refresh_access_token()
                response = await self._client.request(
                    method, url, params=params, headers=self.auth.get_headers()
                )

            if response.status_code == 401:
                raise OuraAuthError(
                    "Invalid access token after refresh — re-authorize with "
                    "`python generate_tokens.py`"
                )
            elif response.status_code == 429:
                raise OuraRateLimitError("Rate limit exceeded")
            elif response.status_code >= 400:
                raise OuraAPIError(
                    f"API error {response.status_code}: {response.text}"
                )
            
            return response.json()
        
        except httpx.HTTPError as e:
            raise OuraAPIError(f"HTTP error: {e}")
    
    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET request wrapper."""
        return await self._request("GET", path, params)
    
    def _format_date(self, d: date) -> str:
        """Format date for API."""
        return d.isoformat()
    
    # === Daily Data Methods ===

    async def get_daily_sleep(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get daily sleep data (summary scores).

        Args:
            start_date: Start date (default: yesterday)
            end_date: End date (default: today)

        Returns:
            List of daily sleep records with scores
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=1)

        params = {
            "start_date": self._format_date(start_date),
            "end_date": self._format_date(end_date),
        }

        response = await self._get("/v2/usercollection/daily_sleep", params)
        return response.get("data", [])

    async def get_sleep(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get detailed sleep data (all sleep periods with durations).

        This endpoint returns ALL sleep periods, including naps and
        multi-period sleep (e.g., biphasic sleep).

        Args:
            start_date: Start date (default: yesterday)
            end_date: End date (default: today)

        Returns:
            List of sleep period records with actual durations in seconds
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=1)

        params = {
            "start_date": self._format_date(start_date),
            "end_date": self._format_date(end_date),
        }

        response = await self._get("/v2/usercollection/sleep", params)
        return response.get("data", [])
    
    async def get_daily_readiness(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get daily readiness data.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of daily readiness records
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=1)
        
        params = {
            "start_date": self._format_date(start_date),
            "end_date": self._format_date(end_date),
        }
        
        response = await self._get("/v2/usercollection/daily_readiness", params)
        return response.get("data", [])
    
    async def get_daily_activity(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get daily activity data.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of daily activity records
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=1)
        
        params = {
            "start_date": self._format_date(start_date),
            "end_date": self._format_date(end_date),
        }
        
        response = await self._get("/v2/usercollection/daily_activity", params)
        return response.get("data", [])
    
    async def get_heart_rate(
        self,
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get heart rate data.
        
        Args:
            start_datetime: Start datetime
            end_datetime: End datetime
            
        Returns:
            List of heart rate records
        """
        if end_datetime is None:
            end_datetime = datetime.now()
        if start_datetime is None:
            start_datetime = end_datetime - timedelta(hours=24)
        
        params = {
            "start_datetime": start_datetime.isoformat(),
            "end_datetime": end_datetime.isoformat(),
        }
        
        response = await self._get("/v2/usercollection/heartrate", params)
        return response.get("data", [])
    
    async def get_personal_info(self) -> Dict[str, Any]:
        """
        Get personal info.
        
        Returns:
            Personal information (age, weight, height, sex)
        """
        response = await self._get("/v2/usercollection/personal_info")
        return response
    
    async def get_sessions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get Oura "sessions" — guided breathing, meditation and relaxation moments.

        ⚠️ These are NOT workouts. Oura keeps sport in a separate collection; use
        :meth:`get_workouts` for that. The docstring here used to say
        "workout/activity sessions", which is how get_workout_sessions ended up
        querying this endpoint and silently returning an empty list forever.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of session records
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=7)
        
        params = {
            "start_date": self._format_date(start_date),
            "end_date": self._format_date(end_date),
        }
        
        response = await self._get("/v2/usercollection/session", params)
        return response.get("data", [])

    async def get_workouts(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get workouts — sport activity with calories, distance and intensity.

        Separate collection from :meth:`get_sessions`; confusing the two is why
        workout data was missing until 2026-08-29.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of workout records
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=7)

        params = {
            "start_date": self._format_date(start_date),
            "end_date": self._format_date(end_date),
        }

        response = await self._get("/v2/usercollection/workout", params)
        return response.get("data", [])

    async def get_ring_battery_level(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get the ring's battery level history (present in openapi 1.37)."""
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=7)

        params = {
            "start_date": self._format_date(start_date),
            "end_date": self._format_date(end_date),
        }

        response = await self._get("/v2/usercollection/ring_battery_level", params)
        return response.get("data", [])

    async def get_daily_stress(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get daily stress data.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of daily stress records with stress load, recovery time, etc.
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=1)

        params = {
            "start_date": self._format_date(start_date),
            "end_date": self._format_date(end_date),
        }

        response = await self._get("/v2/usercollection/daily_stress", params)
        return response.get("data", [])

    async def get_daily_spo2(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get daily SpO2 (blood oxygen saturation) data.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of daily SpO2 records with average percentage
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=1)

        params = {
            "start_date": self._format_date(start_date),
            "end_date": self._format_date(end_date),
        }

        response = await self._get("/v2/usercollection/daily_spo2", params)
        return response.get("data", [])

    async def get_vo2_max(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get VO2 Max (cardiorespiratory fitness) data.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of VO2 Max estimates
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        params = {
            "start_date": self._format_date(start_date),
            "end_date": self._format_date(end_date),
        }

        # ⛔ The path really is "vO2_max" with a capital O — openapi 1.37 spells it
        # that way and the lowercase variant returns 404. Verified live 2026-08-29.
        response = await self._get("/v2/usercollection/vO2_max", params)
        return response.get("data", [])

    async def get_tags(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user-created tags.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of tags with timestamps and comments
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=7)

        params = {
            "start_date": self._format_date(start_date),
            "end_date": self._format_date(end_date),
        }

        response = await self._get("/v2/usercollection/tag", params)
        return response.get("data", [])

    async def get_daily_resilience(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get daily resilience data.

        Resilience reflects long-term stress-recovery balance, derived from
        sleep recovery, daytime recovery, and stress load.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of daily resilience records with level and contributors
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=7)

        params = {
            "start_date": self._format_date(start_date),
            "end_date": self._format_date(end_date),
        }

        response = await self._get("/v2/usercollection/daily_resilience", params)
        return response.get("data", [])

    async def get_daily_cardiovascular_age(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get daily cardiovascular age estimates.

        Estimates vascular age relative to chronological age based on
        cardiovascular metrics.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of daily cardiovascular age records
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        params = {
            "start_date": self._format_date(start_date),
            "end_date": self._format_date(end_date),
        }

        response = await self._get("/v2/usercollection/daily_cardiovascular_age", params)
        return response.get("data", [])

    async def get_sleep_time(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get sleep time recommendations.

        Returns Oura's optimal bedtime window and a recommendation/status
        per day (e.g. improve_efficiency / earlier_bedtime).

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of sleep time recommendation records
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=7)

        params = {
            "start_date": self._format_date(start_date),
            "end_date": self._format_date(end_date),
        }

        response = await self._get("/v2/usercollection/sleep_time", params)
        return response.get("data", [])

    async def get_rest_mode_periods(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get rest mode periods.

        Rest Mode is a user-activated recovery mode; each period spans one or
        more days with associated episodes.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of rest mode period records
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        params = {
            "start_date": self._format_date(start_date),
            "end_date": self._format_date(end_date),
        }

        response = await self._get("/v2/usercollection/rest_mode_period", params)
        return response.get("data", [])

    async def get_enhanced_tags(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get enhanced tags.

        Enhanced tags support named tags with start/end times and comments
        (a richer successor to the classic tag endpoint).

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of enhanced tag records
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=7)

        params = {
            "start_date": self._format_date(start_date),
            "end_date": self._format_date(end_date),
        }

        response = await self._get("/v2/usercollection/enhanced_tag", params)
        return response.get("data", [])

    async def get_ring_configuration(self) -> List[Dict[str, Any]]:
        """
        Get ring configuration(s).

        Hardware details of the user's ring(s): color, design, firmware,
        hardware generation and size. This endpoint is not date-filtered.

        Returns:
            List of ring configuration records
        """
        response = await self._get("/v2/usercollection/ring_configuration")
        return response.get("data", [])
