from flask import Flask, render_template, request, jsonify
from textblob import TextBlob
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)

# PubMed API URLs
PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

def calculate_rating(text):
    """Calculate a rating based on the sentiment polarity of the text."""
    polarity = TextBlob(text).sentiment.polarity
    # Map polarity (-1 to 1) to a 1 to 5 scale
    if polarity >= 0.6:
        return 5
    elif polarity >= 0.2:
        return 4
    elif polarity >= -0.2:
        return 3
    elif polarity >= -0.6:
        return 2
    else:
        return 1

def search_pubmed(query, count=10):
    """Searches PubMed for research papers based on the query and retrieves paper summaries."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": count,
        "retmode": "xml"
    }
    response = requests.get(PUBMED_SEARCH_URL, params=params)
    
    if response.status_code != 200:
        return []  # Handle API errors by returning an empty list

    root = ET.fromstring(response.content)
    ids = [id_elem.text for id_elem in root.findall(".//Id")]
    
    if not ids:
        return []
    
    summary_params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "xml"
    }
    summary_response = requests.get(PUBMED_SUMMARY_URL, params=summary_params)
    
    if summary_response.status_code != 200:
        return []  # Handle API errors by returning an empty list

    summary_root = ET.fromstring(summary_response.content)
    
    papers = []
    for docsum in summary_root.findall("DocSum"):
        paper_id = docsum.find("Id").text
        title = docsum.find("Item[@Name='Title']").text
        source = docsum.find("Item[@Name='Source']").text
        
        fetch_params = {
            "db": "pubmed",
            "id": paper_id,
            "retmode": "xml"
        }
        fetch_response = requests.get(PUBMED_FETCH_URL, params=fetch_params)
        
        if fetch_response.status_code != 200:
            continue  # Skip this paper if fetching fails
        
        fetch_root = ET.fromstring(fetch_response.content)
        
        abstract_element = fetch_root.find(".//Abstract/AbstractText")
        abstract = abstract_element.text if abstract_element is not None else "No abstract available."
        
        rating = calculate_rating(abstract)
        
        link = f"https://pubmed.ncbi.nlm.nih.gov/{paper_id}/"
        
        papers.append({
            "title": title,
            "summary": abstract,
            "link": link,
            "source": source,
            "rating": rating
        })
    
    return papers

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.form['query']
    count = int(request.form.get('count', 10))  # Default to 10 if not specified
    papers = search_pubmed(query, count)
    
    if papers:
        return jsonify(papers)
    else:
        return jsonify({"error": "No research papers found for your query."})

if __name__ == "__main__":
    app.run(debug=True)