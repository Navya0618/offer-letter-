from flask import Flask, render_template, request, send_file, redirect, url_for, flash, session, make_response
from docxtpl import DocxTemplate
import os
import uuid
from supabase import create_client, Client
from functools import wraps
import datetime
from dotenv import load_dotenv

# Supabase config
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")# Hide this in env vars for production

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__, template_folder='templates')
app.secret_key = 'your-secret-key'  # Make sure this is secure!

# ✅ Date formatting function
def format_date_with_suffix(date_str):
    date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    day = int(date_obj.strftime("%d"))
    suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    return f"{day}{suffix} {date_obj.strftime('%B %Y')}"

# ✅ Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'token' not in session:
            flash("You must be logged in to access that page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'token' in session:
        return redirect(url_for('form'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            result = supabase.auth.sign_in_with_password({
                'email': email,
                'password': password
            })

            if result.session:
                session['token'] = result.session.access_token
                session['user'] = email
                flash('Login successful!', 'success')
                return redirect(url_for('form'))
            else:
                flash('Login failed. Please check your credentials.', 'error')

        except Exception as e:
            flash(f'Error: {str(e)}', 'error')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        try:
            result = supabase.auth.sign_up({
                'email': email,
                'password': password
            })

            if result.user:
                flash('Registration successful! Please check your email to verify.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Registration failed.', 'error')

        except Exception as e:
            flash(f'Error: {str(e)}', 'error')

    return render_template('register.html')

@app.route('/form', methods=['GET', 'POST'])
@login_required
def form():
    if request.method == 'POST':
        first_name = request.form['first_name']
        middle_name = request.form['middle_name']
        last_name = request.form['last_name']
        role = request.form['role']
        email = request.form['email']
        start_date_raw = request.form['start_date']
        end_date_raw = request.form['end_date']
        letter_date_raw = request.form['letter_date']
        template_file = request.form['template']

        doc = DocxTemplate(f"templates/word_templates/{template_file}")

        start_date = format_date_with_suffix(start_date_raw)
        end_date = format_date_with_suffix(end_date_raw)
        letter_date = format_date_with_suffix(letter_date_raw)

        context = {
            'first_name': first_name,
            'middle_name': middle_name,
            'last_name': last_name,
            'role': role,
            'email': email,
            'start_date': start_date,
            'end_date': end_date,
            'letter_date': letter_date
        }

        safe_first_name = first_name.strip().capitalize().replace(" ", "_")
        safe_role = role.strip().replace(" ", "_").capitalize()
        output_filename = f"{safe_first_name}_Offer_Letter_{safe_role}.docx"
        output_path = os.path.join("generated_letters", output_filename)

        os.makedirs("generated_letters", exist_ok=True)

        doc.render(context)
        doc.save(output_path)

        return send_file(output_path, as_attachment=True)

    return render_template("form.html")

@app.route('/logout')
@login_required
def logout():
    session.clear()
    supabase.auth.sign_out()
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)