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

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# API Configuration
CEREBRAS_API_KEY = os.getenv('CEREBRAS_API_KEY', 'csk-mckj2jpdthdv9cypr5yk6r58j2ywxncvtdv43w8wftj6k8vk')
HUGGINGFACE_API_TOKEN = os.getenv('HUGGINGFACE_API_TOKEN', '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')

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
    API_URL = "https://api-inference.huggingface.co/models/espnet/kan-bayashi_ljspeech_vits"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}
    
    max_chunk_length = 500
    chunks = [script[i:i+max_chunk_length] for i in range(0, len(script), max_chunk_length)]
    
    combined_audio = AudioSegment.empty()
    for chunk_index, chunk in enumerate(chunks):
        payload = {"inputs": chunk}
        for attempt in range(10):  # Allow for more retries
            try:
                logger.info(f"Processing chunk {chunk_index + 1}/{len(chunks)} (attempt {attempt + 1}/10)")
                response = requests.post(API_URL, headers=headers, json=payload, timeout=60)  # Adding timeout per request
                response.raise_for_status()

                audio_bytes = response.content
                content_type = response.headers.get('Content-Type', '')

                audio_segment = None
                if 'audio/flac' in content_type:
                    audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="flac")
                elif 'audio/wav' in content_type:
                    audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="wav")
                else:
                    audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))

                combined_audio += audio_segment
                break
            except requests.Timeout:
                logger.warning(f"Timeout occurred for chunk {chunk_index + 1}. Retrying in 15 seconds...")
                time.sleep(15)  # Increase wait time for retry
            except requests.RequestException as e:
                if attempt < 9:
                    logger.info(f"Error with chunk {chunk_index + 1}, attempt {attempt + 1}. Retrying in 10 seconds...")
                    time.sleep(10)
                else:
                    raise Exception(f"Model loading timeout or other error: {e}")
            except Exception as e:
                logger.error(f"Error processing TTS for chunk {chunk_index + 1}: {e}")
                raise
    
    if combined_audio.duration_seconds > 0:
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3').name
        combined_audio.export(output_file, format="mp3")
        return output_file
    else:
        raise Exception("No audio was generated.")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_podcast', methods=['POST'])
def generate_podcast():
    try:
        data = request.get_json()
        topic = data.get('topic')

        if not topic:
            return jsonify({'error': 'No topic provided'}), 400

        scraped_content = scrape_content(topic)
        if not scraped_content:
            return jsonify({'error': 'No content found for the topic'}), 404

        podcast_script = generate_podcast_script(scraped_content, topic)
        return jsonify({'script': podcast_script})
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    try:
        data = request.get_json()
        script = data.get('script')
        topic = data.get('topic')

        if not script or not topic:
            return jsonify({'error': 'Script or topic not provided'}), 400
        
        pdf = create_pdf(script, topic)
        return Response(
            pdf,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename={topic.replace(" ", "_")}_podcast_script.pdf'}
        )
    except Exception as e:
        logger.error(f"Error in download_pdf: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate_audio', methods=['POST'])
def generate_audio():
    try:
        data = request.get_json()
        script = data.get('script')
        if not script:
            return jsonify({'error': 'Script not provided'}), 400
        
        audio_file = text_to_speech(script)
        return send_file(
            audio_file,
            mimetype='audio/mp3',
            as_attachment=True,
            download_name='podcast_audio.mp3'
        )
    except Exception as e:
        logger.error(f"Error in generate_audio: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
