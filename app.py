import streamlit as st
import backend as bk
import pandas as pd
import matplotlib.pyplot as plt

# ---------------- PAGE CONFIG -----------------
st.set_page_config(page_title="Centralized LMS", page_icon="🎓", layout="wide")

# ---------------- SESSION STATE -----------------
for key, default in {"login": False, "user_id": None, "role": None}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ---------------- HEADER -----------------
st.title("🎓 Centralized LMS Platform")
st.caption("Empowering Learning with Analytics, Engagement, and AI-driven Efficiency")

# ---------------- LOGIN / SIGNUP -----------------
def login_form():
    with st.form("login_form", clear_on_submit=False):
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

    nav = st.sidebar.radio("Navigate", ["🏠 Dashboard", "📚 Enroll", "🎓 My Courses", "📝 Assignments", "📖 Notes", "🧠 Exams", "🏅 My Rank"])

    if st.sidebar.button("Logout"):
        st.session_state.login = False
        st.session_state.user_id = None
        st.session_state.role = None
        st.rerun()

    if nav == "🏠 Dashboard":
        st.subheader("📊 Your Learning Analytics")

        enrolled_courses = bk.get_enrolled_courses(uid)
        total_courses = len(enrolled_courses)
        total_assignments = bk.count_user_assignments(uid)
        total_exams = bk.count_user_exams(uid)
        points = bk.get_user_points(uid)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Courses Enrolled", total_courses)
        col2.metric("Assignments Done", total_assignments)
        col3.metric("Exams Attempted", total_exams)
        col4.metric("Total Points 🏅", points)

        st.divider()
        st.write("### Progress Overview")
        progress_data = bk.get_course_progress(uid)
        if progress_data:
            df = pd.DataFrame(progress_data, columns=["Course", "Progress"])
            fig, ax = plt.subplots()
            ax.bar(df["Course"], df["Progress"], color="skyblue")
            ax.set_ylabel("Completion %")
            st.pyplot(fig)
        else:
            st.info("No progress data available yet.")

        # Download Report
        if progress_data:
            df = pd.DataFrame(progress_data, columns=["Course", "Progress"])
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Progress Report", data=csv, file_name="progress_report.csv", mime="text/csv")

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

    elif nav == "🎓 My Courses":
        enrolled_courses = bk.get_enrolled_courses(uid)
        if enrolled_courses:
            st.write("### Enrolled Courses:")
            for cid, name in enrolled_courses:
                st.markdown(f"- {name}")
        else:
            st.info("No enrolled courses found.")

    elif nav == "📝 Assignments":
        enrolled = bk.get_enrolled_courses(uid)
        if enrolled:
            course = st.selectbox("Select Course", [c[1] for c in enrolled], key="assign_course")
            cid = [c[0] for c in enrolled if c[1] == course][0]
            assignments = bk.get_assignments(cid)
            if assignments:
                for a in assignments:
                    st.markdown(f"**{a[1]}**: {a[2]}")
                    ans = st.text_area(f"Submit Answer for '{a[1]}'", key=f"assign_{a[0]}")
                    if st.button(f"Submit {a[1]}", key=f"btn_{a[0]}"):
                        bk.submit_assignment(uid, a[0], ans)
                        bk.add_points(uid, 10)  # Gamification
                        st.toast(f"✅ Submitted! +10 points", icon="🏅")
            else:
                st.info("No assignments yet.")
        else:
            st.info("Enroll in a course first.")

    elif nav == "📖 Notes":
        enrolled = bk.get_enrolled_courses(uid)
        if enrolled:
            course = st.selectbox("Select Course", [c[1] for c in enrolled], key="note_course")
            cid = [c[0] for c in enrolled if c[1] == course][0]
            notes = bk.get_notes(cid)
            if notes:
                for n in notes:
                    st.markdown(f"📘 {n[1]}")
            else:
                st.info("No notes uploaded.")
        else:
            st.info("Enroll in a course first.")

    elif nav == "🧠 Exams":
        enrolled = bk.get_enrolled_courses(uid)
        if enrolled:
            course = st.selectbox("Select Course", [c[1] for c in enrolled], key="exam_course")
            cid = [c[0] for c in enrolled if c[1] == course][0]
            exams = bk.get_exams(cid)
            if exams:
                exam = st.selectbox("Select Exam", [e[1] for e in exams], key="exam_select")
                eid = [e[0] for e in exams if e[1] == exam][0]
                st.info(exams[0][2])
                ans = st.text_area("Your Answers", key=f"ans_{eid}")
                if st.button("Submit Exam", key=f"submit_{eid}"):
                    bk.submit_exam(uid, eid, ans)
                    bk.add_points(uid, 20)  # Gamification
                    st.toast("✅ Exam submitted successfully! +20 points", icon="🏆")
            else:
                st.info("No exams available.")
        else:
            st.info("Enroll in a course first.")

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

    # Courses
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

    # Assignments
    elif nav == "🧾 Assignments":
        if my_courses:
            course = st.selectbox("Select Course", [c[1] for c in my_courses], key="t_assign")
            cid = [c[0] for c in my_courses if c[1] == course][0]
            title = st.text_input("Assignment Title")
            content = st.text_area("Assignment Details")
            if st.button("Create Assignment"):
                bk.add_assignment(cid, title, content)
                st.toast("📝 Assignment added!", icon="✅")
        else:
            st.warning("Please add a course first.")

    # Notes
    elif nav == "📚 Notes":
        if my_courses:
            course = st.selectbox("Select Course", [c[1] for c in my_courses], key="t_notes")
            cid = [c[0] for c in my_courses if c[1] == course][0]
            content = st.text_area("Note Content")
            if st.button("Upload Note"):
                bk.upload_note(cid, content)
                st.success("📘 Note uploaded.")
        else:
            st.info("Add a course first.")

    # Exams
    elif nav == "🧠 Exams":
        if my_courses:
            course = st.selectbox("Select Course", [c[1] for c in my_courses], key="t_exam")
            cid = [c[0] for c in my_courses if c[1] == course][0]
            title = st.text_input("Exam Title")
            content = st.text_area("Exam Content / Questions")
            if st.button("Create Exam"):
                bk.create_exam(cid, title, content)
                st.success("🧠 Exam created!")
        else:
            st.info("Add a course first.")

    # Analytics
    elif nav == "📊 Analytics":
        if my_courses:
            course = st.selectbox("Select Course", [c[1] for c in my_courses], key="t_analytics")
            cid = [c[0] for c in my_courses if c[1] == course][0]
            students = bk.count_enrolled_students(cid)
            assignments = bk.count_assignments(cid)
            st.metric("Enrolled Students", students)
            st.metric("Assignments Created", assignments)
        else:
            st.info("No course data available.")


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
