# app.py
import os
import json
import traceback
from typing import List, Dict, Any

from flask import Flask, request, jsonify
from flask_cors import CORS

from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.chains import RetrievalQA
from langchain_google_genai import ChatGoogleGenerativeAI

# ---------------------------
# Config (sesuaikan path & model)
# ---------------------------
FORMASI_FILE = os.environ.get("FORMASI_JSON", "../data/datajurusan.json")
FAQ_FILE = os.environ.get("FAQ_JSON", "../data/Regulasi_Penerimaan_CPNS(AutoRecovered).json")

# FAISS index directories
FAISS_FORMASI_DIR = os.environ.get("FAISS_FORMASI_DIR", "../model/faiss_index_formasi")
FAISS_FAQ_DIR = os.environ.get("FAISS_FAQ_DIR", "../data/Regulasi_Penerimaan_CPNS(AutoRecovered).json")

# Embedding model path/name (lokal atau hub)
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "/Users/muhammadzuamaalamin/Documents/fintunellm/model/bge-m3")  # contoh: "/Users/.../bge-m3"
EMBEDDING_DEVICE = os.environ.get("EMBEDDING_DEVICE", "cpu")

# Google API
# GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", None)
GOOGLE_MODEL = os.environ.get("GOOGLE_MODEL", "gemini-2.5-flash")

# Retriever params
RETRIEVER_K = int(os.environ.get("RETRIEVER_K", "4"))

# ---------------------------
# Helper: Detect query type
# ---------------------------
def detect_query_type(query: str) -> str:
    q = (query or "").lower()
    formasi_keywords = ["formasi", "jabatan", "penempatan", "instansi", "gaji", "kualifikasi", "unit kerja", "lulusan", "kebutuhan"]
    faq_keywords = ["apa itu", "bagaimana", "aturan", "dasar hukum", "pppk", "cpns", "asn", "sscasn", "n h", "n i k", "n i k"]

    if any(kw in q for kw in formasi_keywords):
        return "formasi"
    if any(kw in q for kw in faq_keywords):
        return "faq"
    # fallback: prefer formasi for queries that mention positions/fields, else faq
    # heuristik sederhana:
    if len(q.split()) >= 4:
        return "formasi"
    return "faq"

# ---------------------------
# Build documents for indices
# ---------------------------
def load_formasi_docs(formasi_path: str) -> List[Document]:
    with open(formasi_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict):
        raw = [raw]
    docs = []
    for idx, item in enumerate(raw):
        # normalize keys tolerant to capitalization
        # (optional) you may want to normalize more fields as needed
        jabatan = item.get("jabatan") or item.get("Jabatan") or "Tidak disebutkan"
        instansi = item.get("instansi") or item.get("Instansi") or "Tidak disebutkan"
        penempatan = item.get("penempatan") or item.get("Penempatan") or "Tidak disebutkan"
        unit = item.get("unit_kerja") or item.get("Unit Kerja") or item.get("unit kerja") or ""
        jenis = item.get("jenis_formasi") or item.get("Jenis Formasi") or ""
        khusus_dis = item.get("khusus_disabilitas") or item.get("Khusus Disabilitas") or False
        penghasilan = item.get("penghasilan") or item.get("penghasilan_juta") or {}
        min_gaji = penghasilan.get("min") if isinstance(penghasilan, dict) else None
        max_gaji = penghasilan.get("max") if isinstance(penghasilan, dict) else None
        if min_gaji is None and isinstance(penghasilan, str):
            # try parse "7 - 11" style
            try:
                parts = [p.strip() for p in penghasilan.split("-")]
                if len(parts) == 2:
                    min_gaji = float(parts[0])
                    max_gaji = float(parts[1])
            except Exception:
                min_gaji = max_gaji = None
        jumlah = item.get("jumlah_kebutuhan") or item.get("Jumlah Kebutuhan") or 0
        pendidikan = item.get("kualifikasi_pendidikan") or item.get("Kualifikasi Pendidikan") or []
        if isinstance(pendidikan, str):
            pendidikan = [pendidikan]

        text_parts = [
            "[FORMASI ASN]",
            f"Jabatan: {jabatan}",
            f"Instansi: {instansi}",
            f"Unit Kerja: {unit}",
            f"Penempatan: {penempatan}",
            f"Jenis Formasi: {jenis}",
            f"{'Formasi khusus disabilitas' if khusus_dis else 'Bukan formasi khusus disabilitas'}",
            f"Gaji (juta): {min_gaji if min_gaji is not None else '-'} - {max_gaji if max_gaji is not None else '-'}",
            f"Jumlah Kebutuhan: {jumlah}",
            f"Kualifikasi Pendidikan: {', '.join(pendidikan) if pendidikan else '-'}"
        ]
        page_content = "\n".join(text_parts)
        metadata = {
            "tipe": "formasi",
            "jabatan": jabatan,
            "instansi": instansi,
            "penempatan": penempatan,
            "min_gaji": min_gaji,
            "max_gaji": max_gaji,
            "jumlah_kebutuhan": jumlah,
            "index": idx
        }
        docs.append(Document(page_content=page_content, metadata=metadata))
    return docs

def load_faq_docs(faq_path: str) -> List[Document]:
    with open(faq_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict):
        raw = [raw]
    docs = []
    for idx, item in enumerate(raw):
        q = item.get("Pertanyaan (FAQ)") or item.get("Pertanyaan") or item.get("question") or "Tidak disebutkan"
        a = item.get("Jawaban") or item.get("answer") or "-"
        regulasi = item.get("Regulasi yang Menjadi Dasar") or item.get("Regulasi") or "-"
        sumber = item.get("Sumber") or item.get("sumber") or "-"
        text = "[FAQ ASN]\n" + "\n".join([
            f"Pertanyaan: {q}",
            f"Jawaban: {a}",
            f"Regulasi: {regulasi}",
            f"Sumber: {sumber}"
        ])
        metadata = {"tipe": "faq", "index": idx, "sumber": sumber, "regulasi": regulasi}
        docs.append(Document(page_content=text, metadata=metadata))
    return docs

# ---------------------------
# Build / Load indices
# ---------------------------
def build_or_load_indices(embedding_model: str, device: str):
    embeddings = HuggingFaceEmbeddings(model_name=embedding_model, model_kwargs={"device": device})

    # formasi
    if os.path.isdir(FAISS_FORMASI_DIR) and len(os.listdir(FAISS_FORMASI_DIR)) > 0:
        db_formasi = FAISS.load_local(FAISS_FORMASI_DIR, embeddings, allow_dangerous_deserialization=True)
    else:
        formasi_docs = load_formasi_docs(FORMASI_FILE)
        db_formasi = FAISS.from_documents(formasi_docs, embeddings)
        db_formasi.save_local(FAISS_FORMASI_DIR)

    # faq
    if os.path.isdir(FAISS_FAQ_DIR) and len(os.listdir(FAISS_FAQ_DIR)) > 0:
        db_faq = FAISS.load_local(FAISS_FAQ_DIR, embeddings, allow_dangerous_deserialization=True)
    else:
        faq_docs = load_faq_docs(FAQ_FILE)
        db_faq = FAISS.from_documents(faq_docs, embeddings)
        db_faq.save_local(FAISS_FAQ_DIR)

    return db_formasi, db_faq, embeddings

# ---------------------------
# Prompt & Output parser
# ---------------------------
schemas = [
    ResponseSchema(name="jawaban", description="Jawaban singkat dan relevan dalam bahasa Indonesia.")
]
output_parser = StructuredOutputParser.from_response_schemas(schemas)
format_instructions = output_parser.get_format_instructions()

base_prompt = ChatPromptTemplate.from_template("""
Kamu adalah asisten resmi dari Badan Kepegawaian Negara (BKN) yang membantu masyarakat memahami informasi seputar Aparatur Sipil Negara (ASN), termasuk CPNS, PPPK, formasi, kualifikasi pendidikan, alur pendaftaran, dan regulasi terkait.

Instruksi:
1. Jawab PERTANYAAN PENGGUNA secara LENGKAP namun LANGSUNG KE INTI.
   - Jika pertanyaan tentang formasi: sebutkan jabatan, instansi, jumlah kebutuhan, kualifikasi pendidikan, dan kisaran gaji (jika tersedia dalam konteks).
   - Jika pertanyaan tentang konsep (misal: “Apa itu CPNS?”): berikan penjelasan sederhana dalam bahasa Indonesia yang mudah dipahami.

2. Penafsiran kualifikasi:
   - “S1 semua jurusan” berarti semua lulusan S1 dari jurusan apa pun boleh mendaftar.
   - Pelamar S1 hanya boleh mendaftar ke formasi yang mensyaratkan kualifikasi S1.
   - Pelamar S2 hanya boleh mendaftar ke formasi yang mensyaratkan kualifikasi S2.
   - Pelamar S3 hanya boleh mendaftar ke formasi yang mensyaratkan kualifikasi S3.
   - Jangan merekomendasikan pelamar ke formasi dengan kualifikasi di bawah atau di atas jenjang pendidikannya.

3. Jika ada banyak formasi yang relevan:
   - Tampilkan SEMUA formasi yang sesuai.
   - Setiap formasi ditulis dalam satu baris terpisah.
   - Urutkan berdasarkan: (a) jumlah kebutuhan (terbanyak → paling sedikit), lalu (b) kisaran gaji (jika tersedia).
   - Formasi dengan jumlah kebutuhan lebih tinggi dianggap memiliki peluang lolos lebih besar.

4. Gunakan HANYA informasi yang tersedia dalam KONTEKS.
   - Jangan mengarang, menebak, atau menambahkan data di luar konteks.

5. Jika konteks tidak mencukupi:
   - Untuk topik ASN/CPNS/PPPK:  
     → "Maaf, saya tidak tahu jawaban pastinya berdasarkan dokumen yang tersedia."
   - Untuk topik di luar rekrutmen ASN:  
     → "Maaf, saya tidak tahu. Saya hanya bisa menjawab pertanyaan seputar formasi CPNS, kualifikasi pendidikan, dan informasi rekrutmen ASN berdasarkan dokumen resmi."

6. Selalu akhiri dengan arahan:  
   → "Untuk informasi lebih lengkap dan terkini, silakan kunjungi https://sscasn.bkn.go.id"

Pertanyaan pengguna: {question}
Konteks tambahan dari dokumen:
{context}
{format_instructions}
""")

# ---------------------------
# Initialize Flask app
# ---------------------------
app = Flask(__name__)
CORS(app)

# Build indices at startup (costly but done once)
try:
    db_formasi, db_faq, embeddings = build_or_load_indices(EMBEDDING_MODEL, EMBEDDING_DEVICE)
    print("✅ FAISS indices ready.")
except Exception as e:
    print("❌ Gagal membangun/ memuat indices:", e)
    traceback.print_exc()
    db_formasi = db_faq = None
    embeddings = None

# LLM client
# if not GOOGLE_API_KEY:
#     print("⚠️ GOOGLE_API_KEY environment variable is not set. LLM calls will fail unless set.")
llm = ChatGoogleGenerativeAI(model=GOOGLE_MODEL, google_api_key="xxxxxxxxx", temperature=0.2) # ganti api key sesuai dengan di google AI studio

# ---------------------------
# Endpoint /ask
# ---------------------------
@app.route("/ask", methods=["POST"])
def ask():
    try:
        body = request.get_json(force=True)
        question = body.get("question") or body.get("q") or ""
        top_k = int(body.get("k", RETRIEVER_K))

        if not question:
            return jsonify({"error": "Missing 'question' in request body"}), 400

        qtype = detect_query_type(question)
        # choose db
        if qtype == "formasi":
            db = db_formasi
        else:
            db = db_faq

        retriever = db.as_retriever(search_kwargs={"k": top_k})
        # get relevant docs
        docs = retriever.get_relevant_documents(question)

        # prepare context (concat top docs' page_content)
        context_text = "\n\n---\n\n".join([d.page_content for d in docs])

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            chain_type_kwargs={"prompt": base_prompt.partial(format_instructions=format_instructions)},
            input_key="query"
        )

        response = qa_chain.invoke({"query": question})


        # normalize response object
        if isinstance(response, dict):
            raw = response.get("result") or response.get("answer") or response.get("output_text") or str(response)
        else:
            raw = str(response)

        # try structured parsing
        try:
            parsed = output_parser.parse(raw)
            jawaban = parsed.get("jawaban", raw)
        except Exception:
            # fallback: raw text
            jawaban = raw

        # optional: return top docs metadata for debugging/tracing
        top_docs_meta = [{"tipe": d.metadata.get("tipe"), "instansi": d.metadata.get("instansi"),
                          "jabatan": d.metadata.get("jabatan"), "penempatan": d.metadata.get("penempatan")} for d in docs]

        return jsonify({
            "question": question,
            "detected_type": qtype,
            "answer": jawaban,
            "retrieved_docs": top_docs_meta
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

# ---------------------------
# Run
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
