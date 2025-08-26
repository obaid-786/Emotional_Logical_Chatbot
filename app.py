from flask import Flask, request, jsonify, session, render_template, send_from_directory
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
import os
import time
import logging
from groq import APIConnectionError

# Import LangChain message types at the top
try:
    from langchain.schema import HumanMessage, AIMessage
except ImportError:
    # Fallback if langchain is not available
    class HumanMessage:
        def model_dump(self):
            return {"type": "human", "content": getattr(self, 'content', '')}


    class AIMessage:
        def model_dump(self):
            return {"type": "ai", "content": getattr(self, 'content', '')}


class CustomJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, (HumanMessage, AIMessage)):
            # Use model_dump() instead of dict() for Pydantic v2 compatibility
            return obj.model_dump()
        return super().default(obj)


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import from your Groq.py file
try:
    from Groq import graph, State, llm
except ImportError as e:
    logger.error(f"Failed to import from Groq.py: {e}")


    # Create fallback functions if import fails
    def fallback_graph(state):
        return {"messages": [{"role": "assistant",
                              "content": "I'm having trouble connecting to the AI service. Please check your internet connection."}],
                "message_type": None}


    graph = fallback_graph
    State = dict

app = Flask(__name__)
app.json = CustomJSONProvider(app)
app.secret_key = os.urandom(24)  # Secure random key for sessions
CORS(app)


# Add retry mechanism for API calls
def retry_api_call(func, *args, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except APIConnectionError as e:
            logger.warning(f"API connection error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
        except Exception as e:
            logger.error(f"Unexpected error in API call: {e}")
            raise


# Serve static files
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


@app.route('/')
def home():
    return render_template('mind_chat.html')


def convert_messages_to_dicts(messages):
    """Convert LangChain message objects to dictionaries"""
    converted = []
    for msg in messages:
        if hasattr(msg, 'model_dump'):
            converted.append(msg.model_dump())
        elif hasattr(msg, 'dict'):
            converted.append(msg.dict())
        elif isinstance(msg, dict):
            converted.append(msg)
        else:
            # Fallback: try to extract content
            content = getattr(msg, 'content', str(msg))
            role = getattr(msg, 'type', getattr(msg, 'role', 'unknown'))
            converted.append({"role": role, "content": content})
    return converted


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        # Check if request contains JSON
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400

        user_message = request.json.get('message')

        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        logger.info(f"Received message: {user_message}")

        # Initialize or get the current state from session
        if 'state' not in session:
            session['state'] = {"messages": [], "message_type": None}

        # Ensure messages are in dictionary format
        if session['state'].get('messages'):
            session['state']['messages'] = convert_messages_to_dicts(session['state']['messages'])

        # Add user message to state
        session['state']['messages'] = session['state'].get('messages', []) + [
            {"role": "user", "content": user_message}
        ]

        # Invoke the graph with retry mechanism
        try:
            result_state = retry_api_call(graph.invoke, session['state'])
        except APIConnectionError:
            return jsonify(
                {'error': 'Unable to connect to the AI service. Please check your internet connection.'}), 503
        except Exception as e:
            logger.error(f"Error in graph invocation: {e}")
            return jsonify({'error': 'Error while processing your message.'}), 500

        # Convert any message objects to dictionaries before storing in session
        if result_state.get('messages'):
            result_state['messages'] = convert_messages_to_dicts(result_state['messages'])

        # Update session state
        session['state'] = result_state

        # Get the last message (AI response)
        if result_state.get('messages') and len(result_state['messages']) > 0:
            # Find the last assistant message
            for msg in reversed(result_state['messages']):
                if msg.get('role') == 'assistant' or msg.get('type') == 'ai':
                    ai_response = msg.get('content', '')
                    break
            else:
                ai_response = "I'm sorry, I didn't get a response."
        else:
            ai_response = "I'm sorry, I didn't get a response."

        return jsonify({'response': ai_response})

    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        return jsonify({'error': 'Sorry, I encountered an unexpected error. Please try again.'}), 500


@app.route('/api/reset', methods=['POST'])
def reset_chat():
    # Reset the conversation
    session['state'] = {"messages": [], "message_type": None}
    return jsonify({'status': 'conversation reset'})


@app.route('/api/health', methods=['GET'])
def health_check():
    """Check if the Groq API is accessible"""
    try:
        # Try a simple API call to check connectivity
        test_response = retry_api_call(llm.invoke, "Hello")
        return jsonify({'status': 'healthy', 'api_accessible': True})
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'api_accessible': False, 'error': str(e)}), 503


if __name__ == '__main__':
    app.run(debug=True, port=5000)