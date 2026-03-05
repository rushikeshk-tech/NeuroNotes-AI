import streamlit as st
import whisper
import tempfile
import nltk
import re
import random
import os

from nltk.tokenize import sent_tokenize
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ---------------- NLTK ----------------
nltk.download("punkt")

# ---------------- CONFIG ----------------
st.set_page_config(page_title=" ", layout="wide")

LOGO = "logo.png"

# ---------------- STYLE ----------------
st.markdown("""
<style>

.transcript-box{
background:#111827;
padding:20px;
border-radius:10px;
color:white;
font-size:16px;
}

.summary-box{
background:#1f2937;
padding:20px;
border-radius:10px;
color:white;
font-size:16px;
margin-bottom:10px;
}

.correct{color:#22c55e;font-weight:bold;}
.wrong{color:#ef4444;font-weight:bold;}

</style>
""", unsafe_allow_html=True)

# ---------------- SESSION ----------------
if "page" not in st.session_state:
    st.session_state.page = "login"

if "users" not in st.session_state:
    st.session_state.users = {"demo": "demo123"}  # examiner login

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------------- LOAD MODEL ----------------
@st.cache_resource
def load_model():
    return whisper.load_model("base")

# ---------------- CLEAN TEXT ----------------
def clean_text(text):

    text = text.lower()

    filler = ["okay","umm","uh","like","you know"]
    for w in filler:
        text = text.replace(w,"")

    text = re.sub(r'\b(\w+)( \1\b)+', r'\1', text)
    text = re.sub(r'\s+', ' ', text)

    return text

# ---------------- SUMMARY ----------------
def generate_summary(text):

    sentences = sent_tokenize(text)
    good = []

    for s in sentences:
        if len(s.split()) > 8:
            good.append(s)

    return good[:6]

# ---------------- QUIZ ----------------
def generate_quiz(summary):

    questions=[]

    for sentence in summary:

        words=sentence.split()

        if len(words) < 5:
            continue

        keyword=random.choice(words[3:])
        q=sentence.replace(keyword,"_____")

        distractors=[]

        for s in summary:
            for w in s.split():
                if w!=keyword and len(w)>4:
                    distractors.append(w)

        distractors=random.sample(list(set(distractors)),min(3,len(distractors)))

        options=distractors+[keyword]
        random.shuffle(options)

        questions.append({
            "question":q,
            "options":options,
            "answer":keyword
        })

    return questions

# ---------------- PDF ----------------
def create_pdf(summary, report):

    file="NeuroNotes_Report.pdf"

    doc=SimpleDocTemplate(file)
    styles=getSampleStyleSheet()

    elements=[]

    elements.append(Paragraph("NeuroNotes AI Report",styles["Title"]))
    elements.append(Spacer(1,10))

    elements.append(Paragraph("SUMMARY",styles["Heading2"]))

    for s in summary:
        elements.append(Paragraph("• "+s,styles["Normal"]))

    elements.append(Spacer(1,10))

    elements.append(Paragraph("QUIZ REPORT",styles["Heading2"]))
    elements.append(Paragraph(report,styles["Normal"]))

    doc.build(elements)

    return file

# ================= LOGIN =================
def login():

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if os.path.exists(LOGO):
            st.image(LOGO, width=260)

    st.write("")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in st.session_state.users and st.session_state.users[username] == password:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Invalid credentials")

    if st.button("Create Account"):
        st.session_state.page = "create"
        st.rerun()

# ================= CREATE ACCOUNT =================
def create():

    st.subheader("Create Account")

    username = st.text_input("New Username")
    password = st.text_input("New Password", type="password")

    if st.button("Create"):
        if username == "" or password == "":
            st.warning("Enter details")
        else:
            st.session_state.users[username] = password
            st.success("Account created. Now login.")
            st.session_state.page = "login"
            st.rerun()

    if st.button("Back"):
        st.session_state.page = "login"
        st.rerun()

# ================= MAIN =================
def main():

    # ===== CENTER PNG =====
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if os.path.exists(LOGO):
            st.image(LOGO, width=280)

    st.write("")

    uploaded_file = st.file_uploader("Upload Lecture", type=["mp3","wav","mp4"])

    if uploaded_file:

        if "done" not in st.session_state:

            st.info("Transcribing...")

            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(uploaded_file.read())
                path=tmp.name

            model=load_model()
            result=model.transcribe(path)

            transcript=clean_text(result["text"])
            summary=generate_summary(transcript)
            quiz=generate_quiz(summary)

            st.session_state.transcript=transcript
            st.session_state.summary=summary
            st.session_state.quiz=quiz
            st.session_state.done=True

        transcript=st.session_state.transcript
        summary=st.session_state.summary
        quiz=st.session_state.quiz

        tab1,tab2,tab3=st.tabs(["Transcript","Summary","Quiz"])

# -------- TRANSCRIPT --------
        with tab1:
            st.markdown(f"<div class='transcript-box'>{transcript}</div>",unsafe_allow_html=True)

# -------- SUMMARY --------
        with tab2:
            for s in summary:
                st.markdown(f"<div class='summary-box'>• {s}</div>",unsafe_allow_html=True)

# -------- QUIZ --------
        with tab3:

            user_answers=[]

            for i,q in enumerate(quiz):

                st.write(f"Q{i+1}. {q['question']}")

                ans=st.radio(
                    "Select answer",
                    q["options"],
                    index=None,
                    key=f"q{i}"
                )

                user_answers.append(ans)

            if st.button("Submit Quiz"):

                if None in user_answers:
                    st.warning("⚠ Please answer all questions first.")
                else:

                    score=0
                    report=[]

                    st.markdown("### 📊 Result")

                    for i,q in enumerate(quiz):

                        if user_answers[i]==q["answer"]:
                            score+=1
                            st.markdown(f"<p class='correct'>✔ Q{i+1} Correct</p>",unsafe_allow_html=True)
                            report.append(f"Q{i+1}: Correct")

                        else:
                            st.markdown(
                                f"<p class='wrong'>❌ Q{i+1} Wrong (Correct: {q['answer']})</p>",
                                unsafe_allow_html=True
                            )
                            report.append(f"Q{i+1}: Wrong (Correct: {q['answer']})")

                    st.success(f"Final Score: {score}/{len(quiz)}")

                    report_text="<br/>".join(report)
                    pdf=create_pdf(summary,report_text)

                    with open(pdf,"rb") as f:
                        st.download_button(
                            "📄 Download Full Report PDF",
                            f,
                            file_name="NeuroNotes_Report.pdf"
                        )

    if st.button("Logout"):
        st.session_state.logged_in=False
        st.session_state.done=False
        st.rerun()

# ================= ROUTING =================
if st.session_state.logged_in:
    main()
else:
    if st.session_state.page == "login":
        login()
    else:
        create()