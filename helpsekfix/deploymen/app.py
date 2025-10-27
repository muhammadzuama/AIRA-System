from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from langchain.schema import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains import RetrievalQA
from langchain.output_parsers import StructuredOutputParser, ResponseSchema

# --- Konfigurasi ---
FAISS_INDEX_PATH = "/Users/muhammadzuamaalamin/Documents/risetmandiir/project/AIRA/helpsekfix/model/faiss_index123"
EMBEDDING_MODEL_PATH = "/Users/muhammadzuamaalamin/Documents/fintunellm/model/multilingual-e5-large-instruct"
# GOOGLE_API_KEY = os.getenv("AIzaSyCiT8Z6lhmKfaxnZSSYlN0zygTD-yOow84")  # ⚠️ Simpan di environment variable!

# if not GOOGLE_API_KEY:
#     raise ValueError("Setel environment variable GOOGLE_API_KEY terlebih dahulu.")

# --- Inisialisasi Flask ---
app = Flask(__name__)
CORS(app)  # Izinkan semua origin (untuk dev). Untuk production, batasi origin!

# --- Load Embedding & Vector DB ---
print("Loading embedding model...")
embeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL_PATH,
    model_kwargs={"device": "cpu"}
)

print("Loading FAISS index...")
vectorstore = FAISS.load_local(
    FAISS_INDEX_PATH,
    embeddings,
    allow_dangerous_deserialization=True
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# --- Setup LLM & Chain ---
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key="Axxxxxxxxxxx",
    temperature=0.2
)

# Output parser
schemas = [
    ResponseSchema(
        name="jawaban",
        description="Jawaban lengkap dalam bahasa Indonesia yang mudah dipahami."
    )
]
output_parser = StructuredOutputParser.from_response_schemas(schemas)
format_instructions = output_parser.get_format_instructions()

# Prompt
prompt = ChatPromptTemplate.from_template("""
Kamu adalah asisten resmi Badan Kepegawaian Negara (BKN) yang membantu masyarakat memahami informasi tentang CPNS, PPPK, formasi, kualifikasi pendidikan, dan proses rekrutmen ASN.

### Aturan Penting:
1. **Jawab langsung ke inti**, jangan bertele-tele.
2. **Hanya gunakan informasi dari konteks yang diberikan**. Jangan mengarang, menebak, atau menambah data.
3. **Sesuaikan jawaban dengan jenjang pendidikan pelamar**:
   - Lulusan S1 hanya boleh direkomendasikan ke formasi yang mensyaratkan **S1**.
   - Lulusan S2 hanya untuk formasi **S2**.
   - Lulusan S3 hanya untuk formasi **S3**.
   - Jika disebut “S1 semua jurusan”, artinya semua lulusan S1 boleh mendaftar — tapi tetap **tidak boleh direkomendasikan ke formasi S2/S3**.

### Cara Menjawab Berdasarkan Jenis Pertanyaan:
- **Jika tanya tentang FORMASI**:
  Sebutkan:  
  → Jabatan  
  → Instansi  
  → Jumlah kebutuhan  
  → Kualifikasi pendidikan **yang relevan dengan pertanyaan saja** (jangan tampilkan semua kualifikasi jika tidak diminta)  
  → Kisaran gaji (jika ada di konteks)

- **Jika tanya tentang PENEMPATAN (misal: di Jakarta, Banten, dll)**:
  Sebutkan:  
  → Jabatan  
  → Instansi  
  → Jumlah kebutuhan  
  → Kualifikasi pendidikan yang dibutuhkan

- **Jika tanya tentang KONSEP (misal: “Apa itu CPNS?”)**:
  Beri penjelasan **sederhana dalam bahasa Indonesia** yang mudah dipahami.

### Jika Ada Banyak Formasi:
- Tampilkan **semua formasi yang sesuai**.
- Setiap formasi ditulis **dalam satu baris terpisah**.
- Urutkan berdasarkan:  
  (1) Jumlah kebutuhan → dari **tertinggi ke terendah**  
  (2) Jika sama, urutkan berdasarkan **kisaran gaji tertinggi dulu**

### Jika Tidak Ada Informasi di Konteks:
- Untuk topik **CPNS/PPPK/ASN**:  
  → "Maaf, saya tidak tahu jawaban pastinya berdasarkan dokumen yang tersedia."
- Untuk topik **di luar rekrutmen ASN**:  
  → "Maaf, saya tidak tahu. Saya hanya bisa menjawab pertanyaan seputar formasi CPNS, kualifikasi pendidikan, dan informasi rekrutmen ASN berdasarkan dokumen resmi."

### Akhiri Selalu Dengan:
→ "Untuk informasi lebih lengkap dan terkini, silakan kunjungi https://sscasn.bkn.go.id"

---

Pertanyaan pengguna: {question}  
Konteks tambahan dari dokumen:  
{context}  
{format_instructions}
""")

# Chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type_kwargs={"prompt": prompt.partial(format_instructions=format_instructions)},
    return_source_documents=False
)

# --- Endpoint API ---
@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json()
        if not data or "question" not in data:
            return jsonify({"error": "Field 'question' diperlukan."}), 400

        question = data["question"].strip()
        if not question:
            return jsonify({"error": "Pertanyaan tidak boleh kosong."}), 400

        # Jalankan RAG
        response = qa_chain.invoke({"query": question})
        raw_answer = response["result"]

        # Parse output
        parsed = output_parser.parse(raw_answer)
        jawaban = parsed.get("jawaban", "Maaf, saya tidak dapat memberikan jawaban.")

        return jsonify({
            "status": "success",
            "question": question,
            "answer": jawaban
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# --- Health check ---
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "OK", "service": "BKN RAG API"})

# --- Info kontak BKN (dari knowledge base) ---
@app.route("/contact", methods=["GET"])
def contact():
    return jsonify({
        "phone": ["021-8093008", "021-80882815 (Humas BKN)"],
        "email": "helpdesk.casn@bkn.go.id",
        "address": "Jl. Mayjen Sutoyo No.12, RT.9/RW.9 Cililitan, Kec. Kramat jati Kota Jakarta Timur 13640"
    })

# --- Jalankan server ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)