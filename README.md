# AI Chatbot with Flask and LangChain

A conversational AI chatbot built with Flask, LangChain, and Groq's LLM API.

## Features

- Natural language processing with Groq's API
- Session-based conversation history
- RESTful API endpoints
- Web interface for interaction
- Error handling and retry mechanisms

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Set up environment variables
3. Run the application: `python app.py`

## API Endpoints

- `POST /api/chat` - Send a message to the chatbot
- `POST /api/reset` - Reset conversation history
- `GET /api/health` - Check API status
