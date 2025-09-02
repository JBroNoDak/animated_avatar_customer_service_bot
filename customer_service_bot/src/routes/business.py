from flask import Blueprint, request, jsonify, send_file
from src.models.business import BusinessKnowledge, ChatConversation, db
import requests
from bs4 import BeautifulSoup
import openai
import uuid
from datetime import datetime
import os
import tempfile

business_bp = Blueprint('business', __name__)

@business_bp.route('/knowledge', methods=['GET'])
def get_knowledge():
    """Get all business knowledge entries"""
    try:
        knowledge_entries = BusinessKnowledge.query.all()
        return jsonify([entry.to_dict() for entry in knowledge_entries])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@business_bp.route('/knowledge', methods=['POST'])
def add_knowledge():
    """Add new business knowledge from URL or manual input"""
    try:
        data = request.get_json()
        
        if 'url' in data:
            # Process URL
            url = data['url']
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = soup.find('title')
            title = title.get_text().strip() if title else url
            
            # Extract main content
            content = ""
            for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
                text = tag.get_text().strip()
                if text:
                    content += text + "\n"
            
            knowledge = BusinessKnowledge(
                title=title,
                content=content,
                source_url=url,
                source_type='url'
            )
            
        elif 'title' in data and 'content' in data:
            # Manual input
            knowledge = BusinessKnowledge(
                title=data['title'],
                content=data['content'],
                source_type='manual'
            )
        else:
            return jsonify({'error': 'Either URL or title/content required'}), 400
        
        db.session.add(knowledge)
        db.session.commit()
        
        return jsonify(knowledge.to_dict()), 201
        
    except requests.RequestException as e:
        return jsonify({'error': f'Failed to fetch URL: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@business_bp.route('/knowledge/<int:knowledge_id>', methods=['DELETE'])
def delete_knowledge(knowledge_id):
    """Delete a business knowledge entry"""
    try:
        knowledge = BusinessKnowledge.query.get_or_404(knowledge_id)
        db.session.delete(knowledge)
        db.session.commit()
        return jsonify({'message': 'Knowledge deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@business_bp.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages and generate responses"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get all business knowledge for context
        knowledge_entries = BusinessKnowledge.query.all()
        context = "\n".join([f"Title: {entry.title}\nContent: {entry.content}\n---" 
                           for entry in knowledge_entries])
        
        # Create system prompt
        system_prompt = f"""You are a helpful customer service bot. Use the following business knowledge to answer questions:

{context}

If you don't have specific information about the question, politely say so and offer to help in other ways. Be friendly and professional."""
        
        # Generate response using OpenAI
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        bot_response = response.choices[0].message.content
        
        # Save conversation
        conversation = ChatConversation(
            session_id=session_id,
            message=message,
            response=bot_response
        )
        db.session.add(conversation)
        db.session.commit()
        
        return jsonify({
            'response': bot_response,
            'session_id': session_id,
            'has_speech': True
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@business_bp.route('/chat/history/<session_id>', methods=['GET'])
def get_chat_history(session_id):
    """Get chat history for a session"""
    try:
        conversations = ChatConversation.query.filter_by(session_id=session_id).order_by(ChatConversation.created_at).all()
        return jsonify([conv.to_dict() for conv in conversations])
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@business_bp.route('/speech', methods=['POST'])
def generate_speech():
    """Generate speech audio from text"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        # Create temporary file for audio
        temp_dir = tempfile.mkdtemp()
        audio_path = os.path.join(temp_dir, 'speech.wav')
        
        # Generate speech using OpenAI TTS
        client = openai.OpenAI()
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",  # Female voice
            input=text
        )
        
        # Save audio to file
        response.stream_to_file(audio_path)
        
        return send_file(audio_path, as_attachment=True, download_name='speech.wav', mimetype='audio/wav')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

