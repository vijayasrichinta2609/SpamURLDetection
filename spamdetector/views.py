from django.shortcuts import render, redirect
from django.views import View
from django.http import HttpResponse
import requests
import  random
import joblib
import json
import hashlib
import datetime
import csv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from io import BytesIO
import socket
import requests

def get_location(ip_address):
    response = requests.get(f'https://ipapi.co/{ip_address}/json/').json()
    return {
        "ip": ip_address,
        "city": response.get("city"),
        "region": response.get("region"),
        "country": response.get("country_name")
    }



global data
data = [['URL', 'Result']]
def download_pdf(request):
    # Your PDF generation code here
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    global data
    table = Table(data)
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    table.setStyle(table_style)
    elements.append(table)
    doc.build(elements)

    # Prepare the response, setting Content-Type and Content-Disposition headers
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="report.pdf"'
    buffer.close()
    return response
def handle_uploaded_file(f):
    data = []
    try:
        reader = csv.reader(f.read().decode('utf-8').splitlines())
        for row in reader:
            data.append(row)
    except Exception as e:
        print("Failed to read file:", e)
    return data
def md5_hash(string):
    """Return the MD5 hash of the given string."""
    return hashlib.md5(string.encode()).hexdigest()

# Load your spam detection model
global model
model = joblib.load('trained_model/Multinomial_Naive_Bayes_model.pkl')

class SpamDetectorView(View):
    def get(self, request):
        if request.session.get('is_logged_in', False):
            with open('database/users.json', 'r') as f:
                users = json.load(f)
                user = users.get(request.session['username'])
                id = user['user_id']
                userdata = []
                for i in users:
                    temp = []
                    temp.append(users[i]['user_id'])
                    temp.append(i)
                    temp.append(users[i]['email'])
                    userdata.append(temp)
            with open('database/feedback.json', 'r') as f:
                feed = json.load(f)
                feedback = []
                for i in feed:
                    temp = []
                    temp.append(feed[i]['feedback_id'])
                    temp.append(feed[i]['user_id'])
                    userandtime = i.split("_")
                    temp.append(userandtime[0])
                    temp.append(userandtime[1])
                    temp.append(feed[i]['feedback'])
                    feedback.append(temp)
            with open('database/history.json', 'r') as f:
                history = json.load(f)
                history_data = []
                temp2 = []
                for i in history:
                    temp = []
                    dummy = []
                    temp.append(history[i]['history_id'])
                    temp.append(history[i]['user_id'])
                    userandtime = i.split("_")
                    temp.append(userandtime[0])
                    temp.append(userandtime[1])
                    temp.append(history[i]['description'])
                    history_data.append(temp)
                    dummy.append(history[i]['user_id'])
                    dummy.append(userandtime[1])
                    dummy.append(history[i]['description'])
                    temp2.append(dummy)
                user_history = []
                for i in temp2:
                    if id in i:
                        user_history.append(i)
            if request.session.get('is_admin', False):
                return render(request, 'adminindex.html', {'history':history_data, 'feedback':feedback, 'username': request.session['username'], 'userdata': userdata})
            else:
                return render(request, 'index.html', {'username': request.session['username'], 'history':user_history})
        # Show login or signup based on the action query parameter
        action = request.GET.get('action', 'login')
        if action == 'signup':
            return render(request, 'signup.html')
        else:
            return render(request, 'login.html')

    def post(self, request):
        # Handling login
        if 'login' in request.POST:
            username = request.POST['username']
            password = request.POST['password']
            hashed_password = md5_hash(password)

            # Check user credentials against regular users first
            with open('database/users.json', 'r') as f:
                users = json.load(f)
                user = users.get(username)

                if user and user['password'] == hashed_password:
                    request.session['is_logged_in'] = True
                    request.session['username'] = username

                    # Now check if the user is an admin
                    with open('database/admin.json', 'r') as admin_file:
                        admins = json.load(admin_file)
                        admin_user = admins.get(username)

                        # Check if username exists in admin.json and the passwords match
                        if admin_user and admin_user['password'] == hashed_password:
                            request.session['is_admin'] = True
                        else:
                            request.session['is_admin'] = False

                    # Redirect to the homepage or admin dashboard based on role
                    return redirect('/')

            return render(request, 'login.html', {'error': 'Invalid Username or Password'})
        # Handling signup
        elif 'signup' in request.POST:
            username = request.POST['username']
            email = request.POST['email']
            password = request.POST['password']
            hashed_password = md5_hash(password)
            with open('database/users.json', 'r+') as f:
                users = json.load(f)
                users[username] = {'email': email, 'password': hashed_password, "user_id": random.randint(1, 10000)}
                f.seek(0)
                json.dump(users, f, indent=4)
            return redirect('/')
        # Handling URL and file check
        elif 'url' in request.POST or 'fileUpload' in request.FILES:
            global model
            try:
                url = request.POST['url']
                if url != "":
                    X_new = []
                    prefixes = ['http://', 'https://', 'www.']
                    for prefix in prefixes:
                        if url.startswith(prefix):
                            url = url[len(prefix):]
                    X_new.append(url)
                    predictions = model.predict(X_new)
                    if 'good' in predictions[0]:
                        result = url + ' is Ham URL'
                    else:
                        result = url + ' is Spam URL'

                else:
                    url = 0

            except :
                url = 0
            try:
                global data
                fileupload = request.FILES.get('fileUpload', None)
                if fileupload is not None:
                    url_list = handle_uploaded_file(fileupload)
                    for i in url_list:
                        prefixes = ['http://', 'https://', 'www.']
                        for prefix in prefixes:
                            if i[0].startswith(prefix):
                                i[0] = i[0][len(prefix):]
                        predictions = model.predict(i)
                        if 'good' in predictions[0]:
                            i.append("HAM")
                            data.append(i)
                        else:
                            i.append("SPAM")
                            data.append(i)

                else:
                    fileupload = 0
            except Exception as e:
                fileupload = 0
            with open('database/users.json', 'r') as f:
                users = json.load(f)
                user = users.get(request.session['username'])
                id = user['user_id']
                userdata = []
                for i in users:
                    temp = []
                    temp.append(users[i]['user_id'])
                    temp.append(i)
                    temp.append(users[i]['email'])
                    userdata.append(temp)
            with open('database/feedback.json', 'r') as f:
                feed = json.load(f)
                feedback = []
                for i in feed:
                    temp = []
                    temp.append(feed[i]['feedback_id'])
                    temp.append(feed[i]['user_id'])
                    userandtime = i.split("_")
                    temp.append(userandtime[0])
                    temp.append(userandtime[1])
                    temp.append(feed[i]['feedback'])
                    feedback.append(temp)

            with open('database/history.json', 'r') as f:
                history = json.load(f)
                history_data = []
                temp2 = []
                for i in history:
                    temp = []
                    dummy = []
                    temp.append(history[i]['history_id'])
                    temp.append(history[i]['user_id'])
                    userandtime = i.split("_")
                    temp.append(userandtime[0])
                    temp.append(userandtime[1])
                    temp.append(history[i]['description'])
                    history_data.append(temp)
                    dummy.append(history[i]['user_id'])
                    dummy.append(userandtime[1])
                    dummy.append(history[i]['description'])
                    temp2.append(dummy)
                user_history = []
                for i in temp2:
                    if id in i:
                        user_history.append(i)

            if url != 0 and fileupload != 0:
                try:
                    ip_address = socket.gethostbyname(X_new[0])
                # Fetch and print location information for the IP address
                    location_info = get_location(ip_address)
                except:
                    location_info = {"Request": "Failed"}
                with open('database/users.json', 'r') as t:
                    users = json.load(t)
                    user = users.get(request.session['username'])
                    t.seek(0)
                with open('database/history.json', 'r+') as f:
                    users = json.load(f)
                    current_timestamp = datetime.datetime.now().timestamp()
                    readable_date = datetime.datetime.fromtimestamp(current_timestamp)
                    readable_date_string = readable_date.strftime('%Y-%m-%d %H:%M:%S')
                    h_d = url + " is checked. Also csv file was uploaded to check url."
                    users[request.session['username'] + "_" + readable_date_string] = {'description': h_d,
                                                                                       'history_id': random.randint(1,
                                                                                                                    1000),
                                                                                       "user_id": user["user_id"]}
                    f.seek(0)
                    json.dump(users, f, indent=4)
                if request.session.get('is_admin', False):

                    return render(request, 'adminindex.html', {'history':history_data, 'feedback':feedback,'pdf_url': request.build_absolute_uri('download-pdf/'), 'pdf_true':1, 'result': result, 'username': request.session['username'], 'userdata': userdata})
                else:
                    return render(request, 'index.html', {'location_info': location_info,'history':user_history, 'pdf_url': request.build_absolute_uri('download-pdf/'),'pdf_true':1, 'result': result, 'username': request.session['username']})
            elif url == 0 and fileupload != 0:
                with open('database/users.json', 'r') as t:
                    users = json.load(t)
                    user = users.get(request.session['username'])
                    t.seek(0)
                with open('database/history.json', 'r+') as f:
                    users = json.load(f)
                    current_timestamp = datetime.datetime.now().timestamp()
                    readable_date = datetime.datetime.fromtimestamp(current_timestamp)
                    readable_date_string = readable_date.strftime('%Y-%m-%d %H:%M:%S')
                    h_d = "csv file was uploaded to check url."
                    users[request.session['username'] + "_" + readable_date_string] = {'description': h_d,
                                                                                       'history_id': random.randint(1,
                                                                                                                    1000),
                                                                                       "user_id": user["user_id"]}
                    f.seek(0)
                    json.dump(users, f, indent=4)
                if request.session.get('is_admin', False):
                    return render(request, 'adminindex.html', {'history':history_data, 'feedback':feedback, 'pdf_url': request.build_absolute_uri('download-pdf/'),'pdf_true':1, 'result': " ", 'username': request.session['username'], 'userdata': userdata})
                else:
                    return render(request, 'index.html', {'history':user_history, 'pdf_url': request.build_absolute_uri('download-pdf/'),'pdf_true':1, 'result': " ", 'username': request.session['username']})
            elif url != 0 and fileupload == 0:
                try:
                    ip_address = socket.gethostbyname(X_new[0])
                # Fetch and print location information for the IP address
                    location_info = get_location(ip_address)
                except:
                    location_info = {"Request": "Failed"}
                with open('database/users.json', 'r') as t:
                    users = json.load(t)
                    user = users.get(request.session['username'])
                    t.seek(0)
                with open('database/history.json', 'r+') as f:
                    users = json.load(f)
                    current_timestamp = datetime.datetime.now().timestamp()
                    readable_date = datetime.datetime.fromtimestamp(current_timestamp)
                    readable_date_string = readable_date.strftime('%Y-%m-%d %H:%M:%S')
                    h_d = url + " is checked"
                    users[request.session['username'] + "_" + readable_date_string] = {'description': h_d,
                                                                                       'history_id': random.randint(1,
                                                                                                                    1000),
                                                                                       "user_id": user["user_id"]}
                    f.seek(0)
                    json.dump(users, f, indent=4)
                if request.session.get('is_admin', False):
                    return render(request, 'adminindex.html', {'history':history_data, 'feedback' : feedback, 'result': result,'pdf_true':0, 'username': request.session['username'], 'userdata': userdata})
                else:
                    return render(request, 'index.html', {'location_info': location_info,'history':user_history, 'result': result, 'pdf_true':0, 'username': request.session['username']})

        # Handling feedback submission
        elif 'feedback' in request.POST:
            feedback = request.POST['feedback']
            with open('database/users.json', 'r') as t:
                users = json.load(t)
                user = users.get(request.session['username'])
                t.seek(0)
            with open('database/feedback.json', 'r+') as f:
                users = json.load(f)
                current_timestamp = datetime.datetime.now().timestamp()
                readable_date = datetime.datetime.fromtimestamp(current_timestamp)
                readable_date_string = readable_date.strftime('%Y-%m-%d %H:%M:%S')
                users[request.session['username']+"_" + readable_date_string] = {'feedback': feedback, 'feedback_id':random.randint(1,1000), "user_id": user["user_id"] }
                f.seek(0)
                json.dump(users, f, indent=4)

            with open('database/users.json', 'r') as f:
                users = json.load(f)
                user = users.get(request.session['username'])
                id = user['user_id']
            with open('database/history.json', 'r') as f:
                history = json.load(f)
                temp2 = []
                for i in history:
                    dummy = []
                    dummy.append(history[i]['user_id'])
                    userandtime = i.split("_")
                    dummy.append(userandtime[1])
                    dummy.append(history[i]['description'])
                    temp2.append(dummy)
                user_history = []
                for i in temp2:
                    if id in i:
                        user_history.append(i)
                print(user_history)
            return render(request, 'index.html', {'history':user_history, 'feedback': 'Thank you for your feedback!', 'username': request.session['username']})

        # Handling logout
        elif 'logout' in request.POST:
            if request.session.get('is_logged_in', False):
                request.session.flush()
            return redirect('/')

