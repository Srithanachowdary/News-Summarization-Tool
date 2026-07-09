import streamlit as st
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
from newspaper import Article
import nltk
from io import StringIO
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract
import pdfplumber

# Custom CSS for green gradient background and font styling
def set_custom_style():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Poppins', sans-serif;
        }
        
        .stApp {
            background: linear-gradient(135deg, #74ebd5,#acb6e5);
            color: #333333;
        }
        
        .stTextInput>div>div>input, 
        .stTextArea>div>div>textarea, 
        .stFileUploader>div>div {
            background-color: rgba(255, 255, 255, 0.9);
            border-radius: 10px;
        }
        
        .stButton>button {
            background-color: #2e8b57;
            color: white;
            border-radius: 10px;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: 600;
        }
        
        .stButton>button:hover {
            background-color: #3cb371;
            color: white;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background-color: rgba(255, 255, 255, 0.7);
            border-radius: 10px 10px 0 0;
            padding: 10px 20px;
            font-weight: 600;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: rgba(255, 255, 255, 0.9);
            color: #2e8b57;
        }
        
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            color: #2e8b57;
        }
        
        .css-1aumxhk {
            background-color: rgba(255, 255, 255, 0.9);
            border-radius: 10px;
            padding: 20px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class NewsSummarizer:
    def __init__(self):

        self.t5_tokenizer = AutoTokenizer.from_pretrained('t5-base')
        self.t5_model = AutoModelForSeq2SeqLM.from_pretrained('t5-base')
        self.bert_summarizer = pipeline('summarization', model='facebook/bart-large-cnn')
        
    def extract_article(self, url):
        """Extract article from URL using newspaper3k"""
        article = Article(url)
        try:
            article.download()
            article.parse()
            article.nlp()
            return article.text
        except Exception as e:
            st.error(f"Error extracting article: {e}")
            return None

    def summarize_with_t5(self, text):
        """Summarize text using T5 model"""
        inputs = self.t5_tokenizer.encode("summarize: " + text, return_tensors="pt", max_length=1000, truncation=True)
        outputs = self.t5_model.generate(inputs, max_length=1000, min_length=40, length_penalty=2.0, num_beams=4, early_stopping=True)
        return self.t5_tokenizer.decode(outputs[0], skip_special_tokens=True)

    def summarize_with_bert(self, text):
        """Summarize text using BERT model"""
        return self.bert_summarizer(text, max_length=130, min_length=30, do_sample=False)[0]['summary_text']

def display_summaries(text):
    """Display summaries for the given text"""
    if text:
        summarizer = NewsSummarizer()
        
        st.subheader("Original Content")
        st.write(text[:2000] + "..." if len(text) > 2000 else text)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("T5 Summary")
            t5_summary = summarizer.summarize_with_t5(text)
            st.markdown(f'<div style="background-color: rgba(255, 255, 255, 0.8); padding: 15px; border-radius: 10px;">{t5_summary}</div>', unsafe_allow_html=True)
        
        with col2:
            st.subheader("BERT Summary")
            bert_summary = summarizer.summarize_with_bert(text)
            st.markdown(f'<div style="background-color: rgba(255, 255, 255, 0.8); padding: 15px; border-radius: 10px;">{bert_summary}</div>', unsafe_allow_html=True)

def extract_text_from_pdf(uploaded_file):
    """Extract text from PDF using OCR if needed"""
    text = ""
    
    try:
        
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        
        if not text.strip():
            st.warning("No text found in PDF. Attempting OCR...")
            images = convert_from_bytes(uploaded_file.read())
            for img in images:
                text += pytesseract.image_to_string(img) + "\n"
                
    except Exception as e:
        st.error(f"PDF processing failed: {e}")
    
    return text


def main():
    set_custom_style()  # Apply custom styling
    
    st.title(" NEWS SUMMARIZER")
    st.markdown("Summarize content from URL, text input, or document upload using AI models")
    
    
    tab1, tab2, tab3 = st.tabs(["🌐 URL", "📝 Text Input", "📄 Document Upload"])
    
    with tab1:
        st.header("Summarize from URL")
        url = st.text_input("Enter URL:", key="url_input", placeholder="https://example.com/news-article")
        if st.button("Summarize URL", key="url_button"):
            if url:
                summarizer = NewsSummarizer()
                article_text = summarizer.extract_article(url)
                if article_text:
                    display_summaries(article_text)
            else:
                st.error("Please enter a valid URL.")
    
    with tab2:
        st.header("Summarize from Text")
        text_input = st.text_area("Enter text to summarize:", height=200, key="text_input", placeholder="Paste your text here...")
        if st.button("Summarize Text", key="text_button"):
            if text_input.strip():
                display_summaries(text_input)
            else:
                st.error("Please enter some text to summarize.")
    
    with tab3:
        st.header("Summarize from Document")
        uploaded_file = st.file_uploader("Choose a file", type=['txt', 'pdf', 'docx'], key="file_uploader")
        if st.button("Summarize Document", key="doc_button"):
            if uploaded_file is not None:
                try:
                    if uploaded_file.type == "text/plain":
                        text = uploaded_file.read().decode("utf-8")
                    elif uploaded_file.type == "application/pdf":
                        text = extract_text_from_pdf(uploaded_file)
                    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                        import docx
                        doc = docx.Document(uploaded_file)
                        text = "\n".join([para.text for para in doc.paragraphs])
                    
                    if text.strip():
                        display_summaries(text)
                    else:
                        st.error("The document is empty or could not be read.")
                except Exception as e:
                    st.error(f"Error processing document: {str(e)}")
            else:
                st.error("Please upload a document first.")

if __name__ == "__main__":
    main()