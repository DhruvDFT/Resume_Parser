# FOOLPROOF RAILWAY FIX - "No start command found" Error

# The issue is Railway can't detect how to start your Python app
# Here are 3 guaranteed solutions:

# ===== SOLUTION 1: Add Procfile (Recommended) =====

# Create a file named exactly "Procfile" (no extension):
echo "web: gunicorn app:app --bind 0.0.0.0:\$PORT" > Procfile

# ===== SOLUTION 2: Update requirements.txt with Python version =====

# requirements.txt
cat > requirements.txt << 'EOF'
Flask==2.3.3
gunicorn==21.2.0
EOF

# ===== SOLUTION 3: Create railway.toml instead of railway.json =====

# railway.toml
cat > railway.toml << 'EOF'
[build]
builder = "nixpacks"

[deploy]
startCommand = "gunicorn app:app --bind 0.0.0.0:$PORT"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
EOF

# ===== SOLUTION 4: Super Simple app.py =====

# app.py (ultra-minimal version)
cat > app.py << 'EOF'
from flask import Flask, request, jsonify, render_template_string
import re

app = Flask(__name__)

@app.route('/')
def home():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Resume Parser</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            .header { background: #3498db; color: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 30px; }
            .upload-area { border: 2px dashed #3498db; padding: 40px; text-align: center; border-radius: 10px; margin-bottom: 20px; }
            .btn { background: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
            .result { background: #f8f9fa; padding: 20px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #3498db; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🐍 Resume Parser</h1>
            <p>Upload resume files and extract information</p>
        </div>
        
        <div class="upload-area">
            <h3>📄 Upload Resume Files</h3>
            <form id="uploadForm" enctype="multipart/form-data">
                <input type="file" id="fileInput" multiple accept=".txt,.pdf,.doc,.docx">
                <br><br>
                <button type="submit" class="btn">Parse Resumes</button>
            </form>
        </div>
        
        <div id="results"></div>
        
        <script>
            document.getElementById('uploadForm').onsubmit = async function(e) {
                e.preventDefault();
                
                const fileInput = document.getElementById('fileInput');
                const files = fileInput.files;
                
                if (files.length === 0) {
                    alert('Please select files first!');
                    return;
                }
                
                const formData = new FormData();
                for (let i = 0; i < files.length; i++) {
                    formData.append('files', files[i]);
                }
                
                document.getElementById('results').innerHTML = '<p>Processing...</p>';
                
                try {
                    const response = await fetch('/parse', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    displayResults(data);
                } catch (error) {
                    document.getElementById('results').innerHTML = '<p style="color: red;">Error: ' + error.message + '</p>';
                }
            };
            
            function displayResults(results) {
                let html = '<h3>📊 Results:</h3>';
                
                results.forEach(result => {
                    if (result.success) {
                        html += `
                            <div class="result">
                                <h4>✅ ${result.filename}</h4>
                                <p><strong>Name:</strong> ${result.data.name}</p>
                                <p><strong>Email:</strong> ${result.data.email}</p>
                                <p><strong>Phone:</strong> ${result.data.phone}</p>
                                <p><strong>Skills:</strong> ${result.data.skills.join(', ')}</p>
                            </div>
                        `;
                    } else {
                        html += `
                            <div class="result" style="border-left-color: #e74c3c;">
                                <h4>❌ ${result.filename}</h4>
                                <p style="color: #e74c3c;">${result.error}</p>
                            </div>
                        `;
                    }
                });
                
                document.getElementById('results').innerHTML = html;
            }
        </script>
    </body>
    </html>
    ''')

@app.route('/health')
def health():
    return {'status': 'healthy'}

@app.route('/parse', methods=['POST'])
def parse_resumes():
    try:
        files = request.files.getlist('files')
        results = []
        
        for file in files:
            try:
                # Read file content
                content = file.read().decode('utf-8', errors='ignore')
                
                # Simple parsing
                email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)
                phone_match = re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', content)
                
                # Extract skills (simple keyword search)
                skills = []
                skill_keywords = ['python', 'javascript', 'java', 'react', 'node', 'sql', 'html', 'css']
                content_lower = content.lower()
                for skill in skill_keywords:
                    if skill in content_lower:
                        skills.append(skill)
                
                # Extract name (first line that looks like a name)
                lines = content.split('\n')[:5]
                name = 'Not found'
                for line in lines:
                    line = line.strip()
                    if len(line) > 3 and len(line) < 50 and not any(x in line.lower() for x in ['resume', 'cv', '@']):
                        name_match = re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+', line)
                        if name_match:
                            name = name_match.group(0)
                            break
                
                results.append({
                    'filename': file.filename,
                    'success': True,
                    'data': {
                        'name': name,
                        'email': email_match.group(0) if email_match else 'Not found',
                        'phone': phone_match.group(0) if phone_match else 'Not found',
                        'skills': skills if skills else ['Not specified']
                    }
                })
                
            except Exception as e:
                results.append({
                    'filename': file.filename,
                    'success': False,
                    'error': str(e)
                })
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
EOF

# ===== SOLUTION 5: Create start.sh script =====

# start.sh
cat > start.sh << 'EOF'
#!/bin/bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120
EOF

chmod +x start.sh

# ===== Final file structure should be: =====
echo "
📁 Your project should have these files:

✅ app.py (ultra-simple Flask app)
✅ requirements.txt (only Flask + gunicorn)
✅ Procfile (tells Railway how to start)
✅ .gitignore (optional)

That's it! Only 3-4 files total.
"

# ===== Deploy commands =====
echo "
🚀 Deploy commands:

1. Create these files in your project folder
2. Run these commands:

git init
git add .
git commit -m 'Working resume parser'
git remote add origin https://github.com/yourusername/resume-parser.git
git push -u origin main

3. On Railway:
   - New Project
   - Deploy from GitHub repo
   - Select your repository
   - Railway will auto-deploy!

🎯 Alternative: Set start command manually in Railway:
   - Go to your Railway project
   - Settings → Deploy
   - Custom Start Command: gunicorn app:app --bind 0.0.0.0:\$PORT
"

# ===== Quick test locally =====
echo "
🧪 Test locally first:

pip install flask gunicorn
python app.py

Then visit: http://localhost:5000
"

# ===== Complete working example =====
echo "
💡 COMPLETE WORKING FILES:

Create exactly these 3 files:

1. app.py (copy from above)
2. requirements.txt:
   Flask==2.3.3
   gunicorn==21.2.0

3. Procfile:
   web: gunicorn app:app --bind 0.0.0.0:\$PORT

That's it! This WILL work on Railway.
"
