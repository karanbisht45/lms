import streamlit as st
import backend as bk
import pandas as pd
import os

# ---------------- PAGE CONFIG -----------------
st.set_page_config(page_title="Centralized LMS", page_icon="🎓", layout="wide")

# ---------------- SESSION STATE -----------------
for key, default in {"login": False, "user_id": None, "role": None}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ---------------- HEADER -----------------
st.title("🎓 Centralized LMS Platform")
st.caption("Empowering Learning with Analytics, Engagement, and AI-driven Efficiency")

# ---------------- HELPER -----------------
def save_pdf(uploaded_file, folder):
    """Save PDF locally and return file path."""
    if uploaded_file is not None:
        path = os.path.join(folder, uploaded_file.name)
        with open(path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return path
    return None

# ---------------- LOGIN / SIGNUP -----------------
def login_form():
    with st.form("login_form"):
        st.subheader("🔐 Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["Student", "Teacher"])
        submitted = st.form_submit_button("Login")
        if submitted:
            user = bk.login(username, password, role)
            if user:
                st.session_state.login = True
                st.session_state.user_id = user[0]
                st.session_state.role = role
                st.toast(f"✅ Welcome {username} ({role})!", icon="🎉")
                st.rerun()
            else:
                st.error("❌ Invalid credentials.")

def signup_form():
    with st.form("signup_form"):
        st.subheader("📝 Signup")
        username = st.text_input("Create Username")
        password = st.text_input("Create Password", type="password")
        role = st.selectbox("Role", ["Student", "Teacher"])
        submitted = st.form_submit_button("Signup")
        if submitted:
            if bk.signup(username, password, role):
                st.success("✅ Account created successfully! Please login.")
            else:
                st.error("⚠️ Username already exists.")

# ---------------- STUDENT DASHBOARD -----------------
def student_dashboard(uid):
    st.sidebar.title("🎓 Student Menu")

    nav = st.sidebar.radio("Navigate", [
        "🏠 Dashboard", "📚 Enroll", "🎓 My Courses", "📝 Assignments",
        "📖 Notes", "🧠 Exams", "🏅 My Rank"
    ])

    if st.sidebar.button("Logout"):
        st.session_state.login = False
        st.session_state.user_id = None
        st.session_state.role = None
        st.rerun()

    # ---------------- Dashboard -----------------
    if nav == "🏠 Dashboard":
        st.subheader("📊 Your Learning Analytics")

        enrolled_courses = bk.get_enrolled_courses(uid)
        total_courses = len(enrolled_courses)
        total_assignments = sum([len(bk.get_assignments(c[0])) for c in enrolled_courses])
        total_exams = sum([len(bk.get_exams(c[0])) for c in enrolled_courses])
        points = bk.get_user_points(uid)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Courses Enrolled", total_courses)
        col2.metric("Assignments Available", total_assignments)
        col3.metric("Exams Available", total_exams)
        col4.metric("Total Points 🏅", points)

        st.divider()
        st.write("### Progress Overview")
        progress_data = bk.get_course_progress(uid)
        if progress_data:
            df = pd.DataFrame(progress_data, columns=["Course", "Progress %"])
            st.bar_chart(df.set_index("Course"))
        else:
            st.info("No progress data available yet.")

    # ---------------- Enroll -----------------
    elif nav == "📚 Enroll":
        all_courses = bk.get_courses()
        enrolled = [c[0] for c in bk.get_enrolled_courses(uid)]
        available = [c for c in all_courses if c[0] not in enrolled]

        st.subheader("📘 Available Courses")
        search = st.text_input("🔍 Search Courses")
        filtered = [c for c in available if search.lower() in c[1].lower()] if search else available

        if filtered:
            choice = st.selectbox("Select Course to Enroll", [c[1] for c in filtered])
            if st.button("Enroll Now"):
                cid = [c[0] for c in filtered if c[1] == choice][0]
                bk.enroll_course(uid, cid)
                st.success(f"✅ Enrolled in {choice}")
                st.toast(f"🎉 Successfully enrolled in {choice}!", icon="🎓")
                st.rerun()
        else:
            st.info("No matching or available courses found.")

    # ---------------- My Courses -----------------
    elif nav == "🎓 My Courses":
        enrolled_courses = bk.get_enrolled_courses(uid)
        if enrolled_courses:
            st.write("### Enrolled Courses:")
            for cid, name in enrolled_courses:
                st.markdown(f"- {name}")
        else:
            st.info("No enrolled courses found.")

    # ---------------- Assignments -----------------
    elif nav == "📝 Assignments":
        enrolled = bk.get_enrolled_courses(uid)
        if enrolled:
            course = st.selectbox("Select Course", [c[1] for c in enrolled])
            cid = [c[0] for c in enrolled if c[1] == course][0]
            assignments = bk.get_assignments(cid)
            if assignments:
                for a in assignments:
                    st.markdown(f"### 📘 {a[1]}")
                    if a[2]:
                        with open(a[2], "rb") as f:
                            st.download_button("📄 Download Assignment PDF", f, file_name=a[1] + ".pdf")
                    ans = st.text_area(f"Submit Answer for '{a[1]}'", key=f"assign_{a[0]}")
                    if st.button(f"Submit {a[1]}", key=f"btn_{a[0]}"):
                        bk.submit_assignment(uid, a[0], ans)
                        bk.add_points(uid, 10)
                        st.toast(f"✅ Submitted! +10 points", icon="🏅")
            else:
                st.info("No assignments uploaded yet.")
        else:
            st.info("Enroll in a course first.")

    # ---------------- Notes -----------------
    elif nav == "📖 Notes":
        enrolled = bk.get_enrolled_courses(uid)
        if enrolled:
            course = st.selectbox("Select Course", [c[1] for c in enrolled])
            cid = [c[0] for c in enrolled if c[1] == course][0]
            notes = bk.get_notes(cid)
            if notes:
                for n in notes:
                    st.markdown(f"📘 Note File:")
                    if n[1]:
                        with open(n[1], "rb") as f:
                            st.download_button("📄 Download Note PDF", f, file_name=os.path.basename(n[1]))
            else:
                st.info("No notes uploaded.")
        else:
            st.info("Enroll in a course first.")

    # ---------------- Exams -----------------
    elif nav == "🧠 Exams":
        enrolled = bk.get_enrolled_courses(uid)
        if enrolled:
            course = st.selectbox("Select Course", [c[1] for c in enrolled])
            cid = [c[0] for c in enrolled if c[1] == course][0]
            exams = bk.get_exams(cid)
            if exams:
                for e in exams:
                    st.markdown(f"### 🧠 {e[1]}")
                    if e[2]:
                        with open(e[2], "rb") as f:
                            st.download_button("📄 View Exam Paper (PDF)", f, file_name=e[1] + ".pdf")
                    ans = st.text_area(f"Write Answers for {e[1]}", key=f"exam_ans_{e[0]}")
                    if st.button(f"Submit {e[1]}", key=f"submit_exam_{e[0]}"):
                        bk.submit_exam(uid, e[0], ans)
                        bk.add_points(uid, 20)
                        st.toast("✅ Exam submitted successfully! +20 points", icon="🏆")
            else:
                st.info("No exams available.")
        else:
            st.info("Enroll in a course first.")

    # ---------------- Leaderboard -----------------
    elif nav == "🏅 My Rank":
        st.subheader("🏆 Student Leaderboard")
        leaderboard = bk.get_leaderboard()
        df = pd.DataFrame(leaderboard, columns=["Username", "Points"])
        st.table(df.sort_values(by="Points", ascending=False))


# ---------------- TEACHER DASHBOARD -----------------
def teacher_dashboard(uid):
    st.sidebar.title("👩‍🏫 Teacher Menu")
    nav = st.sidebar.radio("Navigate", ["📘 Courses", "🧾 Assignments", "📚 Notes", "🧠 Exams", "📊 Analytics"])

    if st.sidebar.button("Logout"):
        st.session_state.login = False
        st.session_state.user_id = None
        st.session_state.role = None
        st.rerun()

    my_courses = [c for c in bk.get_courses() if c[2] == uid]

    # ---------------- Courses -----------------
    if nav == "📘 Courses":
        st.subheader("Add New Course")
        cname = st.text_input("Course Name")
        if st.button("Add Course"):
            bk.add_course(cname, uid)
            st.toast(f"✅ Course '{cname}' added!", icon="📘")
            st.rerun()

        st.write("### My Courses")
        if my_courses:
            for c in my_courses:
                st.markdown(f"- {c[1]} (ID: {c[0]})")
        else:
            st.info("No courses added yet.")

    # ---------------- Assignments -----------------
    elif nav == "🧾 Assignments":
        if my_courses:
            course = st.selectbox("Select Course", [c[1] for c in my_courses])
            cid = [c[0] for c in my_courses if c[1] == course][0]
            title = st.text_input("Assignment Title")
            uploaded = st.file_uploader("📤 Upload Assignment PDF", type=["pdf"])
            if st.button("Upload Assignment"):
                path = save_pdf(uploaded, bk.ASSIGN_DIR)
                if path:
                    bk.add_assignment(cid, title, path)
                    st.success("📝 Assignment uploaded successfully!")
                else:
                    st.warning("Please upload a valid PDF file.")
        else:
            st.warning("Please add a course first.")

    # ---------------- Notes -----------------
    elif nav == "📚 Notes":
        if my_courses:
            course = st.selectbox("Select Course", [c[1] for c in my_courses])
            cid = [c[0] for c in my_courses if c[1] == course][0]
            uploaded = st.file_uploader("📤 Upload Notes PDF", type=["pdf"])
            if st.button("Upload Note"):
                path = save_pdf(uploaded, bk.NOTES_DIR)
                if path:
                    bk.upload_note(cid, path)
                    st.success("📘 Note uploaded successfully!")
                else:
                    st.warning("Please upload a valid PDF file.")
        else:
            st.info("Add a course first.")

    # ---------------- Exams -----------------
    elif nav == "🧠 Exams":
        if my_courses:
            course = st.selectbox("Select Course", [c[1] for c in my_courses])
            cid = [c[0] for c in my_courses if c[1] == course][0]
            title = st.text_input("Exam Title")
            uploaded = st.file_uploader("📤 Upload Exam Paper (PDF)", type=["pdf"])
            if st.button("Create Exam"):
                path = save_pdf(uploaded, bk.EXAMS_DIR)
                if path:
                    bk.create_exam(cid, title, path)
                    st.success("🧠 Exam uploaded successfully!")
                else:
                    st.warning("Please upload a valid PDF file.")
        else:
            st.info("Add a course first.")

    # ---------------- Analytics -----------------
    elif nav == "📊 Analytics":
     st.subheader("📈 Detailed Student Report")

     my_courses = [c for c in bk.get_courses() if c[2] == uid]

    if my_courses:
        course = st.selectbox("Select Course", [c[1] for c in my_courses], key="analytics_course")
        cid = [c[0] for c in my_courses if c[1] == course][0]

        data = bk.get_teacher_student_performance(cid)

        if data:
            df = pd.DataFrame(data)
            st.dataframe(df)

            # Optional CSV download
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Report as CSV",
                data=csv,
                file_name=f"{course}_performance_report.csv",
                mime="text/csv"
            )
        else:
            st.info("No student submissions or exams yet for this course.")
    else:
        st.warning("Please add a course first.")

    # TODO: Add email notification system in next phase




# ---------------- MAIN -----------------
if not st.session_state.login:
    choice = st.sidebar.radio("Menu", ["Login", "Signup"])
    if choice == "Login":
        login_form()
    else:
        signup_form()
else:
    if st.session_state.role == "Student":
        student_dashboard(st.session_state.user_id)
    elif st.session_state.role == "Teacher":
        teacher_dashboard(st.session_state.user_id)
