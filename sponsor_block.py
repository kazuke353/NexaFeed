import asyncio
import sponsorblock as sb
from sponsorblock.errors import BadRequest, ServerException, UnexpectedException, NotFoundException

class SponsorBlockManager:
    def __init__(self):
        self.client = sb.Client()

    async def get_sponsored_segments(self, video_id):
        loop = asyncio.get_event_loop()
        try:
            segments = await loop.run_in_executor(None, self.client.get_skip_segments, "https://www.youtube.com/watch?v=" + video_id)
            return segments
        except (BadRequest, ServerException, UnexpectedException, NotFoundException) as e:
            return []
