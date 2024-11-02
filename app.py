from flask import Flask, request, jsonify, render_template, send_file, Response
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import logging
from cerebras.cloud.sdk import Cerebras
import os
from fpdf import FPDF
import tempfile
from pydub import AudioSegment
import time
import io
from dotenv import load_dotenv
from gtts import gTTS

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# API Configuration
CEREBRAS_API_KEY = os.getenv('CEREBRAS_API_KEY')
HUGGINGFACE_API_TOKEN = os.getenv('HUGGINGFACE_API_TOKEN')

if not CEREBRAS_API_KEY or not HUGGINGFACE_API_TOKEN:
    logger.error("Missing required API keys in environment variables")
    raise ValueError("Missing required API keys")

os.environ["CEREBRAS_API_KEY"] = CEREBRAS_API_KEY

def scrape_content(topic, num_results=3, max_chars=1500):
    search_url = f"https://www.google.com/search?q={quote_plus(topic)}&num={num_results}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        search_results = soup.find_all('div', class_='yuRUbf')
        
        content = ""
        for result in search_results:
            if len(content) >= max_chars:
                break
                
            url = result.find('a')['href']
            try:
                page_response = requests.get(url, headers=headers, timeout=5)
                page_response.raise_for_status()
                page_soup = BeautifulSoup(page_response.text, 'html.parser')
                
                paragraphs = page_soup.find_all('p')
                for p in paragraphs:
                    text = p.get_text().strip()
                    if len(text) > 50:  # Only add substantial paragraphs
                        content += text + " "
                        if len(content) >= max_chars:
                            break
                        
            except requests.RequestException as e:
                logger.error(f"Error scraping {url}: {e}")
                continue
        
        return content[:max_chars]
    except requests.RequestException as e:
        logger.error(f"Error during scraping: {e}")
        return ""

def generate_podcast_script(content, topic):
    try:
        client = Cerebras()

        system_prompt = "You are a professional podcast script writer. Create a concise, engaging 3-minute podcast script without timestamps or stage directions."
        user_prompt = f"""Create a podcast script about the topic: {topic}.

        The script should be concise, engaging, and conversational. Use the following information to craft the podcast:

        {content}

        Include:
        - An engaging introduction
        - 2-3 key points related to the topic
        - A brief conclusion
        """
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama3.1-8b",
            max_tokens=800,
            temperature=0.7,
            top_p=1
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating script: {e}")
        return "Error generating script."

def create_pdf(script, topic):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('DejaVu', '', '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf', uni=True)
    pdf.set_font("DejaVu", size=12)
    pdf.cell(200, 10, txt=f"Podcast Script: {topic}", ln=1, align='C')
    
    # Split the script into lines and add them to the PDF
    lines = script.split('\n')
    for line in lines:
        pdf.multi_cell(0, 10, txt=line)
    
    return pdf.output(dest='S').encode('latin-1', errors='ignore')

def text_to_speech(script):
    tts = gTTS(text=script, lang='en', slow=False)
    fp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
    
