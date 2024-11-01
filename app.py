from flask import Flask, request, jsonify, render_template, send_file, Response
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import logging
from cerebras.cloud.sdk import Cerebras
import os
from fpdf import FPDF
import io
import tempfile
from pydub import AudioSegment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Cerebras API configuration
os.environ["CEREBRAS_API_KEY"] = "csk-mckj2jpdthdv9cypr5yk6r58j2ywxncvtdv43w8wftj6k8vk"

# Hugging Face API configuration
HUGGINGFACE_API_TOKEN = "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"  # Replace with your actual Hugging Face API token

def scrape_content(topic, num_results=3, max_chars=1500):
    search_url = f"https://www.google.com/search?q={quote_plus(topic)}&num={num_results}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        search_results = soup.find_all('div', class_='yuRUbf')
        
        content = ""
        for result in search_results:
            if len(content) >= max_chars:
                break
                
            url = result.find('a')['href']
            try:
                page_response = requests.get(url, headers=headers, timeout=5)
                page_soup = BeautifulSoup(page_response.text, 'html.parser')
                
                paragraphs = page_soup.find_all('p')
                for p in paragraphs:
                    text = p.get_text().strip()
                    if len(text) > 50:  # Only add substantial paragraphs
                        content += text + " "
                        if len(content) >= max_chars:
                            break
                        
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                continue
        
        return content[:max_chars]
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        return ""

def generate_podcast_script(content, topic):
    try:
        client = Cerebras()

        system_prompt = "You are a professional podcast script writer. Create a concise, engaging 3-minute podcast script without timestamps or stage directions."
        user_prompt = f"""Topic: {topic}

Based on the following research, create a brief podcast script. Focus on the most interesting points and maintain a conversational tone.

Research: {content}

Format the script with:
1. An engaging introduction
2. 2-3 main points
3. A brief conclusion

Please do not include timestamps or any annotations that are not part of the spoken script."""


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
        raise

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

import time

def text_to_speech(script, voice):
    import time
    import io
    from pydub import AudioSegment

    API_URL = "https://api-inference.huggingface.co/models/espnet/kan-bayashi_ljspeech_vits"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}
    
    max_chunk_length = 500  # Adjust as needed
    chunks = [script[i:i+max_chunk_length] for i in range(0, len(script), max_chunk_length)]
    
    combined_audio = AudioSegment.empty()
    
    for chunk in chunks:
        payload = {"inputs": chunk}
        max_retries = 10
        retry_delay = 10

        for attempt in range(max_retries):
            response = requests.post(API_URL, headers=headers, json=payload)
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                logger.info(f"Received content-type: {content_type}")

                audio_bytes = io.BytesIO(response.content)
                if 'audio/flac' in content_type:
                    audio_segment = AudioSegment.from_file(audio_bytes, format="flac")
                elif 'audio/wav' in content_type:
                    audio_segment = AudioSegment.from_file(audio_bytes, format="wav")
                else:
                    # Attempt to detect format automatically
                    audio_segment = AudioSegment.from_file(audio_bytes)
                combined_audio += audio_segment
                break
            elif response.status_code == 503:
                if attempt < max_retries - 1:
                    logger.info(f"Model is loading. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise Exception("Model loading timeout. Please try again later.")
            else:
                logger.error(f"Error in TTS API: {response.status_code} - {response.text}")
                raise Exception(f"Error in TTS API: {response.text}")
        
    if combined_audio.duration_seconds > 0:
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3').name
        combined_audio.export(output_file, format="mp3")
        return output_file
    else:
        raise Exception("No audio was generated")

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

        # Step 1: Scrape content
        logger.info(f"Scraping content for topic: {topic}")
        scraped_content = scrape_content(topic)
        
        if not scraped_content:
            return jsonify({'error': 'No content found for the topic'}), 404

        # Step 2: Generate podcast script
        logger.info("Generating podcast script")
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
            headers={
                'Content-Disposition': f'attachment; filename={topic.replace(" ", "_")}_podcast_script.pdf',
                'Content-Type': 'application/pdf'
            }
        )
    except Exception as e:
        logger.error(f"Error in download_pdf: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate_audio', methods=['POST'])
def generate_audio():
    try:
        data = request.get_json()
        script = data.get('script')
        voice = data.get('voice', 'female')  # Note: The Hugging Face model doesn't support voice selection, but we keep this for future extensibility
        if not script:
            return jsonify({'error': 'Script not provided'}), 400
        
        audio_file = text_to_speech(script, voice)
        return send_file(
            audio_file,
            mimetype='audio/wav' if audio_file.endswith('.wav') else 'audio/mp3',
            as_attachment=True,
            download_name='podcast_audio.mp3'
        )
    except Exception as e:
        logger.error(f"Error in generate_audio: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)