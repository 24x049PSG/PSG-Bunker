PSG Bunker – Attendance and CGPA Tracking Web Application for PSG Tech
PSG Bunker is a web-based application developed to streamline the process of monitoring attendance and CGPA for students of PSG College of Technology. The application securely connects to the official PSG Tech eCampus portal and extracts essential academic data, presenting it in a simplified, modern, and mobile-optimized interface.

Project Overview
The PSG eCampus portal provides students with access to their academic information, including attendance records and grade history. However, the interface can be difficult to navigate and is not optimized for mobile devices. Students often have to log in repeatedly and manually calculate their eligibility to miss classes or estimate their CGPA. PSG Bunker was developed to address these limitations by offering an intuitive dashboard that summarizes a student's attendance status, subject-wise breakdown, and computed CGPA.

Objectives
Provide a clear and accessible overview of attendance and CGPA

Calculate and display how many classes a student can safely miss or must attend to maintain the required minimum attendance percentage

Offer a modern, responsive, mobile-friendly interface that improves usability

Enable students to make informed decisions regarding attendance and academic planning

Key Features
Secure Login System
Students log in using their roll number and eCampus password. The application uses secure session-based communication to authenticate and retrieve data from the PSG eCampus portal.

Attendance Dashboard
The dashboard presents:

Total working hours

Total hours attended

Overall attendance percentage

Subject-wise attendance statistics

Calculations on how many classes can be bunked (if above 75%) or must be attended (if below 75%)

Each subject is displayed with clear status indicators based on the attendance percentage. Subjects below 75% are highlighted in red, while those above are shown in green.

CGPA Viewer
The application retrieves recent academic records and grades, calculates the CGPA using the standard grade-to-point mapping system, and displays the most recent semester CGPA.

Responsive User Interface
Designed with a mobile-first approach, the interface is fully responsive and optimized for Android and iOS devices. A dark theme ensures readability in low-light conditions.

SEO and Deployment Ready
The application includes search engine optimization (SEO) features such as meta tags, sitemap.xml, and robots.txt to improve discoverability through Google Search.

Technical Stack
Component	Technology Used
Frontend	HTML5, CSS3, JavaScript (Vanilla)
Backend	Python 3, Flask
Data Parsing	BeautifulSoup, pandas, requests
Deployment	Render / Vercel (for hosting)

System Workflow
The user logs in with their PSG Tech roll number and password.

The backend authenticates and establishes a session with the PSG eCampus portal.

Attendance and grade data are fetched in HTML format and parsed using BeautifulSoup and pandas.

Data is structured and served to the frontend via JSON.

The frontend displays the data in a clean, responsive format with conditional formatting based on attendance thresholds.

This project was created to address a real student need by improving access to academic data and providing actionable insights in a user-friendly format. It combines backend automation, frontend design, and practical problem-solving.

Future Enhancements
Timetable integration

Push notifications for attendance alerts

Biometric authentication (fingerprint/Face ID) for faster login

Offline access through caching and PWA (Progressive Web App) support

Export to PDF feature for attendance and CGPA reports

Conclusion
PSG Bunker is a practical solution built to simplify the student experience at PSG Tech. By eliminating the need for repetitive manual checks and calculations, it helps students make better academic decisions. The project demonstrates full-stack development skills and addresses a real-world use case in the academic domain.
