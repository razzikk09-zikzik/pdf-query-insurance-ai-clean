import os
import logging
import json
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from datetime import datetime
import pdfplumber
import glob

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = "dev_key"

# Global variables
policy_documents = {}
search_history = []

def extract_all_pdf_texts():
    global policy_documents
    policy_documents = {}

    pdf_files = glob.glob("*.pdf")

    for pdf_path in pdf_files:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

                policy_name = pdf_path.replace('.pdf', '').replace('_', ' ').title()
                policy_documents[policy_name] = {
                    'filename': pdf_path,
                    'content': text,
                    'length': len(text)
                }
        except Exception as e:
            logging.error(f"Error reading {pdf_path}: {e}")

def add_to_search_history(claim_description, selected_policy, result):
    history_entry = {
        'id': len(search_history) + 1,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'claim_description': claim_description[:100] + '...' if len(claim_description) > 100 else claim_description,
        'full_claim_description': claim_description,
        'selected_policy': selected_policy,
        'decision': result['decision'],
        'amount': result['amount'],
        'justification': result['justification'][:200] + '...' if len(result['justification']) > 200 else result['justification'],
        'full_justification': result['justification']
    }
    search_history.append(history_entry)
    if len(search_history) > 50:
        search_history = search_history[-50:]

def get_all_policies_text():
    combined_text = ""
    for policy_name, policy_data in policy_documents.items():
        combined_text += f"\n\n=== {policy_name.upper()} POLICY ===\n"
        combined_text += policy_data['content']
        combined_text += f"\n=== END OF {policy_name.upper()} POLICY ===\n"
    return combined_text

def analyze_insurance_claim(claim_description, selected_policy=None):
    if not policy_documents:
        return {
            "decision": "Rejected",
            "amount": "N/A",
            "justification": "No policy documents available."
        }

    if selected_policy and selected_policy in policy_documents:
        policy_text = policy_documents[selected_policy]['content']
    else:
        policy_text = get_all_policies_text()

    if not claim_description.strip():
        return {
            "decision": "Rejected",
            "amount": "N/A",
            "justification": "No claim description provided."
        }

    # MOCKED RESULT (since no OpenAI integration)
    return {
        "decision": "Approved" if "surgery" in claim_description.lower() else "Rejected",
        "amount": "$5000" if "surgery" in claim_description.lower() else "N/A",
        "justification": "Mocked analysis. Add OpenAI integration for real analysis."
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    claim_description = ""
    selected_policy = ""

    if request.method == 'POST':
        claim_description = request.form.get('claim_description', '').strip()
        selected_policy = request.form.get('selected_policy', '').strip()

        if claim_description:
            analysis_result = analyze_insurance_claim(claim_description, selected_policy if selected_policy != 'all' else None)
            result = {
                'decision': analysis_result['decision'],
                'amount': analysis_result['amount'],
                'justification': analysis_result['justification'],
                'claim_description': claim_description,
                'selected_policy': selected_policy
            }
            add_to_search_history(claim_description, selected_policy, analysis_result)
        else:
            result = {
                'decision': 'Rejected',
                'amount': 'N/A',
                'justification': "Please provide a claim description."
            }

    return render_template('index.html', 
                           result=result,
                           claim_description=claim_description,
                           selected_policy=selected_policy,
                           available_policies=list(policy_documents.keys()),
                           search_history=list(reversed(search_history[-10:])))

@app.route('/history')
def view_history():
    return render_template('history.html', 
                           search_history=list(reversed(search_history)),
                           available_policies=list(policy_documents.keys()))

@app.route('/api/history')
def api_history():
    return jsonify(list(reversed(search_history)))

@app.route('/api/history/<int:history_id>')
def api_history_detail(history_id):
    for item in search_history:
        if item['id'] == history_id:
            return jsonify(item)
    return jsonify({'error': 'History item not found'}), 404

@app.route('/api/clear_history', methods=['POST'])
def clear_history():
    global search_history
    search_history = []
    return jsonify({'status': 'success', 'message': 'Search history cleared'})

with app.app_context():
    extract_all_pdf_texts()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
