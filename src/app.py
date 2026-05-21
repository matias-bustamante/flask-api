from flask import Flask 
from flask_cors import CORS
from routes.gemini import gemini_ai 

app=Flask(__name__) 
CORS(app,expose_headers=["Content-Type", "Content-Disposition"])
app.register_blueprint(gemini_ai)

if __name__=='__name__': 
    app.run(Debug=True)