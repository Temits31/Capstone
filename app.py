from flask import Flask, render_template, request, jsonify, redirect, url_for, render_template_string, session,send_from_directory, flash
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, leave_room, send, emit
from PIL import Image
import mysql.connector
import base64
from inference import get_model
import supervision as sv
from sklearn.metrics import accuracy_score



import cv2
import os
import io
from geopy.geocoders import ArcGIS
from geopy.geocoders import Nominatim
from geopy.geocoders import OpenCage
from geopy.geocoders import get_geocoder_for_service

from datetime import datetime
import random


import requests

import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import random
import string




API_KEY = "5c9af440b34248e955e93d77520f9410"


lat = "15.3627"
lon = "120.8838"
BASE_URL = "https://api.openweathermap.org/data/2.5/weather?lat="+ lat + "&lon="+ lon +"&exclude=hourly,daily&appid="+ API_KEY


response = requests.get(BASE_URL).json()


connection = mysql.connector.connect(
    host='localhost',
    port='3306',
    database='new_caps',
    user='root',
    password=''
)

cursor = connection.cursor(buffered=True)

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'secret!'

socketio = SocketIO(app, cors_allowed_origins="*")

app.config['UPLOAD_FOLDER'] = r'C:\xampp\htdocs\backup capstone\xammp_projects\static\upload_folder'
ALLOWED_EXTENSIONS = {'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_random_code(length=6):
    letters_and_digits = string.ascii_uppercase + string.digits
    return ''.join(random.choice(letters_and_digits) for i in range(length))

@app.route('/register_un', methods=['GET', 'POST'])
def username():
    text = ''

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute('''SELECT * FROM tbl_user WHERE username = %s AND password = %s''', (username, password,))
        check= cursor.fetchall()

        if check:
            text = 'You already have an account.'
        else:
            # 7 is default - nagreregister palang 
            role_id = 7
            current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('INSERT INTO tbl_user (username,  role_id, created_at, password) VALUES (%s, %s, %s, %s)', (username, role_id, current_timestamp, password))
            connection.commit()
            cursor.execute('SELECT user_id FROM tbl_user ORDER BY user_id DESC LIMIT 1')
            user_id = cursor.fetchone()[0]
            return redirect(url_for('farmback', user_id = user_id))

    return render_template('register_un.html', text =text)

@app.route('/farmback', methods=['GET', 'POST'])
def farmback():

    user_id = request.args.get('user_id')



    print(user_id)



    if request.method == 'POST':
        role_id = request.form['role_id']
        user_id = request.form['user_id']
        


        cursor.execute('UPDATE tbl_user SET role_id = %s WHERE user_id = %s', (role_id, user_id))
        connection.commit()
        if role_id == '5':
            # 5 farmer nag reregister
            print(user_id)
            return redirect(url_for("register_farmer", user_id = user_id))
        elif role_id == '1':
            return redirect(url_for("register_backyard", user_id = user_id))
        else: 
            text = 'ERROR'
            return render_template("farmback.html", text=text)
    return render_template("farmback.html", user_id = user_id)

@app.route('/register_farmer', methods=['GET', 'POST'])
def register_farmer():
    user_id = request.args.get('user_id')
    print(user_id)
    if request.method == 'POST':
        user_id = request.form['user_id']
        
        fname = request.form['fname']
        mname = request.form['mname']
        lname = request.form['lname']
        province = request.form['province']
        city = request.form['city']
        brgy = request.form['brgy']
        strt_add = request.form['strt_add']
        cont_num = request.form['cont_num']
        cursor.execute('INSERT INTO user_details (fname, mname, lname, province, city, brgy, strt_add, cont_num, user_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)', 
                       (fname, mname, lname, province, city, brgy, strt_add, cont_num, user_id))
        connection.commit()
        return redirect(url_for('ask', user_id = user_id))
    return render_template('register_farmer.html', user_id = user_id)


@app.route('/register_backyard', methods=['GET', 'POST'])
def register_backyard():
    user_id = request.args.get('user_id')

    if request.method == 'POST':
        user_id = request.form['user_id']
        fname = request.form['fname']
        mname = request.form['mname']
        lname = request.form['lname']
        province = request.form['province']
        city = request.form['city']
        brgy = request.form['brgy']
        strt_add = request.form['strt_add']
        cont_num = request.form['cont_num']
        country = "Philippines"

        address = f"{brgy}, {city}, {province}, {country}"
        print(f"Geocoding address: {address}")


        cursor.execute("""INSERT INTO user_details (fname, mname, lname, province, city, brgy, strt_add, cont_num, user_id) 
        VALUES ( %s, %s, %s, %s, %s, %s,%s, %s, %s)""", (fname, mname, lname, province, city, brgy, strt_add, cont_num, user_id,))
        connection.commit()

        return render_template('login.html')
        

       
    return render_template('register_backyard.html', user_id=user_id)



def get_coords_and_disease_sql():
    cursor.execute('''SELECT f.latitude, f.longitude, COUNT(DISTINCT d.detection_id) AS disease_count
                    FROM farm f
                    LEFT JOIN detection d ON d.farm_id = f.farm_id
                    WHERE d.health_status_id IS NOT NULL
                    AND d.health_status_id != 8 
                    AND d.health_status_id != 9
                    GROUP BY f.latitude, f.longitude
                   ''')
    results = cursor.fetchall()
    
    if results:
        data = [
            {"latitude": float(row[0]), "longitude": float(row[1]), "disease_count": int(row[2])}
            for row in results
        ]
    else:
        data = []
    
    return data

@app.route('/map', methods=['GET', 'POST'])
def map():
    if 'id' in session:
        sid = session['id']

        coords_with_disease_count = get_coords_and_disease_sql()

        print(coords_with_disease_count)

        return render_template('map.html', coords=coords_with_disease_count)
    
    return redirect(url_for('login'))







@app.route('/ask', methods=['GET', 'POST'])
def ask():
    user_id = request.args.get('user_id')
    print('this is user id in ask', user_id)

    if request.method == 'POST':
        user_id = request.form['user_id']

        ask = int(request.form['ask'])
        print(ask)
        if ask == 1:
            # 6 farm owner sya
            cursor.execute('UPDATE tbl_user SET role_id = 6 WHERE user_id = %s', (user_id,))
            connection.commit()
           
            return redirect(url_for('register_farm', user_id = user_id))
        elif ask == 2:
            # 5 farmer lang
            cursor.execute('UPDATE tbl_user SET role_id = 5 WHERE user_id = %s', (user_id,))
            connection.commit()
            return redirect(url_for('nofarm', user_id = user_id))
    return render_template('ask.html', user_id = user_id)




@app.route('/nofarm', methods=['GET', 'POST'])
def nofarm():
    user_id = request.args.get('user_id')  # Get user_id from URL parameters
    farm_id = request.args.get('farm_id')  # Get farm_id from URL parameters

    if request.method == 'POST':
        farm_id = request.form['farm_id']  # Get farm_id from the submitted form
        user_id = request.form.get('user_id', user_id) 
        print('userid', user_id)

        if not user_id:  # Handles both None and empty string cases
            user_id = session.get('id')  # Safely get the user_id from session
            if user_id:
                print('User ID is in session:', user_id)
            else:
                print('User ID not found in session')

        return redirect(url_for('learnmore', user_id=user_id, farm_id=farm_id))  # Pass both IDs to the next route

    cursor.execute('SELECT * FROM farm')
    farm = cursor.fetchall()

    farm_with_images = []
    h_index = 0
    for f in farm:
        if f[9]:  
            h_index += 1
            binary_data = f[9]
            image_binary = base64.b64decode(binary_data)
            iodata = io.BytesIO(image_binary)
            image = Image.open(iodata)
            filename = f"{f[1]}_{h_index}.png" 

            file_path = os.path.join(r'C:\xampp\htdocs\backup capstone\xammp_projects\static\upload_folder', filename)
            image.save(file_path)
            new_fpath = f"../static/upload_folder/{filename}"
        else:
            new_fpath = None 

        farm_with_images.append(f + (new_fpath,))  

    return render_template('nofarm.html', farm=farm_with_images, user_id=user_id, farm_id=farm_id)

    


@app.route('/learnmore', methods=['GET', 'POST'])
def learnmore():

    farm_id = request.args.get('farm_id')
    user_id = request.args.get('user_id')

    print(f'Initial farm_id from GET: {farm_id}')
    print(f'Initial user_id from GET: {user_id}')

    if request.method == 'POST':
  
        farm_id = request.form.get('farm_id', farm_id)
        user_id = request.form.get('user_id', user_id)
        print(f'Updated farm_id from POST: {farm_id}')
        print(f'Updated user_id from POST: {user_id}')

        if 'id' in session: 
            user_id = session.get('id') 
            if user_id:
                print('User ID is in session:', user_id)
            else:
                print('User ID not found in session')


        if 'id' not in session:
            cursor.execute('UPDATE tbl_user SET role_id = 5 WHERE user_id = %s', (user_id,))
            connection.commit()
            print(f'Role updated for user_id: {user_id}')
        else:
            print('Session exists, skipping role update')

        cursor.execute('SELECT user_details_id FROM user_details WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        user_details_id = result[0] if result else None

        if user_details_id and farm_id:
            cursor.execute('SELECT uf.group_id FROM ud_farm uf WHERE uf.farm_id = %s', (farm_id,))
            result = cursor.fetchone()
            group_id = result[0] if result else None

            cursor.execute('INSERT INTO ud_farm (user_details_id, farm_id, status, group_id) VALUES (%s, %s, "member pending", %s)', 
                           (user_details_id, farm_id, group_id))
            connection.commit()

        return redirect(url_for('login'))

    cursor.execute('''SELECT farm_id, farm_name, province, city, brgy, strt_add, zip_code
                      FROM farm
                      WHERE farm_id = %s LIMIT 1''', (farm_id,))
    farm = cursor.fetchone()
    print('Farm data in learnmore:', farm)

    return render_template('learnmore.html', farm=farm, user_id=user_id, farm_id=farm_id)

        



@app.route('/register_farm', methods=['GET', 'POST'])
def register_farm():
    user_id = request.args.get('user_id')


    print(user_id)

    text = ''
    if request.method == 'POST': 
        user_id = request.form['user_id']
        print('user id sa POST', user_id)

        farm_name = request.form['farm_name']
        province = request.form['province']
        city = request.form['city']
        brgy = request.form['brgy']
        strt_add = request.form['strt_add']
        zip_code = request.form['zip_code']
        f_img = request.files['f_img']

        cursor.execute('SELECT user_details_id FROM user_details WHERE user_id = %s', (user_id,))
        user_details = cursor.fetchone()
        user_details_id = user_details[0]


        if f_img:
            f_img_binary = f_img.read()
            f_img_base = base64.b64encode(f_img_binary).decode('utf-8')
        else:
            f_img_base = None



        country = 'Philippines'
        address = f"{brgy}, {city}, {province}, {country}"
        print(f"Geocoding address: {address}")

        geolocator = Nominatim(user_agent="JOSHAPP")
        location = geolocator.geocode(address)

        if location:
            latitude = location.latitude
            longitude = location.longitude
            cursor.execute('INSERT INTO farm (farm_name, province, city, brgy, strt_add, zip_code, latitude, longitude, f_img, farm_status) VALUES (%s, %s, %s, %s, %s, %s, %s,%s, %s, "active")', 
                       (farm_name, province, city, brgy, strt_add, zip_code, latitude, longitude, f_img_base))
            connection.commit()
            cursor.execute('SELECT farm_id FROM farm ORDER BY farm_id DESC LIMIT 1')
            farm_id = cursor.fetchone()[0]



            collab_group_code = generate_random_code()

            cursor.execute("INSERT INTO tbl_group (group_code) values (%s)",(collab_group_code,))
            connection.commit()
            cursor.execute("SELECT group_id FROM tbl_group ORDER BY group_id DESC LIMIT 1")
            owner_group_id = cursor.fetchone()[0]

            cursor.execute('INSERT INTO ud_farm VALUES(NULL, %s, %s, "Owner", %s)', (user_details_id, farm_id, owner_group_id))
            connection.commit()
            print('THIS IS GROUP ID', owner_group_id)

            return redirect(url_for('login'))
            

        else:
            print("No geocoding results found.")
            text = 'Please Make sure the address is correct'


        
    return render_template('register_farm.html', user_id = user_id, text = text)


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'id' in session:
        sid = session['id']

        farm_info = []
        cursor.execute('SELECT u.username, ud.fname, ud.mname, ud.lname, ud.province, ud.city, ud.brgy, ud.strt_add FROM tbl_user u INNER JOIN user_details ud on ud.user_id = u.user_id WHERE u.user_id = %s', (sid,))
        info = cursor.fetchone()

        cursor.execute('''SELECT tr.role_name FROM tbl_role tr INNER JOIN tbl_user u on u.role_id = tr.role_id WHERE u.user_id = %s''',(sid,))
        role_name = cursor.fetchone()[0]

        if role_name in ['farm_owner', 'user_farmer']:
            cursor.execute('''SELECT f.farm_name, f.province, f.city, f.brgy, f.strt_add FROM farm f inner join ud_farm uf
                           on uf.farm_id = f.farm_id inner join user_details ud on ud.user_details_id = uf.user_details_id
                           WHERE ud.user_id = %s''',(sid,))
            farm_info = cursor.fetchall()




        return render_template('profile.html', info = info, farm_info = farm_info)
    




def kelvin_to_cs_fr(kelvin):
    cs = kelvin - 273.15

    fr = cs *(9/5) + 32
    return cs, fr



@app.route('/members', methods=['GET', 'POST'])
def members():
    if 'id' in session:
        sid = session['id']

        # Fetch user details
        cursor.execute('''
            SELECT u.user_id, u.username, 
            ud.user_details_id, ud.fname, ud.lname, ud.mname
            FROM tbl_user u 
            INNER JOIN user_details ud ON u.user_id = ud.user_id 
            WHERE u.user_id = %s
        ''', (sid,))
        user_details = cursor.fetchone()
        print('User details: ', user_details)

        # Fetch the status for the user's farms
        cursor.execute('''
            SELECT status
            FROM ud_farm 
            WHERE user_details_id = %s
        ''', (user_details[2],))
        status = cursor.fetchone()[0]
        print('Status: ', status)

        cursor.execute('''
            SELECT uf.farm_id
            FROM tbl_user u 
            INNER JOIN user_details ud ON u.user_id = ud.user_id 
            INNER JOIN ud_farm uf ON ud.user_details_id = uf.user_details_id 
            WHERE u.user_id = %s
        ''', (sid,))
        farms = cursor.fetchall()
        print('Farms associated with user: ', farms)

        all_members = []  # To store members from all farms

        for farm in farms:
            farm_id = farm[0]
            print('Processing farm id: ', farm_id)

            cursor.execute('''
                SELECT u.username, ud.fname, ud.mname, ud.lname, 
                       f.farm_name, uf.status, uf.group_id, uf.user_details_id
                FROM tbl_user u 
                INNER JOIN user_details ud ON u.user_id = ud.user_id 
                INNER JOIN ud_farm uf ON ud.user_details_id = uf.user_details_id 
                INNER JOIN farm f ON f.farm_id = uf.farm_id
                WHERE uf.farm_id = %s
            ''', (farm_id,))
            members = cursor.fetchall()

            if members:
                all_members.extend(members)  # Collect all members across farms
            
        group_id = None

        if request.method == 'POST':
            user_details_id = request.form['user_details_id']
            permission = request.form['permission']

            for member in all_members:
                print('member[7] (user_details_id): ', member[7])

                if str(member[7]) == user_details_id:  # Ensure comparison is consistent
                    group_id = member[6]
                    break

            print('POST: group id: ', group_id, 'permission: ', permission, ' user_details_id: ', user_details_id)

            if group_id is None:
                print("Error: Group ID is None, possible data mismatch.")

            if permission == 'accept' and group_id:
                cursor.execute('''
                    UPDATE ud_farm SET status = "member", group_id = %s WHERE user_details_id = %s
                ''', (group_id, user_details_id,))
                connection.commit()


                cursor.execute('''
                    SELECT u.user_id, u.role_id FROM user_details ud 
                    INNER JOIN tbl_user u ON ud.user_id = u.user_id 
                    WHERE user_details_id = %s
                ''', (user_details_id,))
                join_2 = cursor.fetchone()

                if join_2:
                    cursor.execute('UPDATE tbl_role SET role_name = "user_farmer" WHERE role_id = %s', (join_2[1],))
                    connection.commit()

            elif permission == 'reject':
                cursor.execute('UPDATE ud_farm SET status = "rejected" WHERE user_details_id = %s', (user_details_id,))
                connection.commit()

                cursor.execute('''
                    SELECT u.user_id, u.role_id FROM user_details ud 
                    INNER JOIN tbl_user u ON ud.user_id = u.user_id 
                    WHERE user_details_id = %s
                ''', (user_details_id,))
                join_2 = cursor.fetchone()

                if join_2:
                    cursor.execute('UPDATE tbl_role SET role_name = "rejected_farmer" WHERE role_id = %s', (join_2[1],))
                    connection.commit()

        return render_template('members.html', members=all_members, status=status, group_id=group_id)


@app.route('/admin/update_farm_status', methods=['GET', 'POST'])
def update_farm_status():
    if 'id' in session: 
        if request.method == 'POST':
            farm_id = request.form['farm_id']
            farm_status = request.form['farm_status']

            print('farm_id: ',farm_id)
            
            cursor.execute('''UPDATE farm 
                              SET farm_status = %s 
                              WHERE farm_id = %s''', (farm_status, farm_id))
            connection.commit()
            
            flash(f'Farm ID {farm_id} status updated to {farm_status}.', 'success')
            return redirect(url_for('update_farm_status'))

        # Fetch all farms for display
        cursor.execute('''SELECT farm_id, farm_name, farm_status FROM farm''')
        farms = cursor.fetchall()

        return render_template('admin_farm_status.html', farms=farms)
    else:
        flash('You must be an admin to access this page.', 'danger')
        return redirect(url_for('login'))

@app.route('/admin_test', methods=['GET', 'POST'])
def admin_test():
    if 'id' in session:
        sid = session['id']
        cursor.execute("SELECT username FROM tbl_user WHERE user_id = %s", (sid,))
        result = cursor.fetchone()
        
        image_url = None
        formatted_labels = None

        if result:
            username = result[0]
        else:
            return redirect(url_for('login'))

        if request.method == 'POST':
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = file.filename
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                image = Image.open(file_path)
                model = get_model(model_id="calamansi-0bxbw/3")

                results = model.infer(image)
                detections = sv.Detections.from_inference(results[0].dict(by_alias=True, exclude_none=True))

                labels = [f"{class_name}" for class_name in zip(detections['class_name'])]

                bounding_box_annotator = sv.BoundingBoxAnnotator()
                label_annotator = sv.LabelAnnotator()

                annotated_image = bounding_box_annotator.annotate(scene=image, detections=detections)
                annotated_image = label_annotator.annotate(scene=annotated_image, detections=detections, labels=labels)

                sv.plot_image(annotated_image)

                formatted_labels = [label.replace("('", "").replace("',)", "") for label in labels]

                image_url = url_for('uploaded_file', filename=filename)


                if 'Mites Infestation' in formatted_labels:
                    formatted_labels = formatted_labels[1]
                else:
                    formatted_labels = "None Detected"

        return render_template('admin_test.html', username=username, image_url=image_url, formatted_labels=formatted_labels)
    else:
        return redirect(url_for('login'))




@app.route('/dashboard_cp', methods=['GET', 'POST'])
def dashboard_cp():
    if 'id' in session:
        sid = session['id']

        if 'farm_id' in session:
            farm_id = session['farm_id']
        else:
            farm_id = None

        health_status = ''
        label = ''
        cursor.execute("SELECT username FROM tbl_user WHERE user_id = %s", (sid,))
        result = cursor.fetchone()
        
        if result:
            username = result[0]
        else:
            return redirect(url_for('login'))

        temp_kelv = response['main']['temp']
        temp_cs, temp_fr = kelvin_to_cs_fr(temp_kelv)
        weather = response['weather'][0]['description']
        icon = response['weather'][0]['icon']
        icon_url = f"http://openweathermap.org/img/wn/{icon}@2x.png"

        image_url = None
        formatted_labels = None
        members = []

        cursor.execute('SELECT u.user_id, u.role_id, tr.role_id, tr.role_name FROM tbl_user u INNER JOIN tbl_role tr ON u.role_id = tr.role_id WHERE u.user_id = %s', (sid,))
        result = cursor.fetchone()

        

        status = None
        
        if result:
            role_name = result[3]
        else:
            role_name = None

        if role_name in ['user_farmer', 'farm_owner']:
            cursor.execute('''SELECT u.user_id, u.username, 
                              ud.user_details_id, ud.fname, ud.lname, ud.mname,
                              uf.farm_id, uf.status
                              FROM tbl_user u 
                              INNER JOIN user_details ud ON u.user_id = ud.user_id 
                              INNER JOIN ud_farm uf ON ud.user_details_id = uf.user_details_id 
                              WHERE u.user_id = %s''', (sid,))
            result = cursor.fetchone()

            
            print ('Farm_id sa session: ', farm_id)
            
                    
            if result is not None:
                if result[7]:
                    status = result[7]
                else:
                    status = None
            else:
                status = None


            
            
            
            print(status)
            

            cursor.execute("""SELECT count(detection_id) FROM detection d
                            INNER JOIN tbl_user u ON d.user_id = u.user_id
                            INNER JOIN user_details ud ON ud.user_id = u.user_id
                            INNER JOIN ud_farm uf ON uf.user_details_id = ud.user_details_id
                            WHERE NOT d.health_status_id = 8 AND NOT d.health_status_id = 9 AND uf.farm_id = %s AND u.user_id =%s""",(farm_id, sid))
            ct = cursor.fetchone()

            cursor.execute("""SELECT count(detection_id), d.health_status_id, hs.status_name FROM detection d
                            INNER JOIN tbl_user u ON d.user_id = u.user_id
                            INNER JOIN user_details ud ON ud.user_id = u.user_id
                            INNER JOIN ud_farm uf ON uf.user_details_id = ud.user_details_id
                            inner join health_status hs ON d.health_status_id = hs.health_status_id
                            WHERE NOT hs.status_name = 'None Detected' AND NOT hs.status_name = 'healthy' AND uf.farm_id = %s AND u.user_id =%s
                            group by d.health_status_id
                            order by D.health_status_id DESC""",(farm_id, sid,))
            max = cursor.fetchone()

            
            



        else:
            cursor.execute("""SELECT count(detection_id) FROM detection d
                            INNER JOIN tbl_user u ON d.user_id = u.user_id
                            INNER JOIN user_details ud ON ud.user_id = u.user_id 
                           WHERE NOT d.health_status_id = 8 AND NOT d.health_status_id = 9 AND u.user_id = %s""",(sid,))
            ct = cursor.fetchone()

            cursor.execute("""SELECT count(detection_id), d.health_status_id, hs.status_name FROM detection d
                            INNER JOIN tbl_user u ON d.user_id = u.user_id
                            INNER JOIN user_details ud ON ud.user_id = u.user_id
                            inner join health_status hs ON d.health_status_id = hs.health_status_id
                            WHERE NOT d.health_status_id = 8 AND NOT hs.status_name = 'healthy' AND u.user_id =%s 
                            group by d.health_status_id
                            order by D.health_status_id DESC""",( sid,))
            max = cursor.fetchone()
            
            join = None
            
        if max:

            max = max[2]
        else:
            max =''
        
        
        results = []

        if request.method == 'POST':
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = file.filename
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                image = Image.open(file_path)
                new_size = (500, 500)
                resized_image = image.resize(new_size)
                

                buffered = io.BytesIO()
                resized_image.save(buffered, format="PNG")
                image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

                model = get_model(model_id="calamansi-0bxbw/3")
                results = model.infer(image)
                detections = sv.Detections.from_inference(results[0].dict(by_alias=True, exclude_none=True))

                labels = [f"{class_name}" for class_name in zip(detections['class_name'])]

                bounding_box_annotator = sv.BoxAnnotator()
                label_annotator = sv.LabelAnnotator()

                annotated_image = bounding_box_annotator.annotate(scene=image, detections=detections)
                annotated_image = label_annotator.annotate(scene=annotated_image, detections=detections, labels=labels)

                sv.plot_image(annotated_image)

                annotated_image_filename = f"annotated_{filename}"
                annotated_image_path = os.path.join(app.config['UPLOAD_FOLDER'], annotated_image_filename)
                annotated_image.save(annotated_image_path)  # Save the annotated image



                formatted_labels = [label.replace("('", "").replace("',)", "") for label in labels]

                image_url = url_for('uploaded_file', filename=annotated_image_filename)

                health_status_mapping = {
                    'black spots': 'black spots',
                    'greening': 'greening',
                    'scab': 'scab',
                    'thrips': 'thrips',
                    'heathy': 'healthy',
                    'None Detected': 'None Detected' 
                }

                print("Formatted labels: ", formatted_labels)

                if not formatted_labels:
                    label = 'None Detected'
                else:
                    label = formatted_labels[0]





                processed_labels = set()  # A set to track processed labels
                results = []  # List to store final results

                for label in formatted_labels:
                    if label in health_status_mapping:
                        health_status_name = health_status_mapping[label]
                        print(f'Health Status name: {health_status_name}')

                        if label == 'heathy':
                            label = 'healthy'

                        cursor.execute('SELECT cause, solution, description, health_status_id FROM health_status WHERE status_name = %s', (health_status_name,))
                        health_status = cursor.fetchone()

                        print('health status', health_status)
                        if health_status:
                            print(f"Health Status fetched: {health_status}")

                            # Insert into `detection` table
                            cursor.execute("INSERT INTO detection (user_id, img, prediction, health_status_id, farm_id) VALUES (%s, %s, %s, %s, %s)", 
                             (sid, image_base64, label, health_status[3], farm_id))

                            connection.commit()

                            cursor.execute('SELECT detection_id FROM detection ORDER BY detection_id DESC LIMIT 1')
                            detection_id = cursor.fetchone()[0]

                            time_recorded = datetime.now().strftime('%H:%M:%S')
                            date_recorded = datetime.now().strftime('%Y-%m-%d')
                            temperature = f"{temp_cs}°C / {temp_fr}°F"

                            cursor.execute('INSERT INTO history (date_recorded, time_recorded, detection_id, weather_temp, weather_status) VALUES (%s, %s, %s, %s, %s)',
                                        (date_recorded, time_recorded, detection_id, temperature, weather))
                            connection.commit()

                            if label not in processed_labels:
                                result = {
                                    'label': label,
                                    'description': health_status[2],
                                    'cause': health_status[0],
                                    'solution': health_status[1]
                                }

                                results.append(result)

                                processed_labels.add(label)
                        else:
                            print(f"No health status found for {health_status_name}")


        return render_template('dashboard_cp.html', username=username,count = ct[0], status = status,
                               health_status = health_status, 
                               temp_cs=int(temp_cs), temp_fr=int(temp_fr), weather=weather, icon=icon, icon_url=icon_url, 
                               image_url=image_url, formatted_labels=label, max = max,
                               members=members, user_type = role_name, results = results )
    else:
        return redirect(url_for('login'))
    

@app.route('/check_status', methods=['GET'])
def check_status():
    if 'id' in session:
        sid = session['id']

        cursor.execute('''
            SELECT status FROM ud_farm 
            WHERE user_details_id = (SELECT user_details_id FROM user_details WHERE user_id = %s)
        ''', (sid,))
        current_status = cursor.fetchone()
        print('this is current status', current_status)

        if current_status:
            return jsonify({'status': current_status[0]})  # Returning the current status
        else:
            return jsonify({'status': 'unknown'})
    else:
        return jsonify({'status': 'not_logged_in'}), 401
    





@app.route('/check_new_members', methods=['GET'])
def check_new_members():
    if 'farm_id' in session:
        farm_id = session['farm_id']

        cursor.execute('''
            SELECT u.username, ud.fname, ud.lname, uf.status, u.created_at
            FROM tbl_user u
            INNER JOIN user_details ud ON u.user_id = ud.user_id
            INNER JOIN ud_farm uf ON uf.user_details_id = ud.user_details_id
            WHERE uf.farm_id = %s
            ORDER BY u.created_at DESC LIMIT 1
        ''', (farm_id,))
        new_member = cursor.fetchone()
        print('this is new member', new_member)

        if new_member:
            member_name = f"{new_member[1]} {new_member[2]}"
            return jsonify({'new_member': member_name, 'status': new_member[3]})
        else:
            return jsonify({'new_member': None})

    return jsonify({'error': 'Not authorized'}), 401



@app.route('/history', methods=['GET', 'POST'])
def history():
    if 'id' in session:
        sid = session['id']
        cursor.execute("SELECT username FROM tbl_user WHERE user_id = %s", (sid,))
        username_result = cursor.fetchone()


        cursor.execute('SELECT u.user_id, u.role_id, tr.role_id, tr.role_name FROM tbl_user u INNER JOIN tbl_role tr ON u.role_id = tr.role_id WHERE u.user_id = %s', (sid,))
        result = cursor.fetchone()
        
        status = None
        
        if result:
            role_name = result[3]
        else:
            role_name = None
        
        if role_name in ['user_farmer', 'farm_owner']:
            cursor.execute('''SELECT u.user_id, u.username, 
                              ud.user_details_id, ud.fname, ud.lname, ud.mname,
                              uf.farm_id, uf.status
                              FROM tbl_user u 
                              INNER JOIN user_details ud ON u.user_id = ud.user_id 
                              INNER JOIN ud_farm uf ON ud.user_details_id = uf.user_details_id 
                              WHERE u.user_id = %s''', (sid,))
            result = cursor.fetchone()

            farm_id = result[6]
            status = result[7]

            print('Status: ', status, 'role name: ', role_name)

        if username_result:
            username = username_result[0]
        else:
            username = "Unknown User"

        cursor.execute("""SELECT d.img, d.prediction, h.weather_status, h.weather_temp,
                        h.date_recorded, h.time_recorded  
                        FROM history h 
                        INNER JOIN detection d ON d.detection_id = h.detection_id 
                        INNER JOIN tbl_user u ON u.user_id = d.user_id 
                        WHERE u.user_id = %s""", (sid,))
        h_records = cursor.fetchall()
        file_path = None






        history = []
        h_index = 0
        for record in h_records:
            h_index+=1
            image_binary = record[0]
            binary_data = base64.b64decode(image_binary)
            image = Image.open(io.BytesIO(binary_data))
            filename = f"file{h_index}.png"
            
            file_path = os.path.join( r'C:\xampp\htdocs\backup capstone\xammp_projects\static\upload_folder', filename)
            image.save(file_path)
            new_fpath = "..\\static\\upload_folder\\" + filename
            history.append({
                'image': new_fpath,
                'prediction': record[1],
                'weather_status': record[2],
                'weather_temp': record[3],
                'date_recorded': record[4],
                'time_recorded': record[5]
            })

        return render_template('history.html', user_id=sid, username=username, history=history, file_path = file_path, user_type = role_name, status = status)
    else:
        return redirect(url_for('login'))








    
@app.route('/add_farm', methods=['GET', 'POST'])
def add_farm():
    if 'id' in session:
        user_id = session['id']
        text = ''


        cursor.execute('''SELECT ud.user_details_id, uf.status FROM user_details ud 
                           inner join tbl_user u on u.user_id = ud.user_id
                           inner join ud_farm uf on uf.user_details_id = ud.user_details_id
                            WHERE u.user_id = %s''', (user_id,))
        res = cursor.fetchone()
        user_details_id = res[0]
        status = res[1]
        print(status)

        if request.method == 'POST':

            farm_name = request.form['farm_name']
            province = request.form['province']
            city = request.form['city']
            brgy = request.form['brgy']
            strt_add = request.form['strt_add']
            zip_code = request.form['zip_code']
            f_img = request.files['f_img']


            
            if f_img:
                f_img_binary = f_img.read()
                f_img_base = base64.b64encode(f_img_binary).decode('utf-8')
            else:
                f_img_base = None



            country = 'Philippines'
            address = f"{brgy}, {city}, {province}, {country}"
            print(f"Geocoding address: {address}")

            geolocator = Nominatim(user_agent="JOSHAPP")
            location = geolocator.geocode(address)
            print(location)

            if location:
                latitude = location.latitude
                longitude = location.longitude
                cursor.execute('INSERT INTO farm (farm_name, province, city, brgy, strt_add, zip_code, latitude, longitude, f_img, farm_status) VALUES (%s, %s, %s, %s, %s, %s, %s,%s, %s, "active")', 
                        (farm_name, province, city, brgy, strt_add, zip_code, latitude, longitude, f_img_base))
                connection.commit()
                cursor.execute('SELECT farm_id FROM farm ORDER BY farm_id DESC LIMIT 1')
                farm_id = cursor.fetchone()[0]
                group_code = generate_random_code()
                cursor.execute('INSERT INTO tbl_group (group_code) VALUES( %s)', (group_code,))
                connection.commit()
                cursor.execute('SELECT g.group_id FROM tbl_group g ORDER BY g.group_id DESC LIMIT 1')
                group = cursor.fetchone()
                group_id = group[0]
                print('new group code', group_code)
                cursor.execute('INSERT INTO ud_farm VALUES(NULL, %s, %s, "Owner", %s)', (user_details_id, farm_id, group_id,))
                connection.commit()
                
                text= 'Farm Added'
            else:
                text = f'No Location {address}'

        return render_template('add_farm.html', user_id = user_id, text=text, status = status)
    else:
        return redirect(url_for('login'))
        


@app.route('/rooms', methods=['GET', 'POST'])
def rooms():
    if 'id' in session:
        user_id = session['id']
        username = session['username']

        cursor.execute('''SELECT g.group_code, f.farm_name
                          FROM tbl_user u
                          INNER JOIN user_details ud ON u.user_id = ud.user_id
                          INNER JOIN ud_farm uf ON ud.user_details_id = uf.user_details_id
                       inner join farm f on f.farm_id = uf.farm_id
                          INNER JOIN tbl_group g ON uf.group_id = g.group_id
                          WHERE u.user_id = %s''', (user_id,))
        rooms = cursor.fetchall()

        cursor.execute('''SELECT tr.role_name, uf.status FROM tbl_role tr
                       inner join tbl_user u on u.role_id = tr.role_id
                       inner join user_details ud on ud.user_id = u.user_id
                       inner join ud_farm uf on uf.user_details_id = ud.user_details_id
                       WHERE u.user_id = %s''',(user_id,))
        ress = cursor.fetchone()
        role_name = ress[0]
        status = ress[1]

        selected_room = None
        sanitized_messages = []
        ud_farm_id = None

        if request.method == 'POST':
            selected_room = request.form.get('room')
            if selected_room:
                cursor.execute('''SELECT u.username, m.message, m.timestamp
                                  FROM tbl_user u 
                                  INNER JOIN user_details ud ON u.user_id = ud.user_id 
                                  INNER JOIN ud_farm uf ON ud.user_details_id = uf.user_details_id 
                                  INNER JOIN tbl_message m ON m.ud_farm_id = uf.ud_farm_id
                                  INNER JOIN tbl_group g ON uf.group_id = g.group_id
                                  WHERE g.group_code = %s''', (selected_room,))
                messages = cursor.fetchall()

                sanitized_messages = []
                for msg in messages:
                    username, message, timestamp = msg
                    if contains_inappropriate_content(message):
                        sanitized_message = ("This message has been flagged for inappropriate content.",)
                    else:
                        sanitized_message = (message,)
                    
                    sanitized_messages.append((username, sanitized_message[0], timestamp))
                    print(sanitized_messages)


                cursor.execute('''SELECT u.username, ud.fname, ud.lname, uf.farm_id, ud.user_details_id
                                  FROM tbl_user u 
                                  INNER JOIN user_details ud ON u.user_id = ud.user_id 
                                  INNER JOIN ud_farm uf ON uf.user_details_id = ud.user_details_id
                                  WHERE u.user_id = %s''', (user_id,))
                user = cursor.fetchone()

                cursor.execute('''SELECT uf.ud_farm_id ,g.group_id
                                  FROM tbl_group g
                                  INNER JOIN ud_farm uf ON uf.group_id = g.group_id
                                  INNER JOIN user_details ud ON uf.user_details_id = ud.user_details_id
                                  WHERE g.group_code = %s AND ud.user_details_id = %s ''', 
                               (selected_room, user[4]))
                res = cursor.fetchone()
                print(res)
                if res:
                    ud_farm_id = res[0]

        return render_template('rooms.html', rooms=rooms, selected_room=selected_room, messages=sanitized_messages, username=username, ud_farm_id=ud_farm_id
                               ,user_type = role_name,status = status)

    return redirect(url_for('login'))





@app.route('/chat/<room>')
def chat(room):
    if 'id' in session:
        user_id = session['id']
        
        cursor.execute('''SELECT u.username, ud.fname, ud.lname, uf.farm_id, ud.user_details_id
                          FROM tbl_user u 
                          INNER JOIN user_details ud ON u.user_id = ud.user_id 
                        inner join ud_farm uf on uf.user_details_id = ud.user_details_id
                          WHERE u.user_id = %s''', (user_id,))
        user = cursor.fetchone()
        print(user)

        cursor.execute('''SELECT uf.ud_farm_id ,g.group_id
                              FROM tbl_group g
                       inner join ud_farm uf on uf.group_id = g.group_id
                       inner join user_details ud on uf.user_details_id = ud.user_details_id
                              WHERE g.group_code = %s and ud.user_details_id = %s ''', (room, user[4], ))
        res = cursor.fetchone()
        ud_farm_id = res[0]



        
        
        if user:
            username = user[0]
            full_name = f"{user[1]} {user[2]}"
            
            cursor.execute('''SELECT u.username, m.message, m.timestamp
                                    FROM tbl_user u 
                                    INNER JOIN user_details ud ON u.user_id = ud.user_id 
                                    INNER JOIN ud_farm uf ON ud.user_details_id = uf.user_details_id 
                                    INNER JOIN tbl_message m ON m.ud_farm_id = uf.ud_farm_id
                                    INNER JOIN tbl_group g ON uf.group_id = g.group_id
                                    WHERE g.group_code = %s
                              ''', (room,))
            messages = cursor.fetchall()
            


            return render_template('chat.html', username=username, full_name=full_name, room=room, ud_farm_id=ud_farm_id, messages=messages)
    
    return redirect(url_for('login'))



@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    send({"username": username, "msg": "has entered the room", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, to=room)

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    send({"username": username, "msg": "has left the room", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, to=room)


inappropriate_words = ['tite', 'burat', 'puke','pokpok','pepe', 'bilat', 'putangina']

def contains_inappropriate_content(message):
    for word in inappropriate_words:
        if word.lower() in message.lower():
            return True
    return False

@socketio.on('message')
def handle_message(data):
    message = data['msg']
    room = data['room']
    ud_farm_id = data['ud_farm_id']
    data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if contains_inappropriate_content(message):
        data['msg'] = "This message has been flagged for inappropriate content."
        message = data['msg']

    cursor.execute('INSERT INTO tbl_message (message, timestamp, ud_farm_id) VALUES (%s, %s, %s)', 
                   (message, data['timestamp'], ud_farm_id ))
    connection.commit()

    send({'msg': data['msg'], 'username': data['username'], 'timestamp': data['timestamp']}, to=room, broadcast=True)




@app.route('/farm', methods=['GET', 'POST'])
def farm():
    if 'id' in session:
        sid = session['id']
        role_id = session.get('role_id', None)

        cursor.execute('''
            SELECT f.farm_id, f.farm_name, 
                   COUNT(d.detection_id) AS detection_count
            FROM ud_farm uf
            INNER JOIN user_details ud ON ud.user_details_id = uf.user_details_id
            INNER JOIN tbl_user u ON u.user_id = ud.user_id
            INNER JOIN farm f ON uf.farm_id = f.farm_id
            LEFT JOIN detection d ON f.farm_id = d.farm_id
            WHERE u.user_id = %s
            GROUP BY f.farm_id
        ''', (sid,))
        
        farms = cursor.fetchall()

        if not farms:
            return "No farms found for this user.", 404

     
        if request.method == 'POST':
            farm_id = request.form['farm_id']
            session['farm_id'] = farm_id  
            print(f"Selected farm_id: {session['farm_id']}")

            return redirect(url_for('dashboard_cp')) 
        else:
            farm_id = farms[0][0]  
            session['farm_id'] = farm_id
            print(f"Default farm_id: {farm_id}")

       
        return render_template('farm.html', farms=farms, role_id=role_id)

    else:
        return redirect(url_for('login'))  





@app.route('/leave_farm', methods=['POST'])
def leave_farm():
    if 'id' in session:
        sid = session['id']
        farm_id = request.form['farm_id']

        # Get role ID to check if the user is a farmer or farm owner
        cursor.execute('SELECT role_id FROM tbl_user WHERE user_id = %s', (sid,))
        role_id = cursor.fetchone()[0]

        # Farmer role (role_id = 5)
        if role_id == 5:
            cursor.execute('''
                DELETE FROM ud_farm 
                WHERE user_details_id = (SELECT user_details_id FROM user_details WHERE user_id = %s) 
                AND farm_id = %s
            ''', (sid, farm_id))
            connection.commit()

            flash('You have successfully left the farm.', 'success')
        
        # Farm Owner role (role_id = 6)
        elif role_id == 6:
            reason = request.form['reason']

            if reason:
                
                cursor.execute('''
                    DELETE m FROM tbl_message m INNER JOIN ud_farm uf ON m.ud_farm_id = uf.ud_farm_id
                    WHERE uf.farm_id = %s
                ''', (farm_id,))
                connection.commit()
                cursor.execute('''
                    DELETE FROM ud_farm 
                    WHERE farm_id = %s
                ''', (farm_id,))
                connection.commit()


                cursor.execute('''UPDATE farm  SET farm_status ="pending" WHERE farm_id = %s''',(farm_id,))
                connection.commit()



                flash('You have successfully deleted the farm. All associated farmers have been removed.', 'success')
            else:
                flash('You must provide a reason to delete the farm.', 'danger')

        return redirect(url_for('farm'))
    else:
        return redirect(url_for('login'))




@app.route('/adminfarm', methods=['GET', 'POST'])
def adminfarm():
    if 'id' in session:
        sid = session['id']
        
        cursor.execute('''SELECT f.farm_id, f.farm_name, f.f_img FROM farm f''')
        farms = cursor.fetchall()

        farm_with_images = []
        h_index = 0  # Index to differentiate multiple images of the same farm

        for f in farms:
            farm_id = f[0]
            farm_name = f[1]
            farm_img_binary = f[2] 

            if farm_img_binary:  # If there's an image
                h_index += 1
                image_binary = base64.b64decode(farm_img_binary)
                iodata = io.BytesIO(image_binary)
                image = Image.open(iodata)

                filename = f"{farm_name}_{h_index}.png"
                file_path = os.path.join(r'C:\xampp\htdocs\backup capstone\xammp_projects\static\upload_folder', filename)
                image.save(file_path)

                image_path = f"../static/upload_folder/{filename}"
            else:
                image_path = None  # No image available

            farm_with_images.append((farm_id, farm_name, image_path))

        return render_template('adminfarm.html', farms=farm_with_images)

    else:
        return redirect(url_for('login'))











@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def index():


    

    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    text = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT * FROM tbl_user WHERE username = %s AND password = %s", (username, password,))
        user = cursor.fetchone()


        if user:
            if user and user[5] == password:
                session['loggedin'] = True
                session['id'] = user[0]
                session['username'] = user[1]
                session['role_id'] = user[2]

                if str(user[2]) == '6':
                    return redirect(url_for('farm'))
                elif str(user[2]) == '2':
                    session['admin'] = True
                    return redirect(url_for('admin_dashboard'))
                elif str(user[2]) == '1':
                    return redirect(url_for('dashboard_cp'))
                elif str(user[2]) == '5':
                    return redirect(url_for('farm'))
            else:
                text = 'Incorrect user credentials!'
        else:
            text = 'User not found!'

    return render_template('login.html', text=text)


@app.route('/admin', methods=['GET'])
def admin_dashboard():
    if 'id' in session:
        sid = session['id']
        cursor.execute("SELECT role_id FROM tbl_user WHERE user_id = %s", (sid,))
        role_id = cursor.fetchone()[0]

        if role_id == 2: 
            cursor.execute('''SELECT u.username, ud.fname, ud.lname, ud.mname, r.role_name FROM tbl_user u JOIN tbl_role r ON u.role_id = r.role_id 
                           inner join user_details ud on u.user_id = ud.user_id ''')
            users = cursor.fetchall()

            cursor.execute('''SELECT u.username, f.farm_name, uf.status, f.province, f.city, f.brgy, f.strt_add FROM tbl_user u
                           inner join user_details ud on u.user_id = ud.user_id 
                           inner join ud_farm uf on uf.ud_farm_id = ud.user_details_id
                           inner join farm f on uf.farm_id = f.farm_id''')
            farms = cursor.fetchall()

            

            cursor.execute('SELECT COUNT(user_id) FROM tbl_user WHERE role_id NOT IN (2)')
            total_users = str(cursor.fetchone()[0])

            total_users = total_users.translate(str.maketrans('', '', '()[]'))

            cursor.execute('SELECT COUNT(user_id) FROM tbl_user WHERE role_id = 6')
            total_farmer =int(cursor.fetchone()[0])

            cursor.execute('SELECT COUNT(user_id) FROM tbl_user WHERE role_id = 1')
            total_backyard = int(cursor.fetchone()[0])


            data = {
                'labels': ['Farmers', 'Backyard'],
                'datasets': [{
                    'label': 'Number of Users',
                    'backgroundColor': ['rgba(255, 99, 132, 0.2)', 'rgba(54, 162, 235, 0.2)'],
                    'borderColor': ['rgba(255, 99, 132, 1)', 'rgba(54, 162, 235, 1)'],
                    'borderWidth': 1,
                    'data': [total_farmer, total_backyard]
                }]
            }




           


            return render_template('admin_dashboard.html', users=users, chart_data=data, total_users = total_users, farms = farms)
        else:
            return "Access denied", 403
    else:
        return redirect(url_for('login'))
    

@app.route('/admin_update', methods=['POST'])
def admin_update():
    if 'admin' in session:
        user_id = request.form['user_id']
        user_details_id = request.form['user_details_id']
        username = request.form['username']
        password = request.form['password']
        fname = request.form['fname']
        mname = request.form['mname']
        lname = request.form['lname']
        province = request.form['province']
        city = request.form['city']
        brgy = request.form['brgy']
        strt_add = request.form['strt_add']
        cont_num = request.form['cont_num']

        # Update tbl_user
        cursor.execute('''
            UPDATE tbl_user
            SET username = %s, password = %s
            WHERE user_id = %s
        ''', (username, password, user_id))

        # Update user_details
        cursor.execute('''
            UPDATE user_details
            SET fname = %s, mname = %s, lname = %s, province = %s, city = %s, brgy = %s, strt_add = %s, cont_num = %s
            WHERE user_details_id = %s
        ''', (fname, mname, lname, province, city, brgy, strt_add, cont_num, user_details_id))

        connection.commit()
        text = ('User updated successfully!')
        return redirect(url_for('admin_crud' , text = text))
    else:
        return redirect(url_for('login'))

@app.route('/admin_delete', methods=['POST'])
def admin_delete():
    if 'admin' in session:
        user_id = request.form['user_id']
        user_details_id = request.form['user_details_id']


        cursor.execute('''SELECT uf.user_details_id FROM ud_farm uf INNER JOIN user_details ud on uf.user_details_id = ud.user_details_id
        INNER JOIN tbl_user u on u.user_id = ud.user_id WHERE u.user_id = %s''', (user_id,))
        check_farm = cursor.fetchone()

        print(check_farm)

        if check_farm:
            cursor.execute('''
                    DELETE m FROM tbl_message m INNER JOIN ud_farm uf ON m.ud_farm_id = uf.ud_farm_id
                    WHERE uf.user_details_id = %s
                ''', (user_details_id,))
            connection.commit()
            cursor.execute('DELETE FROM ud_farm WHERE user_details_id = %s', (user_details_id,))
            connection.commit()




        cursor.execute('DELETE FROM user_details WHERE user_id = %s', (user_id,))
        

        # Delete from tbl_user
        cursor.execute('DELETE FROM tbl_user WHERE user_id = %s', (user_id,))

        connection.commit()
        text = ('User deleted successfully!')
        return render_template('admin_crud.html', text = text)

    else:
        return redirect(url_for('login'))


@app.route('/admin_crud', methods=['GET', 'POST'])
def admin_crud():
    if 'admin' in session:

        cursor.execute('''SELECT u.username, u.password, ud.fname, ud.mname, ud.lname, ud.province, ud.city, ud.brgy, ud.strt_add, ud.cont_num, u.user_id, ud.user_details_id
        FROM tbl_user u INNER JOIN user_details ud ON ud.user_id = u.user_id
        ''')
        results = cursor.fetchall()

        text = request.args.get('text', None)

        return render_template('admin_crud.html', results = results, text = text)
    else:
        return redirect(url_for('login')) 



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))




if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
