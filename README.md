# PromptCast.ai 🎙️ AI-Powered Podcast Creation

![PromptCast.ai](https://web-production-3fcf.up.railway.app/)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.9-blue.svg)](https://www.python.org/downloads/release/python-390/)
[![Flask Version](https://img.shields.io/badge/flask-3.0.3-green.svg)](https://flask.palletsprojects.com/en/3.0.x/)

PromptCast.ai is an innovative AI-powered platform that revolutionizes podcast creation. With just a topic input, it generates professional-quality podcast scripts and audio, making content creation accessible to everyone.

## 🌟 Features

- 🔍 **Intelligent Content Scraping**: Gathers relevant information from the web based on your topic.
- 📝 **AI Script Generation**: Creates engaging podcast scripts using advanced AI models.
- 🔊 **Text-to-Speech Conversion**: Transforms written scripts into natural-sounding audio.
- 📄 **PDF Export**: Generates downloadable PDF versions of your podcast scripts.
- 🎨 **User-Friendly Interface**: Intuitive web interface for easy interaction.

## 🚀 Quick Start

Get PromptCast.ai up and running in minutes:

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/promptcast-ai.git
   cd promptcast-ai
   ```

2. Set up a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\\Scripts\\activate`
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the root directory and add:
   ```
   CEREBRAS_API_KEY=your_cerebras_api_key
   HUGGINGFACE_API_TOKEN=your_huggingface_api_token
   ```

5. Run the application:
   ```bash
   python app.py
   ```

6. Open your browser and navigate to `http://localhost:5000`.

## 🏗️ Architecture

PromptCast.ai follows a modular architecture for efficient and scalable podcast creation:

```mermaid
graph TB
    A[Web Interface] -->|User Input| B[Flask Server]
    B -->|Topic| C[Content Scraper]
    C -->|Raw Content| D[Script Generator]
    D -->|Script| E[PDF Creator]
    D -->|Script| F[Text-to-Speech]
    E -->|PDF| B
    F -->|Audio| B
    B -->|Results| A
