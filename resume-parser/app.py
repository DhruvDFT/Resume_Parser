from flask import Flask, request, jsonify, render_template_string
import re
import os
import logging
import io

# Import for document processing
try:
    import zipfile
    import xml.etree.ElementTree as ET
    import PyPDF2
except ImportError:
    zipfile = None
    ET = None
    PyPDF2 = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

@app.route('/')
def home():
    logger.info("Home route accessed")
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Resume Parser</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px; 
                margin: 0 auto; 
                padding: 20px; 
                background: #f5f7fa;
                line-height: 1.6;
            }
            .header { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; 
                padding: 30px; 
                border-radius: 15px; 
                text-align: center; 
                margin-bottom: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            .upload-area { 
                background: white;
                border: 2px dashed #667eea; 
                padding: 40px; 
                text-align: center; 
                border-radius: 15px; 
                margin-bottom: 20px;
                transition: all 0.3s ease;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            }
            .upload-area:hover {
                border-color: #764ba2;
                transform: translateY(-2px);
            }
            .btn { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; 
                padding: 12px 30px; 
                border: none; 
                border-radius: 25px; 
                cursor: pointer;
                font-size: 16px;
                font-weight: 600;
                transition: all 0.3s ease;
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
            }
            .btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            .result { 
                background: white; 
                padding: 25px; 
                margin: 15px 0; 
                border-radius: 12px; 
                border-left: 4px solid #667eea;
                box-shadow: 0 3px 12px rgba(0,0,0,0.1);
                transition: transform 0.2s ease;
            }
            .result:hover {
                transform: translateY(-1px);
            }
            .error { 
                border-left-color: #e74c3c; 
                background: #fdf2f2;
            }
            .loading {
                display: none;
                text-align: center;
                padding: 20px;
            }
            .spinner {
                border: 3px solid #f3f3f3;
                border-top: 3px solid #667eea;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                animation: spin 1s linear infinite;
                margin: 0 auto 10px;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            input[type="file"] {
                margin: 10px 0;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 8px;
                width: 100%;
                max-width: 400px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎯 Resume Parser Pro</h1>
            <p>Extract key information from resume files instantly</p>
        </div>
        
        <div class="upload-area">
            <h3>📄 Upload Resume Files</h3>
            <p>Supported formats: .txt, .pdf, .doc, .docx</p>
            <form id="uploadForm" enctype="multipart/form-data">
                <input type="file" id="fileInput" multiple accept=".txt,.pdf,.doc,.docx">
                <br><br>
                <button type="submit" class="btn" id="submitBtn">Parse Resumes</button>
            </form>
        </div>
        
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Processing your files...</p>
        </div>
        
        <div id="results"></div>
        
        <script>
            document.getElementById('uploadForm').onsubmit = async function(e) {
                e.preventDefault();
                
                const fileInput = document.getElementById('fileInput');
                const files = fileInput.files;
                const submitBtn = document.getElementById('submitBtn');
                const loading = document.getElementById('loading');
                const results = document.getElementById('results');
                
                if (files.length === 0) {
                    alert('Please select at least one file!');
                    return;
                }
                
                // Show loading state
                submitBtn.disabled = true;
                submitBtn.textContent = 'Processing...';
                loading.style.display = 'block';
                results.innerHTML = '';
                
                const formData = new FormData();
                for (let i = 0; i < files.length; i++) {
                    formData.append('files', files[i]);
                }
                
                try {
                    const response = await fetch('/parse', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        throw new Error(`Server error: ${response.status}`);
                    }
                    
                    const data = await response.json();
                    displayResults(data);
                } catch (error) {
                    console.error('Error:', error);
                    results.innerHTML = `
                        <div class="result error">
                            <h4>❌ Error</h4>
                            <p style="color: #e74c3c;">Failed to process files: ${error.message}</p>
                        </div>
                    `;
                } finally {
                    // Reset UI
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Parse Resumes';
                    loading.style.display = 'none';
                }
            };
            
            function displayResults(results) {
                let html = '<h3>📊 Parsing Results:</h3>';
                
                if (!results || results.length === 0) {
                    html += '<p>No results to display.</p>';
                } else {
                    results.forEach(result => {
                        if (result.success) {
                            html += `
                                <div class="result">
                                    <h4>✅ ${escapeHtml(result.filename)}</h4>
                                    <p><strong>👤 Name:</strong> ${escapeHtml(result.data.name)}</p>
                                    <p><strong>📧 Email:</strong> ${escapeHtml(result.data.email)}</p>
                                    <p><strong>📱 Phone:</strong> ${escapeHtml(result.data.phone)}</p>
                                    <p><strong>🛠️ Skills:</strong> ${result.data.skills.map(s => escapeHtml(s)).join(', ')}</p>
                                </div>
                            `;
                        } else {
                            html += `
                                <div class="result error">
                                    <h4>❌ ${escapeHtml(result.filename)}</h4>
                                    <p style="color: #e74c3c;">${escapeHtml(result.error)}</p>
                                </div>
                            `;
                        }
                    });
                }
                
                document.getElementById('results').innerHTML = html;
            }
            
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
        </script>
    </body>
    </html>
    ''')

@app.route('/health')
def health():
    """Health check endpoint for Railway"""
    logger.info("Health check accessed")
    return {'status': 'healthy', 'service': 'resume-parser'}, 200

@app.route('/parse', methods=['POST'])
def parse_resumes():
    """Parse uploaded resume files"""
    try:
        logger.info("Parse endpoint accessed")
        
        if 'files' not in request.files:
            logger.warning("No files in request")
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            logger.warning("Empty file list")
            return jsonify({'error': 'No files selected'}), 400
        
        results = []
        logger.info(f"Processing {len(files)} files")
        
        for file in files:
            try:
                if not file or file.filename == '':
                    continue
                    
                logger.info(f"Processing file: {file.filename}")
                
                # Read file content with format-specific handling
                content = ''
                file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
                
                try:
                    if file_ext == 'docx':
                        content = extract_docx_text(file)
                    elif file_ext == 'pdf':
                        content = extract_pdf_text(file)
                    else:
                        # Handle text files - KEEP ORIGINAL LOGIC
                        try:
                            content = file.read().decode('utf-8')
                        except UnicodeDecodeError:
                            file.seek(0)
                            try:
                                content = file.read().decode('latin-1')
                            except UnicodeDecodeError:
                                file.seek(0)
                                content = file.read().decode('utf-8', errors='ignore')
                except Exception as e:
                    logger.warning(f"File reading error for {file.filename}: {str(e)}")
                    file.seek(0)
                    content = file.read().decode('utf-8', errors='ignore')
                
                if not content.strip():
                    raise ValueError("File appears to be empty or unreadable")
                
                # KEEP ORIGINAL PARSING LOGIC
                parsed_data = parse_resume_content(content)
                
                results.append({
                    'filename': file.filename,
                    'success': True,
                    'data': parsed_data
                })
                
                logger.info(f"Successfully processed: {file.filename}")
                
            except Exception as e:
                logger.error(f"Error processing {file.filename}: {str(e)}")
                results.append({
                    'filename': file.filename if file else 'unknown',
                    'success': False,
                    'error': f"Processing error: {str(e)}"
                })
        
        logger.info(f"Completed processing. {len([r for r in results if r['success']])} successful, {len([r for r in results if not r['success']])} failed")
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Parse endpoint error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

def extract_pdf_text(file):
    """Extract text from PDF file"""
    try:
        if not PyPDF2:
            # Fallback to binary reading if PyPDF2 not available
            file.seek(0)
            raw_content = file.read()
            return raw_content.decode('utf-8', errors='ignore')
            
        file.seek(0)
        
        # Use PyPDF2 to extract text
        pdf_reader = PyPDF2.PdfReader(file)
        text_content = []
        
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_content.append(page_text)
        
        return '\n'.join(text_content)
                
    except Exception as e:
        logger.warning(f"PDF extraction failed: {str(e)}")
        # Fallback to treating as binary
        file.seek(0)
        raw_content = file.read()
        return raw_content.decode('utf-8', errors='ignore')

def extract_docx_text(file):
    """Extract text from DOCX file - MINIMAL ADDITION ONLY"""
    try:
        if not zipfile:
            # Fallback to binary reading if zipfile not available
            file.seek(0)
            raw_content = file.read()
            return raw_content.decode('utf-8', errors='ignore')
            
        file.seek(0)
        file_content = file.read()
        
        # DOCX files are ZIP archives
        with zipfile.ZipFile(io.BytesIO(file_content), 'r') as zip_file:
            # Extract the main document XML
            xml_content = zip_file.read('word/document.xml')
            
            # Simple regex extraction - avoid complex XML parsing
            import re
            text_pattern = r'<w:t[^>]*>(.*?)</w:t>'
            matches = re.findall(text_pattern, xml_content.decode('utf-8'), re.DOTALL)
            return ' '.join(matches)
                
    except Exception as e:
        logger.warning(f"DOCX extraction failed: {str(e)}")
        # Fallback to treating as binary
        file.seek(0)
        raw_content = file.read()
        return raw_content.decode('utf-8', errors='ignore')

def parse_resume_content(content):
    """Enhanced parsing function with better regex and logic"""
    
    # Clean content more thoroughly
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    # Remove extra whitespace and clean up
    content = ' '.join(content.split())
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    content_lower = content.lower()
    
    # Enhanced email extraction with more patterns
    email_patterns = [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
        r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        r'Email\s*:?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        r'E-mail\s*:?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    ]
    
    email = 'Not found'
    for pattern in email_patterns:
        email_match = re.search(pattern, content, re.IGNORECASE)
        if email_match:
            # Get the email from group 1 if it exists, otherwise group 0
            email = email_match.group(1) if email_match.groups() else email_match.group(0)
            break
    
    # Enhanced phone extraction with Indian formats
    phone_patterns = [
        # Indian formats
        r'\+91[-.\s]?\d{10}',  # +91-9876543210 or +91 9876543210
        r'\+91[-.\s]?\d{5}[-.\s]?\d{5}',  # +91-98765-43210
        r'91[-.\s]?\d{10}',  # 91-9876543210
        r'\b[6-9]\d{9}\b',  # 9876543210 (Indian mobile starts with 6,7,8,9)
        r'\b[6-9]\d{4}[-.\s]?\d{5}\b',  # 98765-43210
        r'\([+]?91\)[-.\s]?\d{10}',  # (+91) 9876543210
        # International formats
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # US format
        r'\(\d{3}\)\s?\d{3}[-.\s]?\d{4}',  # (123) 456-7890
        r'\+\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
        r'\b\d{10}\b',
        # Labeled patterns
        r'Phone\s*:?\s*([+\d\s\-\(\)\.]{10,})',
        r'Mobile\s*:?\s*([+\d\s\-\(\)\.]{10,})',
        r'Tel\s*:?\s*([+\d\s\-\(\)\.]{10,})',
        r'Contact\s*:?\s*([+\d\s\-\(\)\.]{10,})',
        # Flexible patterns
        r'\+?\d{1,3}?[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
        r'\d{3}\s\d{3}\s\d{4}'
    ]
    
    phone = 'Not found'
    for pattern in phone_patterns:
        phone_match = re.search(pattern, content, re.IGNORECASE)
        if phone_match:
            # Get the phone from group 1 if it exists, otherwise group 0
            phone_raw = phone_match.group(1) if phone_match.groups() else phone_match.group(0)
            # Clean phone number (remove labels like "Phone:")
            phone_clean = re.sub(r'[^\d\+\-\(\)\.\s]', '', phone_raw)
            if len(re.sub(r'\D', '', phone_clean)) >= 10:  # At least 10 digits
                phone = phone_clean.strip()
                break
    
    # Extract skills with better matching
    skill_keywords = [
        'python', 'javascript', 'java', 'react', 'node', 'nodejs', 'sql', 'html', 'css',
        'angular', 'vue', 'django', 'flask', 'spring', 'mongodb', 'postgresql', 'mysql',
        'aws', 'azure', 'docker', 'kubernetes', 'git', 'linux', 'windows', 'macos',
        'php', 'ruby', 'go', 'rust', 'c++', 'c#', 'swift', 'kotlin', 'typescript',
        'bootstrap', 'tailwind', 'sass', 'less', 'webpack', 'babel', 'npm', 'yarn',
        'redux', 'graphql', 'rest', 'api', 'microservices', 'devops', 'ci/cd',
        'machine learning', 'ai', 'data science', 'pandas', 'numpy', 'tensorflow',
        'pytorch', 'scikit-learn', 'jupyter', 'tableau', 'power bi', 'excel',
        # VLSI & Hardware Design
        'vlsi', 'verilog', 'vhdl', 'systemverilog', 'fpga', 'asic', 'rtl', 'synthesis',
        'place and route', 'dft', 'sta', 'timing analysis', 'power analysis', 'spice',
        'cadence', 'synopsys', 'mentor graphics', 'xilinx', 'altera', 'intel fpga',
        'vivado', 'quartus', 'modelsim', 'questasim', 'ncverilog', 'vcs',
        'design compiler', 'primetime', 'icc', 'encounter', 'innovus',
        # Embedded Systems
        'embedded', 'microcontroller', 'microprocessor', 'arm', 'cortex', 'risc-v',
        'arduino', 'raspberry pi', 'stm32', 'pic', 'avr', 'esp32', 'esp8266',
        'rtos', 'freertos', 'embedded c', 'embedded linux', 'bootloader',
        'i2c', 'spi', 'uart', 'can', 'usb', 'ethernet', 'wifi', 'bluetooth',
        'pwm', 'adc', 'dac', 'gpio', 'interrupt', 'dma', 'timer',
        'iot', 'sensor', 'actuator', 'pcb', 'schematic', 'altium', 'kicad',
        'eagle', 'proteus', 'multisim', 'ltspice', 'pspice'
    ]
    
    skills = []
    # Use word boundaries for better matching
    for skill in skill_keywords:
        skill_lower = skill.lower()
        # For single words, use word boundaries
        if ' ' not in skill_lower:
            if re.search(r'\b' + re.escape(skill_lower) + r'\b', content_lower):
                skills.append(skill.title())
        else:
            # For phrases, simple contains check
            if skill_lower in content_lower:
                skills.append(skill.title())
    
    # Remove duplicates and sort
    skills = sorted(list(set(skills)))
    
    # Extract name with enhanced logic
    name = extract_name_from_content(lines, content)
    
    return {
        'name': name,
        'email': email,
        'phone': phone,
        'skills': skills if skills else ['Not specified']
    }

def extract_name_from_content(lines, content):
    """Enhanced name extraction with better patterns"""
    
    # Skip common header words
    skip_words = {
        'resume', 'cv', 'curriculum', 'vitae', 'profile', 'summary', 'objective',
        'experience', 'education', 'skills', 'contact', 'information', 'personal',
        'details', 'phone', 'email', 'mobile', 'address', 'linkedin', 'github'
    }
    
    # First try to find name patterns in the content
    name_patterns = [
        # Look for "Name:" or "Full Name:" labels
        r'(?:Name|Full Name)\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]*\.?)*\s+[A-Z][a-z]+)',
        # Standard name patterns at line start
        r'^([A-Z][a-z]{1,15}(?:\s+[A-Z][a-z]*\.?)*\s+[A-Z][a-z]{1,15})

@app.errorhandler(413)
def too_large(e):
    logger.warning("File too large uploaded")
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug),
        # Name with middle initial
        r'^([A-Z][a-z]{1,15}\s+[A-Z]\.\s+[A-Z][a-z]{1,15})

@app.errorhandler(413)
def too_large(e):
    logger.warning("File too large uploaded")
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug),
        # Three part names
        r'^([A-Z][a-z]{1,15}\s+[A-Z][a-z]{1,15}\s+[A-Z][a-z]{1,15})

@app.errorhandler(413)
def too_large(e):
    logger.warning("File too large uploaded")
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
    ]
    
    # Search in the full content first for labeled names
    for pattern in name_patterns[:1]:  # Only the labeled pattern
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        if match:
            potential_name = match.group(1).strip()
            if validate_name(potential_name):
                return potential_name
    
    # Then search line by line for names at the beginning
    for i, line in enumerate(lines[:20]):  # Check first 20 lines
        line_clean = line.strip()
        
        # Skip very short or very long lines
        if len(line_clean) < 3 or len(line_clean) > 80:
            continue
            
        # Skip lines with common resume headers
        if any(word in line_clean.lower() for word in skip_words):
            continue
            
        # Skip lines with @ or many numbers or special chars
        if '@' in line_clean or re.search(r'\d{3,}', line_clean) or line_clean.count('.') > 2:
            continue
        
        # Skip lines that are mostly uppercase (likely headers)
        if line_clean.isupper() and len(line_clean) > 8:
            continue
            
        # Try name patterns on this line
        for pattern in name_patterns[1:]:  # Skip the labeled pattern
            match = re.match(pattern, line_clean)
            if match:
                potential_name = match.group(1).strip()
                if validate_name(potential_name):
                    return potential_name
    
    # Last resort: look for any two capitalized words together
    capitalized_words = re.findall(r'\b[A-Z][a-z]{2,15}\b', content)
    if len(capitalized_words) >= 2:
        for i in range(len(capitalized_words) - 1):
            potential_name = f"{capitalized_words[i]} {capitalized_words[i+1]}"
            if validate_name(potential_name):
                # Check it's not a common phrase
                name_lower = potential_name.lower()
                if not any(skip in name_lower for skip in skip_words):
                    return potential_name
    
    return 'Not found'

def validate_name(name):
    """Enhanced name validation"""
    if not name or len(name.split()) < 2:
        return False
        
    parts = name.split()
    
    # Should have 2-4 parts
    if len(parts) < 2 or len(parts) > 4:
        return False
    
    # Check each part
    for part in parts:
        # Should be reasonable length
        if len(part) < 2 or len(part) > 20:
            return False
        # Should start with capital
        if not part[0].isupper():
            return False
        # Should be mostly letters (allow . for middle initials)
        if not re.match(r'^[A-Za-z\.\']+

@app.errorhandler(413)
def too_large(e):
    logger.warning("File too large uploaded")
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug), part):
            return False
        # Avoid common non-name words
        if part.lower() in ['resume', 'email', 'phone', 'contact', 'address', 'skills']:
            return False
    
    return True

@app.errorhandler(413)
def too_large(e):
    logger.warning("File too large uploaded")
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
