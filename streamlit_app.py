"""
PDF Summarizer Chatbot - Streamlit App (Google Gemini / Google AI Studio)
==========================================================================
Aplikasi ini memungkinkan pengguna untuk:
1. Upload file PDF
2. Merangkum isi PDF secara otomatis
3. Chat / tanya jawab tentang isi PDF tersebut

Menggunakan Google Gemini API (didapat gratis dari Google AI Studio:
https://aistudio.google.com/apikey)

Cara menjalankan (LOKAL):
    pip install streamlit pypdf google-genai
    Buat file .streamlit/secrets.toml berisi:
        GEMINI_API_KEY = "AIzaSy...punya_kamu"
    Lalu jalankan:
    streamlit run pdf_chatbot_gemini.py

Cara deploy ke Streamlit Community Cloud (share.streamlit.io):
    1. Push kode ini ke GitHub (JANGAN ikut push file secrets.toml!)
    2. Deploy di https://share.streamlit.io
    3. Di menu App -> Settings -> Secrets, tempel:
        GEMINI_API_KEY = "AIzaSy...punya_kamu"
    4. Orang lain yang membuka link aplikasi TIDAK perlu masukkan API key sendiri.

Catatan penting:
- API key TIDAK ditanam langsung di kode (supaya tidak bocor kalau kode di-share
  atau diupload ke GitHub), melainkan disimpan terpisah lewat Streamlit Secrets.
- Karena semua pengguna memakai API key yang sama (milik kamu), pertimbangkan
  batas pemakaian (lihat MAX_CHARS di bawah) agar kuota/biaya tidak jebol jika
  aplikasi dipakai banyak orang sekaligus.
- Library resmi yang dipakai adalah 'google-genai' (SDK terbaru Google),
  bukan 'google-generativeai' yang sudah deprecated.
"""

import streamlit as st
from pypdf import PdfReader
from google import genai
import io

# ----------------------------
# Konfigurasi halaman
# ----------------------------
st.set_page_config(page_title="Chatbot Rangkuman PDF (Gemini)", page_icon="📄", layout="wide")

st.title("📄 Chatbot Rangkuman PDF — Google Gemini")
st.caption("Upload PDF, dapatkan ringkasan otomatis, dan tanya jawab tentang isinya.")

# ----------------------------
# Ambil API Key dari Streamlit Secrets (bukan dari input user)
# ----------------------------
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    api_key = None
    st.error(
        "⚠️ API Key belum diatur oleh admin aplikasi. "
        "Tambahkan GEMINI_API_KEY di .streamlit/secrets.toml (lokal) "
        "atau menu Secrets (Streamlit Cloud)."
    )
    st.stop()

# ----------------------------
# Sidebar: Pengaturan (tanpa input API key)
# ----------------------------
with st.sidebar:
    st.header("⚙️ Pengaturan")
    model_name = st.selectbox(
        "Model Gemini",
        options=["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
        index=0,
        help="gemini-2.5-flash cepat & hemat kuota, gemini-2.5-pro lebih akurat untuk dokumen kompleks.",
    )
    max_chars = st.slider(
        "Maksimum karakter teks PDF yang diproses",
        min_value=5000,
        max_value=150000,
        value=50000,
        step=5000,
        help="Batasi jumlah teks yang dikirim ke model agar tidak melebihi batas konteks.",
    )
    st.divider()
    if st.button("🗑️ Reset percakapan"):
        st.session_state.messages = []
        st.session_state.pdf_text = ""
        st.session_state.pdf_name = ""
        st.rerun()

# ----------------------------
# Inisialisasi session state
# ----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""
if "pdf_name" not in st.session_state:
    st.session_state.pdf_name = ""


# ----------------------------
# Fungsi bantu
# ----------------------------
def extract_text_from_pdf(uploaded_file) -> str:
    """Ekstrak teks dari file PDF yang diupload."""
    reader = PdfReader(io.BytesIO(uploaded_file.read()))
    text_parts = []
    for i, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        text_parts.append(f"\n--- Halaman {i + 1} ---\n{page_text}")
    return "\n".join(text_parts)


def call_gemini(api_key: str, model: str, prompt: str) -> str:
    """Panggil Google Gemini API (Google AI Studio) dan kembalikan teks respons."""
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return response.text


# ----------------------------
# Upload PDF
# ----------------------------
uploaded_file = st.file_uploader("Upload file PDF di sini", type=["pdf"])

if uploaded_file is not None and uploaded_file.name != st.session_state.pdf_name:
    with st.spinner("Mengekstrak teks dari PDF..."):
        try:
            full_text = extract_text_from_pdf(uploaded_file)
            st.session_state.pdf_text = full_text
            st.session_state.pdf_name = uploaded_file.name
            st.session_state.messages = []  # reset chat untuk PDF baru
            st.success(f"Berhasil membaca '{uploaded_file.name}' ({len(full_text)} karakter).")
        except Exception as e:
            st.error(f"Gagal membaca PDF: {e}")

# ----------------------------
# Tombol Ringkas Otomatis
# ----------------------------
if st.session_state.pdf_text:
    col1, col2 = st.columns([1, 3])
    with col1:
        summarize_clicked = st.button("✨ Ringkas PDF Ini", use_container_width=True)

    if summarize_clicked:
        with st.spinner("Membuat ringkasan..."):
            try:
                text_to_send = st.session_state.pdf_text[:max_chars]
                prompt = (
                    "Anda adalah asisten yang ahli merangkum dokumen. "
                    "Buat ringkasan yang jelas, terstruktur, dan mudah dipahami "
                    "dalam Bahasa Indonesia. Gunakan poin-poin untuk ide utama, "
                    "dan sertakan kesimpulan singkat di akhir.\n\n"
                    f"Berikut adalah isi dokumen PDF:\n\n{text_to_send}\n\n"
                    "Tolong buatkan ringkasan dari dokumen di atas."
                )
                summary = call_gemini(api_key, model_name, prompt)

                st.session_state.messages.append(
                    {"role": "assistant", "content": f"**Ringkasan PDF '{st.session_state.pdf_name}':**\n\n{summary}"}
                )
            except Exception as e:
                st.error(f"Terjadi kesalahan saat memanggil API: {e}")

    with st.expander("📖 Lihat teks mentah hasil ekstraksi PDF"):
        st.text_area("Isi PDF", st.session_state.pdf_text, height=200)

st.divider()

# ----------------------------
# Tampilkan riwayat chat
# ----------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ----------------------------
# Input chat untuk tanya jawab
# ----------------------------
user_question = st.chat_input("Tanyakan sesuatu tentang isi PDF...")

if user_question:
    if not st.session_state.pdf_text:
        st.warning("Silakan upload PDF terlebih dahulu.")
    else:
        st.session_state.messages.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)

        with st.chat_message("assistant"):
            with st.spinner("Berpikir..."):
                try:
                    text_context = st.session_state.pdf_text[:max_chars]

                    # Sertakan riwayat percakapan singkat sebagai konteks tambahan
                    history_snippet = "\n".join(
                        f"{m['role']}: {m['content']}" for m in st.session_state.messages[-6:-1]
                    )

                    prompt = (
                        "Anda adalah asisten yang menjawab pertanyaan berdasarkan isi "
                        "dokumen PDF yang diberikan. Jawablah dalam Bahasa Indonesia "
                        "dengan jelas dan akurat berdasarkan konteks dokumen. "
                        "Jika jawabannya tidak ada dalam dokumen, katakan dengan jujur "
                        "bahwa informasi tersebut tidak ditemukan dalam dokumen.\n\n"
                        f"Isi dokumen PDF:\n\n{text_context}\n\n"
                        f"Riwayat percakapan sebelumnya:\n{history_snippet}\n\n"
                        f"Pertanyaan pengguna: {user_question}"
                    )

                    answer = call_gemini(api_key, model_name, prompt)
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                except Exception as e:
                    error_msg = f"Terjadi kesalahan: {e}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

# ----------------------------
# Info tambahan jika belum ada PDF
# ----------------------------
if not st.session_state.pdf_text:
    st.info("👆 Upload file PDF di atas untuk memulai.")
