from flask import Flask, render_template, request, jsonify
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)

# PubMed API URLs
PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

def search_pubmed(query):
    """Searches PubMed for research papers based on the query and retrieves paper summaries."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": 10,  # Limit the results to 10 papers
        "retmode": "xml"
    }
    response = requests.get(PUBMED_SEARCH_URL, params=params)
    
    # Parse XML response to get list of IDs
    root = ET.fromstring(response.content)
    ids = [id_elem.text for id_elem in root.findall(".//Id")]
    
    if not ids:
        return []
    
    # Fetch summary information for each paper ID
    summary_params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "xml"
    }
    summary_response = requests.get(PUBMED_SUMMARY_URL, params=summary_params)
    summary_root = ET.fromstring(summary_response.content)
    
    papers = []
    for docsum in summary_root.findall("DocSum"):
        paper_id = docsum.find("Id").text
        title = docsum.find("Item[@Name='Title']").text
        source = docsum.find("Item[@Name='Source']").text
        
        # Fetch abstract and summary using PubMed efetch
        fetch_params = {
            "db": "pubmed",
            "id": paper_id,
            "retmode": "xml"
        }
        fetch_response = requests.get(PUBMED_FETCH_URL, params=fetch_params)
        fetch_root = ET.fromstring(fetch_response.content)
        
        # Check if AbstractText is available
        abstract_element = fetch_root.find(".//Abstract/AbstractText")
        abstract = abstract_element.text if abstract_element is not None else "No abstract available."
        
        link = f"https://pubmed.ncbi.nlm.nih.gov/{paper_id}/"
        
        papers.append({
            "title": title,
            "summary": abstract,
            "link": link,
            "source": source
        })
    
    return papers

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.form['query']
    papers = search_pubmed(query)
    
    if papers:
        return jsonify(papers)
    else:
        return jsonify({"error": "No research papers found for your query."})

if __name__ == "__main__":
    app.run(debug=True)
