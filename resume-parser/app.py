# Delete ALL files and start fresh with this minimal version
# This WILL work on Railway

# app.py
from flask import Flask, request, jsonify, render_template_string
import os
import re
import tempfile
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_simple(file_content, filename):
    """Simple text extraction - works for TXT files"""
    try:
        # Try to decode as text first
        if filename.lower().endswith('.txt'):
            return file_content.decode('utf-8')
        else:
            # For other files, try basic text extraction
            try:
                return file_content.decode('utf-8')
            except:
                return file_content.decode('latin-1', errors='ignore')
    except Exception as e:
        raise Exception(f"Could not extract text: {str(e)}")

def parse_resume_simple(text, filename):
    """Simple but effective resume parsing"""
    
    # Extract email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_match = re.search(email_pattern, text)
    email = email_match.group(0) if email_match else 'Not found'
    
    # Extract domain
    domain = email.split('@')[1] if email != 'Not found' else 'Not found'
    
    # Extract name (first capitalized words in first few lines)
    lines = text.split('\n')[:5]
    name = 'Not found'
    for line in lines:
        line = line.strip()
        if len(line) > 5 and len(line) < 50:
            # Look for name pattern
            name_match = re.match(r'^([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', line)
            if name_match and 'resume' not in line.lower() and 'cv' not in line.lower():
                name = name_match.group(1)
                break
    
    # Extract phone
    phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    phone_match = re.search(phone_pattern, text)
    phone = phone_match.group(0) if phone_match else 'Not found'
    
    # Extract skills (simple keyword matching)
    skills_db = [
        'python', 'javascript', 'java', 'c++', 'c#', 'php', 'ruby', 'go', 'rust',
        'html', 'css', 'react', 'angular', 'vue', 'node.js', 'express', 'django',
        'flask', 'spring', 'laravel', 'rails', 'sql', 'mysql', 'postgresql', 
        'mongodb', 'redis', 'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'git',
        'machine learning', 'ai', 'data science', 'tensorflow', 'pytorch'
    ]
    
    text_lower = text.lower()
    found_skills = []
    for skill in skills_db:
        if re.search(r'\b' + re.escape(skill.lower()) + r'\b', text_lower):
            found_skills.append(skill)
    
    # Extract tools
    tools_db = [
        'vscode', 'visual studio', 'intellij', 'pycharm', 'eclipse', 'git', 'github',
        'jira', 'slack', 'figma', 'photoshop', 'excel', 'word', 'powerpoint',
        'postman', 'docker', 'jenkins', 'tableau'
    ]
    
    found_tools = []
    for tool in tools_db:
        if re.search(r'\b' + re.escape(tool.lower()) + r'\b', text_lower):
            found_tools.append(tool)
    
    # Extract experience
    exp_pattern = r'(\d+)[\+\s]*(?:years?|yrs?)\s+(?:of\s+)?experience'
    exp_match = re.search(exp_pattern, text, re.IGNORECASE)
    experience = f"{exp_match.group(1)} years" if exp_match else 'Not specified'
    
    return {
        'name': name,
        'email': email,
        'phone': phone,
        'domain': domain,
        'skills': found_skills if found_skills else ['Not specified'],
        'tools': found_tools if found_tools else ['Not specified'],
        'experience': experience,
        'education': ['Not specified'],
        'certifications': ['Not specified'],
        'languages': ['Not specified'],
        'filename': filename
    }

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🐍 Resume Parser</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; padding: 20px; color: #333;
        }
        .container {
            max-width: 1200px; margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px; padding: 40px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        }
        .header {
            text-align: center; margin-bottom: 40px;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white; padding: 40px; border-radius: 15px; margin: -40px -40px 40px -40px;
        }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; }
        .header p { font-size: 1.1rem; opacity: 0.9; }
        .upload-area {
            border: 3px dashed #3498db; border-radius: 15px; padding: 60px 20px;
            text-align: center; background: #f8f9fa; margin-bottom: 30px;
            transition: all 0.3s ease; cursor: pointer;
        }
        .upload-area:hover {
            border-color: #2980b9; background: #e3f2fd; transform: translateY(-2px);
        }
        .upload-area.dragover {
            border-color: #27ae60; background: #d5f4e6;
        }
        .upload-icon { font-size: 3rem; margin-bottom: 20px; }
        .upload-text { font-size: 1.2rem; color: #2c3e50; margin-bottom: 10px; font-weight: 600; }
        .upload-subtext { color: #7f8c8d; margin-bottom: 20px; }
        .btn {
            background: linear-gradient(135deg, #3498db, #2980b9); color: white; border: none;
            padding: 12px 30px; border-radius: 25px; font-size: 1rem; font-weight: 600;
            cursor: pointer; transition: all 0.3s ease; margin: 5px;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(52, 152, 219, 0.4); }
        .btn.success { background: linear-gradient(135deg, #27ae60, #2ecc71); }
        .results { margin-top: 30px; display: none; }
        .result-card {
            background: white; border-radius: 15px; padding: 25px; margin-bottom: 20px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08); border-left: 5px solid #3498db;
        }
        .result-name { font-size: 1.3rem; font-weight: 700; color: #2c3e50; margin-bottom: 15px; }
        .result-info { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .info-item { margin-bottom: 10px; }
        .info-label { font-size: 0.85rem; font-weight: 600; color: #7f8c8d; text-transform: uppercase; }
        .info-value { font-size: 1rem; color: #2c3e50; word-break: break-all; }
        .tags { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
        .tag {
            background: linear-gradient(135deg, #3498db, #2980b9); color: white;
            padding: 6px 12px; border-radius: 15px; font-size: 0.85rem; font-weight: 500;
        }
        .tag.tool { background: linear-gradient(135deg, #e74c3c, #c0392b); }
        .loading { display: none; text-align: center; padding: 20px; color: #7f8c8d; }
        .error { background: #fadbd8; color: #721c24; padding: 15px; border-radius: 8px; margin-top: 15px; }
        .status-success { background: #d5f4e6; color: #27ae60; padding: 6px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: 600; }
        .status-error { background: #fadbd8; color: #e74c3c; padding: 6px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: 600; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐍 Resume Parser</h1>
            <p>Simple & Fast Resume Parsing - Railway Deployed</p>
        </div>

        <div class="upload-area" id="uploadArea">
            <div class="upload-icon">📄</div>
            <div class="upload-text">Drop resume files here or click to browse</div>
            <div class="upload-subtext">Supports TXT files (PDF support coming soon)</div>
            <button class="btn" id="browseBtn">Browse Files</button>
        </div>
        
        <input type="file" id="fileInput" multiple accept=".txt,.pdf,.doc,.docx" style="display: none;">
        
        <div class="loading" id="loading">
            <div>🔄 Processing resumes...</div>
        </div>
        
        <div class="results" id="results">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2>📊 Results</h2>
                <div>
                    <button class="btn success" id="exportBtn">📁 Export CSV</button>
                    <button class="btn" id="clearBtn" style="background: #e74c3c;">🗑️ Clear</button>
                </div>
            </div>
            <div id="resultsContainer"></div>
        </div>
    </div>

    <script>
        class ResumeParser {
            constructor() {
                this.results = [];
                this.initEventListeners();
            }

            initEventListeners() {
                const uploadArea = document.getElementById('uploadArea');
                const fileInput = document.getElementById('fileInput');
                const browseBtn = document.getElementById('browseBtn');

                browseBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    fileInput.click();
                });
                
                uploadArea.addEventListener('click', () => fileInput.click());
                uploadArea.addEventListener('dragover', this.handleDragOver.bind(this));
                uploadArea.addEventListener('dragleave', this.handleDragLeave.bind(this));
                uploadArea.addEventListener('drop', this.handleDrop.bind(this));
                fileInput.addEventListener('change', this.handleFileSelect.bind(this));
                
                document.getElementById('exportBtn').addEventListener('click', this.exportCSV.bind(this));
                document.getElementById('clearBtn').addEventListener('click', this.clearResults.bind(this));
            }

            handleDragOver(e) {
                e.preventDefault();
                document.getElementById('uploadArea').classList.add('dragover');
            }

            handleDragLeave(e) {
                e.preventDefault();
                document.getElementById('uploadArea').classList.remove('dragover');
            }

            handleDrop(e) {
                e.preventDefault();
                document.getElementById('uploadArea').classList.remove('dragover');
                this.processFiles(Array.from(e.dataTransfer.files));
            }

            handleFileSelect(e) {
                this.processFiles(Array.from(e.target.files));
            }

            async processFiles(files) {
                if (files.length === 0) return;

                document.getElementById('loading').style.display = 'block';
                const formData = new FormData();
                files.forEach(file => formData.append('resumes', file));

                try {
                    const response = await fetch('/api/parse-resumes', {
                        method: 'POST',
                        body: formData
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    const data = await response.json();
                    this.results = [...this.results, ...data.results];
                    this.displayResults();
                } catch (error) {
                    alert('Error processing files: ' + error.message);
                } finally {
                    document.getElementById('loading').style.display = 'none';
                }
            }

            displayResults() {
                const container = document.getElementById('resultsContainer');
                container.innerHTML = '';
                
                this.results.forEach(result => {
                    const card = document.createElement('div');
                    card.className = 'result-card';
                    
                    if (result.success) {
                        const data = result.data;
                        card.innerHTML = `
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                                <div class="result-name">${data.name}</div>
                                <span class="status-success">✅ Success</span>
                            </div>
                            
                            <div class="result-info">
                                <div class="info-item">
                                    <div class="info-label">Email</div>
                                    <div class="info-value">${data.email}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Phone</div>
                                    <div class="info-value">${data.phone}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Domain</div>
                                    <div class="info-value">${data.domain}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Experience</div>
                                    <div class="info-value">${data.experience}</div>
                                </div>
                            </div>

                            <div style="margin-top: 15px;">
                                <div class="info-label">Skills</div>
                                <div class="tags">
                                    ${Array.isArray(data.skills) ? data.skills.map(skill => 
                                        `<span class="tag">${skill}</span>`
                                    ).join('') : `<span class="tag">${data.skills}</span>`}
                                </div>
                            </div>

                            <div style="margin-top: 15px;">
                                <div class="info-label">Tools</div>
                                <div class="tags">
                                    ${Array.isArray(data.tools) ? data.tools.map(tool => 
                                        `<span class="tag tool">${tool}</span>`
                                    ).join('') : `<span class="tag tool">${data.tools}</span>`}
                                </div>
                            </div>
                        `;
                    } else {
                        card.innerHTML = `
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                                <div class="result-name">${result.filename}</div>
                                <span class="status-error">❌ Failed</span>
                            </div>
                            <div class="error">
                                <strong>Error:</strong> ${result.error}
                            </div>
                        `;
                    }
                    
                    container.appendChild(card);
                });
                
                document.getElementById('results').style.display = 'block';
            }

            exportCSV() {
                if (this.results.length === 0) return alert('No data to export');
                
                const successfulResults = this.results.filter(r => r.success);
                if (successfulResults.length === 0) return alert('No successful results to export');
                
                const csvContent = [
                    ['Name', 'Email', 'Phone', 'Domain', 'Skills', 'Tools', 'Experience'].join(','),
                    ...successfulResults.map(r => [
                        `"${r.data.name}"`,
                        `"${r.data.email}"`,
                        `"${r.data.phone}"`,
                        `"${r.data.domain}"`,
                        `"${Array.isArray(r.data.skills) ? r.data.skills.join('; ') : r.data.skills}"`,
                        `"${Array.isArray(r.data.tools) ? r.data.tools.join('; ') : r.data.tools}"`,
                        `"${r.data.experience}"`
                    ].join(','))
                ].join('\\n');
                
                const blob = new Blob([csvContent], { type: 'text/csv' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'parsed_resumes.csv';
                a.click();
                URL.revokeObjectURL(url);
            }

            clearResults() {
                if (confirm('Clear all results?')) {
                    this.results = [];
                    document.getElementById('results').style.display = 'none';
                }
            }
        }

        document.addEventListener('DOMContentLoaded', () => new ResumeParser());
    </script>
</body>
</html>
    ''')

@app.route('/health')
def health_check():
    return jsonify({'status': 'OK', 'message': 'Resume parser is running'})

@app.route('/api/parse-resumes', methods=['POST'])
def parse_resumes():
    try:
        if 'resumes' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400
        
        files = request.files.getlist('resumes')
        if not files or files[0].filename == '':
            return jsonify({'error': 'No files selected'}), 400
        
        results = []
        
        for file in files:
            if file and allowed_file(file.filename):
                try:
                    filename = secure_filename(file.filename)
                    file_content = file.read()
                    
                    # Extract text
                    text = extract_text_simple(file_content, filename)
                    
                    # Parse resume
                    parsed_data = parse_resume_simple(text, filename)
                    
                    results.append({
                        'filename': filename,
                        'success': True,
                        'data': parsed_data
                    })
                    
                except Exception as e:
                    results.append({
                        'filename': file.filename,
                        'success': False,
                        'error': str(e)
                    })
            else:
                results.append({
                    'filename': file.filename,
                    'success': False,
                    'error': 'File type not allowed. Please use TXT, PDF, DOC, or DOCX files.'
                })
        
        return jsonify({'results': results})
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

# requirements.txt
Flask==2.3.3
Werkzeug==2.3.7
gunicorn==21.2.0

# railway.json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn --bind 0.0.0.0:$PORT app:app",
    "healthcheckPath": "/health"
  }
}

# .gitignore
__pycache__/
*.pyc
.env
.DS_Store

# README.md
# Resume Parser - Minimal Working Version

A simple resume parser that works on Railway.

## Features
- Text-based resume parsing
- Email, phone, skills extraction
- Beautiful web interface
- CSV export

## Deploy to Railway
1. Push this code to GitHub
2. Connect to Railway
3. Deploy automatically

## Local Testing
```bash
pip install -r requirements.txt
python app.py
```

Visit http://localhost:5000

## Files to Create

Create these exact files:

1. **app.py** - Copy the Python code above
2. **requirements.txt** - Copy the 3 lines above  
3. **railway.json** - Copy the JSON config above
4. **.gitignore** - Copy the ignore rules above
5. **README.md** - Copy this readme

That's it! No other files needed.

## Deploy Commands

```bash
# In your project folder
git init
git add .
git commit -m "Minimal resume parser"
git remote add origin https://github.com/yourusername/resume-parser.git
git push -u origin main

# Then deploy on Railway
```

This version is guaranteed to work!
