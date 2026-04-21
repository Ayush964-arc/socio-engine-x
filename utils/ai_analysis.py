import os
try:
    import google.generativeai as genai
except:
    import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def analyze_channel(channel_data):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "❌ Gemini API key not found. Please check your .env file."

    genai.configure(api_key=api_key)

    # Try every available model until one works
    models_to_try = [
    "models/gemini-3-flash-preview",
    "models/gemini-3-pro-preview",
    "models/gemini-3.1-flash-lite-preview",
    "models/gemini-3.1-pro-preview",
]

    recent = channel_data.get("recent_videos", [])
    video_summary = ""
    for i, v in enumerate(recent[:5], 1):
        video_summary += f"\n  Video {i}: {v['title']} | Views: {v['views']:,} | Likes: {v['likes']:,} | Comments: {v['comments']:,}"

    prompt = f"""
You are a professional YouTube growth strategist.
Analyze this YouTube channel and give a detailed report.

CHANNEL: {channel_data['name']}
Subscribers: {channel_data['subscribers']:,}
Total Views: {channel_data['total_views']:,}
Videos: {channel_data['video_count']}
Avg Views/Video: {channel_data['avg_views']:,}
Likes (last 10): {channel_data['total_likes']:,}
Comments (last 10): {channel_data['total_comments']:,}
Engagement Rate: {channel_data['engagement_rate']}%
Country: {channel_data['country']}
Created: {channel_data['created_at']}

RECENT VIDEOS: {video_summary}

Provide:
1. GROWTH SCORE: X/10 with explanation
2. CHANNEL HEALTH: Overall summary paragraph
3. TOP 3 PRO TIPS: Specific actionable growth tips
4. CONTENT STRATEGY: Best content type and posting frequency
5. BIGGEST STRENGTH: What this channel does well
6. BIGGEST WEAKNESS: Main area holding channel back
"""

    last_error = ""
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            last_error = str(e)
            continue

    # If all Gemini models fail, use fallback rule-based analysis
    return generate_fallback_analysis(channel_data)


def generate_fallback_analysis(data):
    subs = data['subscribers']
    eng  = data['engagement_rate']
    avg  = data['avg_views']

    if subs > 1_000_000:
        tier = "Major Creator"
        score = 8
    elif subs > 100_000:
        tier = "Mid-tier Creator"
        score = 6
    elif subs > 10_000:
        tier = "Growing Creator"
        score = 5
    else:
        tier = "Emerging Creator"
        score = 4

    if eng > 5:
        eng_note = "Excellent engagement — your audience is highly active."
    elif eng > 2:
        eng_note = "Good engagement — above YouTube average of 2%."
    else:
        eng_note = "Engagement needs improvement — focus on call-to-actions."

    tips = []
    if avg < 10000:
        tips.append("📌 Improve thumbnail and title CTR — aim for 5-10% click-through rate")
    if eng < 3:
        tips.append("📌 Add strong call-to-actions asking viewers to like and comment")
    if data['video_count'] < 50:
        tips.append("📌 Post consistently — minimum 2 videos per week to grow faster")
    if not tips:
        tips = [
            "📌 Collaborate with similar-sized channels for cross-promotion",
            "📌 Use YouTube Shorts to boost channel visibility",
            "📌 Optimize video descriptions with relevant keywords"
        ]

    return f"""
1. GROWTH SCORE: {score}/10
   Channel classified as: {tier}

2. CHANNEL HEALTH:
   This channel has {data['subscribers']:,} subscribers with {data['total_views']:,} total views.
   {eng_note} Average views per video stand at {avg:,} which is
   {'strong' if avg > 50000 else 'growing' if avg > 10000 else 'needs improvement'}.

3. TOP 3 PRO TIPS:
   {tips[0] if len(tips) > 0 else ''}
   {tips[1] if len(tips) > 1 else ''}
   {tips[2] if len(tips) > 2 else ''}

4. CONTENT STRATEGY:
   Based on current performance, posting 3-4 times per week is recommended.
   Focus on trending topics in your niche with strong thumbnails and SEO-optimized titles.

5. BIGGEST STRENGTH:
   {'Strong subscriber base showing established audience trust.' if subs > 100000 else 'Growing community with loyal early audience.'}

6. BIGGEST WEAKNESS:
   {'Engagement rate needs improvement to match subscriber count.' if eng < 3 else 'Average views per video could be improved with better SEO and thumbnails.' if avg < subs * 0.1 else 'Consistency in upload schedule will drive further growth.'}
"""
