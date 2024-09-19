from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
import re

app = FastAPI()

class TranscriptRequest(BaseModel):
    url: str
    language: str = "en"
    format: str = "paragraph"

def extract_video_id(url: str) -> str:
    youtube_regex = r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})'
    match = re.search(youtube_regex, url)
    return match.group(1) if match else None

def combine_transcript(transcript: list) -> str:
    return ' '.join(segment['text'] for segment in transcript)

@app.post("/api/transcript")
async def get_transcript(request: TranscriptRequest):
    video_id = extract_video_id(request.url)
    
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[request.language])
        
        if request.format == 'paragraph':
            transcript_text = combine_transcript(transcript)
            return {"transcript": transcript_text}
        else:
            return {"transcript": transcript}
    
    except Exception as e:
        if "TranscriptsDisabled" in str(e):
            raise HTTPException(status_code=404, detail="Transcripts are disabled for this video")
        elif "NoTranscriptFound" in str(e):
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                available_languages = [
                    {"language_code": t.language_code, "language": t.language} 
                    for t in transcript_list
                ]
                raise HTTPException(status_code=404, detail={
                    "error": f"No transcript found for language code '{request.language}'",
                    "available_languages": available_languages
                })
            except Exception as inner_e:
                raise HTTPException(status_code=500, detail=str(inner_e))
        else:
            raise HTTPException(status_code=500, detail=str(e))

# # This is for local testing
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)