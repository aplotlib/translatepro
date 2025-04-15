import streamlit as st
import PyPDF2
import docx
import tempfile
import os
from pathlib import Path
import time
import base64
from io import BytesIO
import requests

st.set_page_config(
    page_title="Document Translator",
    page_icon="🌐",
    layout="wide"
)

# Use LibreTranslate API (self-hosted or public instances)
LIBRE_TRANSLATE_INSTANCES = [
    "https://translate.argosopentech.com",  # Public instance
    "https://libretranslate.de",            # Public instance
    "https://translate.terraprint.co"       # Public instance
]

def translate_text_libre(text, source_lang, target_lang="en"):
    """Translate text using LibreTranslate API"""
    
    # Convert language codes
    lang_map = {
        "Spanish": "es",
        "Chinese (Mandarin)": "zh"
    }
    
    source = lang_map.get(source_lang, "auto")
    
    # Split text into chunks of about 1000 characters to avoid request limits
    chunks = []
    for i in range(0, len(text), 1000):
        chunks.append(text[i:i+1000])
    
    translated_chunks = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Try different instances if one fails
    instance_index = 0
    current_instance = LIBRE_TRANSLATE_INSTANCES[instance_index]
    
    for i, chunk in enumerate(chunks):
        status_text.text(f"Translating chunk {i+1}/{len(chunks)}")
        
        # Skip empty chunks
        if not chunk.strip():
            translated_chunks.append("")
            progress_bar.progress((i + 1) / len(chunks))
            continue
        
        # Try to translate with current instance
        max_retries = 3
        for retry in range(max_retries):
            try:
                payload = {
                    "q": chunk,
                    "source": source,
                    "target": target_lang,
                    "format": "text"
                }
                
                headers = {"Content-Type": "application/json"}
                
                response = requests.post(
                    f"{current_instance}/translate",
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    translated_chunks.append(result.get("translatedText", ""))
                    break
                else:
                    # If this instance fails, try another one
                    instance_index = (instance_index + 1) % len(LIBRE_TRANSLATE_INSTANCES)
                    current_instance = LIBRE_TRANSLATE_INSTANCES[instance_index]
                    st.warning(f"Switching to alternative translation server... ({retry+1}/{max_retries})")
                    time.sleep(1)  # Wait a bit before retrying
                    
            except Exception as e:
                # If request fails, try another instance
                instance_index = (instance_index + 1) % len(LIBRE_TRANSLATE_INSTANCES)
                current_instance = LIBRE_TRANSLATE_INSTANCES[instance_index]
                st.warning(f"Switching to alternative translation server... ({retry+1}/{max_retries})")
                time.sleep(1)  # Wait a bit before retrying
        
        # Update progress
        progress_bar.progress((i + 1) / len(chunks))
    
    status_text.text("Translation complete!")
    return '\n'.join(translated_chunks)

# Functions to handle different file formats
def extract_text_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    total_pages = len(pdf_reader.pages)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, page in enumerate(pdf_reader.pages):
        status_text.text(f"Extracting text from page {i+1}/{total_pages}")
        text += page.extract_text() + "\n\n"
        progress_bar.progress((i + 1) / total_pages)
    
    status_text.text("Text extraction complete!")
    return text

def extract_text_from_docx(file):
    doc = docx.Document(file)
    text = ""
    total_paragraphs = len(doc.paragraphs)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, para in enumerate(doc.paragraphs):
        status_text.text(f"Extracting text from paragraph {i+1}/{total_paragraphs}")
        text += para.text + "\n"
        progress_bar.progress((i + 1) / total_paragraphs)
    
    status_text.text("Text extraction complete!")
    return text

def extract_text_from_txt(file):
    return file.read().decode('utf-8')

def save_docx(translated_text):
    doc = docx.Document()
    for para in translated_text.split('\n'):
        if para.strip():
            doc.add_paragraph(para)
    
    # Save to BytesIO object
    docx_bytes = BytesIO()
    doc.save(docx_bytes)
    docx_bytes.seek(0)
    
    return docx_bytes

# Main UI
st.title("🌐 Document Translator")
st.subheader("Translate documents from Spanish and Mandarin to English")

# Sidebar
st.sidebar.title("Settings")
source_language = st.sidebar.radio("Source Language", ["Spanish", "Chinese (Mandarin)"])
output_format = st.sidebar.radio("Output Format", ["Text", "Word Document (.docx)"])

# File uploader
uploaded_file = st.file_uploader("Upload your document (PDF, DOCX, or TXT)", 
                                type=["pdf", "docx", "txt"])

if uploaded_file is not None:
    st.info(f"File uploaded: {uploaded_file.name}")
    file_extension = Path(uploaded_file.name).suffix.lower()
    
    with st.spinner("Processing..."):
        # Extract text based on file type
        if file_extension == ".pdf":
            text = extract_text_from_pdf(uploaded_file)
        elif file_extension == ".docx":
            text = extract_text_from_docx(uploaded_file)
        elif file_extension == ".txt":
            text = extract_text_from_txt(uploaded_file)
        else:
            st.error("Unsupported file format. Please upload a PDF, DOCX, or TXT file.")
            st.stop()
        
        # Display extracted text
        st.subheader("Extracted Text")
        with st.expander("Show original text"):
            st.text_area("Original", text, height=200)
        
        # Translate button
        if st.button("Translate Document"):
            with st.spinner("Translating... This may take several minutes for large documents"):
                start_time = time.time()
                translated_text = translate_text_libre(text, source_language)
                end_time = time.time()
                
                st.success(f"Translation completed in {end_time - start_time:.2f} seconds!")
                
                # Display translated text
                st.subheader("Translated Text")
                st.text_area("Translation", translated_text, height=300)
                
                # Download options
                st.subheader("Download Options")
                
                if output_format == "Text":
                    # Text download
                    text_bytes = translated_text.encode()
                    st.download_button(
                        label="Download as Text",
                        data=text_bytes,
                        file_name="translated_document.txt",
                        mime="text/plain"
                    )
                else:
                    # DOCX download
                    docx_bytes = save_docx(translated_text)
                    st.download_button(
                        label="Download as Word Document",
                        data=docx_bytes,
                        file_name="translated_document.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

# Instructions and information
with st.expander("How to use this app"):
    st.markdown("""
    1. Select the source language (Spanish or Chinese) from the sidebar
    2. Choose your preferred output format
    3. Upload your document (PDF, DOCX, or TXT format)
    4. Click "Translate Document"
    5. Review the translated text
    6. Download the translation in your preferred format
    
    **Note:** Translation of large documents can take several minutes. The app processes text in chunks to handle documents of any size.
    """)

with st.expander("About this translator"):
    st.markdown("""
    This document translator uses free translation APIs to translate documents from Spanish and Chinese to English.
    It's designed to handle large documents (30+ pages) efficiently by splitting them into smaller chunks.
    
    **Features:**
    - Free translation
    - Support for PDF, DOCX, and TXT files
    - Word-for-word translation
    - No installation of ML models required
    - Download options for the translated text
    
    The translation quality depends on the APIs used and the complexity of the source text.
    """)

# Footer
st.markdown("---")
st.markdown("Using free LibreTranslate servers for translation")
