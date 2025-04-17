import streamlit as st
from pytube import YouTube
from pathlib import Path
import shutil
import whisper
import os
import openai
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")  # Ensure the API key is set in .env

# Sanitize filename by removing special characters
def sanitize_filename(title):
    return re.sub(r'[\\/*?:"<>|]', "", title).strip().replace(" ", "_")

# Load whisper model
@st.cache_resource
def load_model():
    model = whisper.load_model("base")
    return model

# Save video
def save_video(url, video_filename):
    try:
        youtubeObject = YouTube(url)
        youtubeObject = youtubeObject.streams.get_highest_resolution()
        youtubeObject.download(filename=video_filename)
        print("Video Download successful")
    except Exception as e:
        print(f"An error occurred while downloading the video: {e}")
    return video_filename

# Clean YouTube URL to get video ID
def clean_youtube_url(url):
    match = re.match(r'(https?://(?:www\.)?youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(2)
    return None

# Save audio from YouTube video
def save_audio(url):
    video_id = clean_youtube_url(url)
    if not video_id:
        raise ValueError("Invalid YouTube URL")
    
    try:
        yt = YouTube(f'https://www.youtube.com/watch?v={video_id}')
        video = yt.streams.filter(only_audio=True).first()
        out_file = video.download()

        base, ext = os.path.splitext(out_file)
        file_name = base + '.mp3'

        try:
            os.rename(out_file, file_name)
        except WindowsError:
            os.remove(file_name)
            os.remove(out_file)

        audio_filename = sanitize_filename(Path(file_name).stem) + '.mp3'
        video_filename = save_video(url, sanitize_filename(Path(file_name).stem) + '.mp4')

        print(f"{yt.title} has been successfully downloaded")
        return yt.title, audio_filename, video_filename
    except Exception as e:
        print(f"Error during audio download: {e}")
        return None, None, None

# Transcribe audio to text
def audio_to_transcription(audio_file):
    try:
        model = load_model()
        result = model.transcribe(audio_file)
        transcript = result['text']
        return transcript
    except Exception as e:
        print(f"Error during transcription: {e}")
        return "Error during transcription."

# Generate recipe from text
def text_to_recipe(text):
    try:
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt="Write the food recipe from the below text:\n" + text,
            temperature=0.7,
            max_tokens=600,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        return response['choices'][0]['text']
    except Exception as e:
        print(f"Error during recipe generation: {e}")
        return "Error generating recipe."

# Streamlit UI setup
st.set_page_config(layout='wide')
st.subheader("Recipe Generator")

# Input field for YouTube video URL
url = st.text_input("Enter YouTube video URL for cooking")

# When the button is clicked
if url:
    if st.button("Generate Recipe"):
        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            st.info("Video uploaded successfully")
            video_title, audio_filename, video_filename = save_audio(url)
            if video_filename:
                st.video(video_filename)
            else:
                st.error("Failed to download video or audio.")

        with col2:
            if audio_filename:
                st.info("Transcript is below")
                transcript_result = audio_to_transcription(audio_filename)
                st.success(transcript_result)
            else:
                st.error("Audio file is missing or failed to download.")

        with col3:
            if audio_filename:
                st.info("Recipe is below")
                recipe_result = text_to_recipe(transcript_result)
                st.success(recipe_result)
            else:
                st.error("Audio file is missing, recipe cannot be generated.")

