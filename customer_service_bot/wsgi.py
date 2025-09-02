# wsgi.py (at repo root)
import os, sys
# Add the src folder to Python's import path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# Import the Flask app object from your app file
# If your Flask app is created as `app = Flask(__name__)` in src/main.py, this will work:
from main import app

# If your project instead uses a factory like create_app(), use this instead:
# from main import create_app
# app = create_app()
