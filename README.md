## Android Development
## 📦 Instalasi & Menjalankan Aplikasi

### 1. Clone Proyek

```bash
git clone https://github.com/nandanvsh/AIRA-System.git
cd AIRA-System
```

### 2. Cek JDK & Flutter

```bash
java -version     # Pastikan menggunakan JDK > 17
flutter doctor    # Cek apakah environment Flutter telah siap
```

### 3. Install Dependency

```bash
flutter pub get
```

### 4. Jalankan Aplikasi

```bash
flutter run
```

> ⚠️ Pastikan emulator Android aktif atau perangkat Android sudah terhubung.

---

## Model RAG

## ⚙️ 1 Persiapan Lingkungan

### 🔹 Python Version

Gunakan **Python 3.10+** (direkomendasikan).

### 🔹 Buat virtual environment

```bash
python -m venv venv
source venv/bin/activate       # macOS / Linux
venv\Scripts\activate          # Windows
```

---

## 📦 2 Instalasi Dependensi

Buat file bernama `requirements.txt` seperti ini:

```txt
flask==2.3.2
flask_cors==3.0.10
langchain==0.3.27
langchain-community==0.3.27
langchain-huggingface==0.3.1
langchain-google-genai==2.1.12
faiss-cpu==1.12.0
torch>=2.0.0
transformers>=4.45.0
sentence-transformers>=2.2.2
```

Lalu jalankan:

```bash
pip install -r requirements.txt
```

---

## 🔑 3 Konfigurasi API Key (untuk Google Generative AI)

LangChain menggunakan `ChatGoogleGenerativeAI`, jadi kamu butuh **Google Gemini API key**.

Buat API key di sini:
👉 [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

Set environment variable:

```bash
export GOOGLE_API_KEY="ISI_API_KEY_KAMU"
```

> Windows (PowerShell):
>
> ```bash
> setx GOOGLE_API_KEY "ISI_API_KEY_KAMU"
> ```

---


## 🚀 4 Menjalankan Server

Jalankan Flask:

```bash
python app.py
```

Server akan aktif di:
👉 [http://localhost:5000](http://localhost:5000)

---

## 🧪 5 Uji API dengan `curl` atau Postman

Contoh pakai `curl`:

```bash
curl -X POST http://localhost:5000/ask \
    -H "Content-Type: application/json" \
    -d '{"query": "apa perbedaan cpns dengan pppk?"}'
```

---

## 🧰 6 Troubleshooting

| Masalah                    | Solusi                                                     |
| -------------------------- | ---------------------------------------------------------- |
| `ModuleNotFoundError`      | Pastikan library sudah diinstall sesuai versi.             |
| `Google API key not found` | Cek environment variable `GOOGLE_API_KEY`.                 |
| `CUDA error`               | Ganti `device` ke `"cpu"` di `HuggingFaceEmbeddings`.      |
| `FAISS error`              | Pastikan `faiss-cpu` terinstall dan versi cocok dengan OS. |

---

## 🧾 7 Versi Environment

| Library                | Versi  |
| ---------------------- | ------ |
| Flask                  | 2.3.2  |
| Flask-CORS             | 3.0.10 |
| LangChain              | 0.3.27 |
| LangChain-Community    | 0.3.27 |
| LangChain-HuggingFace  | 0.3.1  |
| LangChain-Google-GenAI | 2.1.12 |
| FAISS-CPU              | 1.12.0 |
| Python                 | ≥ 3.10 |
| langchain-ollama       | 0.3.6  |

---
