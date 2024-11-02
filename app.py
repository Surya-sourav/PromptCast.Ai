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
CEREBRAS_API_KEY = os.getenv('CEREBRAS_API_KEY')
HUGGINGFACE_API_TOKEN = os.getenv('HUGGINGFACE_API_TOKEN')

if not CEREBRAS_API_KEY or not HUGGINGFACE_API_TOKEN:
    logger.error("Missing required API keys in environment variables")
    raise ValueError("Missing required API keys")

os.environ["CEREBRAS_API_KEY"] = CEREBRAS_API_KEY

# Keep all your existing helper functions (scrape_content, generate_podcast_script, etc.)
# ... (keep all the existing functions unchanged)

# Update the main execution block
if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
