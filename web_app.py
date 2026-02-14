# web_app.py - Complete with Authentication, Voice, File Uploads, and Multi-User
import os
import time
import threading
import json
import secrets
import re
import random
import sys
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for, send_file

# Optional imports for file processing - with error handling
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("⚠️ PyPDF2 not installed. PDF support disabled.")

try:
    import docx2txt
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False
    print("⚠️ docx2txt not installed. DOCX support disabled.")

try:
    from PIL import Image
    PIL_SUPPORT = True
except ImportError:
    PIL_SUPPORT = False
    print("⚠️ PIL not installed. Image support limited.")

try:
    import pytesseract
    TESSERACT_SUPPORT = True
except ImportError:
    TESSERACT_SUPPORT = False
    print("⚠️ pytesseract not installed. OCR disabled.")

app = Flask(__name__, 
            static_folder='web_ui/static',
            template_folder='web_ui/templates')

# Configuration
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}

# Create directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('user_data', exist_ok=True)
os.makedirs('user_data/files', exist_ok=True)

# Global state
users = {}
conversations = {}
user_files = {}
file_contents = {}  # Store extracted text content
ai_modules_loaded = False
llm = None
brain_modules = {}
is_processing = False

def load_ai_modules():
    """Load AI modules"""
    global llm, brain_modules, ai_modules_loaded
    try:
        print("🔄 Loading AI modules...")
        
        # Try to import brain modules
        try:
            from brain.local_llm import LocalLLM
            from brain.prompts import JARVIS_SYSTEM_PROMPT
            from brain.memory import load_memory, update_memory, save_memory
            from brain.mood import get_mood
            from brain.planner import plan_action
            
            brain_modules = {
                'LocalLLM': LocalLLM,
                'JARVIS_SYSTEM_PROMPT': JARVIS_SYSTEM_PROMPT,
                'load_memory': load_memory,
                'update_memory': update_memory,
                'save_memory': save_memory,
                'get_mood': get_mood,
                'plan_action': plan_action
            }
            print("✓ Brain modules loaded")
        except ImportError as e:
            print(f"⚠️ Brain modules not available: {e}")
        
        # Try to import agents
        try:
            from agents import browser_agent, windows_agent
            brain_modules['browser_agent'] = browser_agent
            brain_modules['windows_agent'] = windows_agent
            print("✓ Agents loaded")
        except:
            print("⚠️ Agents not available")
        
        # Initialize LLM
        try:
            if 'LocalLLM' in brain_modules:
                llm = brain_modules['LocalLLM'](model_name="phi3")
                ai_modules_loaded = True
                print("✅ AI modules loaded successfully")
            else:
                print("⚠️ LocalLLM not available")
                ai_modules_loaded = False
        except Exception as e:
            print(f"❌ Error initializing AI: {e}")
            ai_modules_loaded = False
        
    except Exception as e:
        print(f"❌ Error loading AI: {e}")
        ai_modules_loaded = False

# Load AI in background
ai_thread = threading.Thread(target=load_ai_modules)
ai_thread.daemon = True
ai_thread.start()

# Authentication
def load_users():
    try:
        with open('user_data/users.json', 'r') as f:
            return json.load(f)
    except:
        return {}

def save_users():
    with open('user_data/users.json', 'w') as f:
        json.dump(users, f, indent=2)

users = load_users()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if 'user_id' in session:
        return users.get(session['user_id'])
    return None

def get_user_conversation(user_id):
    if user_id not in conversations:
        # Try to load from file
        conv_file = f'user_data/{user_id}_conversations.json'
        if os.path.exists(conv_file):
            try:
                with open(conv_file, 'r') as f:
                    conversations[user_id] = json.load(f)
            except:
                conversations[user_id] = []
        else:
            conversations[user_id] = []
    return conversations[user_id]

def save_user_conversation(user_id):
    conv_file = f'user_data/{user_id}_conversations.json'
    if user_id in conversations:
        with open(conv_file, 'w') as f:
            json.dump(conversations[user_id][-100:], f, indent=2)  # Keep last 100

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# File processing functions
def extract_text_from_file(filepath, filename, file_type):
    """Extract text content from various file types"""
    text_content = ""
    summary = ""
    
    try:
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        # Text files
        if file_type == 'text/plain' or file_ext == 'txt':
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                text_content = f.read()
            summary = f"Text file with {len(text_content.split())} words"
        
        # PDF files
        elif file_ext == 'pdf' and PDF_SUPPORT:
            with open(filepath, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text_content = ""
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
            summary = f"PDF with {len(pdf_reader.pages)} pages, {len(text_content.split())} words"
        
        # Word documents
        elif file_ext == 'docx' and DOCX_SUPPORT:
            text_content = docx2txt.process(filepath)
            summary = f"Word document with {len(text_content.split())} words"
        
        # Images (OCR)
        elif file_ext in ['png', 'jpg', 'jpeg', 'gif'] and PIL_SUPPORT and TESSERACT_SUPPORT:
            image = Image.open(filepath)
            text_content = pytesseract.image_to_string(image)
            summary = f"Image with extracted text: {len(text_content.split())} words"
        
        # Fallback
        else:
            text_content = f"[File type {file_type} - content extraction not available]"
            summary = f"{file_type.upper()} file"
        
        # Truncate very long text
        if len(text_content) > 10000:
            text_content = text_content[:10000] + "... [truncated]"
        
    except Exception as e:
        print(f"Error extracting text from {filename}: {e}")
        text_content = f"[Error extracting content: {str(e)}]"
        summary = f"Error processing file"
    
    return text_content, summary

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get current user data
    user_id = session['user_id']
    user_data = users.get(user_id, {})
    
    # Get user stats
    user_conversations = get_user_conversation(user_id)
    user_files_list = user_files.get(user_id, [])
    
    return render_template('dashboard.html', 
                         current_user=user_data,
                         conversations_count=len(user_conversations),
                         files_count=len(user_files_list))

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html')

@app.route('/upload')
def upload():
    """File upload page"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user_data = users.get(user_id, {})
    
    return render_template('upload.html', current_user=user_data)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('profile.html')

@app.route('/voice')
def voice():
    """Voice assistant page"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user_data = users.get(user_id, {})
    
    return render_template('voice.html', current_user=user_data)

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        user = next((u for u in users.values() if u['username'] == username), None)
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return jsonify({'success': True, 'message': 'Login successful'})
        
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        email = data.get('email', '').strip()
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password required'}), 400
        
        if len(username) < 3:
            return jsonify({'success': False, 'message': 'Username must be at least 3 characters'}), 400
        
        if len(password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400
        
        if any(u['username'] == username for u in users.values()):
            return jsonify({'success': False, 'message': 'Username exists'}), 400
        
        user_id = secrets.token_hex(16)
        users[user_id] = {
            'id': user_id,
            'username': username,
            'password': generate_password_hash(password),
            'email': email,
            'created_at': datetime.now().isoformat(),
            'preferences': {}
        }
        
        save_users()
        session['user_id'] = user_id
        session['username'] = username
        
        return jsonify({'success': True, 'message': 'Registration successful'})
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    # Save conversations before logout
    if 'user_id' in session:
        save_user_conversation(session['user_id'])
    session.clear()
    return redirect(url_for('index'))

# File upload routes
@app.route('/api/files', methods=['GET'])
@login_required
def get_files():
    user_id = session['user_id']
    if user_id not in user_files:
        # Try to load from file
        files_file = f'user_data/{user_id}_files.json'
        if os.path.exists(files_file):
            try:
                with open(files_file, 'r') as f:
                    user_files[user_id] = json.load(f)
            except:
                user_files[user_id] = []
        else:
            user_files[user_id] = []
    return jsonify(user_files[user_id])

@app.route('/api/files/upload', methods=['POST'])
@login_required
def upload_file():
    user_id = session['user_id']
    username = session.get('username', 'unknown')
    
    print(f"📁 File upload attempt by user: {username}")
    
    if 'files' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    
    uploaded_files = request.files.getlist('files')
    uploaded = []
    
    # Initialize user files if needed
    if user_id not in user_files:
        user_files[user_id] = []
    
    for file in uploaded_files:
        if file.filename == '':
            continue
        
        if file and allowed_file(file.filename):
            # Generate unique filename
            filename = secure_filename(file.filename)
            file_id = secrets.token_hex(8)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            saved_filename = f"{user_id}_{timestamp}_{file_id}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
            
            # Save file
            file.save(filepath)
            
            # Extract text content
            file_type = file.content_type or 'application/octet-stream'
            text_content, summary = extract_text_from_file(filepath, filename, file_type)
            
            # Store content for AI reference
            content_id = secrets.token_hex(8)
            file_contents[content_id] = {
                'text': text_content,
                'filename': filename,
                'user_id': user_id
            }
            
            file_info = {
                'id': file_id,
                'content_id': content_id,
                'original_filename': filename,
                'saved_filename': saved_filename,
                'file_type': file_type,
                'size': os.path.getsize(filepath),
                'uploaded_at': datetime.now().isoformat(),
                'processing_status': 'processed',
                'summary': summary
            }
            
            user_files[user_id].append(file_info)
            uploaded.append(file_info)
            
            print(f"✅ File uploaded: {filename} ({len(text_content)} chars extracted)")
    
    # Save to disk
    files_file = f'user_data/{user_id}_files.json'
    with open(files_file, 'w') as f:
        json.dump(user_files[user_id], f, indent=2)
    
    return jsonify({'success': True, 'files': uploaded})

@app.route('/api/files/<file_id>', methods=['GET'])
@login_required
def get_file(file_id):
    user_id = session['user_id']
    
    if user_id in user_files:
        for file in user_files[user_id]:
            if file['id'] == file_id:
                return jsonify(file)
    
    return jsonify({'error': 'File not found'}), 404

@app.route('/api/files/<file_id>/content', methods=['GET'])
@login_required
def get_file_content(file_id):
    user_id = session['user_id']
    
    if user_id in user_files:
        for file in user_files[user_id]:
            if file['id'] == file_id:
                # Return stored content if available
                if 'content_id' in file and file['content_id'] in file_contents:
                    return jsonify({
                        'text': file_contents[file['content_id']]['text'],
                        'filename': file['original_filename'],
                        'summary': file.get('summary', '')
                    })
                
                # Fallback to reading from file
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file['saved_filename'])
                if os.path.exists(filepath):
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(5000)
                        return jsonify({
                            'text': content,
                            'filename': file['original_filename'],
                            'summary': file.get('summary', '')
                        })
                    except:
                        pass
                
                return jsonify({'text': 'Content not available', 'filename': file['original_filename']})
    
    return jsonify({'error': 'File not found'}), 404

@app.route('/api/files/<file_id>/ask', methods=['POST'])
@login_required
def ask_about_file(file_id):
    """Answer questions about a specific file"""
    user_id = session['user_id']
    data = request.json
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    # Find the file
    file_info = None
    if user_id in user_files:
        for file in user_files[user_id]:
            if file['id'] == file_id:
                file_info = file
                break
    
    if not file_info:
        return jsonify({'error': 'File not found'}), 404
    
    # Get file content
    file_content = ""
    if 'content_id' in file_info and file_info['content_id'] in file_contents:
        file_content = file_contents[file_info['content_id']]['text']
    else:
        # Try to read from file
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file_info['saved_filename'])
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.read(5000)
            except:
                file_content = "Could not read file content"
    
    # Use AI to answer question
    if ai_modules_loaded and llm:
        try:
            prompt = f"""Based on the following file content, answer the user's question.

File: {file_info['original_filename']}
File Type: {file_info['file_type']}
File Summary: {file_info.get('summary', 'No summary')}

File Content:
{file_content[:2000]}

Question: {question}

Answer concisely based only on the file content. If the answer cannot be found in the file, say so. Be helpful and informative."""
            
            answer = llm.generate(prompt)
            return jsonify({'answer': answer})
        except Exception as e:
            print(f"AI error: {e}")
            return jsonify({'answer': f"I couldn't process your question. Error: {str(e)}"})
    else:
        # Simple keyword matching fallback
        answer = generate_simple_answer(question, file_content, file_info)
        return jsonify({'answer': answer})

def generate_simple_answer(question, content, file_info):
    """Generate simple answer without AI"""
    question_lower = question.lower()
    content_lower = content.lower()
    
    # Check for word count question
    if 'how many words' in question_lower or 'word count' in question_lower:
        word_count = len(content.split())
        return f"The file has approximately {word_count} words."
    
    # Check for summary request
    if 'summary' in question_lower or 'summarize' in question_lower:
        return file_info.get('summary', f"This is a {file_info['file_type']} file named {file_info['original_filename']}.")
    
    # Check for keyword presence
    words = question_lower.split()
    keywords = [w for w in words if len(w) > 3]
    
    for keyword in keywords:
        if keyword in content_lower:
            # Find surrounding context
            pos = content_lower.find(keyword)
            start = max(0, pos - 50)
            end = min(len(content), pos + 100)
            context = content[start:end]
            return f"I found '{keyword}' in the file near: ...{context}..."
    
    return f"I couldn't find specific information about '{question}' in this file. The file contains {len(content.split())} words. You could try asking about specific topics or keywords."

@app.route('/api/files/<file_id>', methods=['DELETE'])
@login_required
def delete_file(file_id):
    user_id = session['user_id']
    
    if user_id in user_files:
        for i, file in enumerate(user_files[user_id]):
            if file['id'] == file_id:
                # Remove from disk
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file['saved_filename'])
                if os.path.exists(filepath):
                    os.remove(filepath)
                
                # Remove content from memory
                if 'content_id' in file and file['content_id'] in file_contents:
                    del file_contents[file['content_id']]
                
                # Remove from list
                user_files[user_id].pop(i)
                
                # Save to disk
                files_file = f'user_data/{user_id}_files.json'
                with open(files_file, 'w') as f:
                    json.dump(user_files[user_id], f, indent=2)
                
                return jsonify({'success': True})
    
    return jsonify({'error': 'File not found'}), 404

# Chat API
@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    global is_processing
    user_id = session['user_id']
    username = session.get('username', 'User')
    
    if is_processing:
        return jsonify({'error': 'AI is busy'}), 429
    
    try:
        is_processing = True
        data = request.json
        user_input = data.get('message', '').strip()
        
        if not user_input:
            return jsonify({'error': 'Empty message'}), 400
        
        print(f"👤 [{username}]: {user_input}")
        
        # Check for special commands
        if user_input.lower() in {"exit", "quit", "stop", "goodbye"}:
            response = "Goodbye! See you next time."
            add_to_history(user_id, user_input, response)
            return jsonify({'response': response, 'type': 'text'})
        
        # Check for file references
        file_context = ""
        file_pattern = r'\[file:([a-f0-9]+)\]'
        file_matches = re.findall(file_pattern, user_input)
        
        for file_id in file_matches:
            # Find the file
            for file in user_files.get(user_id, []):
                if file['id'] == file_id:
                    file_context += f"\n\n[Referenced File: {file['original_filename']}]\n"
                    file_context += f"File Summary: {file.get('summary', 'No summary')}\n"
                    
                    # Add content if available
                    if 'content_id' in file and file['content_id'] in file_contents:
                        content = file_contents[file['content_id']]['text']
                        if content:
                            file_context += f"File Content Preview:\n{content[:500]}...\n"
                    break
        
        if file_context:
            user_input += f"\n\nUser has referenced these files:{file_context}"
        
        # Use AI if available
        if ai_modules_loaded and llm:
            try:
                # Get conversation history
                history = get_user_conversation(user_id)
                recent_history = history[-5:] if history else []
                
                # Format history
                history_text = ""
                for msg in recent_history:
                    history_text += f"User: {msg['user']}\nAssistant: {msg['assistant']}\n"
                
                # Get user memory
                memory = get_user_memory(user_id)
                
                # Prepare prompt
                system_prompt = brain_modules.get('JARVIS_SYSTEM_PROMPT', 'You are EchoMind, a helpful AI assistant.')
                
                prompt = f"""{system_prompt}

User: {username}
Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Recent Conversation:
{history_text}

User Memory: {json.dumps(memory)}

User says: {user_input}

Assistant:"""
                
                # Generate response
                response = llm.generate(prompt)
                
                # Update memory (simple version)
                update_user_memory(user_id, user_input, response)
                
            except Exception as e:
                print(f"AI error: {e}")
                response = random.choice([
                    "I'm processing that request. Give me a moment.",
                    "Interesting! Let me think about that.",
                    "I'm working on your question.",
                    "Thanks for asking! Let me formulate a response."
                ])
        else:
            # Smart fallback responses
            response = generate_smart_response(user_input)
        
        add_to_history(user_id, user_input, response)
        
        return jsonify({
            'response': response,
            'type': 'text',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        is_processing = False

def generate_smart_response(user_input):
    """Generate smart fallback responses without AI"""
    user_input_lower = user_input.lower()
    
    # Time queries
    if 'time' in user_input_lower:
        return f"The current time is {datetime.now().strftime('%I:%M %p')}."
    
    # Date queries
    if 'date' in user_input_lower or 'day' in user_input_lower:
        return f"Today is {datetime.now().strftime('%B %d, %Y')}."
    
    # Help
    if 'help' in user_input_lower or 'what can you do' in user_input_lower:
        return """I can help you with:
• Answering questions
• Opening websites (try: open youtube)
• Playing videos (try: play music)
• Opening applications (try: open notepad)
• Uploading and analyzing files
• Voice conversations
• Remembering our conversations"""
    
    # File related
    if 'file' in user_input_lower or 'upload' in user_input_lower:
        return "You can upload files from the Upload page. Once uploaded, you can ask me questions about them!"
    
    # Greetings
    if any(word in user_input_lower for word in ['hello', 'hi', 'hey']):
        return f"Hello {session.get('username', 'there')}! How can I help you today?"
    
    # Default response
    return random.choice([
        "I understand. Tell me more about that.",
        "Interesting! What else would you like to discuss?",
        "I'm here to help. What would you like to know?",
        "Got it. Is there anything specific you'd like me to do?",
        "Thanks for sharing. How can I assist you further?"
    ])

def add_to_history(user_id, user_input, response):
    """Add to conversation history"""
    if user_id not in conversations:
        conversations[user_id] = get_user_conversation(user_id)
    
    conversations[user_id].append({
        'user': user_input,
        'assistant': response,
        'timestamp': datetime.now().isoformat()
    })
    
    # Keep only last 100 messages
    if len(conversations[user_id]) > 100:
        conversations[user_id] = conversations[user_id][-100:]
    
    # Save periodically (every 5 messages)
    if len(conversations[user_id]) % 5 == 0:
        save_user_conversation(user_id)

@app.route('/api/conversation', methods=['GET'])
@login_required
def get_conversation():
    user_id = session['user_id']
    return jsonify(get_user_conversation(user_id))

@app.route('/api/clear', methods=['POST'])
@login_required
def clear_conversation():
    user_id = session['user_id']
    if user_id in conversations:
        conversations[user_id] = []
        save_user_conversation(user_id)
    return jsonify({'success': True})

def get_user_memory(user_id):
    """Get user memory"""
    memory_file = f'user_data/{user_id}_memory.json'
    if os.path.exists(memory_file):
        try:
            with open(memory_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"interests": [], "last_topics": [], "preferences": {}}

def save_user_memory(user_id, memory):
    """Save user memory"""
    memory_file = f'user_data/{user_id}_memory.json'
    with open(memory_file, 'w') as f:
        json.dump(memory, f, indent=2)

def update_user_memory(user_id, user_input, response):
    """Simple memory update"""
    memory = get_user_memory(user_id)
    
    # Track topics (simple keyword extraction)
    keywords = [word for word in user_input.lower().split() if len(word) > 4]
    memory['last_topics'] = keywords[:5]
    
    # Save
    save_user_memory(user_id, memory)

# Voice API routes
@app.route('/api/voice/status', methods=['GET'])
@login_required
def voice_status():
    """Check voice support status"""
    return jsonify({
        'web_speech_supported': True,
        'browser_supported': 'webkitSpeechRecognition' in dir(window) if hasattr(window, 'webkitSpeechRecognition') else True,
        'ai_loaded': ai_modules_loaded
    })

@app.route('/api/voice/process', methods=['POST'])
@login_required
def process_voice():
    """Process voice command and return response"""
    data = request.json
    command = data.get('command', '').strip()
    
    if not command:
        return jsonify({'error': 'No command provided'}), 400
    
    # This endpoint just forwards to chat API
    # The actual processing happens in the browser with Web Speech API
    return jsonify({'success': True, 'command': command})
@app.route('/api/voice/synthesize', methods=['POST'])
@login_required
def synthesize_speech():
    """Get text to be spoken by browser"""
    data = request.json
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    return jsonify({
        'success': True,
        'text': text
    })

# Status API
@app.route('/api/status', methods=['GET'])
def get_status():
    user = get_current_user()
    return jsonify({
        'authenticated': user is not None,
        'username': user['username'] if user else None,
        'ai_loaded': ai_modules_loaded,
        'users_count': len(users),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/user/profile', methods=['GET'])
@login_required
def get_profile():
    user = get_current_user()
    if user:
        # Remove password from response
        profile = user.copy()
        profile.pop('password', None)
        return jsonify(profile)
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/user/profile', methods=['PUT'])
@login_required
def update_profile():
    user_id = session['user_id']
    data = request.json
    
    if user_id in users:
        # Update allowed fields
        if 'email' in data:
            users[user_id]['email'] = data['email'].strip()
        
        if 'preferences' in data:
            users[user_id]['preferences'] = data['preferences']
        
        save_users()
        return jsonify({'success': True})
    
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/voice/supported', methods=['GET'])
def check_voice_support():
    """Check if voice features are supported"""
    return jsonify({
        'web_speech_api': True,
        'browser_supported': True
    })

# Serve static files
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('web_ui/static', filename)

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

# Debug before request
@app.before_request
def before_request():
    """Debug session info"""
    if request.path.startswith('/static') or request.path.startswith('/api/status'):
        return
    
    if request.path in ['/upload', '/voice', '/chat', '/dashboard']:
        if 'user_id' not in session:
            print(f"⚠️ {request.path}: No session, redirecting to login")

def main():
    """Start the server"""
    print("=" * 50)
    print("🌐 EchoMind Web UI")
    print("=" * 50)
    print(f"📡 Server: http://localhost:5000")
    print(f"⚡ Features:")
    print(f"   • Authentication & Multi-User")
    print(f"   • File Uploads & Processing")
    print(f"   • Voice Assistant (Web Speech API)")
    print(f"   • AI Chat with Memory")
    print(f"   • PDF/DOCX/Image Support: {PDF_SUPPORT and DOCX_SUPPORT}")
    print(f"   • OCR Support: {TESSERACT_SUPPORT}")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)

if __name__ == '__main__':
    main()