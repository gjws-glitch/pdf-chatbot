"""
PDF Summarizer Chatbot - Streamlit App
========================================
Aplikasi ini memungkinkan pengguna untuk:
1. Upload file PDF
2. Merangkum isi PDF secara otomatis
3. Chat / tanya jawab tentang isi PDF tersebut

Cara menjalankan:
    pip install streamlit pypdf anthropic
    streamlit run pdf_chatbot.py

Catatan:
- Aplikasi ini menggunakan Anthropic API (Claude) untuk membuat ringkasan
  dan menjawab pertanyaan. Anda perlu memasukkan API key Anthropic di sidebar
  (dapatkan di https://console.anthropic.com/).
"""

import streamlit as st
from pypdf import PdfReader
import anthropic
import io

# ----------------------------
# Konfigurasi halaman
# ----------------------------
st.set_page_config(page_title="Chatbot Rangkuman PDF", page_icon="📄", layout="wide")

st.title("📄 Chatbot Rangkuman PDF")
st.caption("Upload PDF, dapatkan ringkasan otomatis, dan tanya jawab tentang isinya.")

# ----------------------------
# Sidebar: API Key & Pengaturan
# ----------------------------
with st.sidebar:
    st.header("⚙️ Pengaturan")
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        help="Dapatkan API key di https://console.anthropic.com/",
    )
    model_name = st.selectbox(
        "Model",
        options=["claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
        index=0,
    )
    max_chars = st.slider(
        "Maksimum karakter teks PDF yang diproses",
        min_value=5000,
        max_value=100000,
        value=40000,
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


def call_claude(client, model, system_prompt, user_prompt):
    """Panggil Anthropic API dan kembalikan teks respons."""
    response = client.messages.create(
        model=model,
        max_tokens=1500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


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
        if not api_key:
            st.warning("Masukkan Anthropic API Key di sidebar terlebih dahulu.")
        else:
            with st.spinner("Membuat ringkasan..."):
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    text_to_send = st.session_state.pdf_text[:max_chars]
                    system_prompt = (
                        "Anda adalah asisten yang ahli merangkum dokumen. "
                        "Buat ringkasan yang jelas, terstruktur, dan mudah dipahami "
                        "dalam Bahasa Indonesia. Gunakan poin-poin untuk ide utama, "
                        "dan sertakan kesimpulan singkat di akhir."
                    )
                    user_prompt = (
                        f"Berikut adalah isi dokumen PDF:\n\n{text_to_send}\n\n"
                        "Tolong buatkan ringkasan dari dokumen di atas."
                    )
                    summary = call_claude(client, model_name, system_prompt, user_prompt)

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
    elif not api_key:
        st.warning("Masukkan Anthropic API Key di sidebar terlebih dahulu.")
    else:
        st.session_state.messages.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)

        with st.chat_message("assistant"):
            with st.spinner("Berpikir..."):
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    text_context = st.session_state.pdf_text[:max_chars]

                    system_prompt = (
                        "Anda adalah asisten yang menjawab pertanyaan berdasarkan isi "
                        "dokumen PDF yang diberikan. Jawablah dalam Bahasa Indonesia "
                        "dengan jelas dan akurat berdasarkan konteks dokumen. "
                        "Jika jawabannya tidak ada dalam dokumen, katakan dengan jujur "
                        "bahwa informasi tersebut tidak ditemukan dalam dokumen."
                    )

                    # Sertakan riwayat percakapan singkat sebagai konteks tambahan
                    history_snippet = "\n".join(
                        f"{m['role']}: {m['content']}" for m in st.session_state.messages[-6:-1]
                    )

                    user_prompt = (
                        f"Isi dokumen PDF:\n\n{text_context}\n\n"
                        f"Riwayat percakapan sebelumnya:\n{history_snippet}\n\n"
                        f"Pertanyaan pengguna: {user_question}"
                    )

                    answer = call_claude(client, model_name, system_prompt, user_prompt)
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
