import os
import re
import requests
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

def get_youtube_client():
    api_key = os.getenv("YOUTUBE_API_KEY")
    return build("youtube", "v3", developerKey=api_key)

# ─────────────────────────────────────────
# EXTRACT CHANNEL ID FROM ANY URL OR NAME
# ─────────────────────────────────────────
def extract_channel_id(user_input):
    youtube = get_youtube_client()
    user_input = user_input.strip()

    # Direct channel ID
    if re.match(r'^UC[a-zA-Z0-9_-]{22}$', user_input):
        return user_input

    # URL patterns
    patterns = [
        r'youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})',
        r'youtube\.com/@([a-zA-Z0-9_\-\.]+)',
        r'youtube\.com/user/([a-zA-Z0-9_-]+)',
        r'youtube\.com/c/([a-zA-Z0-9_-]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, user_input)
        if match:
            identifier = match.group(1)

            # Already a channel ID
            if identifier.startswith("UC") and len(identifier) == 24:
                return identifier

            # Handle format (@username) — resolve to channel ID
            try:
                response = youtube.channels().list(
                    part="id",
                    forHandle=identifier
                ).execute()
                if response.get("items"):
                    return response["items"][0]["id"]
            except:
                pass

            # Try search as fallback
            try:
                response = youtube.search().list(
                    q=identifier,
                    type="channel",
                    part="id",
                    maxResults=1
                ).execute()
                if response.get("items"):
                    return response["items"][0]["id"]["channelId"]
            except:
                pass

    # Plain text name — search directly
    try:
        response = youtube.search().list(
            q=user_input,
            type="channel",
            part="id",
            maxResults=1
        ).execute()
        if response.get("items"):
            return response["items"][0]["id"]["channelId"]
    except:
        pass

    return None


# ─────────────────────────────────────────
# GET FULL CHANNEL STATS
# ─────────────────────────────────────────
def get_channel_stats(user_input):
    youtube = get_youtube_client()
    channel_id = extract_channel_id(user_input)

    if not channel_id:
        return None

    response = youtube.channels().list(
        part="snippet,statistics,contentDetails",
        id=channel_id
    ).execute()

    if not response.get("items"):
        return None

    channel      = response["items"][0]
    snippet      = channel["snippet"]
    stats        = channel["statistics"]
    content      = channel["contentDetails"]
    uploads_id   = content["relatedPlaylists"]["uploads"]

    subscribers  = int(stats.get("subscriberCount", 0))
    total_views  = int(stats.get("viewCount", 0))
    video_count  = int(stats.get("videoCount", 1))

    # Thumbnail — highest quality available
    thumbnails = snippet.get("thumbnails", {})
    thumbnail = ""
    for quality in ["maxres", "high", "medium", "default"]:
        t = thumbnails.get(quality, {})
        if t.get("url"):
            thumbnail = t["url"]
            break

    # Fetch recent 10 videos for engagement data
    recent_videos = get_recent_videos(youtube, uploads_id)

    total_likes    = sum(v["likes"]    for v in recent_videos)
    total_comments = sum(v["comments"] for v in recent_videos)
    total_v_views  = sum(v["views"]    for v in recent_videos)

    engagement_rate = 0.0
    if total_v_views > 0:
        engagement_rate = round(
            ((total_likes + total_comments) / total_v_views) * 100, 2
        )

    avg_views = total_views // max(video_count, 1)

    return {
        "channel_id":       channel_id,
        "name":             snippet["title"],
        "description":      snippet.get("description", "")[:300],
        "country":          snippet.get("country", "N/A"),
        "created_at":       snippet["publishedAt"][:10],
        "thumbnail":        thumbnail,
        "subscribers":      subscribers,
        "total_views":      total_views,
        "video_count":      video_count,
        "avg_views":        avg_views,
        "total_likes":      total_likes,
        "total_comments":   total_comments,
        "engagement_rate":  engagement_rate,
        "recent_videos":    recent_videos,
    }


# ─────────────────────────────────────────
# GET RECENT 10 VIDEOS WITH STATS
# ─────────────────────────────────────────
def get_recent_videos(youtube, uploads_playlist_id):
    videos = []

    # Get last 10 video IDs from uploads playlist
    playlist_response = youtube.playlistItems().list(
        part="contentDetails",
        playlistId=uploads_playlist_id,
        maxResults=10
    ).execute()

    video_ids = [
        item["contentDetails"]["videoId"]
        for item in playlist_response.get("items", [])
    ]

    if not video_ids:
        return []

    # Fetch stats for all video IDs in one API call
    video_response = youtube.videos().list(
        part="snippet,statistics",
        id=",".join(video_ids)
    ).execute()

    for item in video_response.get("items", []):
        s = item["statistics"]
        videos.append({
            "title":    item["snippet"]["title"][:40],
            "views":    int(s.get("viewCount",    0)),
            "likes":    int(s.get("likeCount",    0)),
            "comments": int(s.get("commentCount", 0)),
        })

    return videos